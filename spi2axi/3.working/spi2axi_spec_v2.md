# SPI2AXI Bridge IP — 芯片设计规格书 (v2)

> 生成日期: 2026-05-20
> 源文档: SPI2AXI SPEC.pdf
> 状态: v2 — 补充完整版（含操作码、寄存器映射、FSM、时序图）
> 设计类型: 内部 Block (Bridge IP)
> 参考模板: 03_block_arch.HLD.md / 04_block_micro.LLD.md

---

## 1. 模块概述 (Module Overview)

### 1.1 概述

SPI2AXI IP 是一个将 **SPI 从设备 (Slave) 接口** 转换为 **AXI 主设备 (Master) 接口** 的桥接模块（Bridge），允许外部 SPI 主机（MCU/FPGA/测试设备）通过 SPI 总线访问 SoC 内部 AXI 总线上的存储器和外设。

SPI 是通用数字接口，SPI2AXI 桥接器可在桌面 PC 上配合 SPI 调试器使用，方便 pattern 调试和实验室 bringup/debug。

### 1.2 设计目标

| 目标 | 说明 |
|------|------|
| 功能 | SPI ↔ AXI4-Lite 协议转换桥接 |
| SPI 模式 | 标准 SPI (1线) + QSPI (4线) |
| AXI 协议 | AXI4-Lite，burst length = 1 (single transfer) |
| 时钟域 | 双时钟域：SPI_CLK (≤50MHz) / AXI_CLK (独立，如 100MHz+) |
| CDC 方案 | Dual-clock Asynchronous FIFO + Gray-code 指针同步 |
| 地址环绕 | 可配置 Wrap 地址环绕访问 (0=disabled, N>0=窗口大小) |
| 使用场景 | SoC 配置空间访问 (S3 config 空间) |
| 数据宽度 | 32-bit (AXI_DATA_WIDTH=32) |

### 1.3 主要特性

| 特性 | 描述 |
|------|------|
| **SPI 接口** | 支持标准 SPI 和四线 SPI (QSPI) 两种工作模式。SPI Slave 作为主动外设（active peripheral），无需 SoC 内部 CPU 干预即可完成 SoC 功能配置、状态观测等功能 |
| **AXI Lite 接口** | 将 SPI 侧接收到的命令/数据转换成 AXI 事务。通过 AXI Lite 接口访问 SoC 的内存和外设 |
| **跨时钟域处理** | SPI 时钟域与 AXI 时钟域分离。内置 dual-clock FIFOs（双时钟 FIFO）实现可靠跨时钟域传输（CDC） |
| **地址环绕** | 可配置 Wrap 地址环绕，支持连续地址窗口的循环访问 |
| **SPI 模式支持** | 支持所有 4 种 SPI 模式 (CPOL/CPHA 可配置)，MSB-first |

### 1.4 应用场景

- **系统调试和配置接口**: 通过 SPI 接口访问 SoC 配置空间 (S3 config)
- **低引脚数系统总线扩展**: 4-pin SPI 即可扩展 AXI 总线访问能力
- **嵌入式系统固件更新**: 外部 SPI 主机通过桥接器更新 SoC 固件
- **芯片测试和验证接口**: 实验室 bringup 和 debug 的标准接口

---

## 2. 接口定义 (Interface Definition)

### 2.1 SPI 从设备接口

#### 信号列表

| 信号名称 | 方向 | 位宽 | 描述 |
|----------|------|------|------|
| spi_sclk | 输入 | 1 | SPI 串行时钟，最大 50MHz |
| spi_cs_n | 输入 | 1 | SPI 片选信号（低有效） |
| spi_sdi | 输入 | 4 | SPI 数据输入线 [3:0] (QSPI 模式) |
| spi_sdo | 输出 | 4 | SPI 数据输出线 [3:0] (QSPI 模式) |

#### SPI 模式配置

| 模式 | CPOL | CPHA | 描述 |
|------|------|------|------|
| **0** (默认) | 0 | 0 | SCLK 空闲低电平，上升沿采样数据，下降沿更新数据 |
| 1 | 0 | 1 | SCLK 空闲低电平，下降沿采样数据，上升沿更新数据 |
| 2 | 1 | 0 | SCLK 空闲高电平，下降沿采样数据，上升沿更新数据 |
| 3 | 1 | 1 | SCLK 空闲高电平，上升沿采样数据，下降沿更新数据 |

#### 工作模式

| 模式 | 数据线宽 | 时钟周期/bit | 描述 |
|------|----------|-------------|------|
| 标准 SPI | 1-bit (sdi[0]/sdo[0]) | 1 | 单线双向传输 |
| QSPI | 4-bit (sdi[3:0]/sdo[3:0]) | 1/4 | 四线双向传输，4x 吞吐量 |

### 2.2 AXI4-Lite 主设备接口

