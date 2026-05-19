# Round 3: 流水线设计与指令级并行 — 研究结果

> 创建时间: 2026-05-19
> 来源: ISCA 2020, EET China, Zellic Analysis, ProgrammerSought, Groq Blog

---

## 1. 流水线架构概览

### 1.1 空间-时间双维度执行模型

Groq TSP 的流水线与传统流水线有本质不同——它是**二维的**：

```
时间维度 (Y 方向 — 指令流动):
  SuperLane 0  ← 指令在此注入
       ↓ (每 cycle 推进 1 个 SuperLane)
  SuperLane 1
       ↓
  ...
       ↓
  SuperLane 19

空间维度 (X 方向 — 数据流动):
  MXM → SXM → MEM → VXM → MEM → SXM → MXM
  ← 数据在相邻功能切片间以 1 cycle 一跳传播
```

**关键洞察**：当指令和数据在某个功能单元"相遇"时，执行发生。

### 1.2 SuperLane 组织

TSP 被划分为 **20 个 SuperLane**。每个 SuperLane 包含：

```
一个 SuperLane (水平行) 的结构:
┌──────┬──────┬──────┬──────┬──────┬──────┬──────┐
│ MXM  │ SXM  │ MEM  │ VXM  │ MEM  │ SXM  │ MXM  │
│ (x2) │      │ (x2) │      │      │      │ (x2) │
└──────┴──────┴──────┴──────┴──────┴──────┴──────┘
         ← 512 字节/cycle 数据总线宽度 →
           (32 字节 × 16 lanes)
```

每个 SuperLane 进一步分为 **16 条 lane**（每条 32 字节宽），共 **320 条 lane**（20 × 16）。

## 2. 流水线阶段详解

### 2.1 指令流动 (Y-direction / Southbound)

```
阶段 0: ICU 取指
    ↓ (1 cycle)
阶段 1: ICU 译码 & 分发到 144 队列
    ↓ (1 cycle)
阶段 2-21: 指令沿 SuperLane 0→19 向下传播
    (每 SuperLane 1 cycle, 共 20 cycle)
    ↓
阶段 22: 到达最后 SuperLane, 执行完成
```

**关键特性**：
- 指令垂直流动，每个 cycle 从一个 SuperLane 推进到下一个
- 每个 SuperLane 中的功能单元可以从经过的指令流中 "pick off" 自己的指令
- 编译器知道每条指令何时到达哪个 SuperLane

### 2.2 数据流动 (X-direction / East-West)

```
数据流方向 (East):
  MXM → SXM → MEM → VXM → MEM → SXM → MXM
  每跳 ≈ 1 cycle 相邻传递

数据流方向 (West):
  MXM ← SXM ← MEM ← VXM ← MEM ← SXM ← MXM
```

**每个功能切片的流水线深度 ~20 级**，这意味着：
- 从数据进入切片到产生结果需要约 20 cycle
- 由于每 SuperLane 都有独立的计算管道，整体是深度流水线化的

### 2.3 流式寄存器文件 (Stream Register File)

每个 SuperLane 包含**流式寄存器文件**作为切片间数据传递的媒介：

- **64 个逻辑流**: 32 条向东 + 32 条向西
- **每流 512 字节/cycle** 带宽 (32B × 16 lanes)
- 数据在相邻功能切片间仅需 **1 cycle 一跳**
- 无传统寄存器重命名 — 数据通过流 ID 标识

## 3. 指令发射带宽

### 3.1 每 cycle 指令分配

| 功能切片 | 指令/cycle | 占比 |
|---------|-----------|------|
| MXM (矩阵) | 6 | 7.5% |
| SXM (开关/网络) | 14 | 17.5% |
| MEM (内存) | 44 | 55% |
| VXM (向量) | 16 | 20% |
| **合计** | **80+** | **100%** |

### 3.2 指令发射的关键特征

1. **无需硬件调度器**: 编译器已安排好每 cycle 每条指令的发射
2. **完全静态**: 无 OoO 窗口、无 reservation stations
3. **高带宽**: 80+ 条指令/cycle 在 144 队列中分发
4. **确定性**: 总执行时间编译时可知

## 4. Forwarding / Bypass 机制

### 4.1 Stream Chaining (流式链)

