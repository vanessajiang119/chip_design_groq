# SPI2AXI Bridge — Low Level Design Document (LLD)

**文档版本**: v1.0
**日期**: 2026-05-21
**设计模块**: SPI2AXI Bridge (SPI Slave to AXI4-Lite Master)
**文档类型**: Block微架构LLD (14-Chapter AI-Executable Template)

---

## 第1章 模块概述 (Module Overview)

### 1.1 功能描述

SPI2AXI Bridge IP 是一个将 SPI Slave（串行外设接口从设备）协议转换为 AXI4-Lite Master（高级可扩展接口主设备）协议的桥接模块。该模块作为主动外设（Active Peripheral），允许外部 SPI Master（微控制器、FPGA 或测试设备）通过标准的 SPI 总线访问 SoC 内部的 AXI 总线地址空间，包括系统内存（Memory Space）和配置寄存器空间（Configuration Register Space）。因为 SPI 是通用数字接口，SPI2AXI 可以在桌面 PC 上使用通用的 SPI 调试工具进行 SoC 的 pattern 调试和实验室 bringup 验证，极大降低了芯片验证阶段的硬件依赖。

SPI2AXI 的核心设计思路是在两个完全异步的时钟域（SPI 时钟域和 AXI 系统时钟域）之间建立一个可靠的数据传输通道。外部 SPI Master 在低速 SPI 时钟域（最高 50MHz）发送命令帧，SPI2AXI 内部的状态机对命令帧进行解析、解码生成 AXI 总线事务控制信号，并通过 dual-clock 异步 FIFO 将命令和数据同步到 AXI 时钟域，最终由 AXI Master 接口模块发起 AXI4-Lite 读写事务。读回的数据通过反向路径（AXI 时钟域 → 异步 FIFO → SPI 时钟域）返回给 SPI Master。

该 IP 在 S3 子系统中用于访问 config 配置空间，是芯片系统调试和配置的关键通路。SPI2AXI 的设计充分考虑了跨时钟域可靠性、可编程配置灵活性以及低引脚数系统总线扩展的典型应用需求。

### 1.2 主要特性

- **SPI 接口兼容性**：支持标准 SPI（1-line，单线模式）和 Quad SPI（QSPI，4线模式）两种工作模式，可通过配置寄存器动态切换，兼容 SPI Mode 0（CPOL=0, CPHA=0，即 sclk 空闲为低，数据在上升沿采样）
- **SPI Slave 模式**：作为主动外设（Active Peripheral），无需 SoC 内部 CPU 干预即可完成 SoC 功能配置、状态观测、内存访问等功能，支持外部 Master 主动发起访问
- **AXI4-Lite Master 接口**：将 SPI 侧接收到的命令和地址解码后转换为 AXI4-Lite 总线事务，支持 5 个独立通道（AW、W、B、AR、R）的独立握手和传输管理
- **可编程地址环绕**：支持可配置的地址 Wrap 功能，Wrap 窗口大小（N words）可通过配置寄存器设定，实现高效的连续地址空间访问
- **跨时钟域处理**：SPI 时钟域与 AXI 时钟域完全分离，通过内置 dual-clock 异步 FIFO 实现可靠的数据跨时钟域传输（CDC），确保亚稳态不会影响功能正确性
- **可编程 Dummy 周期**：读操作插入的可编程 Dummy 周期数可通过参数配置（默认 32 + 1 个 cycle），为 AXI 读数据返回提供充足的等待时间

### 1.3 应用场景

- **系统调试和配置接口**：芯片 bringup 阶段通过 SPI 接口进行寄存器配置、时钟初始化、PLL 锁定等操作，无需 CPU 固件支持
- **低引脚数系统总线扩展**：使用 4~8 根信号线（SPI）扩展出 32-bit 地址和 32-bit 数据的 AXI 系统总线访问能力
- **嵌入式系统固件更新**：通过 SPI 接口将固件数据写入外部或内部存储器，支持 OTA（Over-The-Air）或工厂固件烧录场景
- **芯片测试和验证接口**：在 ATE（Automated Test Equipment）测试中使用 SPI 接口访问芯片内部测试寄存器，无需复杂的 JTAG 调试协议

### 1.4 系统架构框图

```
                    ┌────────────────────────────────────────────┐
                    │              SPI2AXI Bridge IP              │
                    │                                              │
SPI Master          │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │      AXI4-Lite Slave
◄────────►         │  │ SPI      │  │ CMD      │  │ AXI      │  │◄────────►
spi_sclk            │  │ Slave    │─►│ Decoder  │─►│ Master   │  │      axi_aclk
spi_cs              │  │ (QSPI)   │  │ (FSM)    │  │ (5-ch)   │  │
spi_sdi[3:0]        │  └──────────┘  └────┬─────┘  └──────────┘  │
spi_sdo[3:0]        │        │            │              │        │
                    │        ▼            ▼              ▼        │
                    │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
                    │  │ Config   │  │Async FIFO│  │ Wrap     │  │
                    │  │ Regs     │  │(Dual-Clk)│  │ Ctrl     │  │
                    │  └──────────┘  └──────────┘  └──────────┘  │
                    └────────────────────────────────────────────┘
```

上图为 SPI2AXI Bridge IP 的系统级架构框图。SPI 侧信号（spi_sclk, spi_cs, spi_sdi, spi_sdo）从左侧接入 SPI Slave 模块，经过命令解码（FSM 控制器）、异步 FIFO 跨时钟域同步后，由 AXI Master 模块在右侧发起 AXI4-Lite 总线事务。Config Regs 模块提供 SPI 侧的配置寄存器接口，Wrap Ctrl 模块提供地址环绕控制功能。

---

## 第2章 接口规范 (Interface Specification)

### 2.1 SPI 接口信号

SPI 接口信号表详细列出了所有 SPI 侧端口的方向、宽度和功能描述：

| 信号名称 | 方向 | 宽度 | 描述 |
|---------|------|------|------|
| spi_sclk | Input | 1 | SPI 串行时钟，由外部 SPI Master 提供，最高频率 50MHz，SPI Mode 0（空闲为低，上升沿采样） |
| spi_cs_n | Input | 1 | SPI 片选信号（Active Low），低电平时 SPI Slave 被选中，高电平时忽略所有 SPI 输入 |
| spi_sdi | Input | 4 | SPI 串行数据输入总线 [3:0]，1-line 模式下仅使用 bit[0]，4-line 模式下全部使用 |
| spi_sdo | Output | 4 | SPI 串行数据输出总线 [3:0]，1-line 模式下仅输出 bit[0]，4-line 模式下全部输出，高阻态时由外部上拉 |

### 2.2 AXI4-Lite Master 接口信号

AXI4-Lite Master 接口包含 5 个独立通道的完整信号集。以下表格列出每个通道的信号：

**写地址通道（AW Channel）：**

| 信号名称 | 方向 | 宽度 | 描述 |
|---------|------|------|------|
| m_axi_awid | Output | AXI_ID_WIDTH | 写地址通道 ID，用于标识写事务 |
| m_axi_awaddr | Output | AXI_ADDR_WIDTH | 写地址（32-bit），4 字节对齐 |
| m_axi_awlen | Output | 8 | Burst 长度，固定为 8'h00（single transfer） |
| m_axi_awsize | Output | 3 | Burst 大小，固定为 3'b010（4 bytes，AxSIZE=2） |
| m_axi_awburst | Output | 2 | Burst 类型，固定为 2'b01（INCR） |
| m_axi_awvalid | Output | 1 | 写地址通道有效指示 |
| m_axi_awready | Input | 1 | AXI Slave 写地址通道就绪指示 |

**写数据通道（W Channel）：**

| 信号名称 | 方向 | 宽度 | 描述 |
|---------|------|------|------|
| m_axi_wdata | Output | AXI_DATA_WIDTH | 写数据总线（32-bit） |
| m_axi_wstrb | Output | AXI_DATA_WIDTH/8 | 写字节选通信号，固定为 4'b1111 |
| m_axi_wlast | Output | 1 | 写最后一个数据指示，固定为 1'b1 |
| m_axi_wvalid | Output | 1 | 写数据有效指示 |
| m_axi_wready | Input | 1 | AXI Slave 写数据就绪指示 |

**写响应通道（B Channel）：**

| 信号名称 | 方向 | 宽度 | 描述 |
|---------|------|------|------|
| m_axi_bid | Input | AXI_ID_WIDTH | 写响应通道 ID |
| m_axi_bresp | Input | 2 | 写响应状态：2'b00=OKAY, 2'b01=EXOKAY, 2'b10=SLVERR, 2'b11=DECERR |
| m_axi_bvalid | Input | 1 | 写响应有效指示 |
| m_axi_bready | Output | 1 | Master 写响应就绪指示 |

**读地址通道（AR Channel）：**

| 信号名称 | 方向 | 宽度 | 描述 |
|---------|------|------|------|
| m_axi_arid | Output | AXI_ID_WIDTH | 读地址通道 ID |
| m_axi_araddr | Output | AXI_ADDR_WIDTH | 读地址（32-bit），4 字节对齐 |
| m_axi_arlen | Output | 8 | Burst 长度，固定为 8'h00 |
| m_axi_arsize | Output | 3 | Burst 大小，固定为 3'b010（4 bytes） |
| m_axi_arburst | Output | 2 | Burst 类型，固定为 2'b01（INCR） |
| m_axi_arvalid | Output | 1 | 读地址通道有效指示 |
| m_axi_arready | Input | 1 | AXI Slave 读地址通道就绪指示 |

**读数据通道（R Channel）：**

| 信号名称 | 方向 | 宽度 | 描述 |
|---------|------|------|------|
| m_axi_rid | Input | AXI_ID_WIDTH | 读数据通道 ID |
| m_axi_rdata | Input | AXI_DATA_WIDTH | 读数据总线（32-bit） |
| m_axi_rresp | Input | 2 | 读响应状态 |
| m_axi_rlast | Input | 1 | 读最后一个数据指示 |
| m_axi_rvalid | Input | 1 | 读数据有效指示 |
| m_axi_rready | Output | 1 | Master 读数据就绪指示 |

### 2.3 配置参数

以下表格列出了 SPI2AXI IP 的所有可配置参数及其默认值、描述和有效范围：

| 参数名称 | 默认值 | 有效范围 | 描述 |
|---------|--------|---------|------|
| AXI_ADDR_WIDTH | 32 | 12~64 | AXI 地址总线宽度，决定地址空间大小 |
| AXI_DATA_WIDTH | 32 | 32 | AXI 数据总线宽度，固定为 32-bit（Lite 接口要求） |
| AXI_ID_WIDTH | 3 | 1~8 | AXI ID 信号宽度，用于事务标识 |
| DUMMY_CYCLES | 32 | 0~255 | SPI 读操作 Dummy 周期数，Dummy_cycle = 配置值 + 1 |

### 2.4 SPI 协议时序描述

SPI2AXI 采用 SPI Mode 0（CPOL=0, CPHA=0）作为默认 SPI 通信模式。在该模式下，spi_sclk 空闲状态为低电平，数据在 spi_sclk 的上升沿被采样（Input Capture），在 spi_sclk 的下降沿被驱动（Output Launch）。以下为各阶段的 Cycle-Level 时序描述：

**写操作帧格式（Cycle-Level Timing）：**

```
Cycle:    0   1   2   3   4   5   6   7   8   9  10 ... 39  40  41  42  43  44  45  46  47  48
         ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐     ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐
sclk     │   │ │   │ │   │ │   │ │   │ │   │ ... │   │ │   │ │   │ │   │ │   │ │   │ │   │ │
       ──┘   └─┘   └─┘   └─┘   └─┘   └─┘   └─   ─┘   └─┘   └─┘   └─┘   └─┘   └─┘   └─┘   └─┘
cs_n        ──────────────────────────────────────────────────────────────────────────────
         ────                                                                             ────
sdi      XXXXX─── OPCODE[7:0] ───XXXX─── ADDR[31:0] ──XXXX─── WDATA[31:0] ──XXXX
         Phase:   OPCODE               ADDR                   DATA
```