5 个独立通道，遵循 AMBA AXI4-Lite 协议规范：

| 通道 | 方向 | 关键信号 |
|------|------|----------|
| AW (写地址) | Master → Slave | awaddr[31:0], awvalid, awready |
| W (写数据) | Master → Slave | wdata[31:0], wstrb[3:0], wvalid, wready |
| B (写响应) | Slave → Master | bresp[1:0], bvalid, bready |
| AR (读地址) | Master → Slave | araddr[31:0], arvalid, arready |
| R (读数据) | Slave → Master | rdata[31:0], rresp[1:0], rvalid, rready |

### 2.3 AXI 参数配置

| 参数 | 值 | 说明 |
|------|-----|------|
| AXI_ADDR_WIDTH | 32 | 地址总线宽度 |
| AXI_DATA_WIDTH | 32 | 数据总线宽度 |
| AXI_ID_WIDTH | 3 | ID 信号宽度 |
| AxLEN | 0 | 仅支持 single transfer (burst=1) |
| AxSIZE | 2 (4 bytes) | 每次传输 1 个 32-bit 字 |

---

## 3. 系统架构与子模块划分 (System Architecture & Sub-Module Partition)

### 3.1 顶层架构框图

```
+---------------------------+      +-------------------------------+
|   SPI Master (外部)       |      |   SoC                         |
|   (MCU / FPGA / 测试设备)  |      |                               |
|                           |      |   +-------------------------+ |
|   SPI CLK Domain          |      |   |  AXI CLK Domain         | |
|   +--------+              |      |   |  +----------+            | |
|   | SPI    |  SPI Bus     |      |   |  | SPI2AXI  |  AXI4-Lite | |
|   | Master | -----------+ |      |   |  | Bridge   | =========> | |
|   +--------+           | |      |   |  |          |  Config    | |
|                         | |      |   |  |          |  Space     | |
|                         v |      |   |  +----------+  (S3)      | |
|                   +--------+    |   |       |                    | |
|                   | SPI    |    |   |  +---------+               | |
|                   | Slave  |    |   |  | Dual-Clk|               | |
|                   | I/F    |    |   |  | FIFOs   |               | |
|                   +--------+    |   |  +---------+               | |
|                       |         |   +-------------------------+   |
|                       | CDC     |                               |
|                       v         |                               |
+---------------------------+      +-------------------------------+
```

### 3.2 子模块划分

| 子模块 | 时钟域 | 功能描述 |
|--------|--------|----------|
| **SPI Slave Interface** | SPI_CLK | 接收 SPI 时钟域的串行命令/地址/数据，支持 1-line 和 4-line 模式。包含移位寄存器、位计数器 |
| **Command Decoder** | SPI_CLK | 解析 8-bit opcode，区分读/写操作，控制后续数据路径 |
| **Dual-Clock FIFO (RX)** | SPI_CLK ↔ AXI_CLK | SPI → AXI 时钟域数据同步（写命令/数据 FIFO）。异步 FIFO + Gray-code 指针 |
| **Dual-Clock FIFO (TX)** | AXI_CLK ↔ SPI_CLK | AXI → SPI 时钟域数据同步（读返回数据 FIFO）。异步 FIFO + Gray-code 指针 |
| **AXI Master FSM** | AXI_CLK | 控制 AXI4-Lite 总线事务的发起与完成。5 通道握手协议 |
| **Wrap Address Controller** | AXI_CLK | 实现可配置地址环绕逻辑。Wrap=0 时直通；Wrap=N 时窗口回绕 |
| **Dummy Cycle Counter** | SPI_CLK | 读操作时插入可编程 dummy cycle (默认 32, 实际 = cfg + 1) |

### 3.3 数据流

**写数据流**:
```
SPI Master → SPI Slave I/F (串行转并行)
           → Command Decoder (解析 opcode=0x00, 提取地址)
           → RX FIFO (CDC: SPI_CLK → AXI_CLK)
           → AXI Master FSM → AW(AWADDR) + W(WSTRB, WDATA)
           → AXI4-Lite Slave → B(BRESP)
           → 响应回 SPI 侧
```

**读数据流**:
```
SPI Master → SPI Slave I/F (串行转并行)
           → Command Decoder (解析 opcode=0x01, 提取地址)
           → 同步读请求到 AXI 域
           → AXI Master FSM → AR(ARADDR)
           → AXI4-Lite Slave → R(RDATA, RRESP)
           → TX FIFO (CDC: AXI_CLK → SPI_CLK)
           → SPI Slave I/F → 串行输出数据到 SPI Master
```

---

## 4. 操作协议 (Operation Protocol)

### 4.1 SPI 命令格式 (参考 airhdl SPI-to-AXI4-Lite Bridge)

