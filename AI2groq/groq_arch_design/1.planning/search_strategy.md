# Groq 芯片架构分析与详细设计 — 递归搜索策略

> 创建时间: 2026-05-19

## 总体目标

基于已有研究成果（groq_lpu_research + groq_vs_gpu），进一步深入 Groq TSP 芯片的：
1. **架构分析**：各功能切片的微架构原理、数据流方式、设计决策依据
2. **详细设计分析**：RTL 微架构、流水线设计、存储层次、互联拓扑、编译器调度

## 递归架构

```
Layer 0: Groq 芯片架构与详细设计总分析
  ├── Layer 1: TSP 微架构深度分析
  │   ├── Layer 2: ICU 设计
  │   ├── Layer 2: MEM Slice 设计
  │   ├── Layer 2: VXM 设计
  │   ├── Layer 2: MXM 设计
  │   └── Layer 2: SXM 设计
  ├── Layer 1: 数据流与流式架构
  │   ├── Layer 2: Streaming dataflow
  │   ├── Layer 2: 确定性调度
  │   └── Layer 2: 流水线设计
  ├── Layer 1: 存储架构
  │   ├── Layer 2: SRAM tile 组织
  │   ├── Layer 2: 带宽分析
  │   └── Layer 2: NoC 互联
  ├── Layer 1: 编译器架构
  │   ├── Layer 2: GroqFlow 工具流
  │   ├── Layer 2: MLIR 前端
  │   └── Layer 2: 静态调度算法
  └── Layer 1: Multi-TSP 互联架构
      ├── Layer 2: Dragonfly 拓扑
      └── Layer 2: TSP 间通信
```

## 各 Layer 1 搜索方向

### 1. TSP 微架构深度分析 (P0)
- 搜索关键词:
  - `Groq TSP functional slice ICU MEM VXM MXM SXM details`
  - `Groq TSP instruction control unit design`
  - `Groq matrix execution module systolic array`
  - `Groq vector execution module SIMD`
  - `TSP chip floorplan die shot analysis`
- 已有参考: ISCA 2020/2022 papers, EET China analysis

### 2. 数据流与流式架构 (P0)
- 搜索关键词:
  - `Groq TSP streaming dataflow deterministic execution`
  - `Groq instruction queue pipeline design`
  - `Groq TSP ILP instruction level parallelism`
  - `TSP compile-time scheduling vs out-of-order`
- 已有参考: ISCA 2020 论文, Groq blog

### 3. 存储架构 (P0)
- 搜索关键词:
  - `Groq SRAM-only memory hierarchy design`
  - `Groq memory slice MEM tile organization`
  - `Groq TSP memory bandwidth 80TB/s`
  - `Groq NoC interconnect design`
- 已有参考: ISCA 论文, Hot Chips  presentations

### 4. 编译器架构 (P1)
- 搜索关键词:
  - `GroqFlow compiler architecture MLIR`
  - `Groq static scheduling algorithm`
  - `Groq Haskell DSL hardware description`
  - `Groq compiler deterministic timing`
- 已有参考: GroqFlow GitHub, Argonne tutorial

### 5. Multi-TSP 互联架构 (P1)
- 搜索关键词:
  - `Groq dragonfly topology interconnect`
  - `Groq multi-TSP scale-out architecture`
  - `Groq TSP-to-TSP communication latency`
  - `Groq rack-scale LPU system`
- 已有参考: ISCA 2022 论文

## 输出交付物

- Layer 1: 各子 topic 的独立研究报告 (markdown)
- Layer 2: 各子 topic 下的详细设计分析 (markdown)
- Layer 0: 汇总的架构分析 + 详细设计 HTML 报告 (使用 html_chip_design_spec skill)
- Layer 0: 架构图 (使用 drawio_chip_diagram skill)