写操作帧格式包含三个阶段：**OPCODE 阶段**（8 个 SCLK 周期，接收 8-bit 操作码）、**ADDR 阶段**（32 个 SCLK 周期，接收 32-bit 地址，MSB First）、**DATA 阶段**（32 个 SCLK 周期，发送 32-bit 写数据，MSB First）。SPI 帧在 spi_cs_n 为低期间持续进行，spi_cs_n 拉高表示帧结束。

**读操作帧格式（Cycle-Level Timing）：**

```
Cycle:    0   1   2   3   4   5   6   7   8   9  10 ... 39  40  41  42 ... 71  72  73  74  75  76  77  78  79
         ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐     ┌───┐ ┌───┐     ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐
sclk     │   │ │   │ │   │ │   │ │   │ │   │ ... │   │ │   │ ... │   │ │   │ │   │ │   │ │   │ │   │ │   │
       ──┘   └─┘   └─┘   └─┘   └─┘   └─┘   └─   ─┘   └─┘   └─   ─┘   └─┘   └─┘   └─┘   └─┘   └─┘   └─┘   └─┘
cs_n        ──────────────────────────────────────────────────────────────────────────────────────────────
         ────                                                                                             ────
sdi      XXXXX─── OPCODE ──XXXX─── ADDR[31:0] ──────XXXX
         Phase:   OPCODE         ADDR                  DUMMY (32 SCLK)
sdo                                                   ──────── RDATA[31:0] ────────
                                                      Phase:                    DATA
```

读操作帧格式包含四个阶段：**OPCODE 阶段**（8 个 SCLK 周期）、**ADDR 阶段**（32 个 SCLK 周期）、**DUMMY 阶段**（可编程，默认 32 + 1 = 33 个 SCLK 周期）、**DATA 阶段**（32 个 SCLK 周期，SPI Master 从 spi_sdo 读取 32-bit 读数据）。在 DUMMY 阶段，SPI Master 持续提供 SCLK 时钟，SPI Slave 内部的 AXI 读事务在此期间完成。读数据在 DATA 阶段随 SCLK 从 spi_sdo 串行输出。

### 2.5 SPI 帧格式详细定义

**QSPI（4-Line）模式帧格式：**

在 4-Line 模式下，spi_sdi[3:0] 和 spi_sdo[3:0] 四根数据线同时使用。每 2 个 SCLK 周期传输 1 个字节（每周期传输 4-bit nibble）。总的 SCLK 周期数相比 1-Line 模式减少为 1/4：

| 阶段 | 1-Line 模式 (SCLK周期) | 4-Line 模式 (SCLK周期) | 数据宽度 |
|------|----------------------|----------------------|---------|
| OPCODE | 8 | 2 | 8-bit |
| ADDR | 32 | 8 | 32-bit |
| DUMMY | 32 | 8 | 等待时间 |
| DATA | 32 | 8 | 32-bit |
| 总计 | 104 | 26 | - |

### 2.6 AXI4-Lite 握手时序

AXI4-Lite 协议使用 VALID/READY 握手机制进行通道级数据传输。以下为写事务和读事务的完整握手时序描述：

**写事务握手时序（Write Transaction Handshake）：**

写事务需要经过三个子通道的依次握手：AW 通道（写地址）→ W 通道（写数据）→ B 通道（写响应）。AW 和 W 通道可以独立握手且无顺序依赖。B 通道必须等待 AW 和 W 通道的数据都被 AXI Slave 接收后才能返回写响应。

1. **AW 通道握手**：Master 将 m_axi_awaddr 和 m_axi_awvalid 驱动为有效电平，Slave 在准备好接收地址时将 m_axi_awready 拉高。在 awvalid & awready 同时为高的时钟上升沿，地址被传输。
2. **W 通道握手**：Master 将 m_axi_wdata（和 wstrb, wlast）与 m_axi_wvalid 同时驱动为有效，Slave 在准备好接收数据时将 m_axi_wready 拉高。在 wvalid & wready 同时为高的时钟上升沿，数据被传输。
3. **B 通道握手**：Slave 完成写事务后将 m_axi_bresp（写响应状态）和 m_axi_bvalid 驱动为有效，Master 在准备好接收响应时将 m_axi_bready 拉高。在 bvalid & bready 同时为高的时钟上升沿，写响应被接收。

**读事务握手时序（Read Transaction Handshake）：**

读事务需要经过两个子通道的依次握手：AR 通道（读地址）→ R 通道（读数据+响应）。

1. **AR 通道握手**：Master 将 m_axi_araddr 和 m_axi_arvalid 驱动为有效，Slave 在准备好接收地址时将 m_axi_arready 拉高。在 arvalid & arready 同时为高的时钟上升沿，读地址被传输。
2. **R 通道握手**：Slave 在准备好返回读数据时将 m_axi_rdata、m_axi_rresp、m_axi_rlast 和 m_axi_rvalid 驱动为有效，Master 在准备好接收数据时将 m_axi_rready 拉高。在 rvalid & rready 同时为高的时钟上升沿，读数据和响应被接收。

---

## 第3章 子模块划分 (Sub-Module Partition)

### 3.1 模块层次结构

SPI2AXI Bridge IP 由 6 个核心子模块组成，按功能划分为接口模块、控制模块、数据通道模块和配置模块四大类。以下为模块层次结构图：

```
spi2axi_bridge (Top)
├── spi_slave_if          —— SPI Slave 接口模块 (SPI Clock Domain)
│   ├── spi_shift_reg     —— SPI 串并转换移位寄存器
│   └── spi_mode_ctrl     —— SPI 工作模式控制 (1-line/4-line)
├── cmd_decoder_fsm       —— 命令解码器/FSM 控制器 (SPI Clock Domain)
│   ├── opcode_decoder    —— 操作码解码逻辑
│   └── state_machine     —— 6-state FSM (IDLE/OPCODE/ADDR/DUMMY/DATA/RESPONSE)
├── async_fifo            —— 异步 FIFO 跨时钟域桥接 (Dual-Clock Domain)
│   ├── wr_fifo           —— 写数据 FIFO (SPI → AXI)
│   └── rd_fifo           —— 读数据 FIFO (AXI → SPI)
├── axi_master_if         —— AXI4-Lite Master 接口模块 (AXI Clock Domain)
│   ├── axi_wr_ctrl       —— AXI 写事务控制器
│   └── axi_rd_ctrl       —— AXI 读事务控制器
├── config_regs           —— SPI 侧配置寄存器模块 (SPI Clock Domain)
│   ├── mode_reg          —— SPI 模式选择寄存器
│   ├── status_reg        —— 状态寄存器
│   └── wrap_reg          —— Wrap 配置寄存器
└── wrap_ctrl             —— 地址环绕控制器 (AXI Clock Domain)
    └── wrap_addr_gen     —— 环绕地址生成逻辑
```

### 3.2 子模块详细定义

以下表格列出所有子模块的名称、时钟域归属、类型（接口/控制/数据通道/配置）以及简要功能描述：

| 模块名称 | 时钟域 | 类型 | 功能描述 |
|---------|--------|------|---------|
| spi_slave_if | SPI | 接口 | SPI Slave 接口模块，处理 SPI 协议层的信号采样、移位寄存、串并转换，支持标准 SPI 和 Quad SPI（QSPI）两种工作模式的动态切换 |
| cmd_decoder_fsm | SPI | 控制 | 命令解码及 FSM 控制器，接收 SPI 侧解析出的 8-bit 操作码，驱动 6 状态有限状态机（IDLE→OPCODE→ADDR→DUMMY→DATA→RESPONSE）完成命令帧的解析和控制信号的生成 |
| async_fifo | 双时钟域 | 数据通道 | 异步双时钟 FIFO，实现 SPI 时钟域（最高 50MHz）到 AXI 时钟域（SoC 系统时钟）之间可靠的数据跨时钟域传输，内置格雷码同步器和空/满标志生成逻辑 |
| axi_master_if | AXI | 接口 | AXI4-Lite Master 接口模块，5 个独立通道（AW、W、B、AR、R）的协议处理，支持 AXI4-Lite single transfer（AxLEN=0, AxSIZE=2=4bytes） |
| config_regs | SPI | 配置 | SPI 侧寄存器配置模块，包含 SPI 工作模式选择（1-line/4-line）、状态寄存器（FIFO 状态/传输状态）、Wrap 配置寄存器，寄存器地址由操作码编码 |
| wrap_ctrl | AXI | 控制 | 地址环绕控制器，根据配置的 Wrap 参数生成 AXI 地址序列，支持 Wrap=0（无环绕）和 Wrap=N（N words 环绕窗口）两种模式 |

### 3.3 子模块接口信号

**spi_slave_if 模块接口：**

| 信号名称 | 方向 | 宽度 | 描述 |
|---------|------|------|------|
| spi_sclk | Input | 1 | SPI 串行时钟输入 |
| spi_cs_n | Input | 1 | SPI 片选（低有效） |
| spi_sdi | Input | 4 | SPI 数据输入 |
| spi_sdo | Output | 4 | SPI 数据输出 |
| mode_1wire | Input | 1 | 工作模式选择：0=4-line QSPI, 1=1-line Standard SPI |
| opcode_out | Output | 8 | 解码后的 8-bit 操作码 |
| addr_out | Output | 32 | 接收到的 32-bit 地址 |
| wdata_out | Output | 32 | 接收到的 32-bit 写数据 |
| rdata_in | Input | 32 | 待输出的 32-bit 读数据 |
| shift_done | Output | 1 | 当前阶段移位完成脉冲 |
| phase_valid | Output | 1 | 阶段数据有效指示 |

**cmd_decoder_fsm 模块接口：**

| 信号名称 | 方向 | 宽度 | 描述 |
|---------|------|------|------|
| clk_spi | Input | 1 | SPI 时钟 |
| rst_n_spi | Input | 1 | SPI 时钟域异步复位（低有效） |
| spi_cs_n | Input | 1 | SPI 片选 |
| opcode | Input | 8 | 操作码输入 |
| shift_done | Input | 1 | 移位完成标志 |
| state | Output | 3 | 当前 FSM 状态 |
| fifo_wr_en | Output | 1 | FIFO 写使能 |
| fifo_rd_en | Output | 1 | FIFO 读使能 |
| axi_start | Output | 1 | AXI 事务启动指示 |
| wrap_en | Output | 1 | Wrap 功能使能 |
| rdata_valid | Input | 1 | 读数据 FIFO 非空指示 |

**async_fifo 模块接口：**

| 信号名称 | 方向 | 宽度 | 描述 |
|---------|------|------|------|
| wclk | Input | 1 | FIFO 写时钟（SPI 时钟域） |
| wrst_n | Input | 1 | 写时钟域异步复位 |
| wdata | Input | 32 | FIFO 写数据 |
| wren | Input | 1 | FIFO 写使能 |
| full | Output | 1 | FIFO 满标志 |
| rclk | Input | 1 | FIFO 读时钟（AXI 时钟域） |
| rrst_n | Input | 1 | 读时钟域异步复位 |
| rdata | Output | 32 | FIFO 读数据 |
| rden | Input | 1 | FIFO 读使能 |
| empty | Output | 1 | FIFO 空标志 |

**axi_master_if 模块接口：**

| 信号名称 | 方向 | 宽度 | 描述 |
|---------|------|------|------|
| axi_aclk | Input | 1 | AXI 系统时钟 |
| axi_areset_n | Input | 1 | AXI 时钟域异步复位 |
| axi_start | Input | 1 | AXI 事务启动信号 |
| axi_wr_rd_n | Input | 1 | 读写方向指示（0=读, 1=写） |
| axi_addr | Input | 32 | AXI 事务地址 |
| axi_wdata | Input | 32 | AXI 写数据 |
| axi_rdata | Output | 32 | AXI 读数据 |
| axi_done | Output | 1 | AXI 事务完成标志 |
| axi_error | Output | 2 | AXI 响应错误状态 |

### 3.4 模块间数据流

SPI2AXI 的模块间数据流按照命令帧的处理阶段依次穿越各个子模块。以下是详细的模块间数据流定义：

