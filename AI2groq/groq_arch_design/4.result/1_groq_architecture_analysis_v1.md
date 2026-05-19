# Groq TSP 架构分析报告
# Groq TSP Architecture Analysis Report

> 版本: v1.0 | 创建时间: 2026-05-19
> 分析来源: ISCA 2020/2022, Groq Patents, Zellic Research, 公开技术分析

---

## 1. 设计哲学 (Design Philosophy)

Groq TSP (Tensor Streaming Processor) 的设计哲学可归结为三个核心原则。这些原则贯穿于 TSP 的每个微架构模块，构成了与传统 CPU/GPU 设计范式的根本性决裂。

### 1.1 确定性执行 (Deterministic Execution)

TSP 完全消除了传统处理器中所有"响应式"硬件组件：

| 传统设计 | TSP 设计 | 确定性收益 |
|---------|---------|-----------|
| Out-of-Order (乱序执行) | 编译器静态有序调度 | 无重排序缓冲区、无调度波动 |
| 分支预测 (Branch Prediction) | 无分支预测 | 无预测失败惩罚、无推测执行 |
| Cache 层次 (L1/L2/L3) | 纯 SRAM 单级存储 | 无缓存缺失、延迟完全固定 |
| 硬件仲裁器 (Arbiter) | 无仲裁器 | 无总线竞争、无资源冲突等待 |
| DRAM 控制器 | 无 DRAM | 无 refresh 延迟、无 PHY 延迟 |

**核心思想**：处理器不应自己做任何运行时决策。所有调度决策由编译器在编译时完成，硬件只需要按照预定时间表执行。这消除了传统架构中约 30% 的非确定性开销。

### 1.2 复杂性守恒定律 (Complexity Conservation)

Groq 的设计遵循"复杂性守恒"定律：**复杂度不会消失，只会从硬件转移到软件**。

```
传统架构: 硬件复杂度高 (OoO引擎、cache一致性、分支预测器)
               ↓ 复杂度转移
TSP 架构:   编译器复杂度高 (全局静态调度、资源分配、时序验证)
               ↓ 收益
           硬件简化、面积节省、确定性执行
```

量化体现：
- **ICU <3% die** vs 传统 CPU 控制逻辑 15-25% die
- **无调度硬件**节省 ~10-20% 芯片面积
- 编译器增加数万行 MLIR + Haskell 代码

### 1.3 软件定义硬件 (Software-Defined Hardware)

TSP 的硬件是"软件定义"的——编译器拥有硬件资源的完全可见性，在编译时决定所有资源分配：

- **144 指令队列**：编译器控制所有队列的发射时序，无硬件仲裁
- **64 Stream 寄存器**：编译器分配流 ID 和方向
- **220 MB SRAM**：编译器管理所有地址映射，无 MMU/TLB
- **功能切片**：编译器在编译时分配计算到具体切片
- **互联网络**：编译器静态路由所有数据包，无自适应路由

---

## 2. TSP 微架构 (TSP Microarchitecture)

### 2.1 芯片物理参数

| 参数 | 数值 |
|------|------|
| 制程节点 | 14nm FinFET |
| Die 尺寸 | 25mm × 29mm (~725 mm²) |
| 时钟频率 | 900 MHz (最高 1.25 GHz) |
| 片上 SRAM | ~220-230 MB |
| SIMD 通道数 | 320 (20 Super Lanes × 16 lanes) |
| 独立指令队列 | 144 |
| TDP | ~300W |
| INT8 性能 | 750-1000 TOPS |
| FP16 性能 | 188-205 TFLOPS |

### 2.2 五功能切片设计 (Five Functional Slices)

TSP 采用**功能分片 (Functional Slicing)** 架构，芯片按功能类型划分为垂直切片，每列实现单一功能：

```
指令流 (North ↑)         数据流 (East ↔ West)
                        ←───────────────→
┌──────┬──────┬─────────┬────────────┬─────────┬──────┬──────┐
│      │      │         │  20 SL     │         │      │      │
│ MXM  │ SXM  │  MEM    │  (16 lanes)│  MEM    │ SXM  │ MXM  │
│ 矩阵  │ 开关  │  存储   │  VXM(中心) │  存储   │ 开关  │ 矩阵  │
│ ×2   │ ×2   │  ×2     │   ×1      │  ×2     │ ×2   │ ×2   │
└──────┴──────┴─────────┴────────────┴─────────┴──────┴──────┘
                        ↑
                   以 VXM 为中心镜像对称
                   两个准独立"半球 (hemisphere)"
```

