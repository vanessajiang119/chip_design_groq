# 调研报告 — Round 3: SPI2APB Bridge 架构

> 生成日期: 2026-05-20
> 研究方向: 参考设计、CDC 方案、地址映射策略

---

## 1. SPI2APB Bridge 架构概述

SPI2APB bridge 是一种将 SPI 从机接口转换为 APB master 接口的桥接 IP，常见于 SoC 中用于配置内部寄存器。

### 1.1 顶层架构框图

```
┌─────────────────────────────────────────────────────────┐
│                   SPI2APB Bridge Top                     │
│                                                          │
│  ┌──────────┐   ┌───────────┐   ┌──────────┐            │
│  │ QSPI     │   │ CMD       │   │ Async    │   ┌──────┐ │
│  │ Slave    │──>│ Decoder   │──>│ FIFO     │──>│ APB  │ │
│  │ (200MHz) │   │ + Ctrl    │   │ (CDC)    │   │ Mast.│ │
│  └──────────┘   └───────────┘   └──────────┘   └──────┘ │
│       │               │               │                  │
│       v               v               v                  │
│  ┌──────────────────────────────────────┐                │
│  │ Config Registers (APB Slave I/F)     │                │
│  └──────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────┘
```

### 1.2 数据流

**写操作 (SPI → APB)**:
1. SPI Master 发送 WRITE 命令 + 地址 + 数据
2. qspi_slave 接收串行数据，转换为并行
3. cmd_decoder 解析命令，生成写请求
4. 数据通过 async_fifo 跨时钟域到 APB 时钟域
5. apb_master 执行 APB 写传输
6. 状态写入 config_regs

**读操作 (APB → SPI)**:
1. SPI Master 发送 READ 命令 + 地址
2. qspi_slave 接收命令/地址
3. cmd_decoder 解析命令，生成读请求
4. 请求通过 async_fifo 跨时钟域
5. apb_master 执行 APB 读传输
6. 读数据通过 async_fifo (读数据通道) 返回
7. qspi_slave 将并行数据串行化输出

## 2. CDC (Clock Domain Crossing) 方案

### 2.1 时钟域分析

| 时钟域 | 频率 | 模块 |
|--------|------|------|
| SCLK 域 | 200 MHz | qspi_slave, cmd_decoder (部分) |
| PCLK 域 | 50-200 MHz (待定) | apb_master, config_regs |
| 异步桥接 | — | async_fifo (写/读通道) |

### 2.2 CDC 策略

**数据通道**: 使用异步 FIFO 进行跨时钟域传输
- 写数据 FIFO: SCLK 域写入 → PCLK 域读出
- 读数据 FIFO: PCLK 域写入 → SCLK 域读出
- 命令/地址 FIFO: SCLK 域写入 → PCLK 域读出

**控制信号**: 使用两级同步器 + 握手协议
- 请求/应答握手: SCLK 域请求 → PCLK 域应答
- 状态信号 (如 FIFO full/empty): 各自时钟域产生

### 2.3 异步 FIFO 设计参数

| 参数 | 写数据 FIFO | 读数据 FIFO | 命令 FIFO |
|------|------------|------------|----------|
| 数据宽度 | 128 bit | 128 bit | 40 bit |
| 深度 | 8 | 8 | 4 |
| 写时钟 | SCLK (200MHz) | PCLK | SCLK |
| 读时钟 | PCLK | SCLK (200MHz) | PCLK |
| 指针类型 | 格雷码 | 格雷码 | 格雷码 |
| 空/满标志 | 同步读取指针 | 同步写入指针 | 同步读取指针 |

## 3. 地址映射策略

### 3.1 SPI 地址到 APB 地址映射

```
SPI CMD 地址: [23:0] 或 [31:0] (24/32-bit 可变)
APB 地址:    [39:0]

映射关系:
  APB_ADDR[39:0] = APB_BASE_ADDR[39:0] + {zeros, SPI_ADDR[23:0]}

  APB_BASE_ADDR: 可由 config_regs 配置
  SPI_ADDR: 来自 SPI 命令中的地址字段
```

### 3.2 地址空间划分

| 地址范围 | 用途 | 说明 |
|---------|------|------|
| 0x0000_00_0000 - 0x0000_00_FFFF | 配置寄存器 | 64KB 内部配置空间 |
| 0x0000_01_0000 - 0xFFFF_FF_FFFF | 外部 APB 外设 | 基地址可配 |

## 4. 配置寄存器设计

### 4.1 寄存器列表

| 偏移地址 | 寄存器名 | 宽度 | 访问 | 说明 |
|---------|---------|------|------|------|
| 0x00 | CTRL | 32 | R/W | 控制寄存器 (SPI mode, reset, enable) |
| 0x04 | STATUS | 32 | R | 状态寄存器 (busy, fifo_status, error) |
| 0x08 | INTR_EN | 32 | R/W | 中断使能 |
| 0x0C | INTR_STAT | 32 | R/W1C | 中断状态 |
| 0x10 | SPI_CFG | 32 | R/W | SPI 配置 (mode, clock_div, addr_width) |
| 0x14 | APB_BASE_ADDR_L | 32 | R/W | APB 基地址低 32bit |
| 0x18 | APB_BASE_ADDR_H | 32 | R/W | APB 基地址高 8bit |

### 4.2 中断事件

| 中断位 | 事件 | 清除方式 |
|--------|------|---------|
| bit 0 | APB 传输完成 | W1C |
| bit 1 | APB 传输错误 (PSLVERR) | W1C |
| bit 2 | FIFO 溢出 | W1C |
| bit 3 | FIFO 下溢 | W1C |

## 5. 业界参考设计

参考设计包括：
- OpenCores SPI2APB bridge 项目
- 各厂商 (Xilinx, Intel) SPI-to-AXI/AHB/APB bridge 方案
- 开源 Verilog SPI controller with APB interface

**设计目标**:
- 保持低延迟：SPI 命令到 APB 传输的最小延迟
- 确保数据完整性：异步 FIFO 满/空标志防溢出/下溢
- 支持背靠背传输：SPI 连续命令不丢失

## 6. 关键设计决策

| 决策点 | 方案 | 理由 |
|--------|------|------|
| FIFO 类型 | 异步双时钟 FIFO | SCLK 与 PCLK 异步 |
| FIFO 深度 | 8 (数据), 4 (命令) | 平衡面积与吞吐 |
| 地址映射 | 基地址 + 偏移 | 灵活适应不同 SoC 布局 |
| SPI 模式 | Mode 0/3 可配置 | 兼容不同 SPI Master |
| 支持命令 | READ/WRITE/FAST_READ/Quad | 通用 SPI Flash 命令集 |

---

**参考**: AMBA APB Protocol Spec, Quad SPI Flash 标准, 开源 SPI 控制器设计
