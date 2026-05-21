---
source: SPI2AXI SPEC.pdf
page: 1
chapter: clock_reset
tags: [clock, reset, cdc, dual-clock]
---

# 时钟与复位 (Clock & Reset)

## 时钟域划分

SPI2AXI IP包含两个独立的时钟域：

| 时钟域 | 频率 | 描述 |
|--------|------|------|
| SPI 时钟域 | 最高50MHz | SPI串行时钟域，由外部SPI Master提供spi_sclk |
| AXI 时钟域 | 取决于SoC | SoC系统AXI总线时钟域 |

## 跨时钟域处理 (CDC)

SPI时钟域与AXI时钟域完全分离，通过内置 dual-clock FIFOs（双时钟FIFO）实现可靠的数据传输。每个FIFO具有独立的写时钟和读时钟端口：

- **写时钟**: SPI时钟域（spi_sclk或片上同步时钟）
- **读时钟**: AXI时钟域（soc_axi_aclk）

## 复位方案

默认采用异步复位同步释放的复位同步器方案，确保复位释放时序满足CDC要求。所有FIFO和状态机在复位后回到初始状态。