**写数据流路径：** SPI Master → spi_sdi[3:0] → spi_slave_if（串并转换）→ cmd_decoder_fsm（命令解码）→ async_fifo.wr_fifo（跨时钟域同步）→ axi_master_if.aw_ctrl（AW 通道）+ axi_master_if.w_ctrl（W 通道）→ AXI Slave

**读数据流路径：** AXI Slave → axi_master_if.ar_ctrl（AR 通道）+ axi_master_if.r_ctrl（R 通道）→ async_fifo.rd_fifo（跨时钟域同步）→ cmd_decoder_fsm（读取状态控制）→ spi_slave_if（并串转换）→ spi_sdo[3:0] → SPI Master

---

## 第4章 FSM 设计 (FSM Design)

### 4.1 状态机概述

SPI2AXI Bridge 的核心控制逻辑由 cmd_decoder_fsm 模块中的 6 状态有限状态机实现。该 FSM 运行在 SPI 时钟域（spi_sclk），负责解析 SPI 命令帧的各个阶段并生成对应的控制信号。FSM 的输入包括 SPI 片选信号（spi_cs_n）、移位完成标志（shift_done）和操作码（opcode）；输出包括 AXI 事务启动信号、FIFO 读写使能、以及地址/数据加载控制信号。

### 4.2 状态编码

FSM 采用 3-bit 二进制编码（Binary Encoding），共 6 个有效状态。编码方案优先考虑格雷码特性，使得相邻状态之间的汉明距离为 1：

| 状态名称 | 编码 (3-bit) | 格雷码 | 描述 |
|---------|-------------|--------|------|
| IDLE | 3'b000 | 000 | 空闲状态，等待 spi_cs_n 拉低（片选有效） |
| OPCODE | 3'b001 | 001 | 操作码接收状态，接收 8-bit OPCODE 并解码 |
| ADDR | 3'b010 | 011 | 地址接收状态，接收 32-bit 地址（内存访问时） |
| DUMMY | 3'b011 | 010 | 虚拟周期状态，插入可编程数量 Dummy Cycle，等待读数据返回 |
| DATA | 3'b100 | 110 | 数据传输状态，32-bit 写数据接收或读数据发送 |
| RESPONSE | 3'b101 | 111 | 写响应等待或读数据返回完成处理 |

### 4.3 状态转移矩阵

以下状态转移矩阵定义了 FSM 在所有输入条件下的下一状态逻辑。行表示当前状态（Current State），列表示转移条件，交叉点表示下一状态（Next State）：

| 当前状态 | 条件 1 (转移) | 下一状态 | 条件 2 (保持) | 下一状态 | 条件 3 (异常) | 下一状态 |
|---------|-------------|---------|-------------|---------|-------------|---------|
| IDLE | spi_cs_n == 0 | OPCODE | spi_cs_n == 1 | IDLE | - | - |
| OPCODE | shift_done == 1 & opcode[7:6]==2'b00 (MEM) | ADDR | shift_done == 1 & opcode[7:6]==2'b01 (REG) | DATA | shift_done == 0 | OPCODE |
| ADDR | shift_done == 1 & opcode[0]==1'b1 (READ) | DUMMY | shift_done == 1 & opcode[0]==1'b0 (WRITE) | DATA | shift_done == 0 | ADDR |
| DUMMY | dummy_cnt == DUMMY_CYCLES & rdata_valid==1 | DATA | dummy_cnt < DUMMY_CYCLES | DUMMY | - | - |
| DATA | shift_done == 1 & opcode[0]==1'b0 (WRITE) | RESPONSE | shift_done == 1 & opcode[0]==1'b1 (READ) | RESPONSE | shift_done == 0 | DATA |
| RESPONSE | axi_done == 1 & spi_cs_n == 0 | OPCODE | axi_done == 1 & spi_cs_n == 1 | IDLE | axi_done == 0 | RESPONSE |

### 4.4 状态输出解码

以下输出解码表定义了每个状态下 FSM 生成的输出控制信号：

| 状态 | load_opcode | load_addr | load_data | fifo_wr_en | fifo_rd_en | axi_start | dummy_cnt_en | shift_en | sdo_en |
|------|------------|----------|----------|-----------|-----------|---------|-------------|---------|-------|
| IDLE | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| OPCODE | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| ADDR | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| DUMMY | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| DATA (WRITE) | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 0 |
| DATA (READ) | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 1 |
| RESPONSE | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

输出信号说明：
- **load_opcode**: 将移位寄存器内容加载到 OPCODE 寄存器
- **load_addr**: 将移位寄存器内容加载到 ADDR 寄存器
- **load_data**: 将移位寄存器内容加载到写数据寄存器
- **fifo_wr_en**: 写数据 FIFO 写入使能（仅在 WRITE 操作时有效）
- **fifo_rd_en**: 读数据 FIFO 读取使能（仅在 READ 操作时有效）
- **axi_start**: 启动 AXI 总线事务（在 DUMMY 状态时发出）
- **dummy_cnt_en**: Dummy Cycle 计数器使能
- **shift_en**: SPI 移位寄存器移位使能
- **sdo_en**: SPI 数据输出使能（仅在读 DATA 阶段需要）

### 4.5 FSM 状态转移条件详细描述

**IDLE → OPCODE 转移条件：**

当 FSM 处于 IDLE 状态时，spi_cs_n 为高电平（片选无效），所有内部寄存器和计数器处于复位保持状态。当外部 SPI Master 拉低 spi_cs_n 时，表示 SPI 帧开始，FSM 立即从 IDLE 状态转移到 OPCODE 状态。此转移没有延迟，在 spi_cs_n 下降沿后的第一个 spi_sclk 上升沿完成状态更新。

**OPCODE → ADDR/DATA 转移条件：**

FSM 在 OPCODE 状态下启动移位使能信号（shift_en=1），每个 spi_sclk 上升沿将 spi_sdi 上的数据移入 8-bit 移位寄存器。当 8 个 SCLK 周期完成后，shift_done 信号产生一个时钟周期的脉冲。此时 FSM 根据操作码的高 2 位（opcode[7:6]）决定下一状态：若为 2'b00（Memory 访问），则转移到 ADDR 状态；若为 2'b01（Register 访问），则跳过 ADDR 状态直接转移到 DATA 状态。

**ADDR → DUMMY/DATA 转移条件：**

FSM 在 ADDR 状态下继续移位 32 个 SCLK 周期以接收完整的 32-bit 地址。地址接收完成后（shift_done=1），FSM 根据操作码的最低位（opcode[0]）决定下一状态：若为 READ 操作（opcode[0]=1），则转移到 DUMMY 状态等待读数据返回；若为 WRITE 操作（opcode[0]=0），则直接转移到 DATA 状态准备接收写数据。

**DUMMY → DATA 转移条件：**

FSM 在 DUMMY 状态下启动一个可编程的 Dummy Cycle 计数器（dummy_cnt_en=1）。当计数器值等于 DUMMY_CYCLES 参数值（默认 32）且读数据 FIFO 非空标志有效时，FSM 转移到 DATA 状态。Dummy Cycle 的设计目的是为 AXI 读事务提供充足的等待时间，确保读数据在 DATA 阶段开始前已经返回并写入读数据 FIFO。

**DATA → RESPONSE 转移条件：**

FSM 在 DATA 状态下完成 32-bit 数据的移位传输。对于 WRITE 操作，SPI Master 发送写数据到 spi_sdi，由 shift_done 信号触发数据加载到 FIFO；对于 READ 操作，FSM 使能 sdo_en 信号，从读数据 FIFO 读取数据并通过 spi_sdo 串行输出。DATA 阶段完成后（shift_done=1），FSM 无条件转移到 RESPONSE 状态。

**RESPONSE → IDLE/OPCODE 转移条件：**

FSM 在 RESPONSE 状态下等待 AXI 总线事务完成信号（axi_done）。当 axi_done=1 时，表示 AXI 事务已成功完成或出现错误。此时检查 spi_cs_n 状态：若 spi_cs_n 仍为低电平（连续传输模式），则回到 OPCODE 状态接收下一个命令；若 spi_cs_n 已拉高（传输结束），则回到 IDLE 状态等待下一次片选。

### 4.6 状态机时序图

```
spi_sclk    ┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐
            │  ││  ││  ││  ││  ││  ││  ││  ││  ││  ││  ││  ││  ││  │
spi_cs_n  ──┘  └──┘└──┘└──┘└──┘└──┘└──┘└──┘└──┘└──┘└──┘└──┘└──┘└──┘└──
FSM State IDLE OPCODE       ADDR                  DUMMY/     DATA   RESP  IDLE
                             (32 clk)              IDLE
```

### 4.7 状态机 RTL 模板

以下为 SPI2AXI FSM 的 SystemVerilog RTL 模板，包含状态编码定义、状态寄存器和组合逻辑的 next state / output decode：

```systemverilog
// FSM State Encoding
typedef enum logic [2:0] {
    IDLE     = 3'b000,
    OPCODE   = 3'b001,
    ADDR     = 3'b010,
    DUMMY    = 3'b011,
    DATA     = 3'b100,
    RESPONSE = 3'b101
} state_t;

state_t state, next_state;

// State Register (Sequential)
always_ff @(posedge spi_sclk or negedge rst_n_spi) begin
    if (!rst_n_spi)
        state <= IDLE;
    else if (!spi_cs_n)
        state <= next_state;
    else
        state <= IDLE;
end

// Next State Logic (Combinational)
always_comb begin
    case (state)
        IDLE:     next_state = spi_cs_n ? IDLE : OPCODE;
        OPCODE:   next_state = shift_done ? (opcode[7:6]==2'b00 ? ADDR : DATA) : OPCODE;
        ADDR:     next_state = shift_done ? (opcode[0] ? DUMMY : DATA) : ADDR;
        DUMMY:    next_state = (dummy_cnt==DUMMY_CYCLES && rdata_valid) ? DATA : DUMMY;
        DATA:     next_state = shift_done ? RESPONSE : DATA;
        RESPONSE: next_state = axi_done ? (spi_cs_n ? IDLE : OPCODE) : RESPONSE;
        default:  next_state = IDLE;
    endcase
end

// Output Decode (Combinational)
always_comb begin
    load_opcode  = (state == OPCODE)   & shift_done;
    load_addr    = (state == ADDR)     & shift_done;
    load_data    = (state == DATA)     & shift_done & ~opcode[0]; // WRITE
    fifo_wr_en   = (state == DATA)     & shift_done & ~opcode[0]; // WRITE
    fifo_rd_en   = (state == DATA)     & shift_done &  opcode[0]; // READ
    axi_start    = (state == DUMMY)    & (dummy_cnt == 0);        // Start at 1st dummy
    dummy_cnt_en = (state == DUMMY);
    shift_en     = (state == OPCODE) | (state == ADDR) | (state == DATA);
    sdo_en       = (state == DATA)     &  opcode[0];              // READ data output
end
```

---

## 第5章 流水线设计 (Pipeline Design)

### 5.1 流水线阶段划分

SPI2AXI 的 SPI 命令到 AXI 事务的转换过程可划分为 5 个流水线阶段。需要注意的是，由于 SPI 协议本身是全双工串行协议且 AXI 事务涉及跨时钟域同步，这些阶段之间并非严格的寄存器级流水线（Register Pipeline），而是功能级流水线（Functional Pipeline），每个阶段由特定的硬件模块完成。

| 流水线阶段 | 占用模块 | 时钟域 | 延迟（典型值） | 描述 |
|-----------|---------|--------|--------------|------|
| Stage 1: SPI 命令接收 | spi_slave_if | SPI (50MHz) | 8~72 SCLK | 接收 SPI 帧的 OPCODE + ADDR + DATA，串并转换 |
| Stage 2: 命令解码与控制 | cmd_decoder_fsm | SPI (50MHz) | 1 SCLK | 解析操作码，生成控制信号，确定访问类型 |
| Stage 3: CDC 同步传输 | async_fifo | SPI → AXI | 2~5 AXI clk | 通过异步 FIFO 将命令和数据同步到 AXI 时钟域 |
| Stage 4: AXI 总线事务 | axi_master_if | AXI | 2~10 AXI clk | 发起 AXI4-Lite 读写事务，等待 Slave 响应 |
| Stage 5: 数据返回输出 | async_fifo + spi_slave_if | AXI → SPI | 2~5 AXI clk + 32 SCLK | 读数据通过 FIFO 返回 SPI 侧并串行输出 |

