# Round 1: Streaming Dataflow 模型 — 研究结果

> 创建时间: 2026-05-19
> 来源: ISCA 2020/2022, Groq Blog, Zellic Analysis, EET China

---

## 1. 核心概念: Tensor Streaming Processor (TSP)

Groq TSP 的核心创新在于**完全确定性的数据流执行模型**。与传统的 CPU/GPU 不同，TSP 不依赖任何运行时动态调度硬件，所有指令的执行时间在编译时即完全确定。

### 1.1 什么是 Streaming Dataflow？

在 Groq TSP 中，数据以**流 (stream)** 的形式在功能切片 (functional slices) 之间流动：

```
[Memory] --stream--> [Matrix Unit] --stream--> [Vector Unit] --stream--> [Memory]
```

- 每个流有一个 **stream ID** (0-31) 和方向 (East/West)
- 功能单元从 incoming stream 消费张量输入，向 outgoing stream 产生张量输出
- 中间结果可以在功能单元之间"链式传递" (chaining)，无需写回主存

### 1.2 Producer-Consumer 模型

Groq 的编程模型基于 **producer-consumer** 范式：
- **生产者** 产生数据流
- **消费者** 消费数据流
- 编译器确保生产者与消费者的时序完全对齐

## 2. 功能切片与数据流路径

### 2.1 功能切片布局

TSP 将功能单元组织为**二维网格的列 (slices)**。每个 tile 在局部是同构的，但从芯片全局看是异构的：

| Slice (列) | 功能 | 说明 |
|------------|------|------|
| **ICU** | 指令控制 | 位于芯片底部 (水平 bar)，<3% 面积 |
| **MEM** | 内存访问 | SRAM 读/写 |
| **VXM** | 向量执行 | 向量算术 (SIMD) |
| **MXM** | 矩阵执行 | 矩阵乘法、卷积 (脉动阵列) |
| **SXM** | 移位执行 | 向量移位/旋转 |

### 2.2 数据的物理流动

物理布局中，数据在芯片上沿 **X 方向 (水平)** 在功能切片间流动：

```
        MXM  VXM  MEM  SXM  MXM  VXM  MEM  SXM ...
        ┌───┬───┬───┬───┬───┬───┬───┬───┐
Stream ─▶   │   │   │   │   │   │   │   │──▶
(East)  └───┴───┴───┴───┴───┴───┴───┴───┘
                            ◀───   ◀───   ◀───
                          Stream (West)
```

- 每个切片有 20 tiles × 16 SIMD lanes = 320 通道
- 每个通道支持 64 个逻辑流 (32 向东, 32 向西)
- 流在芯片上的**流式寄存器文件 (streaming register file)** 中传递

### 2.3 片内 Streaming Register File

TSP 使用统一的芯片级流式寄存器文件，替代了传统的寄存器层级结构：
- 没有传统的多级寄存器文件
- 内存切片将数据直接送入计算切片
- 数据在切片间通过流寄存器文件传递，无需中间存储

## 3. 确定性数据流的关键特征

### 3.1 无反应式硬件 (No Reactive Hardware)

TSP 完全消除了以下传统处理器中引入非确定性的硬件组件：
- ❌ 无 Cache (无 cache miss → 无延迟不确定性)
- ❌ 无仲裁器 (无总线/网络仲裁 → 无竞争延迟)
- ❌ 无分支预测器 (无序推测执行)
- ❌ 无序执行 (OoO) 引擎
- ❌ 无 Cache Coherence 协议

### 3.2 编译时确定一切

编译器在编译时即可完全确定：
- 每条指令的精确延迟 (cycle 级别)
- 数据到达每个功能单元的时间
- 所有 144 个指令队列的发射时序
- 所有网络路由路径

### 3.3 流式执行的优点

| 特性 | 优点 |
|------|------|
| 确定性延迟 | 每次请求的延迟完全一致，适合 SLA 严格的场景 |
| 可预测性能 | 性能与输入数据无关，无 worst-case variance |
| 高利用率 | 编译器可精确安排所有资源，无竞争浪费 |
| 低功耗 | 无动态调度硬件消耗功耗 |

## 4. 与 GPU/CPU 的关键差异

| 维度 | GPU | CPU | Groq TSP |
|------|-----|-----|----------|
| 调度 | 硬件 warp scheduler | OoO 调度器 + 分支预测 | 编译器静态调度 |
| 存储层次 | HBM + L1/L2 cache | DRAM + 多级 cache | 仅 SRAM (无 cache) |
| 数据流 | 隐式 (由 cache 层次决定) | 隐式 | 显式流式 |
| 延迟模型 | 非确定性 | 非确定性 | 完全确定性 |
| 控制复杂度 | 高 (warp scheduler + cache) | 极高 (OoO + 预测) | 极低 (<3% ICU) |

## 5. 性能数据

- **ResNet-50 (batch=1)**: <43 μs 推理延迟, 20,400 images/sec
- **LLaMA-2 70B**: 237 tokens/s
- **片上 SRAM**: 220 MB (全局共享)
- **计算密度**: >1 TOp/s 每 mm²
- **制程**: 14nm, 25×29mm die
- **主频**: 900 MHz

## 6. 关键参考文献

- ISCA 2020: *"Think Fast: A Tensor Streaming Processor (TSP) for Accelerating Deep Learning Workloads"*
- ISCA 2022: *"A Software-defined Tensor Streaming Multiprocessor for Large-scale Machine Learning"*
- Zellic Blog: *"How Is Groq So Fast? An Overview of Groq's TSP Architecture"*
- Groq LPU Architecture: https://groq.com/lpu-architecture
