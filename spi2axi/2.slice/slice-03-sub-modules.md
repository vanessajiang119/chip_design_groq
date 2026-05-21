<!-- Source: source_raw.md 第1-7页, source_spec.md 第2-8章 -->
<!-- Chapter: 子模块划分 (Sub-Module Partition) -->

# 子模块划分 (Sub-Module Partition)

## 模块层次结构

SPI2AXI Bridge 可划分为以下主要子模块：

```
SPI2AXI_Bridge (Top)
├── spi_slave_if          — SPI 从设备接口模块
│   ├── spi_io            — SPI 串行数据收发（标准 SPI / QSPI 模式）
│   └── spi_cmd_decoder   — SPI 命令解析（opcode + address 解码）
├── cdc_fifo              — 跨时钟域 FIFO 模块
│   ├── cmd_fifo          — 命令/地址跨时钟域传输（SPI → AXI）
│   ├── wdata_fifo        — 写数据跨时钟域传输（SPI → AXI）
│   └── rdata_fifo        — 读数据跨时钟域传输（AXI → SPI）
├── axi_master_if         — AXI4-Lite 主接口模块
│   ├── axi_wr_ctrl       — AXI 写通道控制器（AW + W + B）
│   └── axi_rd_ctrl       — AXI 读通道控制器（AR + R）
├── wrap_addr_gen         — Wrap 地址生成器（可选）
├── csr_regfile           — 配置寄存器文件
└── fsm_ctrl              — 主状态机控制器
```

## 子模块功能描述

### 1. spi_slave_if — SPI 从设备接口
- 支持标准 SPI（1-wire）和 QSPI（4-wire）模式
- 串行数据收发：将 SPI 串行数据转换为并行数据
- 命令解码：解析操作码（opcode）和地址

### 2. cdc_fifo — 跨时钟域 FIFO
- 使用 dual-clock FIFO 实现 SPI 时钟域和 AXI 时钟域的可靠数据传输
- 包含独立的命令 FIFO、写数据 FIFO 和读数据 FIFO
- 防止亚稳态传播，保证 CDC 可靠性

### 3. axi_master_if — AXI4-Lite 主接口
- 处理 AXI4-Lite 协议的所有 5 个通道
- 写操作：通过 AW 通道发送地址，W 通道发送数据，B 通道接收响应
- 读操作：通过 AR 通道发送地址，R 通道接收数据

### 4. wrap_addr_gen — Wrap 地址生成器
- 当 Wrap 功能启用时，自动管理和回绕地址
- 地址自增逻辑和回绕判断

### 5. csr_regfile — 配置寄存器文件
- 存储 SPI 工作模式配置
- 存储 Wrap 配置参数

### 6. fsm_ctrl — 主状态机控制器
- 控制 SPI 事务到 AXI 事务的转换流程
- 管理各子模块的协同工作

## 模块接口关系

```
SPI Pins ──→ spi_slave_if ──→ cdc_fifo ──→ axi_master_if ──→ AXI4-Lite Bus
                 │                │               │
                 ↓                ↓               ↓
              csr_regfile ◄── fsm_ctrl ──→ wrap_addr_gen
```
