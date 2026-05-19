# 搜索策略与需求分析

## 研究目标
用3天时间完成 Groq LPU 芯片的：文档设计 / RTL 设计 / 软件开发 / 编译器设计 / 跑通小型 Transformer 算子

## 研究方向拆分

| # | 方向 | 优先级 | 搜索来源 |
|---|---|---|---|
| 1 | Groq TSP 架构设计（ISCA 论文）| P0 | IEEE Xplore, Groq Blog |
| 2 | 开源硬件实现参考（Systolic Array）| P0 | GitHub |
| 3 | GroqFlow 编译器工具流 | P1 | GitHub, PyPI |
| 4 | Haskell DSL 硬件设计方法 | P1 | Academic talks |
| 5 | Transformer 算子硬件映射 | P1 | GitHub, IEEE |
| 6 | 类似架构的 FPGA 实现 | P2 | GitHub |

## 推荐的社区参考项目
- svkocherla/systolic_array — Verilog 基础 systolic array
- vbachh43/Transformer_Accelerator_Based_on_FPGA — FPGA Transformer 加速器
- FloofyJin/chisel-ai-accelerator — Chisel DNN 加速器
- tastynoob/LPU-sims — Python LPU 仿真器
