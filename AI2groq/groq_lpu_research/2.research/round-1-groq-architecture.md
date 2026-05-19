# Round 1 搜索结果 — Groq 架构与论文

> 搜索时间: 2026-05-18
> 搜索来源: IEEE Xplore, Groq Blog, GitHub, Web

## 核心论文

| 论文 | 来源 | 要点 |
|---|---|---|
| Think Fast: A Tensor Streaming Processor (TSP) for Accelerating Deep Learning Workloads | ISCA 2020 | TSP 基础架构：功能切片、streaming 数据流、确定性调度 |
| A Software-Defined Tensor Streaming Multiprocessor for Large-Scale Machine Learning | ISCA 2022（Award-winning）| Multi-TSP 互联、Dragonfly 拓扑、编译器静态网络调度 |
| Direct-On-Chip Hotspot Targeted Microjet Cooling for Ultra-fast Inference at Scale Running on Groq LPU | ITHERM 2024 | 微喷散热方案 |

## TSP 架构关键参数

| 参数 | 值 |
|---|---|
| 工艺 | 14nm |
| 频率 | 900 MHz |
| Die size | 25×29 mm |
| 片上 SRAM | ~230 MB（无 cache 层次）|
| SRAM 带宽 | ~80 TB/s |
| SIMD | 320 lanes（20 tiles × 16 lanes）|
| 指令队列 | 144 个独立队列 |
| 互联 | Dragonfly，最大 10,440 TSPs |

## 功能切片类型

- ICU（Instruction Control Unit）| < 3% die area
- MEM（Memory Slice）| SRAM 读写
- VXM（Vector Execution Module）| 向量运算
- MXM（Matrix Execution Module）| 矩阵乘累加
- SXM（Shift Execution Module）| 移位/旋转

## 官方开源项目

| 项目 | 链接 | 说明 |
|---|---|---|
| GroqFlow | github.com/groq/groqflow | ML workload → GroqChip 编译工具流 |
| groq-python | github.com/groq/groq-python | 官方 Python API |
| LPU-sims | github.com/tastynoob/LPU-sims | 社区 LPU 仿真原型 |

## 关键结论

Groq **没有开放任何硬件 RTL**，全部 proprietary。最接近的参考是 ISCA 论文描述的架构 + 社区 systolic array 开源项目。