TSP 不使用传统的基于寄存器文件的 forwarding。它使用 **stream chaining**：

```
传统 forwarding:
  [EX] → [WB] → [Register File] → [ID/EX] → 下一指令
  需要 bypass 网络检测 RAW 冲突

TSP stream chaining:
  [VXM 产生 stream] ──── 1 cycle ────▶ [MEM 消费 stream]
  无需 bypass — 直接传递
```

### 4.2 Chaining 的优点

- **无 RAW 冲突检测**: 编译器已确保时序对齐
- **零额外延迟**: 数据从生产者直接流向消费者
- **无 bypass 网络开销**: 无需在硬件中实现旁路多路选择器
- **利用数据流局部性**: 中间结果无需写回再读取

### 4.3 跨 SuperLane 的数据传递

当数据需要在不同 SuperLane 间传递时：
- 使用垂直数据路径 (Y-direction)
- 编译器安排垂直路径的时序
- 所有路径都是确定性的

## 5. 144 队列与 ILP

### 5.1 指令队列架构

144 个独立指令队列分布在芯片上：

```
ICU ( <3% 面积 )
├── 队列 0-35:  MEM 操作 (36 队列)
├── 队列 36-51: VXM 操作 (16 队列)
├── 队列 52-63: MXM 操作 (12 队列)
├── 队列 64-91: SXM 操作 (28 队列)
└── 队列 92-143: 混合/其他 (52 队列)
```

### 5.2 队列间依赖管理

由于编译器完全控制所有 144 个队列：
- **依赖在编译时已解析**: 编译器确保生产者队列在消费者队列之前发射
- **无硬件 scoreboarding**: 无需在运行时跟踪寄存器依赖
- **SYNC/NOTIFY**: 在需要时进行队列间同步

### 5.3 ILP 的实现方式

TSP 通过以下方式实现指令级并行：

1. **空间 ILP**: 不同功能切片上的操作并行执行（如 MXM 矩阵乘 + VXM 向量运算）
2. **流水线 ILP**: 同一功能切片的不同流水线 stage 上有不同操作
3. **流 ILP**: 多个独立的数据流在芯片上并行传输和处理
4. **队列级 ILP**: 144 个队列独立发射，每个 cycle 多条指令

### 5.4 ILP 极限分析

| ILP 来源 | 最大并行度 |
|---------|-----------|
| MXM 操作 | 6 条/cycle |
| SXM 操作 | 14 条/cycle |
| MEM 操作 | 44 条/cycle |
| VXM 操作 | 16 条/cycle |
| **理论最大 ILP** | **80+ 条/cycle** |

## 6. 流水线的功耗/面积优势

### 6.1 面积节省

| 组件 | GPU | Groq TSP |
|------|-----|----------|
| 调度器 + 重命名 | 10-15% | 0% |
| 分支预测器 | 2-5% | 0% |
| Cache (L1+L2) | 20-30% | ~50% SRAM (但更有效) |
| 仲裁器/Crossbar | 5-10% | 0% |
| **控制逻辑总计** | **~30%** | **<3%** |

### 6.2 功耗节省

TSP 的确定性执行在以下方面节省能耗：
- 无调度器动态功耗
- 无 cache miss 导致的停顿和额外访存
- 无推测执行的浪费
- 无仲裁器动态功耗
- 数据搬运减少（stream chaining）

**估计**: 相比 GPU，控制/数据搬运开销降低 60-80%。

## 7. 关键发现总结

1. **二维流水线**: 指令走 Y 方向，数据走 X 方向，在功能单元处交汇执行
2. **80+ 条指令/cycle**: 分布在 144 队列中，编译器静态安排
3. **Stream chaining 替代 forwarding**: 无传统 bypass 网络
4. **<3% 控制逻辑**: 相比 GPU 的 ~30%，面积效率极高
5. **ILP 空间 + 时间**: 同时利用空间并行和流水线并行

## 8. 关键参考文献

- ISCA 2020: *"Think Fast: A Tensor Streaming Processor (TSP) for Accelerating Deep Learning Workloads"*
- Zellic: *"How Is Groq So Fast?"*
- EET China: *"深度拆解 Groq LPU 架构"*
- ProgrammerSought: *"Speed Reading - Tensor Stream Processor (TSP)"*
