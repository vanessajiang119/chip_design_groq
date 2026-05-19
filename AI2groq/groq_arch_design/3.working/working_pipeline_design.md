# Working: 流水线设计 — Layer 2 深度分析

> 创建时间: 2026-05-19
> 分析层级: Layer 2 — 流水线 Stage 划分与 Forwarding

---

## 1. TSP 流水线的独特之处

Groq TSP 的流水线不是传统意义上的"取指→译码→执行→写回"线性流水线。它是一个**二维空间-时间流水线**：

```
传统流水线 (一维时间):
  [IF] → [ID] → [EX] → [MEM] → [WB]
  每 cycle 一个阶段推进

TSP 流水线 (二维空间-时间):
          时间 (Y) ▼
  SuperLane 0 ──────────────────────► X 方向数据流
  SuperLane 1 ─────────────────────►
  SuperLane 2 ─────────────────────►
  ...
  SuperLane 19 ────────────────────►
  
  指令沿 Y 方向流动, 数据沿 X 方向流动
  在 (x, y, t) 交点执行
```

## 2. 指令流水线: Y 方向

### 2.1 ICU 指令取出与分发

```
ICU (SuperLane 0 下方的水平 bar):
  Stage 0:  指令取指 (从指令存储器)
  Stage 1:  指令译码
  Stage 2:  指令分发到 144 队列
  Stage 3:  指令注入 SuperLane 0
  
每 cycle:
  └── ICU 从指令 cache (ICache) 读取最多 80+ 条指令
  └── 译码后分发到对应的功能切片队列
  └── 注入到 SuperLane 0 的指令管道
```

### 2.2 指令在 SuperLane 间传播

```
每 cycle 向下传播一个 SuperLane:

  SuperLane 0:  INSTR[0] 执行 (发射 cycle)
       ↓ (1 cycle)
  SuperLane 1:  INSTR[1] 执行
       ↓
  SuperLane 2:  INSTR[2] 执行
       ↓
  ...
       ↓
  SuperLane 19: INSTR[19] 执行
  
  指令到达 SuperLane N 时:
    └── 如果该指令的目标功能单元在此 SuperLane 中
    └── 则指令 "pick off" 执行
    └── 否则传递到下一 SuperLane
```

### 2.3 指令流水线的时序

```
指令发射时间 = t₀
指令到达 SuperLane n = t₀ + n
指令在某个功能切片上开始执行 = max(t₀ + n, 数据到达时间)
指令完成时间 = 开始执行时间 + 指令延迟
```

编译器必须确保对于每条指令：
```
数据到达时间 − 1 ≤ 指令到达时间 ≤ 数据到达时间 + (SRF 深度 - 1)
```
否则 SRF 会下溢或上溢。

## 3. 数据流水线: X 方向

### 3.1 数据在功能切片间的移动

```
每 cycle 数据可以:

  1. 在同一 SuperLane 内相邻切片间移动
     MXM ──1 cycle──▶ SXM ──1 cycle──▶ MEM ──1 cycle──▶ VXM
  
  2. 在同一功能切片内不同 SuperLane 间移动
     SuperLane N ──1 cycle──▶ SuperLane N+1 (垂直数据路径)

  3. 通过 SRF 旁路直接传递
     生产者在 cycle t 写入 → 消费者在 cycle t+1 读取
```

### 3.2 数据流水线深度

```
从一个 MEM slice 加载数据到 VXM 使用的总延迟:

  MEM 读取:          ~12 cycles (SRAM 访问)
  MEM→VXM 跳转:      ~1 cycle  (相邻切片)
  VXM 管道延迟:      ~20 cycles (向量管道)
  ───────────────────────────
  总计:              ~33 cycles 从加载到结果可用
```

编译器知道这个延迟，并安排后续指令在这个精确时间戳读取结果。

### 3.3 带宽匹配

```
功能切片间的数据总线宽度:
  每 SuperLane: 512 字节/cycle (32 字节 × 16 lanes)
  芯片总带宽 (20 SuperLanes): 10,240 字节/cycle
  @900 MHz:                    9.2 TB/s 片内带宽
  vs 片上 SRAM 带宽:           80 TB/s
```

编译器需要确保每个功能切片的输入/输出带宽匹配，防止瓶颈。

## 4. 各功能切片的内部流水线

### 4.1 MEM (Memory Slice) 流水线

```
MEM 内部流水线 (估计):
  Stage 0-2:  地址计算 (base + offset + stride)
  Stage 3-4:  Bank 解码 + 行激活
  Stage 5-10: SRAM 访问 (6 cycle latency)
  Stage 11:   数据对齐
  Stage 12:   写入 SRF

每个 SuperLane 有 2 个 MEM slice
共有 40 个 MEM slices 在芯片上
每个 MEM slice 内有多个 SRAM bank 以提供带宽
```

### 4.2 VXM (Vector Execution Module) 流水线

```
VXM 内部流水线 (估计 ~20 stages):
  Stage 0-1:  输入数据准备 (从 SRF 读取)
  Stage 2-3:  数据格式转换 (INT8↔FP16↔FP32)
  Stage 4-9:  向量 ALU 运算 (加/乘/比较等)
  Stage 10-14: 特殊函数 (GELU, ReLU, sigmoid, tanh)
  Stage 15-17: 归约操作 (sum, max, min)
  Stage 18-19: 结果写入 SRF

VXM 特点:
  └── 16 个 ALU/lane, 320 lanes = 5,120 ALUs
  └── 支持 element-wise, 归约, 广播
```

### 4.3 MXM (Matrix Execution Module) 流水线