```
帧格式（标准 SPI / QSPI 模式）:

[8-bit Opcode] + [32-bit Address] + [Dummy Cycles] + [32-bit Data]

- Opcode:      8 bits, MSB first
- Address:    32 bits, MSB first (内存访问时需要完整地址)
- Dummy:      可编程 cycles (仅读操作, 默认 32)
- Data:       32 bits, MSB first
```

### 4.2 SPI 命令操作码

| 操作码 (8-bit) | 命令类型 | 描述 |
|:---:|:--------:|------|
| **0x00** | Write | AXI4-Lite 写事务。格式: Opcode + Addr[31:0] + WData[31:0] + Dummy + Status |
| **0x01** | Read | AXI4-Lite 读事务。格式: Opcode + Addr[31:0] + Dummy + RData[31:0] + Status |

**说明**:
- 寄存器访问：地址由操作码编码（固定地址映射）
- 内存访问：需要在 opcode 后跟随 32-bit 地址（MSB first）

### 4.3 写操作 — 字节级事务格式 (11 bytes total)

| Byte | MOSI (Master Out) | MISO (Master In) | 描述 |
|:----:|:-----------------:|:-----------------:|------|
| 0 | `0x00` (Write Opcode) | `0x00` | 写命令标识 |
| 1 | `addr[31:24]` | `0x00` | 地址高字节 [31:24] |
| 2 | `addr[23:16]` | `0x00` | 地址 [23:16] |
| 3 | `addr[15:8]` | `0x00` | 地址 [15:8] |
| 4 | `addr[7:0]` | `0x00` | 地址低字节 [7:0] |
| 5 | `wr_data[31:24]` | `0x00` | 写数据高字节 [31:24] |
| 6 | `wr_data[23:16]` | `0x00` | 写数据 [23:16] |
| 7 | `wr_data[15:8]` | `0x00` | 写数据 [15:8] |
| 8 | `wr_data[7:0]` | `0x00` | 写数据低字节 [7:0] |
| 9 | Don't care | `0x00` | Dummy byte (写流水线延时) |
| 10 | Don't care | **status** | `[2]=timeout`, `[1:0]=BRESP` |

### 4.4 读操作 — 字节级事务格式 (11 bytes total)

| Byte | MOSI | MISO | 描述 |
|:----:|:----:|:----:|------|
| 0 | `0x01` (Read Opcode) | `0x00` | 读命令标识 |
| 1 | `addr[31:24]` | `0x00` | 地址高字节 [31:24] |
| 2 | `addr[23:16]` | `0x00` | 地址 [23:16] |
| 3 | `addr[15:8]` | `0x00` | 地址 [15:8] |
| 4 | `addr[7:0]` | `0x00` | 地址低字节 [7:0] |
| 5 | Don't care | `0x00` | Dummy byte (AXI 读取延迟) |
| 6 | Don't care | `rd_data[31:24]` | 读数据高字节 [31:24] (status=OKAY 时有效) |
| 7 | Don't care | `rd_data[23:16]` | 读数据 [23:16] |
| 8 | Don't care | `rd_data[15:8]` | 读数据 [15:8] |
| 9 | Don't care | `rd_data[7:0]` | 读数据低字节 [7:0] |
| 10 | Don't care | **status** | `[2]=timeout`, `[1:0]=RRESP` |

### 4.5 Status Byte 编码

| Bit | 字段 | 描述 |
|:---:|------|------|
| [2] | TIMEOUT | AXI 事务超时标志 (1=超时) |
| [1:0] | BRESP/RRESP | AXI 响应码 |

**AXI 响应码**:

| BRESP/RRESP | 编码 | 描述 |
|:-----------:|:----:|------|
| OKAY | `2'b00` | 正常访问成功 |
| EXOKAY | `2'b01` | 独占访问成功 |
| SLVERR | `2'b10` | 从设备错误 |
| DECERR | `2'b11` | 地址译码错误 |

### 4.6 Dummy Cycle

- 默认配置: 32 cycles
- 实际 Dummy Cycle = DUMMY_CYCLES 配置值 + 1
- 可编程范围: 1 ~ 33 cycles
- 用途: 等待 AXI 读数据返回至 TX FIFO

### 4.7 写操作序列

```
SPI Master                  SPI2AXI Bridge              AXI Slave
    |                            |                          |
    |--- 配置模式(1-line/4-line)-->|                          |
    |                            |                          |
    |--- 8'h00 (写Opcode) ------>|                          |
    |--- 32'hADDR (地址) ------->|                          |
    |                            |-- 解析命令, 同步到AXI域 -->|
    |                            |                          |
    |--- 32'hDATA (写数据) ------>|-- AW(AWADDR) ----------->|
    |                            |-- W(WSTRB, WDATA) ------>|
    |                            |                          |
    |                            |<-- B(BRESP) -------------|
    |<-- Status (BRESP) ---------|                          |
```

### 4.8 读操作序列

