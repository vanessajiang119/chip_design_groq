# Groq TSP 存储架构分析 — 规划

> **创建时间**: 20260519-1530
> **分析目标**: 深入解析 Groq TSP 的 SRAM-only 无 cache 存储架构及其对 AI 推理性能的影响

---

## 1. 分析范围 (Scope)

### 1.1 核心研究对象
- Groq TSP (Tensor Streaming Processor) 的 SRAM 存储子系统
- 230MB 片上 SRAM 的组织方式与物理分布
- 80TB/s 带宽的实现路径
- 无 cache / 无 DRAM 接口的设计哲学
- 编译器管理的显式数据搬移机制

### 1.2 对比基线
- NVIDIA GPU HBM 存储层次 (HBM2e/HBM3)
- Graphcore IPU 的 SRAM-only 方案
- Cerebras Wafer-Scale Engine

---

## 2. 研究维度 (Research Dimensions)

### 维度 A: SRAM Tile 物理组织
- MEM slice 数量、每个 slice 包含的 SRAM tile 数量
- 每个 tile 的容量、位宽、频率
- SRAM 宏单元 (macro) 微架构

### 维度 B: 带宽实现路径
- SRAM 总位宽 = 每个 SRAM bank 位宽 × bank 数 × 并发路径数
- 频率与数据传输率的关系
- 与 HBM2e/HBM3 的带宽密度对比

### 维度 C: 无 Cache 存储层次
- Streaming buffer 设计模式
- 编译器 (GroqCompiler) 如何管理数据布局
- 显式 DMA / 数据搬移指令
- 与传统 cache 层次的延迟/面积/功耗对比

### 维度 D: 片上互联 (NoC)
- 功能切片 (Tile) 间的数据通路拓扑
- Crossbar 结构与带宽分配
- 拥塞管理与 QoS

---

## 3. 研究计划 (Research Plan)

### Round 1: 架构概览与 SRAM 组织 (ISCA/Hot Chips 论文)
- Groq TSP 整体架构
- MEM tile/Slice 组织
- SRAM 容量与分布

### Round 2: 带宽分析与存储层次 (Deep Dive)
- 80TB/s 带宽的定量计算
- Streaming buffer 工作机制
- 性能定量模型

### Round 3: 互联与编译器优化 (System View)
- NoC 拓扑与拥塞控制
- 编译器数据布局优化策略
- 与 GPU/其他架构的对比

---

## 4. 输出产物 (Deliverables)

| 阶段 | 文件 | 内容 |
|------|------|------|
| Planning | `planning.md` | 本规划文件 |
| Research R1 | `round-1-sram-organization.md` | SRAM tile 组织与架构概览 |
| Research R2 | `round-2-bandwidth-hierarchy.md` | 带宽定量分析与存储层次 |
| Research R3 | `round-3-noc-compiler.md` | NoC 互联与编译器优化 |
| Working | `working/` | Layer 2 深入分析 |
| Result | `result/` | 汇总报告 |

---

## 5. 关键参考文献 (Initial Reference List)

- Jouppi et al., "Ten Lessons From Three Generations Shaped Google's TPU" — cache-less design motivation
- Groq ISCA 2020 / Hot Chips 2020 papers
- GroqCompiler design papers
- Dennis Abts et al., "The Groq TSP Architecture" (if available)
- Various analyses of SRAM bandwidth vs HBM bandwidth
