---
source: SPI2AXI SPEC.pdf
page: N/A
chapter: dft
tags: [dft, scan, test]
status: 待补充
---

# DFT 设计 (DFT Design)

**状态**: 待补充 — 源文档未包含DFT设计章节。

## 建议DFT方案

### 扫描链 (Scan Chain)
- 所有时序单元（FF）应接入扫描链
- 可选择单条或多条扫描链（由面积和测试时间决定）
- 测试时钟（scan_clk）和测试使能（scan_enable）管脚复用

### 测试模式 (Test Mode)
- 外部测试模式引脚（test_mode）控制功能/测试模式切换
- 测试模式下所有时钟通过MUX切换到测试时钟

### 边界扫描 (Boundary Scan)
- SPI接口管脚可选择性接入边界扫描链
- AXI接口管脚建议通过SoC级边界扫描覆盖

### Memory BIST
- 异步FIFO（dual-clock FIFO）建议使用MBIST覆盖
- 使用独立的BIST控制器和BIST时钟