```
SPI Master                  SPI2AXI Bridge              AXI Slave
    |                            |                          |
    |--- 配置模式(1-line/4-line)-->|                          |
    |                            |                          |
    |--- 8'h01 (读Opcode) ------>|                          |
    |--- 32'hADDR (地址) ------->|                          |
    |                            |-- 同步读请求到AXI域 ------>|
    |                            |-- AR(ARADDR) ----------->|
    |                            |                          |
    |                            |<-- R(RDATA, RRESP) ------|
    |                            |-- 数据写入TX FIFO ------->|
    |<== Dummy Cycles (等待) ====|                          |
    |<-- 32'hDATA (读出数据) -----|                          |
    |<-- Status (RRESP) ---------|                          |
```

---

## 5. 跨时钟域设计 (CDC)

### 5.1 时钟域划分

| 时钟域 | 时钟来源 | 频率 | 用途 |
|--------|----------|------|------|
| SPI_CLK | 外部 SPI 主机提供 | ≤ 50MHz | SPI Slave I/F, Command Decoder, Dummy Counter |
| AXI_CLK | SoC 内部时钟 | 100MHz+ (系统时钟) | AXI Master FSM, Wrap Controller |

### 5.2 CDC 方案

**方案: Dual-Clock Asynchronous FIFO + Gray-code 指针同步**

```
SPI_CLK Domain                     AXI_CLK Domain
    +--------+     +-----------+     +---------+
    | SPI    |---->| RX FIFO   |---->| AXI    |
    | Rx FSM |     | (async)   |     | Master |
    +--------+     +-----------+     +---------+
                       |  CDC
                  Gray-code ptr
                  + 2-flop sync

    +---------+    +-----------+     +--------+
    | SPI     |<---| TX FIFO   |<----| AXI    |
    | Tx FSM  |    | (async)   |     | Rd FSM |
    +---------+    +-----------+     +--------+
                       |  CDC
                  Gray-code ptr
                  + 2-flop sync
```

### 5.3 FIFO 设计

| FIFO | 写入域 | 读取域 | 数据宽度 | 深度 | 用途 |
|------|--------|--------|----------|------|------|
| RX FIFO | SPI_CLK | AXI_CLK | 64-bit (cmd+addr+data) | 8 | 缓存写命令和地址 |
| TX FIFO | AXI_CLK | SPI_CLK | 32-bit | 8 | 缓存读返回数据 |

### 5.4 同步器设计

| CDC 信号 | 技术 | 说明 |
|----------|------|------|
| FIFO 写指针 → 读域 | Gray-code + 2-flop sync | 确保多-bit 指针跨时钟域安全性 |
| FIFO 读指针 → 写域 | Gray-code + 2-flop sync | 同上 |
| 空/满标志 | 指针比较 (本地域) | 每个时钟域内比较同步后的对端指针 |
| 控制脉冲 (req/ack) | Pulse synchronizer | 快速→慢速域的脉冲展宽+边沿检测 |
| 单-bit 状态信号 | 2-flop synchronizer | 配置为 ASYNC_REG="TRUE" |

**关键时序约束**:
- 所有同步器链标记为 `set_false_path -from [get_clocks SPI_CLK] -to [get_clocks AXI_CLK]` (除 FIFO 指针路径外)
- FIFO 指针跨时钟域: 不设置 false path，使用 Gray-code 保证单 bit 翻转

---

## 6. FSM 状态机

### 6.1 SPI 接收 FSM (SPI_CLK 域)

基于 ESP32 SPI FSM 和通用 SPI Slave FSM 设计模式。

#### 状态编码

| 状态 | 编码 | 描述 |
|:----:|:----:|------|
| IDLE | `3'b000` | 等待 spi_cs_n 拉低 |
| PREP | `3'b001` | 准备阶段，初始化位计数器 |
| OPCODE | `3'b010` | 接收 8-bit 操作码 |
| ADDR | `3'b011` | 接收 32-bit 地址 (仅内存访问) |
| DUMMY | `3'b100` | 插入 Dummy cycles (仅读操作) |
| DATA | `3'b101` | 发送/接收 32-bit 数据 |
| DONE | `3'b110` | 事务完成，清理状态 |

#### 状态转移表

