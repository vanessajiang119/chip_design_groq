---
source: SPI2AXI SPEC.pdf
page: 2
chapter: interface
tags: [spi-signals, axi-signals, pin-list]
---

# 接口定义 (Interface Definition)

## SPI 接口信号

| 信号名称 | 方向 | 描述 |
|---------|------|------|
| spi_sclk | 输入 | SPI串行时钟，50MHz |
| spi_cs | 输入 | SPI片选信号（低有效） |
| spi_sdi[3:0] | 输入 | SPI数据输入线，支持1线或4线模式 |
| spi_sdo[3:0] | 输出 | SPI数据输出线，支持1线或4线模式 |

## AXI 主设备接口

AXI4-Lite 主设备接口，包含5个独立通道：

- **写地址通道（AW）**
- **读地址通道（AR）**
- **写数据通道（W）**
- **读数据通道（R）**
- **写响应通道（B）**

## 可配置参数

| 参数 | 默认值 | 描述 |
|------|--------|------|
| AXI_ADDR_WIDTH | 32 | AXI地址总线宽度 |
| AXI_DATA_WIDTH | 32 | AXI数据总线宽度 |
| AXI_ID_WIDTH | 3 | AXI ID信号宽度 |
| DUMMY_CYCLES | 32 | SPI读操作虚拟周期数，实际Dummy_cycle=配置值+1 |
