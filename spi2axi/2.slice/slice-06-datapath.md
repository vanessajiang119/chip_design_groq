<!-- Source: source_raw.md 第1-4页, source_spec.md 第2-7章 -->
<!-- Chapter: 数据通路 (Datapath) -->

# 数据通路 (Datapath)

## 概述

SPI2AXI Bridge 的数据通路分为 SPI 域和 AXI 域两个时钟域，通过 dual-clock FIFO 相连。

## 数据通路结构

```
SPI 时钟域                               AXI 时钟域
┌────────────────────┐              ┌────────────────────┐
│                    │    cmd_fifo  │                    │
│  SPI Slave I/F ────┼─────▶───────┼──▶ AXI Master I/F  │
│  (串行↔并行)      │              │   (AXI4-Lite)      │
│                    │  wdata_fifo  │                    │
│  SPI RX Reg  ──────┼─────▶───────┼──▶ AXI W Channel   │
│                    │              │                    │
│  SPI TX Reg  ◀─────┼─────┼───────┼──▶ AXI R Channel   │
│                    │  rdata_fifo  │                    │
└────────────────────┘              └────────────────────┘
```

## 数据通路关键组件

### 1. SPI 接收通路
- `spi_sdi` 串行输入 → 移位寄存器 → 并行数据输出
- 支持 1-bit 和 4-bit 两种移位模式
- 接收数据包括：操作码 (8-bit)、地址 (32-bit)、写数据 (32-bit)

### 2. SPI 发送通路
- 并行数据输入 → 移位寄存器 → `spi_sdo` 串行输出
- 读操作时，从 rdata_fifo 读取数据并串行发送
- 数据以 MSB first 方式传输

### 3. CDC FIFO 数据通路
- **cmd_fifo**：传输操作码和地址信息（SPI → AXI）
  - 宽度：地址宽度 + 控制位
  - 深度：可配置
- **wdata_fifo**：传输写数据（SPI → AXI）
  - 宽度：32-bit
  - 深度：可配置
- **rdata_fifo**：传输读数据（AXI → SPI）
  - 宽度：32-bit
  - 深度：可配置

### 4. AXI 数据通路
- **写数据通路**：wdata_fifo → AXI WDATA → AXI 总线
- **读数据通路**：AXI RDATA → rdata_fifo → SPI 发送寄存器
- 地址通路：cmd_fifo → AXI AWADDR/ARADDR

## SPI 帧格式

| 字段 (Field) | 宽度 (Width) | 描述 (Description) |
|---|---|---|
| **操作码 (Opcode)** | 8 bits | 指定操作类型（读/写）及寄存器地址编码 |
| **地址 (Address)** | 32 bits | 内存访问地址，MSB first（仅在内存访问时使用） |
| **虚拟周期 (Dummy Cycles)** | 可编程 | 读操作插入的等待周期，DUMMY_CYCLES 配置（实际 = DUMMY_CYCLES + 1） |
| **数据 (Data)** | 32 bits | 实际传输的读写数据，MSB first |

- 寄存器地址由操作码直接编码（无需 32-bit 地址字段）
- 数据始终以 MSB first 方式传输

## 数据宽度转换

| 路径 | 输入宽度 | 输出宽度 | 转换方式 |
|---|---|---|---|
| SPI 1-wire → 并行 | 1-bit | 8/32-bit | 串行移位寄存器 |
| SPI 4-wire → 并行 | 4-bit | 8/32-bit | 4-bit 并行移位 |
| 并行 → SPI 1-wire | 8/32-bit | 1-bit | 串行移位输出 |
| 并行 → SPI 4-wire | 8/32-bit | 4-bit | 4-bit 并行输出 |
