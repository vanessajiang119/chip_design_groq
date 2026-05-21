# SPI2AXI Bridge — Source Specification Analysis

## 1. 文档概述 (Document Overview)

- **文档名称 (Document Name)**: SPI2AXI SPEC
- **页数 (Pages)**: 7
- **语言 (Language)**: 中文 + 英文专业术语 (Chinese + English technical terminology)
- **文档类型 (Document Type)**: Block-level IP 规格说明 (Block-level IP Specification)

## 2. IP 概述 (IP Overview)

- **名称 (Name)**: SPI2AXI Bridge
- **功能 (Function)**: SPI Slave to AXI4-Lite Master 桥接模块，将 SPI 从设备接口转换为 AXI 主设备接口，允许通过 SPI 总线访问 AXI 总线上的存储器和外设。
- **应用场景 (Applications)**:
  - 系统调试和配置接口 (System debug and configuration interface)
  - 低引脚数系统总线扩展 (Low pin-count system bus expansion)
  - 嵌入式系统固件更新 (Embedded system firmware update)
  - 芯片测试和验证接口 (Chip test and verification interface)
  - SoC config 配置空间访问 (SoC configuration space access)

## 3. 主要特性 (Key Features)

### 3.1 SPI 接口特性
- 支持 **标准 SPI (Standard SPI)** 和 **四线 SPI / QSPI (Quad SPI)** 两种工作模式
- SPI Slave 作为**主动外设 (active peripheral)**，无需 SoC 内部 CPU 干预即可完成 SoC 功能配置、状态观测等功能
- SPI 时钟频率: 50 MHz (max)

### 3.2 AXI 接口特性
- **AXI4-Lite** 主设备接口 (Master Interface)
- 仅支持单次传输 (single transfer)，每个 burst 长度固定为 1 (AxLEN = 0)
- AxSIZE 通常配置为 2，表示每次传输 1 个 32-bit word (4 bytes)

### 3.3 跨时钟域处理 (CDC)
- SPI 时钟域与 AXI 时钟域分离，时钟域相互独立
- 内置 **dual-clock FIFOs (双时钟 FIFO)**，实现 SPI 时钟域与 SoC AXI 时钟域之间的可靠跨时钟域传输

### 3.4 Wrap 地址环绕功能
- 支持可配置的地址 Wrap 功能
- **Wrap = 0**: 无环绕功能
- **Wrap = N (N > 0)**: 启用地址环绕模式，环绕窗口大小为 N 个 word (4xN bytes)
- 起始地址必须按 4 字节对齐
- 地址从起始地址开始，每次传输后地址 +4，访问完第 N 个 word 后自动回绕到起始地址

## 4. 接口信号 (Interface Signals)

### 4.1 SPI 接口信号 (SPI Interface Signals)

| 信号名称 (Signal) | 方向 (Direction) | 描述 (Description) |
|---|---|---|
| `spi_sclk` | Input | SPI 串行时钟, 50 MHz |
| `spi_cs` | Input | SPI 片选信号，低有效 (Active Low) |
| `spi_sdi[3:0]` | Input | SPI 数据输入线（支持 1-wire 或 4-wire 模式） |
| `spi_sdo[3:0]` | Output | SPI 数据输出线（支持 1-wire 或 4-wire 模式） |

### 4.2 AXI 主设备接口 (AXI Master Interface)

AXI4-Lite 主设备接口，包含 5 个独立通道：

| 通道 (Channel) | 描述 (Description) |
|---|---|
| **写地址通道 (AW)** | Write Address Channel |
| **写数据通道 (W)** | Write Data Channel |
| **写响应通道 (B)** | Write Response Channel |
| **读地址通道 (AR)** | Read Address Channel |
| **读数据通道 (R)** | Read Data Channel |

## 5. 可配置参数 (Configurable Parameters)

| 参数 (Parameter) | 默认值 (Default) | 描述 (Description) |
|---|---|---|
| `AXI_ADDR_WIDTH` | 32 | AXI 地址总线宽度 (AXI address bus width) |
| `AXI_DATA_WIDTH` | 32 | AXI 数据总线宽度 (AXI data bus width) |
| `AXI_ID_WIDTH` | 3 | AXI ID 信号宽度 (AXI ID signal width) |
| `DUMMY_CYCLES` | 32 | SPI 读操作虚拟周期数，实际 Dummy Cycle = 此处配置值 + 1 |

## 6. 操作流程 (Operation Flow)

### 6.1 写操作序列 (Write Sequence)

1. **(可选)** 配置 SPI 参数 (1-wire 或 4-wire 模式)
2. SPI 主机发送写命令和地址
3. 控制器解析命令并同步到 AXI 时钟域
4. AXI 桥接发起写地址事务 (AW channel)
5. 通过 FIFO 传输写数据 (W channel)
6. 等待 AXI 写响应完成 (B channel)

### 6.2 读操作序列 (Read Sequence)

1. **(可选)** 配置 SPI 参数 (1-wire 或 4-wire 模式)
2. SPI 主机发送读命令和地址
3. 控制器同步读请求到 AXI 时钟域
4. AXI 桥接发起读地址事务 (AR channel)
5. 从 AXI 总线读取数据到 TX FIFO (R channel)
6. 通过 SPI 接口返回读取的数据

## 7. 命令格式 (Command Format)

### 7.1 SPI 帧格式 (SPI Frame Format)

SPI 事务帧结构如下：

| 字段 (Field) | 宽度 (Width) | 描述 (Description) |
|---|---|---|
| **操作码 (Opcode)** | 8 bits | 指定操作类型（读/写）及寄存器地址编码 |
| **地址 (Address)** | 32 bits | 内存访问地址，MSB first（仅在内存访问时使用） |
| **虚拟周期 (Dummy Cycles)** | 可编程 | 读操作插入的等待周期，数量由 `DUMMY_CYCLES` 参数配置（实际 = DUMMY_CYCLES + 1） |
| **数据 (Data)** | 32 bits | 实际传输的读写数据，MSB first |

- 寄存器地址由操作码直接编码（无需 32-bit 地址字段）
- 数据始终以 MSB first 方式传输
- 控制器基于 FSM (有限状态机) 实现状态转换

### 7.2 SPI 侧寄存器设定 (SPI-side Register Configuration)

SPI 侧寄存器用于配置工作模式，包括但不限于：
- 1-wire / 4-wire 模式选择
- 其他 SPI 协议参数

## 8. 特殊功能 (Special Features)

### 8.1 Wrap 地址环绕 (Address Wrap)

- 由于 AXI4-Lite 仅支持 single transfer (AxLEN = 0)，SPI2AXI 引入了可配置的地址 Wrap 功能来模拟连续地址访问
- **Wrap = 0**: 无环绕，每次访问地址不自动回绕
- **Wrap = N (N > 0)**: 地址环绕模式，窗口大小 = N words = 4xN bytes
- 起始地址必须 4-byte 对齐
- 地址序列示例 (Wrap = 2, 起始地址 'h100):
  - Burst 0: 'h100 → Burst 1: 'h104 → Burst 2: 'h100 (回绕) → Burst 3: 'h104 → ...

### 8.2 QSPI 读写时序 (QSPI Read/Write Timing)

- 支持 Quad SPI (4-wire) 模式下的读写操作
- QSPI 模式下，4 条数据线 (spi_sdi[3:0] / spi_sdo[3:0]) 同时传输数据，实现 4x 数据吞吐率提升

---

*分析日期: 2026-05-21*
*分析依据: SPI2AXI SPEC (7-page PDF source)*
