# Round 2 搜索结果 — 开源硬件参考与编译器

> 搜索时间: 2026-05-18
> 搜索来源: GitHub, Web, Academic talks

## Systolic Array 开源项目（Verilog）

| 项目 | ⭐ | 说明 | 适用性 |
|---|---|---|---|
| svkocherla/systolic_array | — | 4×4 参数化 systolic array，定点整数 | ⭐⭐⭐ Day1 基础 |
| vbachh43/Transformer_Accelerator_Based_on_FPGA | Popular | 16×16 systolic array，完整 Vivado 项目，PYNQ-Z1 | ⭐⭐⭐ Day1-3 参考 |
| tms4517/2D-Systolic-Array-Multiplier | — | SystemVerilog，可配置 2D | ⭐⭐ 参考 |
| midiareshadi/systolic_array_RTL_implementation | — | Verilog + SystemC | ⭐⭐ 参考 |

## Chisel 项目

| 项目 | 说明 | 适用性 |
|---|---|---|
| FloofyJin/chisel-ai-accelerator | DNN 加速器生成器（类似 Gemmini）| ⭐⭐ 架构参考 |
| jiaaom/HPDLA | 可配置 systolic array，weight-stationary | ⭐⭐⭐ 调度参考 |
| transformer_MM | 完整 Transformer 加速器（GEMM/GEMV/Softmax）| ⭐⭐⭐ Day3 参考 |

## 编译器参考资料

| 资源 | 说明 |
|---|---|
| GroqFlow（官方）| MLIR 前端 + Haskell 后端 |
| MLIR 社区 | 多级 IR，适合 DSA 编译器 |
| Argonne SC23 Groq Tutorial | 官方编程入门 |

## Chinese 技术分析文章

- EET China: 深度拆解 Groq LPU 架构
- 36Kr: 揭开 Groq LPU 神秘面纱
- BAAI: Groq LPU 架构详解
- FPGA 脉动阵列设计实践指南（FPGA 实现教程）
