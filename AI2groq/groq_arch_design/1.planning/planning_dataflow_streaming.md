# 数据流与流式架构 — 递归研究规划

> 创建时间: 2026-05-19
> 分析目标: Groq TSP 确定性数据流执行模型

## 研究框架

```
Layer 0: 数据流与流式架构总览
  ├── Layer 1: Streaming dataflow 模型
  │   ├── Layer 2: Stream-based 计算原语
  │   ├── Layer 2: Tensor 在功能切片间的流动机制
  │   └── Layer 2: 数据依赖与控制流的解耦
  ├── Layer 1: 确定性调度
  │   ├── Layer 2: 编译器静态调度算法
  │   ├── Layer 2: 无 OoO / 无分支预测 / 无 cache coherence
  │   └── Layer 2: 功耗/面积节省量化分析
  ├── Layer 1: 流水线设计
  │   ├── Layer 2: ICU→MEM→VXM/MXM/SXM 阶段划分
  │   ├── Layer 2: 指令发射带宽与吞吐
  │   └── Layer 2: Forwarding / bypass 机制
  └── Layer 1: 指令级并行 (ILP)
      ├── Layer 2: 144 指令队列的仲裁逻辑
      ├── Layer 2: 队列间依赖跟踪
      └── Layer 2: 多发射与 ILP 极限
```

## 研究问题 (核心关注)

1. **确定性执行如何节省功耗/面积？**
   - 无 OoO 调度器节省的功耗
   - 无分支预测器节省的面积
   - 无 cache coherence 协议节省的复杂度
   - 静态调度 vs 动态调度的 overhead 对比

2. **确定性执行的代价是什么？**
   - 编译器复杂度
   - 对动态/不规则计算的性能损失
   - 程序员的编程约束
   - 灵活性损失

3. **Stream 模型如何工作？**
   - Tensor 在功能切片间的物理流动路径
   - Stream 元素的生命周期
   - 同步与 barrier 机制

## 搜索关键词

| 轮次 | 方向 | 关键词 |
|------|------|--------|
| R1 | Streaming dataflow | `Groq TSP streaming dataflow deterministic execution`, `Groq tensor streaming architecture` |
| R2 | 确定性调度 | `Groq compile-time scheduling static`, `Groq no out-of-order execution`, `TSP deterministic timing` |
| R3 | 流水线 + ILP | `Groq instruction queue pipeline design`, `Groq TSP ILP 144 queues`, `Groq functional slices pipeline stages` |

## 输出文件

| 阶段 | 文件 | 内容 |
|------|------|------|
| 规划 | `planning_dataflow_streaming.md` | 本文件 |
| R1 | `round-1-streaming-dataflow.md` | Streaming dataflow 模型搜索结果 |
| R2 | `round-2-deterministic-scheduling.md` | 确定性调度搜索结果 |
| R3 | `round-3-pipeline-ILP.md` | 流水线 + ILP 搜索结果 |
| Working | `working_streaming_model.md` | Layer 2: Streaming 实现分析 |
| Working | `working_deterministic_scheduling.md` | Layer 2: 调度算法分析 |
| Working | `working_pipeline_design.md` | Layer 2: 流水线 stage 分析 |
| Working | `working_ilp_queues.md` | Layer 2: 指令队列仲裁分析 |
| Result | `result_dataflow_streaming.md` | 汇总报告 |