| 当前状态 | 转移条件 | 下一状态 | 输出动作 |
|----------|---------|----------|----------|
| IDLE | `spi_cs_n == 1'b0` | PREP | 清除位计数器，准备接收 |
| IDLE | `spi_cs_n == 1'b1` | IDLE | 保持空闲 |
| PREP | 始终 | OPCODE | 使能移位寄存器，开始接收 opcode |
| OPCODE | bit_cnt == 8 (opcode 接收完) | ADDR | 保存 opcode，若 opcode==读，标记 read_flag |
| OPCODE | bit_cnt < 8 | OPCODE | 继续接收 opcode bit |
| ADDR | bit_cnt == 32 (地址接收完) | DUMMY | 仅 read_flag==1 时进入 DUMMY |
| ADDR | bit_cnt == 32 (地址接收完) | DATA | write_flag==1 时跳过 DUMMY 直接 DATA |
| ADDR | bit_cnt < 32 | ADDR | 继续接收地址 bit |
| DUMMY | dummy_cnt == DUMMY_CYCLES-1 | DATA | 完成等待，开始 SPI 数据输出 |
| DUMMY | dummy_cnt < DUMMY_CYCLES-1 | DUMMY | dummy_cnt++ |
| DATA | bit_cnt == 32 (数据传输完) | DONE | 写: 提交 AXI 写请求；读: 从 TX FIFO 读取数据 |
| DATA | bit_cnt < 32 | DATA | 写: 接收 MOSI 数据；读: 发送 MISO 数据 |
| DONE | spi_cs_n == 1'b1 | IDLE | 断言 done 信号，清除标志 |
| DONE | spi_cs_n == 1'b0 | DONE | 等待 CS 释放 |

### 6.2 AXI Master FSM (AXI_CLK 域)

#### 状态编码

| 状态 | 编码 | 描述 |
|:----:|:----:|------|
| IDLE | `3'b000` | 等待 RX FIFO 非空或读请求 |
| WR_ADDR | `3'b001` | 发送 AW 通道地址 (awvalid=1, awaddr) |
| WR_DATA | `3'b010` | 发送 W 通道数据 (wvalid=1, wdata, wstrb) |
| WR_RESP | `3'b011` | 等待 B 通道响应 (bvalid) |
| RD_ADDR | `3'b100` | 发送 AR 通道地址 (arvalid=1, araddr) |
| RD_DATA | `3'b101` | 等待 R 通道数据 (rvalid) |
| RESP_SYNC | `3'b110` | 同步响应回 SPI 域 (通过回写路径) |

#### 状态转移表

| 当前状态 | 转移条件 | 下一状态 | 输出动作 |
|----------|---------|----------|----------|
| IDLE | rx_fifo_empty==0 && opcode==WRITE | WR_ADDR | 从 RX FIFO 读取地址和数据 |
| IDLE | read_request==1 (来自 SPI 侧) | RD_ADDR | 从 RX FIFO 读取地址 |
| IDLE | 无请求 | IDLE | 保持空闲 |
| WR_ADDR | awready==1 | WR_DATA | awvalid=1, awaddr=target_addr |
| WR_ADDR | awready==0 | WR_ADDR | 等待 AW ready |
| WR_DATA | wready==1 | WR_RESP | wvalid=1, wdata=wr_data, wstrb=4'hF |
| WR_DATA | wready==0 | WR_DATA | 等待 W ready |
| WR_RESP | bvalid==1 | IDLE | 保存 bresp，更新状态字节 |
| WR_RESP | bvalid==0 | WR_RESP | 等待 B ready |
| RD_ADDR | arready==1 | RD_DATA | arvalid=1, araddr=target_addr |
| RD_ADDR | arready==0 | RD_ADDR | 等待 AR ready |
| RD_DATA | rvalid==1 | IDLE | 保存 rdata 和 rresp，写入 TX FIFO |
| RD_DATA | rvalid==0 | RD_DATA | 等待 R ready |

### 6.3 CDC 握手信号

SPI_CLK 域和 AXI_CLK 域之间的同步采用以下机制:

| 信号 | 方向 | 同步方式 | 描述 |
|------|------|----------|------|
| rx_fifo_wr | SPI → AXI | 直接 (FIFO 内建) | SPI 域写入 RX FIFO |
| rx_fifo_rd | AXI → SPI | 直接 (FIFO 内建) | AXI 域读取 RX FIFO |
| read_request | SPI → AXI | Pulse synchronizer | SPI 域发出的读请求脉冲 |
| read_data_ready | AXI → SPI | Pulse synchronizer | AXI 域读数据就绪信号 |
| tx_fifo_wr | AXI → SPI | 直接 (FIFO 内建) | AXI 域写入 TX FIFO |
| tx_fifo_rd | SPI → AXI | 直接 (FIFO 内建) | SPI 域读取 TX FIFO |

---

## 7. 地址 Wrap 功能 (Address Wrap)

### 7.1 功能描述

由于 AXI4-Lite 仅支持 single transfer (AxLEN=0, AxSIZE=2=4bytes)，SPI2AXI 引入可配置地址环绕功能：

| Wrap 配置 | 行为 |
|-----------|------|
| Wrap = 0 | 无环绕，地址线性递增 |
| Wrap = N (N>0) | 环绕窗口 = N words = 4N bytes，起始地址 4B 对齐，每次+4，第 N 次后回绕 |

### 7.2 示例 (Wrap=2, 起始地址 'h100)

