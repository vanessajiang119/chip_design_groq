---
source: SPI2AXI SPEC.pdf
page: 1-3
chapter: sub_modules
tags: [sub-modules, partition, architecture]
---

# 子模块划分 (Sub-Module Partition)

## 模块列表

| 模块名称 | 类型 | 描述 |
|---------|------|------|
| spi_slave | 接口 | SPI Slave 接口模块，支持标准 SPI 和 Quad SPI (QSPI) 两种工作模式 |
| cmd_decoder | Ctrl FSM | 命令解码器/FSM控制器，解析SPI操作码并生成AXI控制信号 |
| async_fifo | FIFO | 异步FIFO跨时钟域桥接，SPI时钟域(50MHz) ↔ AXI时钟域 |
| axi_master | 接口 | AXI4-Lite Master 接口模块，5个独立通道 |
| config_regs | 配置接口 | SPI侧寄存器配置模块，包含工作模式选择和状态寄存器 |
| wrap_ctrl | 地址控制 | 地址环绕控制器，支持可配置的Wrap功能 |

## SPI Slave 模块

SPI Slave作为主动外设（active peripheral），支持标准SPI和四线SPI两种工作模式。最高50MHz SPI时钟，片选低有效。数据线spi_sdi[3:0]和spi_sdo[3:0]支持1线和4线动态切换。

## 命令解码器 (cmd_decoder)

解析SPI操作码(8-bit)，生成AXI传输控制信号。状态机包含IDLE → OPCODE → ADDR → DUMMY → DATA → RESPONSE等状态。支持操作码: READ/WRITE/REG_READ/REG_WRITE等。

## 异步 FIFO (async_fifo)

异步FIFO跨时钟域桥接，SPI时钟域(50MHz) ↔ AXI时钟域。内置dual-clock FIFO实现可靠的CDC传输。包含写数据FIFO和读数据FIFO。

## AXI Master (axi_master)

AXI4-Lite Master接口模块，五个独立通道: AW(写地址), W(写数据), B(写响应), AR(读地址), R(读数据)。支持AXI4-Lite single transfer (AxLEN=0, AxSIZE=2=4bytes)。可配置地址环绕(Wrap)功能。

## 配置寄存器 (config_regs)

SPI侧寄存器配置模块。包含SPI工作模式选择(1线/4线)、状态寄存器、Wrap配置寄存器等。寄存器的地址由操作码(opcode)进行编码。

## 地址环绕控制器 (wrap_ctrl)

可配置地址环绕功能: Wrap=0无环绕，Wrap=N时环绕窗口为N个字(4×N字节)，起始地址4字节对齐，每次+4，到第N个字后回绕到起始地址。