### 5.2 写操作流水线序列

写操作（WRITE 和 REG_WRITE）完整的流水线执行序列如下：

**Stage 1 - SPI 命令接收：** 外部 SPI Master 拉低 spi_cs_n 后，spi_slave_if 模块开始在 spi_sclk 的上升沿采样 spi_sdi 上的数据。对于 WRITE 操作，依次接收：8-bit OPCODE（8 SCLK cycles）、32-bit ADDR（32 SCLK cycles）、32-bit WDATA（32 SCLK cycles），共 72 个 SCLK 周期。对于 REG_WRITE 操作，地址由 OPCODE 编码，接收：8-bit OPCODE（8 SCLK cycles）、32-bit WDATA（32 SCLK cycles），共 40 个 SCLK 周期。

**Stage 2 - 命令解码与控制：** cmd_decoder_fsm 在 OPCODE 接收完成后（shift_done 脉冲）立即解码 opcode[7:6] 确定访问类型（Memory/Register），并根据 opcode[0] 确定读写方向（Write/Read）。FSM 控制信号（fifo_wr_en, axi_start 等）根据当前状态和操作码组合产生。

**Stage 3 - CDC 同步传输：** 在 DATA 阶段完成时，写数据和地址被同步写入 async_fifo 的 wr_fifo（写数据 FIFO）。wr_fifo 使用 SPI 时钟域时钟（spi_sclk）作为写时钟，AXI 时钟域时钟（axi_aclk）作为读时钟。数据经过格雷码同步器完成跨时钟域同步，典型同步延迟为 2~5 个 AXI 时钟周期。

**Stage 4 - AXI 总线事务：** axi_master_if 模块从 wr_fifo 读取写命令和数据后，依次发起 AW 通道（写地址）和 W 通道（写数据）的 VALID/READY 握手传输。然后等待 B 通道（写响应）的返回。AXI4-Lite single transfer 的典型握手延迟为 2~10 个 AXI 时钟周期，取决于 AXI Slave 的响应速度。

**Stage 5 - 数据返回输出：** 写操作完成后，WRITE 操作无需数据返回。FSM 在 RESPONSE 状态等待 axi_done 信号，确认 AXI 写事务已完成。若写响应状态为 OKAY，则返回 IDLE 或 OPCODE 等待下一个命令。

### 5.3 读操作流水线序列

读操作（READ 和 REG_READ）完整的流水线执行序列如下：

**Stage 1 - SPI 命令接收：** 与写操作类似，SPI Master 发送 8-bit OPCODE 和 32-bit ADDR（REG_READ 只有 8-bit OPCODE）。与写操作不同的是，SPI Master 在读操作中额外提供 Dummy Cycles（默认 32+1 个 SCLK）用于等待读数据返回。

**Stage 2 - 命令解码与控制：** cmd_decoder_fsm 解码 OPCODE 确定读操作类型。在 ADDR 阶段完成后，FSM 生成 axi_start 脉冲信号，启动 AXI 读事务流程。同时进入 DUMMY 状态，启动 Dummy Cycle 计数器。

**Stage 3 - CDC 同步传输 + Dummy 等待：** 在 DUMMY 阶段，FSM 维持 dummy_cnt_en=1 使 Dummy 计数器递增。同时，axi_start 信号通过脉冲同步器同步到 AXI 时钟域。同步后的 AXI 读启动信号触发 axi_master_if 模块发起读事务。读数据返回后写入 async_fifo 的 rd_fifo（读数据 FIFO）。Dummy 周期数应足够覆盖 AXI 读事务延迟 + CDC 同步延迟的总和。

**Stage 4 - AXI 总线事务：** axi_master_if 模块发起 AR 通道（读地址）握手，等待 AXI Slave 返回 R 通道（读数据+响应）。读数据收到后立即写入 rd_fifo，同时完成 AXI 读事务的握手确认。

**Stage 5 - 数据返回输出：** 当 Dummy 计数器达到 DUMMY_CYCLES 且 rd_fifo 非空时，FSM 进入 DATA 状态。在 DATA 状态下，FSM 使能 sdo_en 信号，从 rd_fifo 读取 32-bit 数据并通过 spi_sdo[3:0] 逐位串行输出（4-line 模式每 2 个 SCLK 输出一个字节，1-line 模式每 8 个 SCLK 输出一个字节）。

### 5.4 流水线握手信号

以下为流水线阶段之间的关键握手信号定义：

| 握手信号 | 源阶段 | 目标阶段 | 类型 | 描述 |
|---------|-------|---------|------|------|
| shift_done | Stage 1 | Stage 2 | 脉冲 (1 clk) | SPI 移位完成指示，触发 FSM 状态转移 |
| opcode_valid | Stage 1 | Stage 2 | 电平 | OPCODE 已锁存有效 |
| addr_valid | Stage 1 | Stage 2 | 电平 | ADDR 已锁存有效 |
| wr_fifo_wren | Stage 2 | Stage 3 | 脉冲 | 写数据 FIFO 写入使能 |
| rd_fifo_rden | Stage 2 | Stage 3 | 脉冲 | 读数据 FIFO 读取使能 |
| axi_start_req | Stage 2 | Stage 4 | 脉冲 (同步后) | AXI 事务启动请求，经 CDC 同步 |
| axi_done | Stage 4 | Stage 2 | 脉冲 | AXI 事务完成指示 |

---

## 第6章 数据通路 (Datapath)

### 6.1 数据通路架构

SPI2AXI 的数据通路分为两个独立的方向：**写数据通路**（SPI → AXI）和**读数据通路**（AXI → SPI）。两条通路各自经过串并转换、CDC 异步 FIFO、AXI 通道协议处理等阶段。以下是两条数据通路的详细架构描述。

### 6.2 写数据通路

写数据通路将 SPI 侧接收到的串行命令和数据转换为 AXI 写事务，其完整的信号流路径如下：

```
spi_sdi[3:0] → SPI Shift Register → Parallel Load → Write Data Buffer
    → async_fifo.wr_fifo (SPI clk domain → AXI clk domain)
        → axi_master_if.wr_ctrl → m_axi_awaddr / m_axi_wdata → AXI Slave
```

**SPI 串并转换（SPI Serial-to-Parallel Conversion）：**

在 1-Line 模式下，SPI 移位寄存器在每个 spi_sclk 上升沿将 spi_sdi[0] 移入内部 32-bit 移位寄存器的最高位（MSB First）。在 4-Line（QSPI）模式下，每个 spi_sclk 上升沿同时将 spi_sdi[3:0] 的 4 个 bit 移入移位寄存器（每周期移入 4-bit nibble），因此 32-bit 数据的移位时间由 32 个 SCLK 周期缩短为 8 个 SCLK 周期。

移位寄存器配置为 32-bit 宽度，通过 bit 选择逻辑（selecting mux）在 OPCODE 阶段提取高 8 位，在 ADDR 阶段提取全部 32 位，在 DATA 阶段提取全部 32 位。串并转换的关键时序参数：

| 参数 | 1-Line 模式 | 4-Line 模式 | 单位 |
|------|------------|------------|------|
| 每 bit 移位时间 | 1 SCLK | 1 SCLK（4-bit 并行） | - |
| OPCODE 接收时间 | 8 SCLK | 2 SCLK | cycles |
| ADDR 接收时间 | 32 SCLK | 8 SCLK | cycles |
| DATA 接收时间 | 32 SCLK | 8 SCLK | cycles |
| 总写帧时间 | 72 SCLK | 18 SCLK | cycles |

**写数据缓冲（Write Data Buffer）：**

写数据缓冲是一个 32-bit 寄存器，在 DATA 阶段完成时由 shift_done 信号触发并行加载。加载后的数据与地址、控制信号一起打包为 FIFO 写入条目，在下一个 spi_sclk 上升沿写入 async_fifo.wr_fifo。

**异步 FIFO 写入（Async FIFO Write）：**

wr_fifo 的数据宽度为 64-bit（32-bit 地址 + 32-bit 数据），深度建议为 8（可配置）。写入侧逻辑在 FIFO 非满时（full==0）将 cmd_decoder_fsm 提供的地址和数据组合后写入。FIFO 几乎满标志（almost_full）可提前通知 SPI 侧暂停发送，防止 FIFO 溢出。FIFO 的空/满标志生成使用格雷码指针（Gray Code Pointers）进行比较，确保跨时钟域比较的亚稳态安全性。

**AXI 写事务执行（AXI Write Transaction）：**

axi_master_if.wr_ctrl 模块从 wr_fifo 读取写命令条目后，将地址和控制信号驱动到 AW 通道，将数据驱动到 W 通道，然后等待 B 通道的写响应。写事务的握手顺序和超时保护机制如下：

1. 驱动 m_axi_awaddr = fifo_raddr, m_axi_awvalid = 1
2. 驱动 m_axi_wdata = fifo_rdata, m_axi_wvalid = 1, m_axi_wstrb = 4'b1111
3. 等待 m_axi_awready & m_axi_wready（可分别握手）
4. 等待 m_axi_bvalid，读取 m_axi_bresp
5. 断言 axi_done，向 SPI 侧返回完成状态

### 6.3 读数据通路

读数据通路将 AXI 读事务返回的数据通过跨时钟域同步后通过 SPI 接口串行输出，其完整的信号流路径如下：

```
AXI Slave → m_axi_rdata → axi_master_if.rd_ctrl
    → async_fifo.rd_fifo (AXI clk domain → SPI clk domain)
        → Read Data Buffer → SPI Shift Register
            → spi_sdo[3:0] → SPI Master
```

**AXI 读事务执行（AXI Read Transaction）：**

axi_master_if.rd_ctrl 模块在收到来自 SPI 侧的 axi_start_req（经 CDC 同步后）后发起读事务。读事务的握手顺序如下：

1. 驱动 m_axi_araddr = fifo_raddr（写事务时已存入的读地址），m_axi_arvalid = 1
2. 等待 m_axi_arready，地址传输完成
3. 等待 m_axi_rvalid & m_axi_rready，读取 m_axi_rdata
4. 将读数据写入 rd_fifo，断言 axi_done

**异步 FIFO 读取（Async FIFO Read）：**

rd_fifo 的数据宽度为 32-bit，深度建议为 8（可配置）。读取侧在 SPI 时钟域，当 FSM 处于 DATA 状态且 opcode[0]=1（READ 操作）时使能 fifo_rd_en，从 rd_fifo 读取一个 32-bit 数据到读数据缓冲寄存器。

**并串转换（Parallel-to-Serial Conversion）：**

读数据缓冲寄存器中的 32-bit 并行数据在 DATA 阶段通过 SPI 移位寄存器逐位输出到 spi_sdo。在 1-Line 模式下，每个 spi_sclk 下降沿输出 1 个 bit（MSB First），共 32 个 SCLK 周期。在 4-Line 模式下，每个 spi_sclk 下降沿输出 4 个 bit，共 8 个 SCLK 周期。

### 6.4 数据通路控制信号汇总

以下表格汇总了数据通路中所有关键控制信号的来源、用途和时序关系：

| 控制信号 | 源模块 | 目标模块 | 用途 | 有效条件 |
|---------|-------|---------|------|---------|
| shift_en | cmd_decoder_fsm | spi_slave_if | 使能移位寄存器移位 | 非 IDLE/DUMMY 状态 |
| load_opcode | cmd_decoder_fsm | spi_slave_if | 加载操作码到解码器 | OPCODE 状态 & shift_done |
| load_addr | cmd_decoder_fsm | spi_slave_if | 加载地址到地址寄存器 | ADDR 状态 & shift_done |
| load_wdata | cmd_decoder_fsm | spi_slave_if | 加载写数据到缓冲 | DATA 状态 & shift_done & WRITE |
| fifo_wr_en | cmd_decoder_fsm | async_fifo | 写数据 FIFO 写入 | DATA 状态 & shift_done & WRITE |
| fifo_rd_en | cmd_decoder_fsm | async_fifo | 读数据 FIFO 读取 | DATA 状态 & shift_done & READ |
| sdo_en | cmd_decoder_fsm | spi_slave_if | 使能 SPI 数据输出 | DATA 状态 & READ |
| axi_start | cmd_decoder_fsm | axi_master_if | 启动 AXI 事务 | DUMMY 状态 & dummy_cnt==0 |
| axi_done | axi_master_if | cmd_decoder_fsm | AXI 事务完成标志 | AXI 事务完成 |