```
Burst  0: Write to 'h100  (word 1)
Burst  1: Write to 'h104  (word 2)
Burst  2: Write to 'h100  (wrap, back to word 1)
Burst  3: Write to 'h104  (word 2)
Burst  4: Write to 'h100  (wrap, back to word 1)
...
```

### 7.3 Wrap 地址计算逻辑

```systemverilog
// Wrap 地址计算逻辑
logic [31:0] base_addr;     // 起始地址 (4B 对齐)
logic [31:0] wrap_mask;     // 环绕掩码 = (wrap_size * 4) - 1
logic [31:0] next_addr;

always_comb begin
    if (wrap_en && (current_addr[31:2] == base_addr[31:2] + wrap_size - 1)) begin
        // 到达窗口边界，回绕到起始地址
        next_addr = base_addr;
    end else begin
        // 线性递增 (下一个 word)
        next_addr = current_addr + 32'd4;
    end
end
```

---

## 8. 寄存器映射 (CSR)

### 8.1 SPI 侧寄存器

SPI2AXI 模块在 SPI 侧维护以下控制/状态寄存器，通过特定 opcode 访问：

| 偏移地址 | 名称 | 位宽 | 访问 | 描述 |
|----------|------|:----:|:----:|------|
| 0x00 | SPI_CTRL | 32 | R/W | SPI 控制寄存器 |
| 0x04 | SPI_STATUS | 32 | R/W1C | SPI 状态寄存器 |
| 0x08 | WRAP_CFG | 32 | R/W | 地址环绕配置寄存器 |
| 0x0C | DUMMY_CFG | 32 | R/W | Dummy cycle 配置寄存器 |
| 0x10 | SPI_DATA | 32 | R/W | SPI 数据寄存器 (直通 AXI) |

#### SPI_CTRL (@ 0x00)

| 位域 | 名称 | 访问 | 复位值 | 描述 |
|:----:|------|:----:|:------:|------|
| [31:2] | RESERVED | RO | 0 | 保留 |
| [1] | QSPI_EN | R/W | 1'b0 | QSPI 模式使能: 0=标准 SPI, 1=QSPI |
| [0] | SPI_EN | R/W | 1'b0 | SPI 接口使能: 0=禁用, 1=使能 |

#### SPI_STATUS (@ 0x04)

| 位域 | 名称 | 访问 | 复位值 | 描述 |
|:----:|------|:----:|:------:|------|
| [31:4] | RESERVED | RO | 0 | 保留 |
| [3] | TIMEOUT | R/W1C | 1'b0 | AXI 事务超时标志 |
| [2] | SLVERR | R/W1C | 1'b0 | AXI SLVERR 错误标志 |
| [1] | BUSY | RO | 1'b0 | 模块忙: 正在处理 AXI 事务 |
| [0] | READY | RO | 1'b1 | 模块就绪: 可接受新命令 |

#### WRAP_CFG (@ 0x08)

| 位域 | 名称 | 访问 | 复位值 | 描述 |
|:----:|------|:----:|:------:|------|
| [31:8] | RESERVED | RO | 0 | 保留 |
| [7:0] | WRAP_SIZE | R/W | 8'd0 | Wrap 窗口大小 (0=disabled, N=窗口 words) |

#### DUMMY_CFG (@ 0x0C)

| 位域 | 名称 | 访问 | 复位值 | 描述 |
|:----:|------|:----:|:------:|------|
| [31:6] | RESERVED | RO | 0 | 保留 |
| [5:0] | DUMMY_CYCLES | R/W | 6'd32 | 读操作 dummy cycles (实际 = 配置值 + 1) |

### 8.2 数据寄存器

SPI_DATA (@ 0x10) — 用作 SPI 与 AXI 之间的直通数据通道，不经过 FIFO 缓存。主要用于快速寄存器访问。

---

## 9. 可配置参数 (Configurable Parameters)

| 参数名 | 默认值 | 可编程 | 描述 |
|--------|:------:|:------:|------|
| AXI_ADDR_WIDTH | 32 | 设计时固定 | AXI 地址总线宽度 |
| AXI_DATA_WIDTH | 32 | 设计时固定 | AXI 数据总线宽度 |
| AXI_ID_WIDTH | 3 | 设计时固定 | AXI ID 信号宽度 |
| DUMMY_CYCLES | 32 | 运行时 | SPI 读虚拟周期数 (实际 = cfg + 1) |
| WRAP_SIZE | 0 | 运行时 | 地址环绕窗口大小 (0=disabled) |
| SPI_MODE | SPI | 运行时 | SPI 工作模式选择 (SPI/QSPI) |
| SPI_CPOL | 0 | 设计时 | SPI 时钟极性 |
| SPI_CPHA | 0 | 设计时 | SPI 时钟相位 |
| CLK_RATIO | - | 设计时 | SPI_CLK:AXI_CLK 频率比 (用于 FIFO 深度估算) |
| RX_FIFO_DEPTH | 8 | 设计时 | RX FIFO 深度 (entries) |
| TX_FIFO_DEPTH | 8 | 设计时 | TX FIFO 深度 (entries) |

