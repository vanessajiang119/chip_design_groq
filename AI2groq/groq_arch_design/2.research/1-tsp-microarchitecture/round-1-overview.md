# TSP 微架构深度分析 — Round 1 研究报告
# Groq TSP Microarchitecture Deep Dive — Round 1 Research Report

> 创建时间: 2026-05-19T1400
> 来源: ISCA 2020/2022 papers, EET China, 36Kr, BAAI, Zellic, Groq Blog

---

## 一、总体架构概览 (Architecture Overview)

Groq TSP (Tensor Streaming Processor) 是一颗**软件定义的张量流式多处理器**，采用激进的**功能分片 (Functional Slicing)** 架构，完全抛弃传统 CPU/GPU 的多核设计范式。

### 核心设计理念 (Core Philosophy)

| 传统设计 | TSP 设计 |
|---------|---------|
| 每个核心包含所有功能单元（异构） | 每列功能相同，垂直堆叠 → 局部同质、全局异质 |
| 每个核心有自己的控制逻辑 | 公共控制逻辑集中到 ICU 切片 (<3% die) |
| 动态调度 (OoO, branch prediction) | 编译器静态调度 — 完全确定性 |
| 缓存层次 + DRAM | 纯 SRAM — 无缓存、无 DRAM |
| 硬件仲裁/乱序执行 | 无仲裁器、无重放机制 |

### 芯片物理参数 (Physical Parameters)

| 参数 | 数值 |
|------|------|
| 制程节点 | 14nm |
| 时钟频率 | 900 MHz (可升至 1.25 GHz) |
| Die 尺寸 | 25mm × 29mm (~725 mm²) |
| 片上 SRAM | ~220-230 MB (全局共享) |
| SIMD 通道数 | 320 (20 tiles × 16 lanes/tile) |
| 独立指令队列 | 144 |
| 计算密度 | >1 TeraOp/s/mm² |
| INT8 性能 | 750-1000 TOPS |
| FP16 性能 | 188-205 TFLOPS |
| TDP | ~300W |
| 内存带宽 | 80 TB/s |

---

## 二、功能分片架构 (Functional Slicing)

TSP 芯片采用 2D 网格布局，每个**列 (slice)** 实现单一功能：

| 切片 | 全称 | 功能 | 每 Super Lane 数量 | 面积占比 |
|------|------|------|-------------------|---------|
| **ICU** | Instruction Control Unit | 指令取指、解码、分发 | 1 (全局) | <3% |
| **MEM** | Memory Slice | SRAM 读写操作 | 2 | ~40% |
| **VXM** | Vector Execution Module | 向量算术运算 (ALU) | 1 | — |
| **MXM** | Matrix Execution Module | 矩阵乘累加 (systolic array) | 2 | — |
| **SXM** | Switch Execution Module | 移位/旋转/排列/网络 | 2 | — |

### Super Lane 组成 (20 Super Lanes × 16 lanes)

每个 Super Lane 从左到右排列：
```
MXM → SXM → MEM → VXM → MEM → SXM → MXM
```
以 VXM 为中心两侧镜像对称，形成两个准独立的"半球 (hemisphere)"。

每个 Super Lane 的数据路径宽度为 **512 bytes/cycle** (32 bytes/lane × 16 lanes)。

---

## 三、数据流模型 (Dataflow Model)

### 正交流 (Orthogonal Flow)

- **指令流**: 南北方向 (North → South)，从 ICU 向上传播，每个 cycle 传播一个 tile
- **数据流**: 东西方向 (East ↔ West)，通过功能切片水平流动
- **计算触发**: 指令和数据在**精确预定的 cycle** 在功能切片处交汇

### 流式寄存器文件 (Stream Register File, SRF)

- 通过芯片范围的 SRF 实现流式数据传输
- 每个 SIMD lane 支持 **64 个逻辑流**: 32 个向东 + 32 个向西
- 流 ID 范围: 0-31 (每个方向)
- 编译器完全可见每个流的位置和时序

