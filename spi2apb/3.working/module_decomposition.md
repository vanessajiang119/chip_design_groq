# 模块分解 — SPI2APB Bridge

> 生成时间: 2026-05-20
> 来源: 2.research/round-1-qspi_protocol.md, round-2-apb_protocol.md, round-3-bridge_architecture.md

---

## 模块列表

| # | 模块名 | 类型 | 时钟域 | 简要描述 |
|---|--------|------|--------|---------|
| 1 | `qspi_slave` | 接口 | SCLK (200MHz) | QSPI 从机接口，解析 4-bit SPI 命令/地址/数据，支持 Mode 0/3 |
| 2 | `cmd_decoder` | Ctrl FSM | SCLK | 命令解码器，解析 SPI 命令 (READ/WRITE/FAST_READ/Quad IO) |
| 3 | `async_fifo` | FIFO | 双时钟 | 异步 FIFO 桥接 SCLK↔PCLK，写数据/读数据/命令三通道 |
| 4 | `apb_master` | 接口 | PCLK | APB 2.0 主机接口，40bit 地址/128bit 数据 |
| 5 | `config_regs` | 配置接口 | PCLK | 配置寄存器组，SPI 配置/状态/中断控制 |

## 模块间接口关系

```
                              ┌─────────────────────────────────┐
                              │        SPI2APB Bridge Top       │
                              │                                  │
SPI Pads ──►┌──────────┐ cmd ─►┌───────────┐ req ─►┌─────────┐─► APB I/F
             │  qspi_   │       │  cmd_     │       │ apb_    │
 IO0-3 ──►   │  slave   │ addr ─►│ decoder   │ data ─►│ master  │
 CS_N ──►   │(200MHz)  │       │(SCLK)    │       │ (PCLK)  │
 SCLK ──►   └────┬─────┘       └───────────┘       └─────────┘
                 │                  │                    ▲
                 │  cfg_if          │ intr               │
                 │                  ▼                    │
                 │           ┌────────────┐             │
                 │           │ async_fifo │◄═══════════►│
                 │           │  (CDC)     │             │
                 │           └────────────┘             │
                 │                                      │
                 │           ┌────────────┐             │
                 └──────────►│ config_    │◄────────────┘
                             │  regs      │  (APB Slave)
                             │ (PCLK)     │
                             └────────────┘
```

## 关键数据流

### 写数据流 (SPI → APB)
```
qspi_slave → cmd_decoder (cmd+addr) → async_fifo (write_data channel) → apb_master
```

### 读数据流 (APB → SPI)
```
apb_master → async_fifo (read_data channel) → qspi_slave (serialize output)
```

### 配置流
```
config_regs → qspi_slave (SPI mode control)
config_regs → apb_master (base address config)
```

## 模块间信号

| 源模块 | 目标模块 | 信号 | 位宽 | 描述 |
|--------|---------|------|------|------|
| qspi_slave | cmd_decoder | cmd_dec_valid, cmd_data[7:0] | 9 | 命令字节有效 + 命令编码 |
| qspi_slave | cmd_decoder | addr_valid, addr[31:0] | 33 | 地址有效 + 地址 |
| qspi_slave | async_fifo | wdata, wdata_valid | 129 | 写数据 (128bit + valid) |
| cmd_decoder | async_fifo | req_type, req_addr[39:0] | 41 | 请求类型 (读/写) + APB 地址 |
| async_fifo | apb_master | apb_req, apb_addr[39:0], apb_wdata[127:0] | 匹配 | APB 请求 |
| apb_master | async_fifo | apb_rdata[127:0], apb_done, apb_err | 130 | 读返回数据 |
| async_fifo | qspi_slave | rdata[127:0], rdata_valid | 129 | 读数据返回 |
| cmd_decoder | config_regs | intr_event | N | 中断事件 |
| config_regs | qspi_slave | spi_mode, spi_en | 2 | SPI 配置 |
| config_regs | apb_master | base_addr[39:0] | 40 | APB 基地址 |
