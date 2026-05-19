# Round 3 搜索结果 — Transformer 算子与实现参考

> 搜索时间: 2026-05-18
> 搜索来源: GitHub, IEEE, Web

## Transformer Hardware Accelerator 开源项目

| 项目 | 架构 | 性能 |
|---|---|---|
| TALOS-V2（Toronto 大学）| 16-channel systolic array，Q4.12 定点 | >50K tokens/sec on Cyclone V |
| vbachh43/FPGA Transformer | 16×16 systolic array，PYNQ-Z1 | 支持 attention 全流程 |
| transformer_MM（Chisel）| GEMM/GEMV/Softmax/I-BERT | 完整 LLM accelerator |

## Transformer 算子硬件映射要点

| 算子 | 硬件映射方式 | Groq 风格实现 |
|---|---|---|
| Q×K^T MatMul | Systolic array 矩阵乘 | MEM→MXM pipeline |
| Softmax | I-BERT 指数近似 + tree reduction | VXM vector 运算 |
| Score×V MatMul | Systolic array 矩阵乘 | MEM→MXM pipeline |
| FFN (MLP) | 两个连续 MatMul | MXM chain |
| LayerNorm | 向量规约 + 乘加 | VXM vector 运算 |

## 关键参考性能数据（Groq LPU）

| Benchmark | Groq LPU | 对比 GPU |
|---|---|---|
| ResNet-50 单 batch | 20,400 img/sec | 4× GPU |
| 单图延迟 | < 49 μs | — |
| 计算密度 | > 1 TeraOp/s/mm² @ 14nm | — |
| Llama 3 推理吞吐 | 1,300 tokens/s/user | — |

## 实现目标：3天 mini Groq-like 系统

建议基于已有的开源 systolic array 项目构建，专注于理解 Groq 的核心设计理念而非复制其实现。