每个 Super Lane (SL) 从左到右排列：`MXM → SXM → MEM → VXM → MEM → SXM → MXM`

| 切片 | 全称 | 功能 | 每 SL 数量 | 面积占比 |
|------|------|------|-----------|---------|
| **ICU** | Instruction Control Unit | 指令取指、解码、分发 | 1 (全局) | <3% |
| **MEM** | Memory Slice | SRAM 读写操作 | 2 | ~40-50% |
| **VXM** | Vector Execution Module | 向量算术运算 (ALU) | 1 | ~10-15% |
| **MXM** | Matrix Execution Module | 矩阵乘累加 (systolic array) | 2 | ~20-25% |
| **SXM** | Switch Execution Module | 移位/旋转/排列/网络 | 2 | ~10% |

### 2.3 各模块关键参数

**ICU (指令控制单元)**
- <3% die area, 集中控制整个芯片
- 144 个独立指令队列，每队列 32-64 条指令深度
- 南北方向广播指令到所有 tile
- 同步机制: SYNC (暂停) / NOTIFY (恢复) / DESKEW (多 TSP 对齐)

**MEM (存储切片)**
- ~40-50% die area (含 SRAM)
- 40 个 MEM 切片 (20 SL × 2), 每切片 ~5.5 MB
- 总带宽: 80 TB/s (通过细粒度 bank 级并行实现)
- 确定性访问延迟: 2-3 cycles

**VXM (向量执行模块)**
- 每 SL 含 16 个 ALU, 全芯片 320 × 16 = 5,120 个向量 ALU
- 数据类型: INT8/INT16/FP16/FP32/BF16/FP8
- TruePoint Numerics: 100-bit 中间累加，保证无精度损失
- 流水线深度: 20 级

**MXM (矩阵执行模块)**
- 4 planes × 320×320 systolic array = 409,600 MACs/MXM
- Weight-stationary dataflow
- 每 plane 由 20×20 = 400 个 16×16 supercell 组成
- 权重加载: 4 planes < 40 cycles

**SXM (移位/交换执行模块)**
- Tiled 1D crossbar 实现，支持 10 种数据操作
- 延迟: 1-2 cycles (大部分操作)
- 额外功能: C2C 片间通信、PCIe 接口

---

## 3. 数据流模型 (Dataflow Model)

### 3.1 正交数据流 (Orthogonal Dataflow)

TSP 最独特的设计是**指令流和数据流的正交**流动：

```
                指令流 (垂直, North ↑)
                ┌───┐
SL 19       ◄───┤   │───► 数据流 (水平, East ↔ West)
                └───┘
                 ...
                ┌───┐
SL 1        ◄───┤   │───►
                └───┘
                ┌───┐
SL 0        ◄───┤   │───►
                └───┘
       ┌──────────────────────┐
       │  ICU (指令发射)       │
       └──────────────────────┘

指令流: 南北方向 (North from ICU)，每个 cycle 传播一个 SL
数据流: 东西方向 (East/West)，通过功能切片水平流动
计算触发: 指令和数据在精确预定的 cycle 在功能切片处交汇
```

### 3.2 Streaming Dataflow (Producer-Consumer)

数据以流的形式在生产者和消费者之间传递，无传统寄存器文件：

```
MEM(加载A) → SXM(路由) → MXM(Q×Kᵀ) → VXM(Softmax) → MEM(存储)
  ↑            ↑            ↑              ↑
 数据源       数据重排     矩阵乘          激活函数

关键: 中间结果从不写入 SRAM — 直接在功能单元间流动 (chaining)
```

- 每个 SIMD lane 支持 **64 个逻辑流**: 32 个向东 + 32 个向西
- 流 ID 范围: 0-31 (每个方向)
- 编译器完全可见每个流的位置和时序

### 3.3 链式执行 (Chaining)

功能切片之间采用**生产者-消费者**模型，结果直接从一个功能片流向下一个：

| 特性 | 传统设计 | TSP Chaining |
|------|---------|-------------|
| 中间结果 | 写回寄存器文件 → 再读取 | 直接传递，零额外延迟 |
| 延迟开销 | ~10 cycles (2次SRAM访问) | ~1 cycle (旁路) |
| 功耗开销 | ~10 pJ (SRAM读写) | ~1 pJ (直接传递) |
| 代码复杂度 | 硬件自动处理 | 编译器静态安排 |

