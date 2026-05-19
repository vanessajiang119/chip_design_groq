# Result: Groq TSP 确定性数据流执行模型 — 完整分析报告

> 创建时间: 2026-05-19
> 分析范围: Streaming dataflow, 确定性调度, 流水线设计, 指令级并行

---

## 摘要

Groq TSP (Tensor Streaming Processor) 的核心创新是**确定性数据流执行模型**。与传统 CPU/GPU 依赖硬件动态调度不同，TSP 将所有调度决策移至编译器，硬件仅需按预定计划执行。该架构在确定性工作负载（如 AI 推理）上实现了显著的功耗/面积效率优势，但也付出了灵活性损失和编译器复杂度的代价。

---

## 第1部分: 整体架构

### 1.1 芯片概览

| 规格 | 参数 |
|------|------|
| 制程 | 14nm ASIC |
| 主频 | 900 MHz |
| 尺寸 | 25 mm × 29 mm (~725 mm²) |
| 片上 SRAM | 220 MB (全局共享, 无 cache) |
| 功能切片 | MXM, MEM, VXM, SXM, ICU |
| SuperLanes | 20 |
| Lanes | 320 (20 × 16) |
| 指令队列 | 144 |
| 预期 IPC | 25-40 (峰值 80+) |

### 1.2 二维流水线模型

TSP 最独特的设计是**二维空间-时间流水线**：

```
       时间 (Y方向, 指令流动)
       ▲
       │
       │   SuperLane 0 ────────── X方向数据流 ────────▶
       │   SuperLane 1 ───────────────────────────────▶
       │   SuperLane 2 ───────────────────────────────▶
       │   ...
       │   SuperLane 19 ──────────────────────────────▶
       │
       └─────────────────────────────────────────────► 空间 (X方向)
```

- **指令沿 Y 方向流动**: 每 cycle 从 SuperLane 0 向下推进到 SuperLane 19
- **数据沿 X 方向流动**: 在功能切片间以 1 cycle/跳传播
- **执行在交点发生**: 指令和数据在 (Slice, SuperLane, cycle) 处交汇

---

## 第2部分: Streaming Dataflow 模型

### 2.1 核心概念

- **Stream**: 数据在功能切片间流动的抽象单元，由 **Stream ID** (0-31) 和方向 (East/West) 标识
- **Producer-Consumer**: MEM 产生流 → VXM/MXM/SXM 消费流 → 产生新流供下一单元消费
- **Stream Chaining**: 中间结果直接从一个功能单元传递给下一个，不写回 SRAM

### 2.2 数据流动路径

```
典型路径:
  MEM(Load) ──stream(A)──▶ MXM(MatMul) ──stream(C)──▶ VXM(Activation) ──stream(D)──▶ MEM(Store)
                 stream(B)──▶▲
  MEM(Load) ────────────────┘
```

- 每个 SuperLane 有 64 个逻辑流 (32 East + 32 West)
- 数据在相邻切片间 1 cycle 一跳
- 流式寄存器文件 (SRF) 作为中间缓冲

### 2.3 Chaining 的作用

Stream chaining 替代了传统处理器的 forwarding/bypass 网络：
- 无 RAW 检测硬件
- 零额外延迟（数据直接传递）
- 节省 1 SRAM 写 + 1 SRAM 读的能耗 (每跳 ~10 cycle + ~10 pJ)

---

## 第3部分: 确定性调度

### 3.1 "144-wide VLIW" 模型

TSP 可被理解为 144-wide VLIW 处理器：

| 功能切片 | 指令/cycle | 队列数 |
|---------|-----------|--------|
| MXM | 6 | 12 |
| VXM | 16 | 16 |
| MEM | 44 | 36 |
| SXM | 14 | 28 |
| 其他/混合 | — | 52 |
| **合计** | **80+** | **144** |

### 3.2 编译器调度算法

编译器使用改进的列表调度 (list scheduling) + 启发式算法：