### 6.5 数据通路延迟预算

以下为写操作和读操作的总延迟预算分析，单位为对应的时钟周期数。该预算用于指导 Dummy Cycle 的配置和 FIFO 深度的设计：

**写操作延迟预算（从 SPI SDI 最后一位到 AXI BVALID）：**

| 延迟环节 | 时钟域 | 典型延迟 | 最大延迟 |
|---------|--------|---------|---------|
| SPI 串行接收延迟 | SPI | 72 (1-line) / 18 (4-line) SCLK | 同左 |
| FSM 控制延迟 | SPI | 1 SCLK | 1 SCLK |
| CDC 同步延迟 | SPI → AXI | 3 AXI clk | 6 AXI clk |
| AXI AW 通道握手 | AXI | 2 AXI clk | 8 AXI clk |
| AXI W 通道握手 | AXI | 2 AXI clk | 8 AXI clk |
| AXI B 通道握手 | AXI | 2 AXI clk | 8 AXI clk |
| 写总延迟 | - | ~10 AXI clk + 72 SCLK | ~31 AXI clk + 72 SCLK |

**读操作延迟预算（从 SPI 地址最后一位到 SPI SDO 第一位）：**

| 延迟环节 | 时钟域 | 典型延迟 | 最大延迟 |
|---------|--------|---------|---------|
| SPI 地址接收延迟 | SPI | 32 (1-line) / 8 (4-line) SCLK | 同左 |
| FSM DUMMY 进入 | SPI | 1 SCLK | 1 SCLK |
| axi_start CDC 同步 | SPI → AXI | 3 AXI clk | 6 AXI clk |
| AXI AR 通道握手 | AXI | 2 AXI clk | 8 AXI clk |
| AXI R 通道握手 | AXI | 2 AXI clk | 8 AXI clk |
| 读数据 CDC 同步 | AXI → SPI | 3 SPI clk | 6 SPI clk |
| Dummy 等待 (配置) | SPI | DUMMY_CYCLES SCLK | 同左 |
| 读总延迟(不含dummy) | - | ~10 AXI clk + 33 SPI clk | ~28 AXI clk + 36 SPI clk |

---

## 第7章 CSR (Configuration Space Registers)

### 7.1 寄存器概述

SPI2AXI 的配置寄存器（CSR）位于 SPI 时钟域，通过操作码（OPCODE）进行地址编码。外部 SPI Master 使用 REG_READ 和 REG_WRITE 操作码访问这些寄存器，实现对 SPI 工作模式、Wrap 功能和状态查询的配置。

### 7.2 寄存器地址映射

以下为 SPI2AXI CSR 的完整寄存器地址映射表。寄存器地址由 8-bit OPCODE 编码，每个 OPCODE 对应一个独立的功能寄存器：

| OPCODE | 地址编码 | 寄存器名称 | 读写属性 | 默认值 | 描述 |
|--------|---------|-----------|---------|--------|------|
| 8'h40 | REG_WRITE_CTRL | SPI_CTRL | W | 8'h00 | SPI 控制寄存器：配置 SPI 工作模式等控制参数 |
| 8'h41 | REG_WRITE_WRAP | SPI_WRAP_CFG | W | 8'h00 | Wrap 配置寄存器：配置地址环绕参数 |
| 8'h42 | REG_WRITE_DUMMY | SPI_DUMMY_CFG | W | 8'h20 | Dummy Cycle 配置寄存器 |
| 8'h50 | REG_READ_STAT | SPI_STATUS | R | 8'h00 | SPI 状态寄存器：反映 FIFO 状态和传输状态 |
| 8'h51 | REG_READ_ID | SPI_IP_ID | R | 8'h01 | IP 标识寄存器：IP 版本和标识信息 |

### 7.3 寄存器字段定义