### 3.4 Wavefront 传播

```
时间 t=0:  ICU 发射指令到 SL 0, SL 0 MXM 开始计算
时间 t=1:  SL 0 继续, SL 1 开始, 数据流移动
时间 t=2:  SL 0、SL 1、SL 2 同时在流水线中
...
时间 t=19: 所有 20 个 SL 同时在流水线中

→ 稳态: 每个 SL 处于流水线的不同阶段
→ 类似"波纹 (wavefront)"在垂直方向传播
```

---

## 4. 存储架构 (Memory Architecture)

### 4.1 SRAM-Only 层次

TSP 使用**纯 SRAM 单级存储层次**，完全摒弃 DRAM/HBM 和传统缓存层次：

```
传统层次 (CPU/GPU):     TSP 层次 (Groq):
DRAM → L3$ → L2$ → L1$   SRAM (全局 220-230 MB)
  ↓ 高容量/低确定性         ↓ 低容量/完全确定
  ↓ 高延迟/缓存缺失         ↓ 固定延迟/无缺失
```

### 4.2 MEM 切片组织

| 层级 | 容量 | 数量 | 合计 |
|------|------|------|------|
| SRAM Bank | ~172-344 KB | 16-32 / MEM | 5.5 MB / MEM |
| MEM 单元 | 5.5 MB | 40 (20×2) | **220 MB** |
| Super Lane | 11 MB | 20 | **220 MB** |

### 4.3 80 TB/s 带宽推导

```
80 TB/s 定量推导:

基本参数:
  40 MEM 切片 × 2 端口 (RD+WR) × 128 B/端口 × 900 MHz
  = 40 × 2 × 128 × 900 × 10⁶ = 9.216 TB/s (基础)

bank 级并行倍增:
  每 MEM 切片 ~16-32 个 bank
  bank 并行因子 ≈ 4.4× (实际有效并行度)
  
  9.216 TB/s × 4.4(bank_factor) × 2(双向数据流因子) ≈ 80 TB/s

或等价:
  20 (SL) × 2 (RD+WR) × 512 B (数据宽度) × 900 MHz × 4.4 (bank factor)
  = 20 × 2 × 512 × 900M × 4.4 ≈ 80 TB/s
```

### 4.4 无 DRAM 控制器

| 因素 | DRAM 问题 | TSP 方案 |
|------|----------|---------|
| Refresh | 不可预测的暂停 | SRAM 无 refresh |
| Row activate | 可变延迟 | SRAM 固定延迟 |
| Bank conflict | 等待时间变化 | 编译器避免冲突 |
| PHY 延迟 | SerDes 延迟 | 片上直连 |
| 总带宽 | ~3 TB/s (H100 HBM3) | 80 TB/s (SRAM) |
| 访存延迟 | ~375-500 ns | ~5-10 ns |

---

## 5. 编译器架构 (Compiler Architecture)

### 5.1 工具链全景

Groq 编译器采用 **MLIR 前端 + Haskell 后端** 的双层设计：

```
PyTorch / TensorFlow / ONNX
         │
         ▼  groqit(model, inputs)
┌───────────────────────────────────┐
│       GroqFlow (Python)           │
│  Stage 1-4: Convert, Optimize,    │
│  Check, FP16, Compile (MLIR)      │
└────────────────┬──────────────────┘
                 │
                 ▼
┌───────────────────────────────────┐
│  MLIR Frontend (Groq Dialect)     │
│  Canonicalization                 │
│  Operator Fusion (MXM+VXM)       │
│  Layout Transformation            │
│  Type Promotion (FP16/INT8)       │
│  Graph Partition → Slice/Stream/  │
│  Queue IR                         │
└────────────────┬──────────────────┘
                 │  Groq IR
                 ▼
┌───────────────────────────────────┐
│  Haskell Backend (Haste DSL)      │
│  List Scheduling (DAG-level)      │
│  Modulo Scheduling (loops)        │
│  ILP Solver (conflict regions)   │
│  Code Generation (TSP ISA)        │
│  Formal Verification              │
└────────────────┬──────────────────┘
                 │  IOP binary
                 ▼
       GroqChip LPU (TSP Hardware)
```

### 5.2 三层调度算法 (Three-Layer Scheduling)