---

## 10. 时序分析 (Timing Analysis)

### 10.1 QSPI 写时序 (Mode 0: CPOL=0, CPHA=0)

写操作时，所有 4 根数据线 (IO[3:0]) 由 SPI Master 驱动：

```
SCLK    __/  \__/  \__/  \__/  \__/  \__/  \__/  \__
       /  \  /  \  /  \  /  \  /  \  /  \  /  \  /  \
CS_n   \______________________________________________/
         _____ _______ _______ _______
IO[0]  X_CMD0_X_CMD1_X_ADDR0_X_ADDR1_X___DATA0___DATA1_X
         _____ _______ _______ _______
IO[1]  X_CMD2_X_CMD3_X_ADDR2_X_ADDR3_X___DATA2___DATA3_X
         _____ _______ _______ _______
IO[2]  X_CMD4_X_CMD5_X_ADDR4_X_ADDR5_X___DATA4___DATA5_X
         _____ _______ _______ _______
IO[3]  X_CMD6_X_CMD7_X_ADDR6_X_ADDR7_X___DATA6___DATA7_X

           ^          ^          ^
           | 采样边沿  | 采样边沿  | 采样边沿
        上升沿      上升沿      上升沿
```

**时序参数**:
| 参数 | 最小值 | 最大值 | 说明 |
|------|:------:|:------:|------|
| SCLK 周期 | 20 ns | - | 50MHz (最大值) |
| 数据建立时间 (tSU) | 2.9 ns | - | SDI 在 SCLK 上升沿前有效 |
| 数据保持时间 (tH) | -0.1 ns | - | SDI 在 SCLK 上升沿后保持 |
| CS 建立时间 (tCSS) | 5 ns | - | CS 拉低到首个 SCLK 上升沿 |
| CS 保持时间 (tCSH) | 5 ns | - | 最后 SCLK 沿到 CS 拉高 |
| SDO 输出延迟 (tCO) | - | 5 ns | SCLK 下降沿到 SDO 有效 |

### 10.2 QSPI 读时序 (Mode 0: CPOL=0, CPHA=0)

读操作包含 Dummy 周期实现总线方向切换 (Turnaround)：

```
        CMD Phase   Addr Phase   Dummy Phase   Data Phase
        ┌──────────┬────────────┬──────────────┬─────────────┐
SCLK    __/  \__/  \__/  \__/  \_/  \_/  \_/  \__/  \__/  \__
       /  \  /  \  /  \  /  \  /  \  /  \  /  \  /  \  /  \
CS_n   \______________________________________________________/

       MOSI方向 →   →        Hi-Z ←            ← MISO方向
IO[0]  X_CMD0_CMD1_X_ADDR0_ADDR1_X=======X=======X_DATA0_DATA1_X
IO[1]  X_CMD2_CMD3_X_ADDR2_ADDR3_X=======X=======X_DATA2_DATA3_X
IO[2]  X_CMD4_CMD5_X_ADDR4_ADDR5_X=======X=======X_DATA4_DATA5_X
IO[3]  X_CMD6_CMD7_X_ADDR6_ADDR7_X=======X=======X_DATA6_DATA7_X

                                    ^
                                    | Turnaround: Master 释放总线
                                    | Slave 开始驱动数据
```

**关键说明**:
- CMD 阶段: 8 个 SCLK, 1-line 或 4-line 发送 opcode
- ADDR 阶段: 32 个 SCLK, 发送 32-bit 地址 (MSB first)
- DUMMY 阶段: 可编程 N 个 SCLK, 包含总线 Turnaround (至少 1 cycle)
- DATA 阶段: 32 个 SCLK, 4-line 读取 32-bit 数据
- **Turnaround**: Dummy 阶段内 Master 释放 IO 线为 Hi-Z, Slave 开始驱动。至少需要 1 个 dummy cycle 避免总线 contention

---

## 11. 实现指南 (Implementation Guide)

### 11.1 SPI Slave Interface — 移位寄存器设计

```systemverilog
module spi_slave_if (
    input  logic        spi_sclk,
    input  logic        spi_cs_n,
    input  logic [3:0]  spi_sdi,
    output logic [3:0]  spi_sdo,
    input  logic [3:0]  sdo_data,       // 从内部逻辑输入待发送数据
    output logic [3:0]  sdi_data,        // 输出接收到的数据
    output logic        sample_valid     // 采样有效标志
);

    // Mode 0: 上升沿采样, 下降沿更新
    logic [3:0] shift_reg;

    always_ff @(posedge spi_sclk or posedge spi_cs_n) begin
        if (spi_cs_n) begin
            shift_reg <= '0;
        end else begin
            shift_reg <= {spi_sdi, shift_reg[3:0]}; // MSB first
        end
    end

    // 数据输出更新在 SCLK 下降沿
    always_ff @(negedge spi_sclk or posedge spi_cs_n) begin
        if (spi_cs_n) begin
            spi_sdo <= '0;
        end else begin
            spi_sdo <= sdo_data;
        end
    end

endmodule
```