```
MXM 内部流水线 (脉动阵列):

  输入阶段:
    Stage 0-3:   权重加载 (从 SRF 读取权重流)
    Stage 4-7:   输入激活加载 (从 SRF 读取输入流)
    
  计算阶段 (脉动):
    Stage 8-327: 320×320 脉动阵列计算
    └── INT8: 320×320 DP (409,600 MACs)
    └── FP16: 320×160
    
  输出阶段:
    Stage 328-335: 部分和累加
    Stage 336-339: 激活函数 (可选)
    Stage 340:     结果写入 SRF

MXM 特点:
  └── 320×320 脉动阵列
  └── INT8 峰值: 288 TOPS (900 MHz × 409,600 MACs × 2 ops/MAC)
  └── 权重加载可与计算重叠 (流水线隐藏延迟)
```

### 4.4 SXM (Switch/Shift Execution Module) 流水线

```
SXM 内部流水线 (估计 ~18 stages):
  Stage 0-1:   输入数据准备
  Stage 2-5:   数据重排 (permute, broadcast)
  Stage 6-9:   移位/旋转
  Stage 10-12: 数据格式化 (concat, split)
  Stage 13-15: 芯片间 (C2C) 打包
  Stage 16-17: 结果写入 SRF

SXM 特点:
  └── "瑞士军刀"单元 — 灵活的数据操作
  └── 也负责片间和 PCIe 通信
```

## 5. Forwarding / Bypass 详细分析

### 5.1 无传统 Forwarding

TSP 没有传统微架构中的 forwarding 网络（bypass multiplexer network）。原因是：

```
传统 Forwarding (CPU):
  EX/MEM 旁路 → ID/EX 阶段
  └── 检测 RAW 依赖
  └── 多级选择器网络
  └── 面积大, 时序关键

TSP Stream Chaining:
  VXM_out ──direct──▶ MXM_in
  └── 不需要旁路检测
  └── 编译器已确保时序
  └── 通过 SRF 直接传递
```

### 5.2 Chaining 的实现细节

Stream chaining 在微架构层面如何实现：

```
场景: VXM 产生结果立即被 MXM 使用

cycle t:     VXM 在 SuperLane 5 完成计算, 写入 SRF[stream=3]
cycle t+1:   MXM 在 SuperLane 5 从 SRF[stream=3] 读取

硬件实现:
  VXM 的写端口:
    └── 数据总线直接连接到 SRF 输入
    └── 写使能信号在 cycle t 有效
    
  MXM 的读端口:
    └── 数据总线直接连接到 SRF 输出
    └── 读使能信号在 cycle t+1 有效
    
  不需要交叉开关 (crossbar):
    └── 编译器已分配 stream ID
    └── 硬件只是根据 stream ID 路由
```

### 5.3 跨 SuperLane Chaining

当生产者和消费者在不同 SuperLane 时，需要垂直数据路径：

```
SuperLane 5  VXM 产生结果
    │
    │ 垂直数据路径 (1 cycle/SuperLane)
    ▼
SuperLane 8  MXM 消费结果

总延迟: 1 (水平) + 3 (垂直) = 4 cycles
编译器在调度时考虑此延迟
```

## 6. 流水线气泡分析

### 6.1 气泡来源

尽管是确定性调度，气泡仍可能出现在：
1. **SYNC 屏障**: 等待所有队列同步
2. **SRF 耗尽**: 流缓冲区满导致生产者暂停
3. **内存端口冲突**: 编译器安排不当导致端口竞争
4. **数据依赖性**: 等待生产者产生数据

### 6.2 气泡消除策略

编译器使用以下策略消除气泡：
1. **指令重排**: 在依赖关系允许时移动非依赖指令填充气泡
2. **软件流水线化**: 循环的软件流水线 (software pipelining)
3. **延迟隐藏**: 将独立计算安排在等待周期中
4. **预加载**: 在需要之前提前加载数据 (prefetch)

### 6.3 理想化的流水线利用率

在完美调度下，TSP 流水线的利用率可以接近 100%（对于规则的计算模式如 GEMM）。对于不规则模式（如稀疏注意力），利用率可能显著下降。

## 7. 流水线功耗分析

### 7.1 流水线各部分的功耗分布 (估计)

| 流水线部分 | 功耗占比 | 说明 |
|-----------|---------|------|
| MXM (矩阵) | ~40% | 脉动阵列密集计算 |
| MEM (内存) | ~25% | SRAM 访问 |
| VXM (向量) | ~20% | 向量 ALU |
| SXM (开关) | ~10% | 数据重排 + 通信 |
| ICU (控制) | <3% | 指令分发 |
| 时钟 | ~2% | 时钟树 |

### 7.2 确定性带来的功耗节省

| 硬件组件 | GPU 功耗 | TSP 节省原因 |
|---------|---------|-------------|
| 调度器 | ~10% | 无硬件调度器 |
| 分支预测 | ~3% | 无分支预测 |
| Cache 控制器 | ~8% | 无 cache |
| 内存控制器 | ~5% | 无 DRAM 控制器 |
| 网络仲裁 | ~4% | 无仲裁器 |
| **总计** | **~30%** | **直接节省** |

## 8. 结论

TSP 的二维流水线架构是其确定性执行的核心：
1. **指令走 Y 方向**：每 cycle 下降一个 SuperLane
2. **数据走 X 方向**：在功能切片间传播
3. **执行在交点发生**：指令和数据在 (Slice, SuperLane, cycle) 处交汇
4. **Stream chaining 替代 forwarding**：通过 SRF 直接传递，无传统 bypass 网络
5. **编译器负责一切**：所有时序由编译器静态安排