```
Layer 1: List Scheduling (全局贪心)
  - 对整个 DAG 做初始调度
  - 优先级启发式选择就绪操作
  - 快速、可扩展，但贪心可能非最优

Layer 2: Modulo Scheduling (循环流水)
  - 对循环体做流水线调度
  - 确定 Initiation Interval (II)
  - 循环密集型 ML 计算的核心优化

Layer 3: ILP Solving (冲突区域求解)
  - 对冲突区域做局部最优调度 (≤20 ops)
  - 整数线性规划求解精确最优
  - 替换贪心的近似解
```

### 5.3 144 队列协同调度

| 队列范围 | 用途 | 数量 |
|---------|------|------|
| Q0-Q31 | MEM 切片 (左右) | 32 |
| Q32-Q47 | VXM 向量操作 | 16 |
| Q48-Q79 | MXM 切片 (左右) | 32 |
| Q80-Q111 | SXM 切片 (左右) | 32 |
| Q112-Q127 | ICU 控制/同步 | 16 |
| Q128-Q143 | 保留/特殊功能 | 16 |

- **总发射带宽**: 最多 144 条指令/cycle
- **实际平均 IPC**: ~25-40 指令/cycle (取决于计算模式)
- **同步机制**: SYNC (全局屏障) / NOTIFY (点对点) / DESKEW (多 TSP 时钟对齐)

---

## 6. 互联架构 (Interconnect Architecture)

### 6.1 Dragonfly 拓扑

Groq 多 TSP 系统采用 **Dragonfly 拓扑** 实现 scale-out：

```
Dragonfly 参数 (Groq 实现):
  ┌─────────────────────────────────────────┐
  │  TSP chip radix: 11 (7 local + 4 global)│
  │  Group (node) size: 8 TSPs              │
  │  Group virtual router radix: 32         │
  │  Intra-group bandwidth: 7 links × 100G  │
  │  Network diameter: 5 hops max           │
  └─────────────────────────────────────────┘
```

| 参数 | 数值 |
|------|------|
| 每 TSP 链路 | 11 (7 local + 4 global) |
| 每链路带宽 | 100 Gbps (4 lanes × 25 Gbps) |
| Group 大小 | 8 TSP 全连接 |
| 最大网络直径 | 5 跳 (10,440 TSPs 规模) |
| 端到端延迟 | < 3 μs |
| 总全局 SRAM | > 2 TB (10,440 × 230 MB) |

### 6.2 编译器静态路由消除死锁

Groq 采用根本不同的方法消除死锁——**从设计层面消除，而非运行时处理**：

| 传统方法 | Groq 方法 |
|---------|----------|
| 运行时检测 → 回退 → 重试 | 编译时验证 → 零运行时开销 |
| VC shifting (+20-30% buffer 面积) | 无额外 buffer |
| 自适应路由 (动态) | 无自适应路由 (全静态) |
| request/response 协议 | 预协调的 send/receive |

### 6.3 C2C 链路

C2C (Chip-to-Chip) 接口通过 SXM 实现片间通信：

- 8 lanes × 32 GB/s per direction
- 编译器静态调度通信，无自适应路由
- DESKEW 指令同步多 TSP

---

## 7. 设计权衡 (Design Trade-offs)

### 7.1 SRAM vs DRAM

| 权衡 | SRAM (TSP 选择) | DRAM/HBM (GPU) |
|------|----------------|---------------|
| 确定性 | 固定延迟 ✓ | 可变延迟 ✗ |
| 带宽 | 80 TB/s ✓ | ~3 TB/s ✗ |
| 延迟 | ~5-10 ns ✓ | ~100-500 ns ✗ |
| 容量 | 230 MB ✗ | 80 GB ✓ |
| 每 bit 能耗 | ~0.3 pJ ✓ | ~5-10 pJ ✗ |
| 成本 | 高昂 ✗ | 便宜 ✓ |

### 7.2 功能分片 vs 传统多核

| 权衡 | 功能分片 (TSP) | 传统多核 |
|------|--------------|---------|
| 控制逻辑效率 | <3% ✓ | 15-25% ✗ |
| 同构性 | 列内同构、全局异构 | 核内异构 |
| 扩展性 | 增加 tile 数 (垂直) | 增加核数 (水平) |
| 灵活性 | 流式模型受限 ✗ | 通用 ✓ |

### 7.3 静态 vs 动态调度

