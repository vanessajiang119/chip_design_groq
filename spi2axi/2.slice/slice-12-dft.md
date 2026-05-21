<!-- Source: source_raw.md 第1-7页, source_spec.md 第2章 -->
<!-- Chapter: DFT设计 (DFT) -->

# DFT设计 (DFT)

## 概述

**待补充** — 本章为 DFT（可测试性设计）框架，需要在完成 RTL 设计后根据综合工具和工艺库补充。以下为建议的 DFT 策略框架。

## DFT 设计目标

| 目标 | 描述 |
|---|---|
| **扫描链插入 (Scan Chain Insertion)** | 所有时序单元可扫描测试 |
| **扫描压缩 (Scan Compression)** | 减少测试时间和测试数据量 |
| **边界扫描 (Boundary Scan)** | JTAG/IEEE 1149.1 接口测试 |
| **内存 BIST (Memory BIST)** | 内部 FIFO 的 MBIST 实现 |
| **测试覆盖率** | 达到 SoC 级 DFT 覆盖率要求 (typically ≥ 98%) |

## 扫描链设计

- SPI 时钟域和 AXI 时钟域为异步时钟域，建议使用独立的扫描链
- 扫描时钟：
  - SPI 域：spi_sclk（测试模式下由 ATE 提供）
  - AXI 域：axi_aclk（测试模式下由 ATE 提供）
- 扫描模式控制信号：`scan_mode` 或 `test_mode`

## 内存 BIST (MBIST)

内部 dual-clock FIFO 的测试策略：

| FIFO | 深度 | 建议策略 |
|---|---|---|
| cmd_fifo | 待定 | MBIST 或 ATPG 透明测试 |
| wdata_fifo | 待定 | MBIST 或 ATPG 透明测试 |
| rdata_fifo | 待定 | MBIST 或 ATPG 透明测试 |

## 边界扫描

- SPI 接口信号（spi_sclk, spi_cs, spi_sdi, spi_sdo）可通过 JTAG 边界扫描访问
- AXI 接口信号在 SoC 层级通过系统 JTAG 链测试

## DFT 约束

```tcl
# DFT 模式下的时钟约束示例
# (待补充 - 需根据综合工具的 DFT 流程配置)

# 扫描使能信号设置
set_dft_signal -type ScanEnable -port scan_enable -active_state 1
set_dft_signal -type ScanClock  -port spi_sclk    -active_state 1
set_dft_signal -type ScanClock  -port axi_aclk     -active_state 1
set_dft_signal -type Reset      -port spi_rst_n    -active_state 0
set_dft_signal -type Reset      -port axi_areset_n -active_state 0
```

## 待补充项目

- 具体扫描链数目和长度
- 扫描压缩比例
- ATPG 测试覆盖率报告
- 诊断机制（如故障寄存器、错误日志）
- 测试模式下的功耗管理