### 11.2 AXI4-Lite Master FSM — 状态机框架

```systemverilog
typedef enum logic [2:0] {
    IDLE     = 3'b000,
    WR_ADDR  = 3'b001,
    WR_DATA  = 3'b010,
    WR_RESP  = 3'b011,
    RD_ADDR  = 3'b100,
    RD_DATA  = 3'b101
} axi_fsm_state_t;

axi_fsm_state_t state, next_state;

// State register
always_ff @(posedge axi_clk or negedge axi_rst_n) begin
    if (!axi_rst_n)
        state <= IDLE;
    else
        state <= next_state;
end

// Next state logic (combinational)
always_comb begin
    next_state = state;
    case (state)
        IDLE: begin
            if (!rx_fifo_empty && cmd_is_write)
                next_state = WR_ADDR;
            else if (read_request)
                next_state = RD_ADDR;
        end
        WR_ADDR: if (awready) next_state = WR_DATA;
        WR_DATA: if (wready)  next_state = WR_RESP;
        WR_RESP: if (bvalid)  next_state = IDLE;
        RD_ADDR: if (arready) next_state = RD_DATA;
        RD_DATA: if (rvalid)  next_state = IDLE;
    endcase
end
```

---

## 12. 验证计划 (Verification Plan)

| 验证项 | 测试场景 | 覆盖点 |
|--------|----------|--------|
| SPI 协议兼容性 | 标准 SPI / QSPI 模式基本功能 | 4 种 SPI 模式, MSB-first |
| Opcode 译码 | 0x00(写) / 0x01(读) / 非法 opcode | 正确路由到 AXI 读/写路径, 非法 opcode 返回 SLVERR |
| AXI4-Lite 协议合规 | 5 通道握手协议全覆盖 | VALID/READY 时序, OKAY/SLVERR/DECERR 响应 |
| 写事务 | 全地址范围写, 边界地址 | awaddr → wdata → bresp 顺序正确 |
| 读事务 | 全地址范围读, 非法地址 | araddr → rdata → rresp, SLVERR 传播 |
| CDC 功能验证 | 双时钟 FIFO 数据完整性 | 随机频率比, FIFO 满/空, 数据不丢失/不损坏 |
| Wrap 地址环绕 | Wrap=0/1/2/4/8 | 地址计算正确, 边界回绕正确 |
| Dummy Cycle | DUMMY=0/1/32 | 读操作延迟正确, Turnaround 无 contention |
| 时序收敛 | SPI 50MHz, AXI 目标频率 STA | 同步器路径, FIFO 接口路径 |
| 边界测试 | FIFO 满/空, AXI SLVERR/DECERR, CS 异常跳变 | 错误恢复, 超时机制, 状态机死锁避免 |

---

## 13. 修订历史 (Revision History)

| 版本 | 日期 | 作者 | 描述 |
|:----:|:----:|------|------|
| v1 | 2026-05-20 | chip-spec-gen | 初稿，基于 SPI2AXI SPEC.pdf 生成 |
| **v2** | **2026-05-20** | **chip-spec-gen** | **补充完整版: 添加操作码编码表、字节级事务格式、寄存器映射、FSM 状态表(含转移条件)、QSPI 时序图(含 Turnaround 说明)、RTL 代码框架、验证计划** |

---

## 14. 参考来源 (References)

1. **PDF 源文档**: SPI2AXI SPEC.pdf — 原始设计规格
2. **airhdl/spi-to-axi-bridge** — Open-source SPI to AXI4-Lite bridge reference design (Apache 2.0). GitHub: https://github.com/airhdl/spi-to-axi-bridge
3. **ESP32 SPI FSM Register Definitions** — Espressif Systems SPI hardware FSM states (IDLE/PREP/CMD/ADDR/DUMMY/DIN/DOUT/DONE). Source: docs.rs/esp32s3
4. **Xilinx AXI Quad SPI (PG153)** — SPI controller register map reference. Source: AMD/Xilinx
5. **Microchip QSPI Instruction Frame Transmission** — QSPI timing and phase diagrams. Source: onlinedocs.microchip.com
6. **Texas Instruments QSPI Timing** — DRA78x QSPI switching characteristics. Source: TI SPRS975
7. **NXP MPC5606S QuadSPI** — Classic SPI transfer format timing. Source: NXP Reference Manual
8. **Xylon logiSPI** — Commercial SPI to AXI4 Controller Bridge IP. Source: logicbricks.com