```
输入: 计算图 (MLIR) → 硬件模型 → 延迟表 → 资源约束
过程:
  1. 计算图优化 (算子融合、张量分片)
  2. 资源分配 (流ID、SRAM bank、功能切片)
  3. 时序调度 (列表调度 + 约束传播)
  4. 验证 (时序正确性、资源冲突)
输出: 调度表 (cycle × queue)
```

### 3.3 SYNC/NOTIFY 同步

- **SYNC**: 全局屏障，等待所有队列完成
- **NOTIFY**: 点对点通知，轻量级同步
- **编译器安排**: 最小化同步开销，与计算重叠

---

## 第4部分: 为什么确定性执行节省功耗/面积？

### 4.1 消除的硬件组件

| 消除的硬件 | GPU 中占比 | 功耗节省估计 |
|-----------|-----------|------------|
| OoO 调度器 + 重命名 | ~10-15% 面积 | ~10% 总功耗 |
| 分支预测 + 推测执行 | ~2-5% 面积 | ~3% 总功耗 |
| Cache 层次 (L1/L2) | ~20-30% 面积 | ~25% 总功耗 |
| Cache Coherence 协议 | ~2-3% 面积 | ~2% 总功耗 |
| 网络仲裁器 | ~3-5% 面积 | ~4% 总功耗 |
| Warp 调度器 | ~5-8% 面积 | ~5% 总功耗 |
| **总计控制开销** | **~42-66%** | **~49%** |

### 4.2 面积再分配

ICU (指令控制单元) 仅占 **<3% 芯片面积**。相比之下：

```
GPU 芯片面积分配 (估计):
  计算单元 (ALU/Tensor Core):          ~35%
  Cache + 存储:                        ~25%
  调度/控制/仲裁/协议:                  ~30%
  其他 (I/O, 时钟, 互联):              ~10%

TSP 芯片面积分配 (估计):
  计算单元 (MXM, VXM, SXM):            ~45%
  SRAM (220 MB):                       ~50%
  控制 (ICU + 队列):                    <3%
  其他 (I/O, 时钟, 互联):              ~2%
```

TSP 将 GPU 花在控制逻辑上的 **~30% 面积**重新投入计算和存储。

### 4.3 功耗节省的量化

**确定性数据流控制可节省 60-80% 通常浪费在数据搬运和控制开销上的能量** (ISCA 2020)。

| 来源 | GPU | TSP |
|------|-----|-----|
| 调度动态功耗 | 高 (每 cycle 调度决策) | ~0 (编译时完成) |
| Cache miss 额外访存 | 高 (25-50% 带宽浪费) | 无 cache, 无 miss |
| 推测执行浪费 | 3-10% 指令被误推测 | 无推测 |
| 数据搬运 (数据→计算) | 高 (cache 层次间) | 低 (直接流式) |
| 同步 | 高 (atomic ops + barrier) | 低 (编译器最小化) |

---

## 第5部分: 确定性执行的代价

### 5.1 编译器复杂度

| 代价项 | 说明 |
|--------|------|
| 编译器代码量 | 数万行 MLIR + Haskell 代码 |
| 编译时间 | 复杂模型可能数分钟到数小时 |
| 硬件模型 | 需要精确到 cycle 的硬件延迟模型 |
| 调度算法 | NP-hard 问题, 需要启发式 |

### 5.2 灵活性损失

| 场景 | TSP 表现 | 原因 |
|------|---------|------|
| 固定形状密集模型 | 优秀 | 编译器可完美调度 |
| 动态形状输入 | 差 | 无法预编译所有路径 |
| 稀疏计算 | 差 | 运行时稀疏模式无法静态预测 |
| MoE (专家混合) | 中等 | 路由模式需运行时决策 |
| 推测解码 | 差 | 动态分支无法静态调度 |
| 训练 | 中等 | 反向传播动态性较少, 但需要更大 SRAM |

### 5.3 容量限制