| 维度 | 静态调度 (TSP) | 动态调度 (GPU) |
|------|--------------|---------------|
| 调度时机 | 编译时 | 运行时 |
| 硬件开销 | 低 (简单 FIFO) | 高 (warp scheduler + scoreboard) |
| 适应性 | 固定程序最优 ✗ | 动态适应 ✓ |
| 可预测性 | Cycle 级精确 | 统计性 |
| 编译器复杂度 | 极高 ✗ | 低 ✓ |

### 7.4 推理 vs 训练

TSP 架构**高度偏向推理**，在训练场景中存在根本性限制：

| 工作负载 | TSP 表现 | 原因 |
|---------|---------|------|
| 小模型推理 (≤7B) | 10-15× vs GPU | SRAM 可容纳全部权重 |
| 低延迟推理 | ~100× 尾延迟优势 | 确定性执行 |
| Batch=1 推理 | 75-90% 利用率 | 流式架构天然高效 |
| 大模型推理 (≥70B) | TCO 劣势 | 需大量芯片分摊 |
| 训练 | 不支持 | 无动态调度、无自动微分支持 |

---

## 8. 与 GPU/TPU 对比 (vs GPU/TPU Comparison)

### 多维对比表格

| 维度 | Groq TSP (14nm) | NVIDIA H100 (4nm) | Google TPUv4 (7nm) | Cerebras WSE-3 (5nm) | SambaNova RDU |
|------|----------------|------------------|-------------------|---------------------|---------------|
| **制程** | 14nm | 4nm (custom) | 7nm | 5nm | 7nm |
| **频率** | 900 MHz | ~1.8 GHz | ~700 MHz | ~900 MHz | 未知 |
| **面积** | 725 mm² | ~814 mm² | ~600 mm² | 整晶圆 | 未知 |
| **片上存储** | 230 MB SRAM | 50 MB L2 + 80 GB HBM3 | 若干 MB + HBM | 44 GB 分布式 SRAM | ~500 MB SRAM |
| **存储带宽** | 80 TB/s | 3.0 TB/s | ~1.2 TB/s | 214 PB/s | 高 |
| **FP16 性能** | 188-205 TFLOPS | 989 TFLOPS | ~275 TFLOPS | 125 PFLOPS | 未知 |
| **INT8 性能** | 750-1000 TOPS | ~2000 TOPS (sparse) | ~550 TOPS | ~250 POPS | 高 |
| **TDP** | ~300W | 700W | ~280W | ~15 kW | 未知 |
| **调度方式** | 全静态编译 | 动态 warp 调度 | 部分静态 | 静态+数据并行 | 数据流编译 |
| **确定性** | 完全 (cycle 级) | 无 | 部分 | 部分 | 是 |
| **推理延迟** | 极低且可预测 | 低但波动 | 低 | 低 | 低 |
| **编译器** | MLIR + Haskell | NVCC (C++) | XLA (C++) | C++ | Python+自定义 |
| **互联拓扑** | Dragonfly | NVLink Switch | 自定义环 | Wafer-scale | 自定义 |
| **多芯片扩展** | 10,440 TSPs | 数百 GPU | ~4,096 TPUs | 整晶圆 | 可扩展 |
| **延迟 SLA** | **可保证** | 统计性 | 统计性 | 统计性 | 可保证 |
| **灵活度** | 低 (静态图) | 高 | 中 | 中 | 中 |

### 关键差异总结

1. **确定性 vs 统计性**: TSP 是唯一提供 cycle 级执行可预测性的架构，这对实时推理 SLA 至关重要
2. **存储层次**: TSP 用 SRAM 容量换取带宽/延迟确定性，GPU 用 DRAM 换取容量/成本
3. **编译器负担**: TSP 将复杂度推给编译器，GPU 用硬件动态调度承担
4. **延迟性能**: TSP 在 batch=1 场景有 10-100× 优势，但大模型场景 TCO 劣势
5. **生态成熟度**: GPU 生态远优于 TSP，但 TSP 在特定推理场景有不可替代优势

---

> **参考文献**:
> 1. Abts et al., "Think Fast: A TSP for Accelerating Deep Learning Workloads", ISCA 2020
> 2. Singh et al., "The Virtuous Cycles of Determinism", ISCA 2022
> 3. US20240037064A1 — Instruction Format and ISA for TSP
> 4. US20230024670A1 — Deterministic Memory for TSP
> 5. Groq Blog — "Inside the LPU: Deconstructing Groq's Speed"
> 6. Zellic Research — "How Is Groq So Fast?"
