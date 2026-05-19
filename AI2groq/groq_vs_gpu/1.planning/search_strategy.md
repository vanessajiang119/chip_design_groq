# Groq vs GPU 架构对比 — 搜索策略

> 创建时间: 2026-05-18

## 研究目标

系统对比 Groq TSP (Tensor Streaming Processor) 与主流 GPU (NVIDIA CUDA/AMD CDNA) 在架构理念、计算模型、存储层次、编程方式、性能特性等方面的根本差异。

## 三轮搜索规划

### Round 1: 架构基础对比
- **Groq 侧**: TSP 微架构细节 — ICU/MEM/VXM/MXM/SXM 各功能切片的设计原理、数据流方式
- **GPU 侧**: NVIDIA SM 架构、Warp 调度、Tensor Core、CUDA core 结构
- **搜索关键词**: 
  - `Groq TSP microarchitecture` `Groq deterministic execution`
  - `NVIDIA SM architecture` `warp scheduling` `tensor core microarchitecture`
  - `GPU SIMT vs systolic array`

### Round 2: 存储与编程模型
- **Groq 侧**: SRAM-only 流式存储、无 cache 一致性、确定性调度编译器
- **GPU 侧**: HBM + L1/L2 cache 层次、GDDR 与 HBM 选择、CUDA/Triton 编程
- **搜索关键词**:
  - `Groq memory hierarchy SRAM streaming`
  - `GPU memory hierarchy HBM cache coherence`
  - `GroqFlow compiler static scheduling`
  - `CUDA programming model vs Groq`

### Round 3: 性能与生态对比
- **Groq 侧**: MLPerf 结果、LLM 推理延迟与吞吐、能效比
- **GPU 侧**: H100/B200 性能数据、同类 benchmark 数据
- **搜索关键词**:
  - `Groq LPU benchmark latency throughput`
  - `NVIDIA H100 inference benchmark LLM`
  - `Groq vs GPU energy efficiency comparison`
  - `Groq software ecosystem`

## 输出交付物

- 最终 HTML 报告 (NVIDIA 白色主题风格)
- 对比表格 (架构、性能、功耗、生态)
- Draw.io 架构对比图
- 3天实现计划 (可选)