### 链式执行 (Chaining)

- 功能切片之间采用**生产者-消费者**模型
- 结果直接从一个功能片流向下一个 — 无需写回寄存器文件
- MEM(加载数据) → SXM(路由) → VXM/MXM(计算) → SXM(重组) → MEM(存储)

### 流水线深度

- 每个功能切片运行 **20 级向量流水线**
- 20 tiles × 20 级 → 全芯片流水线深度对应 400 cycles 的 tile-流水线

---

## 四、指令系统与调度 (Instruction System & Scheduling)

### VLIW 指令包格式

- ICU 集中取指和解码（仅占芯片面积 3%）
- 每个 VLIW 包包含多个操作，每个功能切片类型对应一个操作
- 编译器静态打包操作到 VLIW 包中

### 144 个独立指令队列

- 每个 queue 每个 cycle 可以发射一个或多个指令
- 编译器完全控制每个 queue 的程序顺序
- **SYNC 指令**: 暂停所有 144 个队列
- **NOTIFY 指令**: 广播同步所有队列恢复执行
- **DESKEW 指令**: 等待硬件对齐计数器 (HAC) 溢出 — 用于多 TSP 同步

### 确定性执行 (Deterministic Execution)

- 无分支预测 → 无推测执行
- 无缓存 → 无缓存缺失
- 无仲裁器 → 无资源冲突
- 无乱序执行 → 无重排序缓冲区
- 编译器精确知道每条指令的执行周期数

---

## 五、各模块简要数据 (Module Quick Data)

### ICU (Instruction Control Unit)
- <3% die area, 集中控制整个芯片
- 144 个独立指令队列
- 南北方向广播指令到所有 tile

### MEM (Memory Slice)
- ~40% die area (SRAM)
- 88 个 MEM slice (20 SL × 2 + 额外)
- 每 MEM 约 2.5-5.5 MB SRAM
- 并发: 176 路 (88 × 2)
- 确定性访问延迟

### VXM (Vector Execution Module)
- 每个 Super Lane 含 16 个 ALU
- 全芯片 320 × 16 = 5,120 个向量 ALU
- 数据类型: INT8/INT16/FP16/FP32/BF16/FP8
- TruePoint Numerics: 100-bit 中间累加

### MXM (Matrix Execution Module)
- 320×320 fused dot product per plane
- 4 planes → 409,600 MACs 总计
- Weight-stationary dataflow
- 每个 320×320 平面 = 20 × 16×16 supercells
- 每个平面存储 102,400 weights

### SXM (Switch Execution Module)
- 任意向量变换 (shift/rotate/permute)
- lane switching / crossbar / permuter circuit
- 连接到 C2C/PCIe I/O
- 数据重组、转置、广播

---

## 六、关键技术要点 (Key Technical Highlights)

1. **TruePoint Numerics**: 100-bit 中间累加，保证无精度损失的累加，同时存储权重和激活值使用更低精度
2. **静态调度 (Static Scheduling)**: 编译器在编译时解决所有资源冲突、数据依赖和路由
3. **功能分片面积效率**: ICU <3% vs 传统设计 15-25% 控制逻辑占比
4. **链式计算**: 消除寄存器文件瓶颈，功能单元间直接数据流动
5. **80 TB/s 带宽**: 纯 SRAM 实现，无需 HBM/DRAM

---

## 七、参考文献 (References)

1. Abts et al., "Think Fast: A Tensor Streaming Processor (TSP) for Accelerating Deep Learning Workloads", ISCA 2020
2. Singh et al., "The Virtuous Cycles of Determinism: Programming Groq's Tensor Streaming Processor", ISCA 2022
3. Groq Blog: "Inside the LPU: Deconstructing Groq's Speed"
4. US Patent 20240037064A1: "Instruction Format and ISA for TSP"
5. Zellic Research: "How Is Groq So Fast? An Overview of Groq's TSP Architecture"