- **220 MB 片上 SRAM**: 远小于 GPU HBM (80 GB+)
- **需要模型并行**: 大模型需要在多个 TSP 间分片
- **权重复用**: 需要编译器高效安排权重加载和计算

### 5.4 编程约束

- **显式流管理**: 开发者 / 编译器需理解数据流
- **形状固定**: 输入张量形状需在编译时确定
- **控制流受限**: 分支需转换为 select/predicate 操作

---

## 第6部分: "复杂性守恒" 定律

```
GPU:
  ┌──────────────────────────────────┐
  │ 硬件: 复杂调度器、cache、仲裁器    │  ← 30%+ 面积用于控制
  │ 编译器: 相对简单                   │
  │ 灵活性: 高                        │
  │ 确定性: 低 (P99 抖动大)            │
  └──────────────────────────────────┘

Groq TSP:
  ┌──────────────────────────────────┐
  │ 硬件: 简单 FIFO, 无调度器, 无 cache│  ← <3% 面积用于控制  
  │ 编译器: 极其复杂 (数万行代码)      │
  │ 灵活性: 低                        │
  │ 确定性: 高 (cycle 精确)            │
  └──────────────────────────────────┘
```

复杂性不会消失，只是从硬件转移到了编译器。Groq 赌的是：
- **编译器复杂性是一次性的**: 投入一次开发，所有芯片受益
- **硬件复杂性是重复的**: 每颗芯片都要冗余的调度硬件
- **AI 工作负载正在变得可预测**: 固定形状、密集计算

---

## 第7部分: 结论

### 7.1 TSP 最适合的场景

1. **Batch-1 在线推理**: 低延迟、高确定性，无 GPU 的批处理延迟
2. **固定形状模型**: ResNet、BERT、LLaMA 等标准架构
3. **SLA 关键任务**: P99 延迟保证至关重要
4. **计算密集型模型**: 矩阵乘法占比高，充分利用 MXM

### 7.2 TSP 不适合的场景

1. **训练**: 反向传播的动态性 + SRAM 容量限制
2. **稀疏/MoE 模型**: 运行时路由决策无法静态编译
3. **动态形状**: NLP 中的可变序列长度
4. **控制流丰富的代码**: 分支密集的算法

### 7.3 关键竞争维度

```
                 确定性 (Determinism)
                        │
                        │
         Groq TSP ──────┤
                        │
                        ├──── 灵活性 (Flexibility)
                        │
              GPU ──────┘
                        │
                        │
                  峰值性能 (Peak Perf)
```

TSP 放弃灵活性以换取确定性和功耗/面积效率。GPU 保留灵活性但承受非确定性和控制开销。实际中，Neural Networks 的规则化特性使得 TSP 的权衡在推理场景中非常有效。

---

## 参考文献

1. ISCA 2020: *"Think Fast: A Tensor Streaming Processor (TSP) for Accelerating Deep Learning Workloads"* — Dennis Abts et al., Groq Inc.
2. ISCA 2022: *"A Software-defined Tensor Streaming Multiprocessor for Large-scale Machine Learning"* — Dennis Abts et al.
3. ASPLOS 2022: *"The Virtuous Cycles of Determinism: Programming Groq's Tensor Streaming Processor"*
4. Groq Blog: *"Introducing the LPU"* — https://groq.com/lpu-architecture
5. Zellic: *"How Is Groq So Fast? An Overview of Groq's TSP Architecture"* — https://www.zellic.io/blog/groq-tsp-whitepapers/
6. EET China: *"深度拆解 Groq LPU 架构"* — https://www.eet-china.com/mp/a484110.html
7. 知乎: *"确定性的边界：从 GPU 到 Groq 的 AI 芯片谱系学"*
8. Stanford EE Seminar: *"New Rules of the Game: Groq's Deterministic LPU Inference Engine"*
9. SC23: *"Strong Scaling of State-of-the-Art LLM Inference with Groq Software-Scheduled Deterministic Networks"*
10. Groq Patent: *"Deterministic Memory for Tensor Streaming Processors"* — US20230024670
