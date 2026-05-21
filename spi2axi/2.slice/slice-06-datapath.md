---
source: SPI2AXI SPEC.pdf
page: 1-3
chapter: datapath
tags: [datapath, data-flow, serial-parallel, fifo]
---

# 数据通路 (Datapath)

## SPI 数据串并转换

SPI接口接收串行数据（1线或4线模式），在SCLK驱动下逐位采样。数据首先经过串并转换模块，将串行比特流转换为并行字节/字数据。

- **1线模式**: 单 bit 串行输入，每 8 个 SCLK 周期完成一个字节接收
- **4线模式 (QSPI)**: 4 bit 并行输入，每 2 个 SCLK 周期完成一个字节接收

## 数据通路路径

### 写数据通路
```
SPI MOSI/SD[3:0] → 串并转换 → 写命令FIFO → CDC异步FIFO → AXI写数据通道 → AXI Slave
```

### 读数据通路
```
AXI Slave → AXI读数据通道 → CDC异步FIFO → TX FIFO → 并串转换 → SPI MISO/SD[3:0]
```

## 跨时钟域数据流

SPI时钟域与AXI时钟域之间通过dual-clock异步FIFO进行数据交换。所有命令、地址、数据在通过FIFO时完成时钟域同步。

- **写数据FIFO**: 缓存SPI侧写入命令和数据，由AXI Master消耗
- **读数据FIFO**: 缓存AXI读取返回数据，由SPI侧消耗并串行输出