**SPI_CTRL (OPCODE=8'h40) — SPI 控制寄存器（SPI Control Register）：**

| 比特位 | 字段名称 | 类型 | 默认值 | 描述 |
|-------|---------|------|--------|------|
| [31:8] | RESERVED | RO | 24'h0 | 保留位，写操作无效，读返回 0 |
| [7:4] | RESERVED | RO | 4'h0 | 保留位 |
| [3] | RESERVED | RO | 1'h0 | 保留位 |
| [2] | SPI_MODE | RW | 1'h0 | SPI 工作模式选择：0=Standard SPI (1-line), 1=QSPI (4-line) |
| [1] | RESERVED | RO | 1'h0 | 保留位 |
| [0] | SPI_EN | RW | 1'h0 | SPI 接口使能：0=Disabled, 1=Enabled（该位置 1 后 SPI Slave 开始响应片选信号） |

SPI_CTRL 寄存器是 SPI2AXI 的核心控制寄存器。SPI_MODE 字段控制 SPI 接口的工作模式，当 SPI_MODE=0 时，spi_sdi 仅使用 bit[0] 进行 1-line 单线传输，spi_sdo 仅输出 bit[0]；当 SPI_MODE=1 时，spi_sdi[3:0] 和 spi_sdo[3:0] 全部 4 根数据线同时传输，每 SCLK 周期传输 4-bit 数据。SPI_EN 字段必须在进行任何 SPI 传输前设置为 1，该位为 0 时所有 SPI 输入被忽略，FSM 保持在 IDLE 状态。对保留位（RESERVED）的写操作应被忽略，读操作返回 0。

**SPI_WRAP_CFG (OPCODE=8'h41) — Wrap 配置寄存器（Wrap Configuration Register）：**

| 比特位 | 字段名称 | 类型 | 默认值 | 描述 |
|-------|---------|------|--------|------|
| [31:8] | RESERVED | RO | 24'h0 | 保留位 |
| [7:4] | WRAP_SIZE | RW | 4'h0 | Wrap 窗口大小（N words）：4'h0=Wrap off（无环绕），4'h1~4'hF=窗口大小为 N words |
| [3:1] | RESERVED | RO | 3'h0 | 保留位 |
| [0] | WRAP_EN | RW | 1'h0 | Wrap 功能使能：0=Disabled（地址持续递增），1=Enabled（启用地址环绕） |

SPI_WRAP_CFG 寄存器控制地址环绕功能的使能和窗口大小配置。当 WRAP_EN=1 时，每个 AXI 访问完成后，wrap_addr_gen 模块将当前地址与起始地址和窗口大小进行比较：若当前地址偏移小于窗口大小 N，则地址加 4（下一个 word）；若当前地址偏移等于或超过 N-1，则地址回绕到起始地址。WRAP_SIZE 字段指定窗口大小（单位为 32-bit word），窗口对应的字节数为 4 × WRAP_SIZE。例如 WRAP_SIZE=4 表示窗口大小为 4 个 word（16 字节），起始地址为 4 字节对齐，地址序列为 Addr, Addr+4, Addr+8, Addr+12, Addr, Addr+4, ...。

**SPI_DUMMY_CFG (OPCODE=8'h42) — Dummy Cycle 配置寄存器（Dummy Cycle Configuration Register）：**

| 比特位 | 字段名称 | 类型 | 默认值 | 描述 |
|-------|---------|------|--------|------|
| [31:8] | RESERVED | RO | 24'h0 | 保留位 |
| [7:0] | DUMMY_CYCLES | RW | 8'h20 | Dummy Cycle 计数值（默认 32），实际 Dummy Cycle = 配置值 + 1，配置范围为 0~255 |

SPI_DUMMY_CFG 寄存器允许软件配置读操作时插入的 Dummy Cycle 数量。Dummy Cycle 用于等待 AXI 读数据返回，其设置应满足最差情况下的读延迟预算。默认值 32（配置值=8'h20）+ 1 = 33 个 SCLK 周期可覆盖典型 AXI 总线延迟（约 10~20 个 AXI 时钟周期）。在低 AXI 时钟频率或高延迟 AXI Slave 场景下，软件可以增加该值以提供充足的等待时间；在高速场景下，可以减少该值以提高读操作效率。

**SPI_STATUS (OPCODE=8'h50) — SPI 状态寄存器（SPI Status Register）：**

| 比特位 | 字段名称 | 类型 | 默认值 | 描述 |
|-------|---------|------|--------|------|
| [31:8] | RESERVED | RO | 24'h0 | 保留位 |
| [7] | BUSY | RO | 1'h0 | SPI 忙标志：0=Idle（空闲，等待片选），1=Busy（正在处理事务） |
| [6] | AXI_ERR | RO | 1'h0 | AXI 总线错误标志：0=No Error, 1=AXI Slave 返回错误响应（SLVERR 或 DECERR），写 1 清除 |
| [5:4] | WR_FIFO_ST | RO | 2'b00 | 写 FIFO 状态：00=Empty, 01=Almost Empty, 10=Almost Full, 11=Full |
| [3:2] | RD_FIFO_ST | RO | 2'b00 | 读 FIFO 状态：00=Empty, 01=Almost Empty, 10=Almost Full, 11=Full |
| [1] | WR_DONE | RO | 1'h0 | 写操作完成标志：0=未完成, 1=最后一次写操作已完成，读后自动清零 |
| [0] | RD_READY | RO | 1'h0 | 读数据就绪标志：0=无可用读数据, 1=读数据已就绪可被读取，读后自动清零 |

SPI_STATUS 寄存器提供 SPI2AXI 的实时运行状态。BUSY 位可用于轮询判断当前事务是否处理完成。AXI_ERR 位记录 AXI 总线异常事件，若检测到 SLVERR（Slave Error）或 DECERR（Decode Error），该位置 1 并通过写 1 清除。WR_FIFO_ST 和 RD_FIFO_ST 提供 FIFO 的填充状态，软件可根据这些状态调整传输速率或判断数据流状态。WR_DONE 和 RD_READY 是单次传输的完成状态指示，具有读后自动清零（Read-to-Clear）的行为特性。

**SPI_IP_ID (OPCODE=8'h51) — IP 标识寄存器（IP Identification Register）：**

| 比特位 | 字段名称 | 类型 | 默认值 | 描述 |
|-------|---------|------|--------|------|
| [31:24] | IP_YEAR | RO | 8'h26 | IP 设计年份（2026 = 8'h1A） |
| [23:16] | IP_MONTH | RO | 8'h05 | IP 设计月份（May = 8'h05） |
| [15:8] | IP_VERSION | RO | 8'h01 | IP 主版本号：v1.0 |
| [7:4] | IP_REVISION | RO | 4'h0 | IP 次版本号/修订号 |
| [3:0] | IP_ID | RO | 4'h1 | IP 类型标识：4'h1=SPI2AXI Bridge |

SPI_IP_ID 寄存器是只读的 IP 标识寄存器，返回 IP 的设计日期、版本号和类型标识。软件可以通过读取该寄存器确认 SPI2AXI IP 的存在及其版本信息，用于驱动兼容性判断和固件版本管理。

### 7.4 CSR 读写操作时序

**CSR 写操作时序（通过 REG_WRITE OPCODE）：**

SPI Master 发送 REG_WRITE OPCODE（8'h40~8'h42）后直接进入 DATA 阶段（跳过 ADDR 阶段），在 DATA 阶段发送 32-bit 寄存器写数据。cmd_decoder_fsm 根据 OPCODE 解码出目标寄存器地址，在 DATA 阶段完成时将写数据锁存到对应寄存器中。

**CSR 读操作时序（通过 REG_READ OPCODE）：**

SPI Master 发送 REG_READ OPCODE（8'h50~8'h51）后进入 DATA 阶段（跳过 ADDR 和 DUMMY 阶段），在 DATA 阶段从指定寄存器读取 32-bit 数据并通过 spi_sdo 输出。REG_READ 操作无需 Dummy Cycle，因为寄存器数据的读取在当前 SPI 时钟周期内即可完成，无需等待 AXI 总线。

### 7.5 CSR RTL 模板

以下为 SPI2AXI CSR 模块的 SystemVerilog RTL 模板：

```systemverilog
// SPI2AXI Configuration Registers
module config_regs (
    input  logic        spi_sclk,
    input  logic        rst_n_spi,
    input  logic [7:0]  opcode,
    input  logic [31:0] reg_wdata,
    input  logic        reg_wr_en,     // from cmd_decoder: DATA & shift_done & REG_WRITE
    input  logic        reg_rd_en,     // from cmd_decoder: DATA & shift_done & REG_READ
    output logic [31:0] reg_rdata,
    output logic        spi_mode,      // 0=1-line, 1=4-line
    output logic        spi_en,
    output logic        wrap_en,
    output logic [3:0]  wrap_size,
    output logic [7:0]  dummy_cycles,
    input  logic [1:0]  wr_fifo_st,
    input  logic [1:0]  rd_fifo_st,
    input  logic        axi_err_in,
    input  logic        busy_in
);

    // Register definitions
    logic [31:0] spi_ctrl, spi_wrap_cfg, spi_dummy_cfg;
    logic [31:0] spi_status, spi_ip_id;

    // SPI_CTRL register write
    always_ff @(posedge spi_sclk or negedge rst_n_spi) begin
        if (!rst_n_spi)
            spi_ctrl <= 32'h0;
        else if (reg_wr_en && (opcode == 8'h40))
            spi_ctrl <= reg_wdata;
    end

    // Register field extraction
    assign spi_mode    = spi_ctrl[2];
    assign spi_en      = spi_ctrl[0];
    assign wrap_en     = spi_wrap_cfg[0];
    assign wrap_size   = spi_wrap_cfg[7:4];
    assign dummy_cycles = spi_dummy_cfg[7:0];

    // SPI_STATUS register (read-only, with clear-on-read for WR_DONE/RD_READY)
    always_ff @(posedge spi_sclk or negedge rst_n_spi) begin
        if (!rst_n_spi)
            spi_status <= 32'h0;
        else begin
            spi_status[7] <= busy_in;
            spi_status[6] <= axi_err_in;
            spi_status[5:4] <= wr_fifo_st;
            spi_status[3:2] <= rd_fifo_st;
        end
    end

    // Read data mux
    always_comb begin
        case (opcode)
            8'h50: reg_rdata = spi_status;
            8'h51: reg_rdata = spi_ip_id;
            default: reg_rdata = 32'h0;
        endcase
    end

endmodule
```

---

## 第8章 时钟与复位 (Clock & Reset)

### 8.1 时钟域划分

SPI2AXI Bridge IP 包含两个完全独立的异步时钟域：SPI 时钟域和 AXI 时钟域。两个时钟域之间没有固定的相位关系或频率比例要求所有跨时钟域路径必须通过异步 FIFO 或脉冲同步器进行处理。

| 时钟域 | 时钟名称 | 频率范围 | 来源 | 描述 |
|--------|---------|---------|------|------|
| SPI 时钟域 | spi_sclk | DC~50MHz | 外部 SPI Master | SPI 串行时钟，由外部主机驱动，仅在 SPI 传输期间存在有效时钟沿 |
| AXI 时钟域 | axi_aclk | 典型 100~200MHz | SoC 系统时钟 | AXI 系统总线时钟，持续运行，由 SoC 时钟管理单元提供 |

### 8.2 时钟域分配

以下表格列出了各子模块所属的时钟域：

| 子模块 | 时钟域 | 时钟源 | 包含的逻辑 |
|--------|--------|-------|-----------|
| spi_slave_if | SPI | spi_sclk | SPI 移位寄存器、模式选择逻辑、并串/串并转换器 |
| cmd_decoder_fsm | SPI | spi_sclk | 6-state FSM、计数器、控制信号生成 |
| config_regs | SPI | spi_sclk | CSR 寄存器读写逻辑、字段提取 |
| async_fifo.wr_port | SPI | spi_sclk | 写 FIFO 的写指针、写数据寄存器、格雷码编码 |
| async_fifo.rd_port | AXI | axi_aclk | 写 FIFO 的读指针、读数据寄存器、格雷码编码 |
| async_fifo.wr_port (rd_fifo) | AXI | axi_aclk | 读 FIFO 的写指针、写数据寄存器、格雷码编码 |
| async_fifo.rd_port (rd_fifo) | SPI | spi_sclk | 读 FIFO 的读指针、读数据寄存器、格雷码编码 |
| axi_master_if | AXI | axi_aclk | AXI 写地址/数据/响应通道、读地址/数据通道控制器 |
| wrap_ctrl | AXI | axi_aclk | 地址环绕计算逻辑、地址序列生成器 |

### 8.3 跨时钟域同步方案

SPI 时钟域和 AXI 时钟域之间的所有数据和控制信号传输均通过专用的跨时钟域同步机制实现：

**数据通路 CDC — 异步 FIFO（Async FIFO）：**

数据通路的 CDC 使用标准的 dual-clock 异步 FIFO 结构。FIFO 的核心组件包括：

1. **双端口存储器（Dual-Port RAM）**：作为 FIFO 的数据存储体，写入端口和读取端口各自使用独立的时钟。典型的 FIFO 深度为 8 或 16，数据宽度为 32-bit（读数据 FIFO）或 64-bit（写数据 FIFO，包含地址+数据）。

2. **写指针和读指针（Write/Read Pointers）**：写指针在写时钟域（wclk）下递增，读指针在读时钟域（rclk）下递增。指针值比实际地址多 1 位（N+1 位指针用于 N 位地址），最高位用于区分满和空状态。

3. **格雷码编码器（Gray Code Encoders）**：写指针和读指针在跨时钟域传递前转换为格雷码（Gray Code）。格雷码的特性是相邻数值之间只有 1 个 bit 发生变化，可最大限度减少亚稳态影响。

4. **两级同步器（2-Flop Synchronizer）**：格雷码指针通过两级 D 触发器链同步到目标时钟域，提供 MTBF（Mean Time Between Failures）满足要求的亚稳态防护。

5. **空/满标志生成器（Empty/Full Flag Generators）**：在各自时钟域内，将同步后的对端指针与本地指针进行比较，生成空标志（empty）和满标志（full），以及可选的几乎空（almost_empty）和几乎满（almost_full）标志。

**控制信号 CDC — 脉冲同步器（Pulse Synchronizer）：**

非数据类的控制信号（如 axi_start_req, axi_done）使用脉冲同步器（Pulse Synchronizer）进行跨时钟域传输。脉冲同步器的基本结构包括：

1. 源时钟域内的电平翻转逻辑（Toggle Flip-Flop）
2. 两级同步器（2-Flop Synchronizer）
3. 目标时钟域内的边沿检测逻辑（Edge Detector）

脉冲同步器将源时钟域的一个时钟周期脉冲转换为目标时钟域的一个时钟周期脉冲，同步延迟为 2~3 个目标时钟周期。

### 8.4 复位方案

SPI2AXI IP 采用异步复位、同步释放（Asynchronous Assertion, Synchronous Deassertion）的复位同步器方案。两个时钟域各自拥有独立的复位同步器：

**复位同步器结构：**

```systemverilog
// SPI Clock Domain Reset Synchronizer
logic rst_sync_spi_1, rst_n_spi_sync;
always_ff @(posedge spi_sclk or negedge rst_n) begin
    if (!rst_n) begin
        rst_sync_spi_1 <= 1'b0;
        rst_n_spi_sync <= 1'b0;
    end else begin
        rst_sync_spi_1 <= 1'b1;
        rst_n_spi_sync <= rst_sync_spi_1;
    end
end

// AXI Clock Domain Reset Synchronizer
logic rst_sync_axi_1, rst_n_axi_sync;
always_ff @(posedge axi_aclk or negedge rst_n) begin
    if (!rst_n) begin
        rst_sync_axi_1 <= 1'b0;
        rst_n_axi_sync <= 1'b0;
    end else begin
        rst_sync_axi_1 <= 1'b1;
        rst_n_axi_sync <= rst_sync_axi_1;
    end
end
```

复位同步器的特性：
- **异步置位（Asynchronous Assertion）**：全局复位 rst_n 的下降沿立即将同步器输出清零，保证复位信号能在最短时间内传播到所有时序单元，不受时钟沿限制
- **同步释放（Synchronous Deassertion）**：全局复位 rst_n 的上升沿通过两级同步器延迟后释放，防止亚稳态传播
- **分层复位**：每个异步 FIFO 内部也包含独立的复位同步器，确保 FIFO 的读/写指针在复位释放后处于正确的初始状态

### 8.5 时钟门控

AXI 时钟域（axi_aclk）由 SoC 系统时钟管理单元控制，SPI2AXI 内部不对 axi_aclk 进行时钟门控。SPI 时钟域（spi_sclk）由外部 SPI Master 提供，在无 SPI 传输时 sclk 保持为低电平（IDLE 状态）。由于 spi_sclk 并非持续运行的时钟，SPI 时钟域内的所有时序逻辑（移位寄存器、FSM、计数器）在 sclk 停止时自动保持当前状态，门控功耗天然为零。

---

## 第9章 SDC 时序约束 (SDC Timing Constraints)

### 9.1 时钟定义

以下为 SPI2AXI IP 的完整 SDC（Synopsys Design Constraints）文件。该 SDC 文件可在综合流程中直接使用，包含时钟定义、I/O 延迟约束、跨时钟域约束和时序例外路径约束：

```tcl
# ============================================================================
# SPI2AXI Bridge IP — Synopsys Design Constraints (SDC)
# File: spi2axi_bridge.sdc
# Version: v1.0
# ============================================================================

# ----------------------------------------------------------------------------
# 1. Clock Definitions (时钟定义)
# ----------------------------------------------------------------------------

# SPI Clock: External SPI Master provides sclk, max 50MHz
create_clock -name spi_sclk -period 20.0 -waveform {0 10.0} [get_ports spi_sclk]
set_clock_uncertainty -setup 0.5 [get_clocks spi_sclk]
set_clock_uncertainty -hold  0.3 [get_clocks spi_sclk]
set_clock_transition -rise 0.5 [get_clocks spi_sclk]
set_clock_transition -fall 0.5 [get_clocks spi_sclk]

# AXI Clock: SoC system clock, assumed 100MHz (period=10ns)
create_clock -name axi_aclk -period 10.0 -waveform {0 5.0} [get_ports axi_aclk]
set_clock_uncertainty -setup 0.3 [get_clocks axi_aclk]
set_clock_uncertainty -hold  0.2 [get_clocks axi_aclk]
set_clock_transition -rise 0.3 [get_clocks axi_aclk]
set_clock_transition -fall 0.3 [get_clocks axi_aclk]

# Generated clocks for internal usage (if needed by synthesis tool)
# create_generated_clock -name spi_clk_int -source [get_ports spi_sclk] \
#     -divide_by 1 [get_pins spi_slave_if/spi_clk_int_reg/Q]
```

### 9.2 输入延迟约束

SPI 输入信号（spi_sdi, spi_cs_n）相对于 spi_sclk 的输入路径延迟约束。这些约束基于典型 PCB 走线延迟和外部 SPI Master 的输出延迟进行设定：

```tcl
# ----------------------------------------------------------------------------
# 2. Input Delay Constraints (输入延迟约束)
# ----------------------------------------------------------------------------

# SPI Chip Select input delay (relative to spi_sclk)
set_input_delay -clock spi_sclk -max 5.0 [get_ports spi_cs_n]
set_input_delay -clock spi_sclk -min 1.0 [get_ports spi_cs_n]
set_input_delay -clock spi_sclk -max 5.0 -clock_fall [get_ports spi_cs_n]
set_input_delay -clock spi_sclk -min 1.0 -clock_fall [get_ports spi_cs_n]

# SPI Data Input (spi_sdi) — sampled on rising edge of spi_sclk
set_input_delay -clock spi_sclk -max 4.0 [get_ports spi_sdi*]
set_input_delay -clock spi_sclk -min 0.5 [get_ports spi_sdi*]

# AXI input signals — Slave to Master handshake signals
# These come from AXI Slave, driven relative to axi_aclk
set_input_delay -clock axi_aclk -max 3.0 [get_ports m_axi_awready]
set_input_delay -clock axi_aclk -min 0.5 [get_ports m_axi_awready]
set_input_delay -clock axi_aclk -max 3.0 [get_ports m_axi_wready]
set_input_delay -clock axi_aclk -min 0.5 [get_ports m_axi_wready]
set_input_delay -clock axi_aclk -max 3.0 [get_ports m_axi_bvalid]
set_input_delay -clock axi_aclk -min 0.5 [get_ports m_axi_bvalid]
set_input_delay -clock axi_aclk -max 3.0 [get_ports m_axi_bresp*]
set_input_delay -clock axi_aclk -min 0.5 [get_ports m_axi_bresp*]
set_input_delay -clock axi_aclk -max 3.0 [get_ports m_axi_arready]
set_input_delay -clock axi_aclk -min 0.5 [get_ports m_axi_arready]
set_input_delay -clock axi_aclk -max 3.0 [get_ports m_axi_rvalid]
set_input_delay -clock axi_aclk -min 0.5 [get_ports m_axi_rvalid]
set_input_delay -clock axi_aclk -max 3.0 [get_ports m_axi_rdata*]
set_input_delay -clock axi_aclk -min 0.5 [get_ports m_axi_rdata*]
set_input_delay -clock axi_aclk -max 3.0 [get_ports m_axi_rresp*]
set_input_delay -clock axi_aclk -min 0.5 [get_ports m_axi_rresp*]
set_input_delay -clock axi_aclk -max 3.0 [get_ports m_axi_rlast]
set_input_delay -clock axi_aclk -min 0.5 [get_ports m_axi_rlast]
set_input_delay -clock axi_aclk -max 3.0 [get_ports m_axi_bid*]
set_input_delay -clock axi_aclk -min 0.5 [get_ports m_axi_bid*]
set_input_delay -clock axi_aclk -max 3.0 [get_ports m_axi_rid*]
set_input_delay -clock axi_aclk -min 0.5 [get_ports m_axi_rid*]
```

### 9.3 输出延迟约束

SPI 输出信号（spi_sdo）和 AXI Master 输出信号的输出路径延迟约束：

```tcl
# ----------------------------------------------------------------------------
# 3. Output Delay Constraints (输出延迟约束)
# ----------------------------------------------------------------------------

# SPI Data Output (spi_sdo) — driven on falling edge of spi_sclk
set_output_delay -clock spi_sclk -max 5.0 [get_ports spi_sdo*]
set_output_delay -clock spi_sclk -min 1.0 [get_ports spi_sdo*]

# AXI Master output signals — Address/Data/Control to AXI Slave
set_output_delay -clock axi_aclk -max 4.0 [get_ports m_axi_awaddr*]
set_output_delay -clock axi_aclk -min 0.5 [get_ports m_axi_awaddr*]
set_output_delay -clock axi_aclk -max 4.0 [get_ports m_axi_awvalid]
set_output_delay -clock axi_aclk -min 0.5 [get_ports m_axi_awvalid]
set_output_delay -clock axi_aclk -max 4.0 [get_ports m_axi_awid*]
set_output_delay -clock axi_aclk -min 0.5 [get_ports m_axi_awid*]
set_output_delay -clock axi_aclk -max 4.0 [get_ports m_axi_wdata*]
set_output_delay -clock axi_aclk -min 0.5 [get_ports m_axi_wdata*]
set_output_delay -clock axi_aclk -max 4.0 [get_ports m_axi_wstrb*]
set_output_delay -clock axi_aclk -min 0.5 [get_ports m_axi_wstrb*]
set_output_delay -clock axi_aclk -max 4.0 [get_ports m_axi_wvalid]
set_output_delay -clock axi_aclk -min 0.5 [get_ports m_axi_wvalid]
set_output_delay -clock axi_aclk -max 4.0 [get_ports m_axi_wlast]
set_output_delay -clock axi_aclk -min 0.5 [get_ports m_axi_wlast]
set_output_delay -clock axi_aclk -max 4.0 [get_ports m_axi_bready]
set_output_delay -clock axi_aclk -min 0.5 [get_ports m_axi_bready]
set_output_delay -clock axi_aclk -max 4.0 [get_ports m_axi_araddr*]
set_output_delay -clock axi_aclk -min 0.5 [get_ports m_axi_araddr*]
set_output_delay -clock axi_aclk -max 4.0 [get_ports m_axi_arvalid]
set_output_delay -clock axi_aclk -min 0.5 [get_ports m_axi_arvalid]
set_output_delay -clock axi_aclk -max 4.0 [get_ports m_axi_arid*]
set_output_delay -clock axi_aclk -min 0.5 [get_ports m_axi_arid*]
set_output_delay -clock axi_aclk -max 4.0 [get_ports m_axi_rready]
set_output_delay -clock axi_aclk -min 0.5 [get_ports m_axi_rready]
```

### 9.4 跨时钟域约束

SPI 时钟域和 AXI 时钟域之间的所有路径必须标记为异步路径，防止 STA（Static Timing Analysis）工具对这些路径进行时序分析：

```tcl
# ----------------------------------------------------------------------------
# 4. Clock Domain Crossing Constraints (跨时钟域约束)
# ----------------------------------------------------------------------------

# Set clock groups as asynchronous — all paths between SPI and AXI clock domains
# should not be analyzed for setup/hold timing (handled by CDC design)
set_clock_groups -asynchronous \
    -group [get_clocks spi_sclk] \
    -group [get_clocks axi_aclk]

# Explicit false path between the two clock domains (backup to clock_groups)
set_false_path -from [get_clocks spi_sclk] -to [get_clocks axi_aclk]
set_false_path -from [get_clocks axi_aclk] -to [get_clocks spi_sclk]
```

### 9.5 异步 FIFO 内部约束

异步 FIFO 内部的跨时钟域路径（格雷码同步器路径）需要被特殊处理。这些路径虽然跨时钟域，但格雷码保证只有 1 个 bit 变化，由 CDC 设计保证功能正确性：

```tcl
# ----------------------------------------------------------------------------
# 5. Async FIFO Internal Constraints (异步FIFO内部约束)
# ----------------------------------------------------------------------------

# False path for FIFO gray-code synchronizer paths
# These paths are CDC-safe by design (gray-code + 2-flop synchronizer)
set_false_path -from [get_clocks spi_sclk] \
    -to [get_registers "async_fifo/*wr_ptr_sync_*"]
set_false_path -from [get_clocks axi_aclk] \
    -to [get_registers "async_fifo/*rd_ptr_sync_*"]
```

### 9.6 假路径约束（False Paths）

以下为设计中不需要进行时序分析的路径：

```tcl
# ----------------------------------------------------------------------------
# 6. False Paths (假路径约束)
# ----------------------------------------------------------------------------

# Test mode signals (if test_mode port exists) — not timing-critical
if {[llength [get_ports test_mode -quiet]] > 0} {
    set_false_path -from [get_ports test_mode]
    set_false_path -to [get_ports test_mode]
}

# Functional reset path — reset synchronizer has its own timing closure
set_false_path -from [get_ports rst_n] -to [get_registers "*rst_sync_*"]
```

### 9.7 多周期路径约束（Multicycle Paths）

设计中若存在从慢时钟域到快时钟域的非关键路径，可设置多周期路径约束以减少综合工具对 setup 的过度优化：

```tcl
# ----------------------------------------------------------------------------
# 7. Multicycle Paths (多周期路径约束)
# ----------------------------------------------------------------------------

# SPI 50MHz -> AXI 100MHz: SPI is slower, AXI receives CDC data.
# The FIFO read enables in AXI domain are asserted after multiple AXI cycles,
# so we can relax setup on these paths.
set_multicycle_path -setup 2 -from [get_clocks spi_sclk] -to [get_clocks axi_aclk] \
    -through [get_pins async_fifo/*/rden]
```

---

## 第10章 实现指南 (Implementation Guide)

### 10.1 RTL 设计规范

SPI2AXI Bridge IP 的 RTL 实现遵循以下设计规范和编码约定：

**命名规范：**

| 规范类别 | 约定 | 示例 |
|---------|------|------|
| 模块名称 | 小写字母 + 下划线 | spi_slave_if, cmd_decoder_fsm |
| 信号名称 | 小写字母 + 下划线 | spi_cs_n, m_axi_awvalid |
| 参数名称 | 大写字母 + 下划线 | AXI_ADDR_WIDTH, DUMMY_CYCLES |
| 本地参数 | 大写字母 + 下划线 | CLK_PERIOD_NS, FIFO_DEPTH |
| 时钟域后缀 | _spi / _axi | clk_spi, clk_axi, rst_n_spi, rst_n_axi |

**编码约定：**

1. **时钟和复位**：所有时序逻辑统一使用 `posedge clk` 触发，异步复位使用 `negedge rst_n`。不使用双边沿触发或门控时钟。
2. **阻塞赋值 vs 非阻塞赋值**：时序逻辑（always_ff）使用非阻塞赋值（<=）；组合逻辑（always_comb）使用阻塞赋值（=）。
3. **FSM 编码**：三段式状态机编码（状态寄存器 + 次态逻辑 + 输出解码）。
4. **参数化设计**：所有可配置的参数化宽度（如 FIFO 深度、AXI 地址宽度）通过 module parameter 传入，不使用硬编码常量。

### 10.2 时钟域交叉处理

SPI 时钟域与 AXI 时钟域之间的所有数据和控制路径必须经过明确的 CDC 处理：

**异步 FIFO 实例化：**

```systemverilog
// Async FIFO instantiation for write data path
async_fifo #(
    .DATA_WIDTH (64),   // 32-bit addr + 32-bit data
    .FIFO_DEPTH (8)
) wr_fifo_inst (
    .wclk      (spi_sclk),
    .wrst_n    (rst_n_spi_sync),
    .wdata     ({addr_reg, wdata_reg}),
    .wren      (fifo_wr_en),
    .wfull     (wr_fifo_full),
    .walmost_full (wr_fifo_almost_full),
    .rclk      (axi_aclk),
    .rrst_n    (rst_n_axi_sync),
    .rdata     ({axi_addr, axi_wdata}),
    .rden      (axi_fifo_rd_en),
    .rempty    (wr_fifo_empty)
);

// Async FIFO instantiation for read data path
async_fifo #(
    .DATA_WIDTH (32),   // 32-bit read data only
    .FIFO_DEPTH (8)
) rd_fifo_inst (
    .wclk      (axi_aclk),
    .wrst_n    (rst_n_axi_sync),
    .wdata     (axi_rdata),
    .wren      (rd_fifo_wr_en),
    .wfull     (rd_fifo_full),
    .walmost_full (rd_fifo_almost_full),
    .rclk      (spi_sclk),
    .rrst_n    (rst_n_spi_sync),
    .rdata     (spi_rdata),
    .rden      (fifo_rd_en),
    .rempty    (rd_fifo_empty)
);
```

### 10.3 AXI4-Lite Master 实现

AXI4-Lite Master 接口的实现需要正确处理 VALID/READY 握手机制。以下是写事务控制器的关键状态机片段：

```systemverilog
typedef enum logic [1:0] {
    WR_IDLE,
    WR_ADDR,
    WR_DATA,
    WR_RESP
} wr_state_t;

wr_state_t wr_state, wr_next;

always_ff @(posedge axi_aclk or negedge rst_n_axi) begin
    if (!rst_n_axi)
        wr_state <= WR_IDLE;
    else
        wr_state <= wr_next;
end

always_comb begin
    wr_next = wr_state;
    case (wr_state)
        WR_IDLE: if (axi_start && axi_wr_rd_n) wr_next = WR_ADDR;
        WR_ADDR: if (m_axi_awready)             wr_next = WR_DATA;
        WR_DATA: if (m_axi_wready)              wr_next = WR_RESP;
        WR_RESP: if (m_axi_bvalid)              wr_next = WR_IDLE;
    endcase
end

// AW channel output
always_ff @(posedge axi_aclk or negedge rst_n_axi) begin
    if (!rst_n_axi) begin
        m_axi_awaddr  <= '0;
        m_axi_awvalid <= 1'b0;
    end else begin
        if (wr_state == WR_IDLE && axi_start && axi_wr_rd_n) begin
            m_axi_awaddr  <= wr_fifo_rdata[63:32];  // address from FIFO
            m_axi_awvalid <= 1'b1;
        end else if (m_axi_awready) begin
            m_axi_awvalid <= 1'b0;
        end
    end
end
```

### 10.4 Wrap 地址生成逻辑

```systemverilog
module wrap_ctrl (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        wrap_en,
    input  logic [3:0]  wrap_size,     // N words
    input  logic [31:0] base_addr,     // Starting address (4B aligned)
    input  logic        access_done,   // AXI access done pulse
    output logic [31:0] next_addr
);

    logic [31:0] current_addr;
    logic [31:0] wrap_boundary;

    // Wrap boundary = base_addr + (wrap_size * 4)
    assign wrap_boundary = base_addr + ({wrap_size, 2'b00});

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            current_addr <= '0;
        else if (access_done) begin
            if (wrap_en) begin
                if (current_addr + 4 >= wrap_boundary)
                    current_addr <= base_addr;   // Wrap back
                else
                    current_addr <= current_addr + 4;  // Next word
            end else begin
                current_addr <= current_addr + 4;  // Linear increment
            end
        end
    end

    // Initial address load
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            current_addr <= '0;
        else if (axi_start)
            current_addr <= base_addr;
    end

    assign next_addr = current_addr;

endmodule
```

---

## 第11章 验证计划 (Verification Plan)

**状态**: 待补充 — 本章节需要根据 SPI2AXI IP 功能特性补充完整的验证计划。以下为验证框架和初步验证点建议。

### 11.1 验证策略

SPI2AXI Bridge IP 的验证需要覆盖功能正确性、接口协议兼容性、跨时钟域可靠性和异常处理能力四个维度。建议使用 SystemVerilog 搭建自检查验证环境，通过随机约束激励和定向测试用例相结合的方式进行验证。

### 11.2 功能验证点

以下为建议的 SPI2AXI 功能验证点列表：

| 验证点 ID | 验证点描述 | 测试类型 | 覆盖场景 |
|----------|---------|---------|---------|
| FUNC-01 | SPI 标准模式（1-line）写操作：OPCODE + ADDR + WDATA 完整写帧传输 | 定向 | WRITE 基本功能 |
| FUNC-02 | SPI 标准模式（1-line）读操作：OPCODE + ADDR + DUMMY + RDATA 完整读帧传输 | 定向 | READ 基本功能 |
| FUNC-03 | QSPI 模式（4-line）写/读操作 | 定向 | QSPI 模式切换和传输 |
| FUNC-04 | REG_WRITE 操作（寄存器写） | 定向 | SPI_CTRL/SPI_WRAP_CFG/SPI_DUMMY_CFG 写入 |
| FUNC-05 | REG_READ 操作（寄存器读） | 定向 | SPI_STATUS/SPI_IP_ID 读取 |
| FUNC-06 | AXI4-Lite AW/W/B 三通道握手 | 随机 | AXI 写事务 VALID/READY 握手 |
| FUNC-07 | AXI4-Lite AR/R 两通道握手 | 随机 | AXI 读事务 VALID/READY 握手 |
| FUNC-08 | 地址环绕功能：Wrap=0（无环绕） | 定向 | 线性递增地址序列 |
| FUNC-09 | 地址环绕功能：Wrap=2 | 定向 | 2-word 环绕地址序列 |
| FUNC-10 | 地址环绕功能：Wrap=4 | 定向 | 4-word 环绕地址序列 |
| FUNC-11 | 跨时钟域数据传输正确性 | 随机 | SPI↔AXI CDC 数据完整性 |
| FUNC-12 | 连续 SPI 帧传输（无 CS 间隔） | 定向 | 多帧连续处理 |
| FUNC-13 | SPI 帧中途 CS 异常拉高 | 异常 | 传输中断后恢复 |

### 11.3 验证环境架构（建议）

**待补充** — 建议的验证环境架构：

- SPI Master BFM：模拟外部 SPI Master 行为，支持 1-line/4-line 模式
- AXI4-Lite Slave BFM：模拟 AXI Slave 响应，支持随机延迟和错误注入
- 参考模型：SPI2AXI 行为级参考模型，用于输出比对
- Scoreboard：用于数据完整性检查
- Coverage Collector：功能覆盖率收集

### 11.4 时序验证点

**待补充** — 建议的时序验证点：

| 验证点 ID | 验证点描述 |
|----------|---------|
| TIM-01 | SPI 时钟最高频率（50MHz）下的建立/保持时间检查 |
| TIM-02 | AXI 接口时序满足 AXI4-Lite 协议规范 |
| TIM-03 | 异步 FIFO CDC 路径的同步正确性（撒点检查） |

### 11.5 异常场景验证

**待补充** — 建议的异常场景验证点：

| 验证点 ID | 验证点描述 |
|----------|---------|
| ERR-01 | SPI 传输中途片选异常拉高后重新开始 |
| ERR-02 | AXI Slave 返回 SLVERR 错误响应 |
| ERR-03 | AXI Slave 返回 DECERR 错误响应 |
| ERR-04 | 写 FIFO 满状态下的写入请求处理 |
| ERR-05 | 读 FIFO 空状态下的读取请求处理 |

---

## 第12章 DFT 设计 (DFT Design)

**状态**: 待补充 — 本章节需要根据具体 SoC 的 DFT 架构要求进行补充。以下为 SPI2AXI 的 DFT 设计建议框架。

### 12.1 扫描链设计（Scan Chain）

SPI2AXI IP 包含的时序单元（Flip-Flop）分布于两个时钟域和多个子模块中，建议将所有时序单元接入 SoC 级的扫描链：

**扫描链接入方案：**

| DFT 要素 | 描述 |
|---------|------|
| 扫描链数量 | 建议 1~2 条扫描链，由面积和测试时间权衡决定 |
| 扫描时钟 | scan_clk（SoC 测试时钟），SPI 和 AXI 时钟域在测试模式下通过时钟 MUX 切换到 scan_clk |
| 扫描使能 | scan_enable 信号控制功能模式 / 扫描移位模式切换 |
| 扫描类型 | Muxed-D 型扫描触发器（Muxed-D Scan FF），面积开销最小 |

**时钟 MUX 方案：**

在测试模式下，spi_sclk 和 axi_aclk 都需要通过时钟 MUX 切换到 scan_clk：

```systemverilog
// Test mode clock muxing
logic spi_clk_int;
logic axi_clk_int;

assign spi_clk_int = test_mode ? scan_clk : spi_sclk;
assign axi_clk_int = test_mode ? scan_clk : axi_aclk;
```

### 12.2 存储器 BIST（Memory BIST）

异步 FIFO（dual-clock FIFO）的内部存储单元建议使用 MBIST 覆盖：

| MBIST 要素 | 描述 |
|-----------|------|
| 测试对象 | async_fifo 内部的双端口 RAM |
| BIST 类型 | March C- 算法，覆盖率较高 |
| BIST 控制器 | SoC 级 MBIST 控制器共享 |
| BIST 时钟 | 独立的 BIST 时钟（bist_clk） |

### 12.3 边界扫描（Boundary Scan）

**待补充** — SPI 接口管脚建议选择性接入边界扫描链，AXI 接口管脚建议通过 SoC 级边界扫描覆盖。

### 12.4 测试覆盖率目标

**待补充** — 建议的 DFT 测试覆盖率目标：

| 覆盖率类型 | 目标值 | 说明 |
|-----------|-------|------|
| Stuck-At 故障覆盖率 | ≥ 98% | 标准 stuck-at 测试 |
| Transition 故障覆盖率 | ≥ 90% | 时序故障测试（at-speed） |
| 桥接故障覆盖率 | ≥ 85% | 使用邻近桥接故障模型 |

---

## 第13章 交付物 (Deliverables)

**状态**: 待补充 — 以下为 SPI2AXI IP 建议的交付物清单。

### 13.1 RTL 交付物

| 交付物 | 文件格式 | 数量 | 描述 |
|--------|---------|------|------|
| SPI2AXI Top-level RTL | .sv | 1 | spi2axi_bridge.sv — 顶层模块，包含所有子模块实例化 |
| SPI Slave Interface | .sv | 1 | spi_slave_if.sv — SPI 从接口，串并/并串转换 |
| Command Decoder FSM | .sv | 1 | cmd_decoder_fsm.sv — 6 状态有限状态机控制器 |
| Async Dual-Clock FIFO | .sv | 1 | async_fifo.sv — 异步双时钟 FIFO，格雷码同步 |
| AXI4-Lite Master | .sv | 1 | axi_master_if.sv — AXI5 通道主接口 |
| Configuration Registers | .sv | 1 | config_regs.sv — SPI 侧配置寄存器 |
| Wrap Controller | .sv | 1 | wrap_ctrl.sv — 地址环绕控制器 |
| Reset Synchronizer | .sv | 1 | rst_sync.sv — 异步复位同步释放模块 |

### 13.2 约束与脚本交付物

| 交付物 | 文件格式 | 数量 | 描述 |
|--------|---------|------|------|
| SDC 时序约束文件 | .sdc | 1 | spi2axi_bridge.sdc — 完整时序约束，含时钟定义和 CDC 约束 |
| Synopsys DC 综合脚本 | .tcl | 1 | synth_spi2axi.tcl — DC 综合流程脚本 |
| 综合后时序报告 | .rpt | 1~3 | 综合后 setup/hold/power 分析报告 |

### 13.3 验证交付物

**待补充** — 以下为建议的验证交付物清单：

| 交付物 | 文件格式 | 数量 | 描述 |
|--------|---------|------|------|
| 验证环境顶层 | .sv | 1 | UVM 或自检查测试平台顶层 |
| SPI Master BFM | .sv | 1 | SPI 主设备行为模型 |
| AXI4-Lite Slave BFM | .sv | 1 | AXI 从设备行为模型 |
| 测试用例 | .sv | 10+ | 功能/异常/随机测试用例 |
| 覆盖率报告 | .rpt | 1 | 功能覆盖率 + 代码覆盖率 |

### 13.4 文档交付物

| 交付物 | 文件格式 | 描述 |
|--------|---------|------|
| 高电平设计文档（HLD） | .md | SPI2AXI 总体架构设计规格书 |
| 低电平设计文档（LLD） | .md | 本规范书（14 章完整微架构文档） |
| 用户指南 | .md | SPI2AXI IP 集成和使用说明 |

---

## 第14章 修订历史 (Revision History)

### 14.1 版本记录

| 版本 | 日期 | 作者 | 修订说明 |
|------|------|------|---------|
| v1.0 | 2026-05-21 | chip-spec-gen | 初始版本，基于 SPI2AXI SPEC.pdf 和 2.slice/ 源文档生成完整 14-章 LLD |

### 14.2 审核记录

| 版本 | 审核人 | 审核日期 | 审核意见 |
|------|-------|---------|---------|
| v1.0 | **待审核** | **待补充** | - |

### 14.3 待办事项清单

以下为本文档后续需要补充和完善的内容：

| 待办项 | 优先级 | 目标章节 | 说明 |
|-------|-------|---------|------|
| 补充完整验证计划（测试用例和覆盖率目标） | 高 | 第11章 | 需要根据 UVM 验证方法论补充 |
| 补充完整 DFT 设计方案 | 中 | 第12章 | 需要根据 SoC DFT 架构要求补充 |
| 验证交付物补充 | 中 | 第13章 | 需要根据验证环境实现补充 |
| 波形时序图补充 | 低 | 第2章、第4章 | 需要生成 WaveJSON 或 Mermaid 格式时序图 |
| 审核签名 | 低 | 第14章 | 设计评审完成后补充审核意见 |

---

> **文档结束** — SPI2AXI Bridge Micro-Architecture LLD v1.0
