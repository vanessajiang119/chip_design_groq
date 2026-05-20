# SPI2AXI Bridge — 模块微架构规格书 (LLD)

> **模块名称:** SPI2AXI Bridge
> **版本:** V2.0
> **日期:** 2026-05-20
> **状态:** Draft
> **层次路径:** top.chip.subsystem.spi2axi
> **工艺节点:** N/A (RTL IP)
> **目标频率:** SPI_CLK ≤ 50MHz, AXI_CLK ≥ 100MHz

---

## 1. Module Overview

### 1.1 Module Identity

| 属性 | 值 |
|------|-----|
| 模块全名 | SPI2AXI Bridge |
| 层次路径 | `top.chip.subsystem.spi2axi` |
| 工艺 / PVT | N/A (RTL IP) |
| 目标频率 | SPI_CLK ≤ 50MHz, AXI_CLK ≥ 100MHz |
| 供电电压 | 取决于 SoC 集成 |
| 面积预算 | ~31 kgates |
| 功耗预算 | N/A (RTL IP) |

### 1.2 Top-Level Ports Summary

| Port Group | Direction | Width | Description |
|------------|-----------|-------|-------------|
| `spi_sclk` | input | 1 | SPI 串行时钟 @ ≤ 50MHz |
| `spi_cs_n` | input | 1 | SPI 片选 (低有效) |
| `spi_sdi` | input | 4 | SPI 数据输入 (QSPI) |
| `spi_sdo` | output | 4 | SPI 数据输出 (QSPI) |
| `axi_clk` | input | 1 | AXI 系统时钟 @ ≥ 100MHz |
| `axi_rst_n` | input | 1 | AXI 异步复位, 低有效 |
| `axi_*` | in/out | 32+ | AXI4-Lite 总线信号组 (5 通道) |

### 1.3 Module Features

- [x] Feature 1: SPI Slave 接口 (标准 SPI 1-line + QSPI 4-line)
- [x] Feature 2: AXI4-Lite Master 接口 (5 通道, single transfer)
- [x] Feature 3: 双时钟域异步 FIFO CDC (Gray-code + 2-flop 同步器)
- [x] Feature 4: 可配置地址环绕 (Wrap)
- [x] Feature 5: 可编程 Dummy Cycle (1~33 cycles)
- [x] Feature 6: 8-bit Opcode 命令译码 (0x00=Write, 0x01=Read)
- [x] Feature 7: 5 个 32-bit CSR (CTRL, STATUS, WRAP_CFG, DUMMY_CFG, SPI_DATA)
- [x] Feature 8: Status Byte 返回 AXI 响应状态

### 1.4 Design Assumptions

- A1: SPI Master 帧格式固定为 Opcode+Addr+Dummy+Data
- A2: AXI Slave 在合理周期内响应 (超时机制保护)
- A3: 数据 MSB-first 传输

---

## 2. Interface Specification

### 2.1 Port Signal Table

| Signal Name | Direction | Width | Type | Clock Domain | Reset Domain | I/O Pad | Description |
|-------------|-----------|-------|------|-------------|-------------|---------|-------------|
| `spi_sclk` | input | 1 | clock | — | — | no | SPI 串行时钟, max 50MHz |
| `spi_cs_n` | input | 1 | data | spi_sclk | — | no | SPI 片选 (低有效) |
| `spi_sdi[3:0]` | input | 4 | data | spi_sclk | — | no | SPI 数据输入 |
| `spi_sdo[3:0]` | output | 4 | data | spi_sclk | — | no | SPI 数据输出 |
| `axi_clk` | input | 1 | clock | — | — | no | AXI 系统时钟, 100MHz+ |
| `axi_rst_n` | input | 1 | reset async low | axi_clk | — | no | AXI 异步复位 |
| `axi_awaddr[31:0]` | output | 32 | data | axi_clk | axi_rst_n | no | AXI 写地址 |
| `axi_awvalid` | output | 1 | data | axi_clk | axi_rst_n | no | AXI 写地址有效 |
| `axi_awready` | input | 1 | data | axi_clk | axi_rst_n | no | AXI 写地址就绪 |
| `axi_wdata[31:0]` | output | 32 | data | axi_clk | axi_rst_n | no | AXI 写数据 |
| `axi_wstrb[3:0]` | output | 4 | data | axi_clk | axi_rst_n | no | AXI 写选通 |
| `axi_wvalid` | output | 1 | data | axi_clk | axi_rst_n | no | AXI 写数据有效 |
| `axi_wready` | input | 1 | data | axi_clk | axi_rst_n | no | AXI 写数据就绪 |
| `axi_bresp[1:0]` | input | 2 | data | axi_clk | axi_rst_n | no | AXI 写响应 |
| `axi_bvalid` | input | 1 | data | axi_clk | axi_rst_n | no | AXI 写响应有效 |
| `axi_bready` | output | 1 | data | axi_clk | axi_rst_n | no | AXI 写响应就绪 |
| `axi_araddr[31:0]` | output | 32 | data | axi_clk | axi_rst_n | no | AXI 读地址 |
| `axi_arvalid` | output | 1 | data | axi_clk | axi_rst_n | no | AXI 读地址有效 |
| `axi_arready` | input | 1 | data | axi_clk | axi_rst_n | no | AXI 读地址就绪 |
| `axi_rdata[31:0]` | input | 32 | data | axi_clk | axi_rst_n | no | AXI 读数据 |
| `axi_rresp[1:0]` | input | 2 | data | axi_clk | axi_rst_n | no | AXI 读响应 |
| `axi_rvalid` | input | 1 | data | axi_clk | axi_rst_n | no | AXI 读数据有效 |
| `axi_rready` | output | 1 | data | axi_clk | axi_rst_n | no | AXI 读数据就绪 |

### 2.2 Cycle-Level Timing Diagrams

#### 2.2.1 SPI Write Timing (Mode 0: CPOL=0, CPHA=0)

```
SCLK Cycle:      T0    T1    T2    T3    T4    T5    T6    T7    T8    T9    T10
spi_sclk       █▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█
spi_cs_n       ████▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁████
spi_sdi[0]     XXXX<Opcode>X<Addr_bit>XX<Data_bit>XXXXXXXX
               ↑采样    ↑采样    ↑采样    ↑采样
```

**Cycle Description**:
- **T0**: CS 拉低, 开始帧
- **T0~T7**: 发送 8-bit Opcode (上升沿采样)
- **T8~T39**: 发送 32-bit Address
- **T40~T71**: 发送 32-bit Data
- **T72**: CS 拉高, 帧结束

#### 2.2.2 SPI Read Timing (Mode 0 with Dummy Cycles)

```
SCLK Cycle:      T0~T7     T8~T39      T40~T71           T72~T103
                ┌───────┬──────────┬────────────────┬─────────────────┐
                │ Opcode │ Address  │ Dummy Cycles   │   Read Data     │
                │ Phase  │  Phase   │   (Turnaround)  │    Phase        │
spi_sclk       █▁█...█▁█▁█...█▁█▁█...█▁█▁█...█▁█▁█...█▁█
spi_cs_n       ▁▁...▁▁▁...▁▁▁...▁▁▁...▁▁▁...▁▁██████████████
spi_sdi        <Opcode ><Address ><Hi-Z>            <Hi-Z>
spi_sdo        <Hi-Z>           <Hi-Z>              <RData >
                                      ↑ Turnaround: Master
                                        释放总线, Slave驱动
```

**Dummy Cycle Timing**:
- 默认 32 cycles, 可编程 (DUMMY_CFG + 1)
- Turnaround 在 Dummy 首个 cycle: Master 释放 IO 线为 Hi-Z, Slave 开始驱动

#### 2.2.3 AXI4-Lite Write Timing

```
Clock Cycle:      T0        T1        T2        T3        T4
axi_clk         █▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█
awvalid         __________████████████████████
awaddr          XXXXXXXX<ADDR>XXXXXXXXXXXXXXXX
awready         ____________________██████████
wvalid          ________________██████████████
wdata           XXXXXXXXXXXXXXXX<WDATA>XXXXXXX
wready          ________________________██████
bvalid          ________________________________██████
bresp           XXXXXXXXXXXXXXXX<BRESP>XXXXXXXXXXXX
bready          ________________________________██████
```

**Write Cycle Description**:
- **T0~T1**: awvalid=1, awaddr 有效; 等待 awready
- **T1~T2**: awready 拉高, AW 握手完成
- **T2~T3**: wvalid=1, wdata 有效; wready 在 T3 拉高, W 握手完成
- **T4**: bvalid 拉高, bresp 返回。bready=1, B 握手完成 → IDLE

### 2.3 Backpressure Behavior

| Condition | Backpressure Action | Latency Impact | RTL Implementation |
|-----------|--------------------|----------------|-------------------|
| RX FIFO 满 | SPI 侧无法接收新命令 | 持续到 FIFO 有空位 | `fifo_full → stall SPI FSM` |
| TX FIFO 空 | SPI 读数据 phase 等待 | 持续到 TX FIFO 有数据 | `fifo_empty → sdo=Hi-Z` |
| AXI awready=0 | AW 通道等待 | 1~N cycles | `state=WR_ADDR` wait |
| AXI wready=0 | W 通道等待 | 1~N cycles | `state=WR_DATA` wait |
| AXI bvalid=0 | B 通道等待 | 1~N cycles | `state=WR_RESP` wait |
| AXI arready=0 | AR 通道等待 | 1~N cycles | `state=RD_ADDR` wait |
| AXI rvalid=0 | R 通道等待 | 1~N cycles | `state=RD_DATA` wait |

### 2.4 Interrupt Interface

本模块不带中断输出。状态通过 SPI Status Byte 返回 (见 §7.2 STATUS 寄存器描述)。

---

## 3. Sub-Module Partition

### 3.1 Block Diagram

```
                        SPI2AXI Bridge
                    ┌──────────────────────────┐
  SPI CLK Domain    │   ┌──────────────┐       │   AXI CLK Domain
  ┌───────────┐     │   │  SPI Slave   │       │   ┌───────────┐
  │ SPI       │─────┼──►│  Interface   │──RX──►│   │  AXI      │────► AXI4-Lite
  │ Master    │     │   │  (移位寄存器)  │  FIFO │   │  Master   │        Bus
  │ (外部)    │◄────┼───│              │◄─TX───┤   │  FSM      │◄────
  └───────────┘     │   │  +Bit Cntr   │  FIFO │   └─────┬─────┘
                    │   └──────┬───────┘       │         │
                    │          │               │   ┌─────┴─────┐
                    │   ┌──────┴───────┐       │   │  Wrap     │
                    │   │  Command     │       │   │  Address  │
                    │   │  Decoder     │       │   │  Ctrl     │
                    │   └──────────────┘       │   └───────────┘
                    │                          │
                    │   ┌──────────────┐       │   ┌───────────┐
                    │   │  Dummy Cycle │       │   │  CSR      │
                    │   │  Counter     │       │   │  Block    │
                    │   └──────────────┘       │   └───────────┘
                    └──────────────────────────┘
```

### 3.2 Sub-Module Responsibilities

| Sub-Module | Input From | Output To | Width | Function |
|------------|-----------|-----------|-------|----------|
| SPI Slave I/F | SPI pins | Command Decoder, RX FIFO | 4/32 | 串行转并行, 移位寄存器, 位计数器 |
| Command Decoder | SPI Slave I/F | AXI Master FSM, RX FIFO | 8 | Opcode 解析, 读/写路径路由 |
| Dummy Cycle Counter | SPI Slave I/F | SPI Slave I/F | 6 | 读操作 dummy cycle 计数 |
| RX FIFO | SPI Slave I/F | AXI Master FSM | 64 | SPI→AXI CDC, 深度 8 |
| TX FIFO | AXI Master FSM | SPI Slave I/F | 32 | AXI→SPI CDC, 深度 8 |
| AXI Master FSM | RX FIFO, TX FIFO | AXI4-Lite pins | — | 7 状态 FSM, 控制 AXI 事务 |
| Wrap Address Ctrl | AXI Master FSM | AXI Master FSM | 32 | 地址环绕计算 |
| CSR Block | N/A | AXI/SPI | 32 | 配置/状态寄存器文件 |

### 3.3 Inter-Module Signal Table

| Signal | Width | Source | Sink | Description |
|--------|-------|--------|------|-------------|
| `rx_fifo_wdata` | 64 | SPI Slave | RX FIFO | {opcode[7:0], addr[31:0], data[31:0]} |
| `rx_fifo_wr` | 1 | SPI Slave | RX FIFO | RX FIFO 写使能 |
| `rx_fifo_rdata` | 64 | RX FIFO | AXI Master | {opcode, addr, data} |
| `rx_fifo_rd` | 1 | AXI Master | RX FIFO | RX FIFO 读使能 |
| `rx_fifo_empty` | 1 | RX FIFO | AXI Master | RX FIFO 空标志 |
| `rx_fifo_full` | 1 | RX FIFO | SPI Slave | RX FIFO 满标志 |
| `tx_fifo_wdata` | 32 | AXI Master | TX FIFO | AXI 读返回数据 |
| `tx_fifo_wr` | 1 | AXI Master | TX FIFO | TX FIFO 写使能 |
| `tx_fifo_rdata` | 32 | TX FIFO | SPI Slave | 读返回数据输出 |
| `tx_fifo_rd` | 1 | SPI Slave | TX FIFO | TX FIFO 读使能 |
| `tx_fifo_empty` | 1 | TX FIFO | SPI Slave | TX FIFO 空标志 |
| `opcode` | 8 | SPI Slave | Command Decoder | 接收到的 opcode |
| `addr` | 32 | SPI Slave | RX FIFO / Decoder | 接收到的地址 |
| `is_read` | 1 | Command Decoder | SPI Slave, AXI Master | 读操作标志 |
| `is_write` | 1 | Command Decoder | SPI Slave, AXI Master | 写操作标志 |
| `dummy_cnt_done` | 1 | Dummy Counter | SPI Slave | Dummy cycle 计数完成 |
| `axi_done` | 1 | AXI Master | SPI Slave | AXI 事务完成 |
| `status_byte` | 8 | CSR | SPI Slave | {TIMEOUT, bresp/rresp} |
| `wrap_size` | 8 | CSR | Wrap Ctrl | 地址环绕窗口大小 |
| `qspi_en` | 1 | CSR | SPI Slave | QSPI 模式使能 |
| `spi_en` | 1 | CSR | SPI Slave | SPI 接口使能 |

---

## 4. FSM Specification

### 4.1 SPI Receive FSM (SPI_CLK Domain)

#### State Encoding Table

| State Name | Encoding | Description |
|------------|----------|-------------|
| `IDLE` | `3'b000` | 等待 spi_cs_n 拉低 |
| `PREP` | `3'b001` | 准备阶段，初始化位计数器 |
| `OPCODE` | `3'b010` | 接收 8-bit 操作码 |
| `ADDR` | `3'b011` | 接收 32-bit 地址 |
| `DUMMY` | `3'b100` | 插入 Dummy cycles (仅读操作) |
| `DATA` | `3'b101` | 发送/接收 32-bit 数据 |
| `DONE` | `3'b110` | 事务完成，清理状态 |

#### State Transition Matrix

| Current State | Condition | Next State | Transition Action |
|--------------|-----------|------------|------------------|
| `IDLE` | `spi_cs_n == 1'b0` | `PREP` | 清除位计数器，准备接收 |
| `IDLE` | `spi_cs_n == 1'b1` | `IDLE` | 保持空闲 |
| `PREP` | 始终 | `OPCODE` | 使能移位寄存器，开始接收 opcode |
| `OPCODE` | bit_cnt == 8 (opcode 收完) | `ADDR` | 保存 opcode, 若 read_flag=1, 标记 |
| `OPCODE` | bit_cnt < 8 | `OPCODE` | 继续接收 opcode bit |
| `ADDR` | bit_cnt == 32 (地址收完) | `DUMMY` | read_flag==1 时进入 DUMMY |
| `ADDR` | bit_cnt == 32 (地址收完) | `DATA` | write_flag==1 时跳过 DUMMY |
| `ADDR` | bit_cnt < 32 | `ADDR` | 继续接收地址 bit |
| `DUMMY` | dummy_cnt == DUMMY_CYCLES-1 | `DATA` | 完成等待, 开始 SPI 数据输出 |
| `DUMMY` | dummy_cnt < DUMMY_CYCLES-1 | `DUMMY` | dummy_cnt++ |
| `DATA` | bit_cnt == 32 (数据收完) | `DONE` | 写: 提交 AXI 写请求; 读: 读 TX FIFO |
| `DATA` | bit_cnt < 32 | `DATA` | 写: 接收 MOSI 数据; 读: 发送 MISO 数据 |
| `DONE` | spi_cs_n == 1'b1 | `IDLE` | 断言 done 信号, 清除标志 |
| `DONE` | spi_cs_n == 1'b0 | `DONE` | 等待 CS 释放 |

#### Output Decode Table

| Output Signal | IDLE | PREP | OPCODE | ADDR | DUMMY | DATA | DONE |
|---------------|------|------|--------|------|-------|------|------|
| `shift_en` | 0 | 1 | 1 | 1 | 0 | 1 | 0 |
| `bit_cnt_en` | 0 | 0 | 1 | 1 | 0 | 1 | 0 |
| `dummy_cnt_en` | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| `rx_fifo_wr` | 0 | 0 | 0 | 0 | 0 | 0 | 1 (写) |
| `tx_fifo_rd` | 0 | 0 | 0 | 0 | 0 | 1 (读) | 0 |
| `axi_start` | 0 | 0 | 0 | 0 | 0 | 1 | 0 |

### 4.2 AXI Master FSM (AXI_CLK Domain)

#### State Encoding Table

| State Name | Encoding | Description |
|------------|----------|-------------|
| `IDLE` | `3'b000` | 等待 RX FIFO 非空或读请求 |
| `WR_ADDR` | `3'b001` | 发送 AW 通道地址 |
| `WR_DATA` | `3'b010` | 发送 W 通道数据 |
| `WR_RESP` | `3'b011` | 等待 B 通道响应 |
| `RD_ADDR` | `3'b100` | 发送 AR 通道地址 |
| `RD_DATA` | `3'b101` | 等待 R 通道数据 |
| `COMPLETE` | `3'b110` | 事务完成, 准备响应 |

> **Safety**: 未使用的编码 (111) 必须解码为 IDLE, 防止 FSM 锁死。

#### State Transition Matrix

| Current State | Condition | Next State | Transition Action |
|--------------|-----------|------------|------------------|
| `IDLE` | rx_fifo_empty==0 && opcode==WRITE | `WR_ADDR` | 从 RX FIFO 读取地址和数据 |
| `IDLE` | read_request==1 (来自 SPI 侧) | `RD_ADDR` | 从 RX FIFO 读取地址 |
| `IDLE` | 无请求 | `IDLE` | 保持空闲 |
| `WR_ADDR` | awready==1 | `WR_DATA` | awvalid=1, awaddr=target_addr |
| `WR_ADDR` | awready==0 | `WR_ADDR` | 等待 AW ready |
| `WR_DATA` | wready==1 | `WR_RESP` | wvalid=1, wdata=wr_data, wstrb=4'hF |
| `WR_DATA` | wready==0 | `WR_DATA` | 等待 W ready |
| `WR_RESP` | bvalid==1 | `COMPLETE` | 保存 bresp, 更新状态字节 |
| `WR_RESP` | bvalid==0 | `WR_RESP` | 等待 B ready |
| `RD_ADDR` | arready==1 | `RD_DATA` | arvalid=1, araddr=target_addr |
| `RD_ADDR` | arready==0 | `RD_ADDR` | 等待 AR ready |
| `RD_DATA` | rvalid==1 | `COMPLETE` | 保存 rdata 和 rresp, 写入 TX FIFO |
| `RD_DATA` | rvalid==0 | `RD_DATA` | 等待 R ready |
| `COMPLETE` | 始终 (1 cycle) | `IDLE` | 更新状态寄存器 |

#### Output Decode Table

| Output Signal | IDLE | WR_ADDR | WR_DATA | WR_RESP | RD_ADDR | RD_DATA | COMPLETE |
|---------------|------|---------|---------|---------|---------|---------|----------|
| `awvalid` | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| `wvalid` | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| `bready` | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| `arvalid` | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| `rready` | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `tx_fifo_wr` | 0 | 0 | 0 | 0 | 0 | 0 | 1 (读) |
| `status_update` | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

### 4.3 CDC 握手信号

| Signal | Direction | Sync Method | Description |
|--------|-----------|-------------|-------------|
| `rx_fifo_wr` | SPI → AXI | FIFO built-in | SPI 域写入 RX FIFO |
| `rx_fifo_rd` | AXI → SPI | FIFO built-in | AXI 域读取 RX FIFO |
| `read_request` | SPI → AXI | Pulse synchronizer | SPI 域读请求脉冲 |
| `tx_fifo_wr` | AXI → SPI | FIFO built-in | AXI 域写入 TX FIFO |
| `tx_fifo_rd` | SPI → AXI | FIFO built-in | SPI 域读取 TX FIFO |
| `status_update` | AXI → SPI | Pulse synchronizer | AXI 事务完成状态更新 |

### 4.4 FSM RTL Implementation Template

```systemverilog
//=============================================================================
// FSM: SPI Receive FSM
//=============================================================================
typedef enum logic [2:0] {
    ST_IDLE   = 3'b000,
    ST_PREP   = 3'b001,
    ST_OPCODE = 3'b010,
    ST_ADDR   = 3'b011,
    ST_DUMMY  = 3'b100,
    ST_DATA   = 3'b101,
    ST_DONE   = 3'b110
} spi_fsm_state_t;

spi_fsm_state_t spi_state_q, spi_next_state;

// State register
always_ff @(posedge spi_sclk or posedge spi_cs_n) begin
    if (spi_cs_n)
        spi_state_q <= ST_IDLE;
    else
        spi_state_q <= spi_next_state;
end

// Next state logic
always_comb begin
    spi_next_state = spi_state_q;
    unique case (spi_state_q)
        ST_IDLE:   if (!spi_cs_n)   spi_next_state = ST_PREP;
        ST_PREP:                     spi_next_state = ST_OPCODE;
        ST_OPCODE: if (bit_cnt == 8) spi_next_state = ST_ADDR;
        ST_ADDR:   if (bit_cnt == 32)
                       spi_next_state = is_read ? ST_DUMMY : ST_DATA;
        ST_DUMMY:  if (dummy_cnt == DUMMY_CYCLES-1)
                       spi_next_state = ST_DATA;
        ST_DATA:   if (bit_cnt == 32) spi_next_state = ST_DONE;
        ST_DONE:   if (spi_cs_n)     spi_next_state = ST_IDLE;
        default:   spi_next_state = ST_IDLE;
    endcase
end
```

```systemverilog
//=============================================================================
// FSM: AXI Master FSM
//=============================================================================
typedef enum logic [2:0] {
    ST_AXI_IDLE     = 3'b000,
    ST_WR_ADDR      = 3'b001,
    ST_WR_DATA      = 3'b010,
    ST_WR_RESP      = 3'b011,
    ST_RD_ADDR      = 3'b100,
    ST_RD_DATA      = 3'b101,
    ST_COMPLETE     = 3'b110
} axi_fsm_state_t;

axi_fsm_state_t axi_state_q, axi_next_state;

always_ff @(posedge axi_clk or negedge axi_rst_n) begin
    if (!axi_rst_n)
        axi_state_q <= ST_AXI_IDLE;
    else
        axi_state_q <= axi_next_state;
end

always_comb begin
    axi_next_state = axi_state_q;
    unique case (axi_state_q)
        ST_AXI_IDLE: begin
            if (!rx_fifo_empty && cmd_is_write)
                axi_next_state = ST_WR_ADDR;
            else if (read_request)
                axi_next_state = ST_RD_ADDR;
        end
        ST_WR_ADDR:  if (awready)        axi_next_state = ST_WR_DATA;
        ST_WR_DATA:  if (wready)         axi_next_state = ST_WR_RESP;
        ST_WR_RESP:  if (bvalid)         axi_next_state = ST_COMPLETE;
        ST_RD_ADDR:  if (arready)        axi_next_state = ST_RD_DATA;
        ST_RD_DATA:  if (rvalid)         axi_next_state = ST_COMPLETE;
        ST_COMPLETE:                     axi_next_state = ST_AXI_IDLE;
        default:     axi_next_state = ST_AXI_IDLE;
    endcase
end
```

---

## 5. Pipeline Specification

SPI2AXI 不使用深度流水线结构。数据路径为三级序列 (非流水线):

| Stage Name | Stage ID | Latency | Description |
|------------|----------|---------|-------------|
| SPI_Receive | 0 | 可变 (SPI bit rate) | SPI 串行接收 Opcode + Addr + Data |
| CDC_Transfer | 1 | 2~8 cycles | 通过异步 FIFO 跨时钟域 |
| AXI_Execute | 2 | 2~N cycles | AXI4-Lite 总线事务 |

由于整个数据路径为**事务型** (transaction-based)，无连续流水线推进，因此不需要 stall/hold/flush 机制。

---

## 6. Datapath Specification

### 6.1 地址 Wrap 计算逻辑

| Operation | Width | Latency | Description |
|-----------|-------|---------|-------------|
| ADD (+4) | 32 | 0 (comb) | 地址线性递增 |
| CMP_EQ | 32 | 0 (comb) | 地址到达窗口边界检测 |
| MUX | 32 | 0 (comb) | 选择下一地址 |

```systemverilog
// Wrap 地址计算逻辑
logic [31:0] base_addr;     // 起始地址 (4B 对齐)
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

### 6.2 Mux Select Encoding

| Mux Name | Select Width | Select Value | Source | Destination |
|----------|-------------|--------------|--------|-------------|
| `mux_addr_src` | 1 | 0: base_addr (first access) | Wrap Ctrl | AXI address channel |
| | | 1: next_addr (wrap calculation) | | |
| `mux_data_src` | 1 | 0: spi_data_parallel | SPI Slave | RX FIFO |
| | | 1: axi_rdata | AXI Slave | TX FIFO |

### 6.3 Datapath Widths

| Datapath Segment | Width | Rationale |
|-----------------|-------|-----------|
| SPI Serial Input | 4 | QSPI 4-line 模式 |
| SPI Parallel Output | 32 | 32-bit 数据字 |
| RX FIFO Entry | 64 | {opcode[8], addr[32], data[32]} |
| TX FIFO Entry | 32 | 读返回数据 |
| AXI Address | 32 | 标准 AXI 地址宽度 |
| AXI Data | 32 | AXI4-Lite 标准位宽 |

---

## 7. CSR Register Map

### 7.1 Address Map Overview

| Address Offset | Register Name | Width | Attribute | Reset Value | Description |
|---------------|---------------|-------|-----------|-------------|-------------|
| `0x00` | SPI_CTRL | 32 | RW | `0x0000_0000` | SPI 控制寄存器 |
| `0x04` | SPI_STATUS | 32 | RO/W1C | `0x0000_0001` | SPI 状态寄存器 |
| `0x08` | WRAP_CFG | 32 | RW | `0x0000_0000` | 地址环绕配置 |
| `0x0C` | DUMMY_CFG | 32 | RW | `0x0000_0020` | Dummy cycle 配置 |
| `0x10` | SPI_DATA | 32 | RW | `0x0000_0000` | SPI 数据直通 |

### 7.2 Bit-Level Field Definitions

#### 7.2.1 SPI_CTRL (0x00) — SPI Control Register

| Bit Field | Bit(s) | Attribute | Reset | HW Set Condition | HW Clear Condition | Description |
|-----------|--------|-----------|-------|-------------------|-------------------|-------------|
| `spi_en` | 0 | RW | 1'b0 | 软件写 1 | 软件写 0 | SPI 接口使能 |
| `qspi_en` | 1 | RW | 1'b0 | 软件写 1 | 软件写 0 | QSPI 模式使能: 0=SPI, 1=QSPI |
| `reserved` | 31:2 | RES | 30'b0 | — | — | 读返回 0 |

#### 7.2.2 SPI_STATUS (0x04) — SPI Status Register

| Bit Field | Bit(s) | Attribute | Reset | HW Set Condition | HW Clear Condition | Description |
|-----------|--------|-----------|-------|-------------------|-------------------|-------------|
| `ready` | 0 | RO | 1'b1 | 模块进入 IDLE | 模块处理中 | 模块就绪 |
| `busy` | 1 | RO | 1'b0 | FSM 非 IDLE | FSM→IDLE | 模块忙 |
| `slverr` | 2 | W1C | 1'b0 | AXI BRESP/RRESP=SLVERR | 软件写 1 | AXI SLVERR 错误 |
| `timeout` | 3 | W1C | 1'b0 | AXI 事务超时 | 软件写 1 | AXI 超时标志 |
| `reserved` | 31:4 | RES | 28'b0 | — | — | 读返回 0 |

#### 7.2.3 WRAP_CFG (0x08) — Wrap Configuration Register

| Bit Field | Bit(s) | Attribute | Reset | Description |
|-----------|--------|-----------|-------|-------------|
| `wrap_size` | 7:0 | RW | 8'd0 | Wrap 窗口大小 (0=disabled, N=words) |
| `reserved` | 31:8 | RES | 24'b0 | — |

#### 7.2.4 DUMMY_CFG (0x0C) — Dummy Cycle Configuration

| Bit Field | Bit(s) | Attribute | Reset | Description |
|-----------|--------|-----------|-------|-------------|
| `dummy_cycles` | 5:0 | RW | 6'd32 | Dummy cycles (实际 = config + 1) |
| `reserved` | 31:6 | RES | 26'b0 | — |

#### 7.2.5 SPI_DATA (0x10) — SPI Data Register

| Bit Field | Bit(s) | Attribute | Reset | Description |
|-----------|--------|-----------|-------|-------------|
| `data` | 31:0 | RW | 32'd0 | SPI 直通数据通道 |

### 7.3 Status Byte 编码 (SPI Response)

| Bit | Field | Description |
|:---:|-------|-------------|
| [2] | TIMEOUT | AXI 事务超时标志 (1=超时) |
| [1:0] | BRESP/RRESP | AXI 响应码 (00=OKAY, 10=SLVERR, 11=DECERR) |

### 7.4 CSR RTL Implementation Template

```systemverilog
//=============================================================================
// CSR Read/Write Logic
//=============================================================================

// Write decode
always_ff @(posedge axi_clk or negedge axi_rst_n) begin
    if (!axi_rst_n) begin
        spi_ctrl_reg   <= 32'b0;
        wrap_cfg_reg   <= 32'b0;
        dummy_cfg_reg  <= 32'h0000_0020;
        spi_data_reg   <= 32'b0;
    end else if (csr_write_en) begin
        unique case (csr_write_addr)
            ADDR_SPI_CTRL:  spi_ctrl_reg  <= csr_write_data;
            ADDR_WRAP_CFG:  wrap_cfg_reg  <= csr_write_data;
            ADDR_DUMMY_CFG: dummy_cfg_reg <= csr_write_data;
            ADDR_SPI_DATA:  spi_data_reg  <= csr_write_data;
            default: ;  // ignore reserved addresses
        endcase
    end
end

// Read mux
always_comb begin
    unique case (csr_read_addr)
        ADDR_SPI_CTRL:   csr_read_data = spi_ctrl_reg;
        ADDR_SPI_STATUS: csr_read_data = spi_status_reg;
        ADDR_WRAP_CFG:   csr_read_data = wrap_cfg_reg;
        ADDR_DUMMY_CFG:  csr_read_data = dummy_cfg_reg;
        ADDR_SPI_DATA:   csr_read_data = spi_data_reg;
        default:         csr_read_data = 32'b0;
    endcase
end
```

---

## 8. Clock & Reset Architecture

### 8.1 Clock Domains

| Domain Name | Source | Frequency | Divider | Description |
|-------------|--------|-----------|---------|-------------|
| `SPI_CLK` | External SPI Master | ≤ 50MHz | — | SPI Slave I/F, Command Decoder, Dummy Counter |
| `AXI_CLK` | SoC PLL | ≥ 100MHz | — | AXI Master FSM, Wrap Controller, CSR |

### 8.2 Clock Relationships

| Domain A | Domain B | Relationship | Synchronous? | CDC Method |
|----------|----------|--------------|-------------|------------|
| `SPI_CLK` | `AXI_CLK` | Asynchronous | No | Async FIFO + Gray-code |
| `SPI_CLK` | `AXI_CLK` | Control signals | No | Pulse synchronizer |
| `AXI_CLK` | `SPI_CLK` | Status signals | No | Pulse synchronizer |

### 8.3 CDC Paths

| Source Domain | Dest Domain | Signal(s) | Width | CDC Scheme | Latency |
|-------------|------------|-----------|-------|------------|---------|
| `SPI_CLK` | `AXI_CLK` | cmd_addr_data | 64 | Async FIFO (8-deep) | 4~8 cycles |
| `SPI_CLK` | `AXI_CLK` | read_request | 1 | Pulse synchronizer | 2~3 cycles |
| `AXI_CLK` | `SPI_CLK` | read_data | 32 | Async FIFO (8-deep) | 4~8 cycles |
| `AXI_CLK` | `SPI_CLK` | status_update | 1 | Pulse synchronizer | 2~3 cycles |

### 8.4 Reset Architecture

| Reset Signal | Type | Domain | Assert | Deassert | Description |
|-------------|------|--------|--------|----------|-------------|
| `spi_rst_n` | Async, active-low | SPI_CLK | async | sync to SPI_CLK | SPI 域复位 (外部) |
| `axi_rst_n` | Async, active-low | AXI_CLK | async | sync to AXI_CLK | AXI 域复位 (SoC) |

```systemverilog
//=============================================================================
// Reset Synchronizer for AXI_CLK domain
//=============================================================================
logic axi_rst_n_sync1, axi_rst_n_sync;
always_ff @(posedge axi_clk or negedge axi_rst_n) begin
    if (!axi_rst_n) begin
        axi_rst_n_sync1 <= 1'b0;
        axi_rst_n_sync  <= 1'b0;
    end else begin
        axi_rst_n_sync1 <= 1'b1;
        axi_rst_n_sync  <= axi_rst_n_sync1;
    end
end
```

---

## 9. Timing Constraints (SDC)

### 9.1 Master Clock Definitions

```tcl
#=============================================================================
# SDC: SPI2AXI Timing Constraints
#=============================================================================
# 文件: spi2axi.sdc
# 工艺: <technology_node>
# 版本: V1.0

#---------------------------------------------------------------------------
# 1. Clock Definitions
#---------------------------------------------------------------------------

# SPI clock (from external master)
create_clock -name spi_clk -period 20.0 [get_ports spi_sclk]

# AXI system clock
create_clock -name axi_clk -period 10.0 [get_ports axi_clk]

#---------------------------------------------------------------------------
# 2. Clock Groups (asynchronous)
#---------------------------------------------------------------------------
set_clock_groups -asynchronous \
    -group { spi_clk } \
    -group { axi_clk }

#---------------------------------------------------------------------------
# 3. Input Delays (SPI inputs, relative to spi_clk)
#---------------------------------------------------------------------------
set_input_delay -clock spi_clk -max 2.9 [get_ports spi_sdi*]
set_input_delay -clock spi_clk -min -0.1 [get_ports spi_sdi*]
set_input_delay -clock spi_clk -max 5.0 -add_delay [get_ports spi_cs_n]

#---------------------------------------------------------------------------
# 4. Output Delays (SPI outputs, relative to spi_clk)
#---------------------------------------------------------------------------
set_output_delay -clock spi_clk -max 5.0 [get_ports spi_sdo*]
set_output_delay -clock spi_clk -min 0.5 [get_ports spi_sdo*]

#---------------------------------------------------------------------------
# 5. Input Delays (AXI inputs, relative to axi_clk)
#---------------------------------------------------------------------------
set_input_delay -clock axi_clk -max 2.0 [get_ports axi_*ready]
set_input_delay -clock axi_clk -max 3.0 [get_ports axi_bresp*]
set_input_delay -clock axi_clk -max 3.0 [get_ports axi_rdata*]
set_input_delay -clock axi_clk -max 2.0 [get_ports axi_rresp*]
set_input_delay -clock axi_clk -max 2.0 [get_ports axi_rvalid]

#---------------------------------------------------------------------------
# 6. Output Delays (AXI outputs, relative to axi_clk)
#---------------------------------------------------------------------------
set_output_delay -clock axi_clk -max 3.0 [get_ports axi_aw*]
set_output_delay -clock axi_clk -max 3.0 [get_ports axi_w*]
set_output_delay -clock axi_clk -max 3.0 [get_ports axi_ar*]
set_output_delay -clock axi_clk -max 3.0 [get_ports axi_rready]
set_output_delay -clock axi_clk -max 3.0 [get_ports axi_bready]

#---------------------------------------------------------------------------
# 7. False Paths
#---------------------------------------------------------------------------

# Async reset paths
set_false_path -from [get_ports axi_rst_n]
set_false_path -from [get_ports spi_cs_n]

# CDC paths (covered by FIFO + pulse synchronizers)
set_false_path -from [get_clocks spi_clk] -to [get_clocks axi_clk]
set_false_path -from [get_clocks axi_clk] -to [get_clocks spi_clk]

#---------------------------------------------------------------------------
# 8. Multicycle Paths
#---------------------------------------------------------------------------

# Status register updates (takes multiple CDC cycles)
set_multicycle_path -setup 4 -from [get_clocks axi_clk] \
    -to [get_pins spi_status_reg/D]
set_multicycle_path -hold 3 -from [get_clocks axi_clk] \
    -to [get_pins spi_status_reg/D]
```

### 9.2 SDC Constraint Derivation Guide

| Constraint Type | Derivation Method | Typical Value |
|----------------|-------------------|---------------|
| `create_clock -period` | 1 / target_frequency | 20ns (SPI 50MHz), 10ns (AXI 100MHz) |
| `set_clock_groups -asynchronous` | SPI_CLK ↔ AXI_CLK | — |
| `set_false_path` | All CDC crossing paths | — |

---

## 10. Implementation Notes

### 10.1 Coding Style

| Rule | Requirement | Rationale |
|------|------------|-----------|
| R10.1 | Use `always_ff @(posedge clk or negedge rst_n)` for sequential logic | 统一风格 |
| R10.2 | Use `always_comb` for combinational logic | SystemVerilog 最佳实践 |
| R10.3 | Non-blocking in seq, blocking in comb | 竞争条件防范 |
| R10.4 | No latches inferred | 组合逻辑必须覆盖所有 case |
| R10.5 | `unique case` for muxes | 综合工具优化 |
| R10.8 | All flops must have a reset value | DFT 要求 |
| R10.9 | All FSMs decode unused states to safe state | 防止锁死 |

### 10.2 Module Parameterization

| Parameter | Default | Type | Description |
|-----------|---------|------|-------------|
| `AXI_ADDR_WIDTH` | 32 | int | AXI 地址总线宽度 |
| `AXI_DATA_WIDTH` | 32 | int | AXI 数据总线宽度 |
| `RX_FIFO_DEPTH` | 8 | int | RX FIFO 深度 |
| `TX_FIFO_DEPTH` | 8 | int | TX FIFO 深度 |
| `SPI_CPOL` | 0 | bit | SPI 时钟极性 |
| `SPI_CPHA` | 0 | bit | SPI 时钟相位 |

```systemverilog
module spi2axi #(
    parameter int AXI_ADDR_WIDTH = 32,
    parameter int AXI_DATA_WIDTH = 32,
    parameter int RX_FIFO_DEPTH  = 8,
    parameter int TX_FIFO_DEPTH  = 8,
    parameter bit SPI_CPOL       = 1'b0,
    parameter bit SPI_CPHA       = 1'b0
) (
    input  logic                  spi_sclk,
    input  logic                  spi_cs_n,
    input  logic [3:0]            spi_sdi,
    output logic [3:0]            spi_sdo,
    input  logic                  axi_clk,
    input  logic                  axi_rst_n,
    // AXI4-Lite Master Interface
    output logic [AXI_ADDR_WIDTH-1:0] axi_awaddr,
    output logic                     axi_awvalid,
    input  logic                     axi_awready,
    output logic [AXI_DATA_WIDTH-1:0] axi_wdata,
    output logic [AXI_DATA_WIDTH/8-1:0] axi_wstrb,
    output logic                     axi_wvalid,
    input  logic                     axi_wready,
    input  logic [1:0]               axi_bresp,
    input  logic                     axi_bvalid,
    output logic                     axi_bready,
    output logic [AXI_ADDR_WIDTH-1:0] axi_araddr,
    output logic                     axi_arvalid,
    input  logic                     axi_arready,
    input  logic [AXI_DATA_WIDTH-1:0] axi_rdata,
    input  logic [1:0]               axi_rresp,
    input  logic                     axi_rvalid,
    output logic                     axi_rready
);
```

### 10.3 Synthesis Pragmas

```systemverilog
// Synthesis pragma conventions:
// synopsys full_case       - force all case items covered
// synopsys parallel_case   - force parallel mux (not priority)
// synopsys translate_off   - simulation-only code
// synopsys translate_on    - resume synthesis
```

### 10.4 Area / Speed Trade-offs

| Optimization | Technique | Area Impact | Timing Impact | When to Use |
|-------------|-----------|-------------|---------------|-------------|
| FIFO depth | 8→4 entries | -20% | 0% | Area constrained |
| Gray-code encoding | Binary → Gray | 0% | 0% CDC | Required for CDC |
| SPI mode parameter | Fixed Mode 0 | -5% | 0% | If only Mode 0 needed |

---

## 11. Verification Guidance

### 11.1 Directed Test Scenarios

| Test ID | Scenario | Stimulus | Expected Behavior | Coverage Point |
|---------|----------|----------|-------------------|----------------|
| T01 | CSR write/read | Write SPI_CTRL, read back | Match written values | 100% reg access |
| T02 | SPI write transaction | Opcode=0x00, addr, data | AXI AW→W→B sequence | SPI→AXI write path |
| T03 | SPI read transaction | Opcode=0x01, addr, dummy | AXI AR→R sequence, data out | SPI→AXI read path |
| T04 | QSPI mode | QSPI_EN=1, 4-line transfer | 4x throughput | QSPI mode |
| T05 | Address wrap | WRAP_CFG=2, sequential access | Address wraps at boundary | Wrap logic |
| T06 | Dummy cycle | DUMMY_CFG=16 | Read data after 16 cycles | Dummy counter |
| T07 | CDC random test | Random SPI_CLK:AXI_CLK ratio | Data integrity across CDC | CDC correctness |
| T08 | Error injection | Force AXI SLVERR | Status byte reflects error | Error propagation |
| T09 | Back-to-back access | Continuous write/read | No data loss | Pipeline throughput |
| T10 | CS abort | CS de-assert mid-operation | FSM→IDLE cleanly | Error recovery |

### 11.2 Assertion Checkers

```systemverilog
//=============================================================================
// Formal Assertions (SVA)
//=============================================================================

// A1: AXI valid/ready handshake protocol
`ifdef FORMAL
    assert_aw_handshake: assert property (
        @(posedge axi_clk) disable iff (!axi_rst_n)
        axi_awvalid |-> s_eventually axi_awready
    );

    // A2: FSM never enters reserved state
    assert_fsm_safe: assert property (
        @(posedge axi_clk) disable iff (!axi_rst_n)
        axi_state_q inside {ST_AXI_IDLE, ST_WR_ADDR, ST_WR_DATA,
                            ST_WR_RESP, ST_RD_ADDR, ST_RD_DATA, ST_COMPLETE}
    );

    // A3: FIFO never read when empty
    assert_fifo_no_empty_read: assert property (
        @(posedge axi_clk) disable iff (!axi_rst_n)
        !(rx_fifo_rd && rx_fifo_empty)
    );

    // A4: FIFO never written when full
    assert_fifo_no_full_write: assert property (
        @(posedge spi_clk) disable iff (spi_cs_n)
        !(rx_fifo_wr && rx_fifo_full)
    );
`endif
```

### 11.3 Functional Coverage Points

| Cover Group | Cover Point | Description |
|-------------|-------------|-------------|
| `cg_opcode` | opcode == 0x00 | Write command |
| `cg_opcode` | opcode == 0x01 | Read command |
| `cg_opcode` | opcode inside {0x02..0xFF} | Invalid opcode |
| `cg_wrap` | wrap_size == 0 | No wrap |
| `cg_wrap` | wrap_size > 0 | Wrap enabled |
| `cg_mode` | qspi_en == 0 | Standard SPI |
| `cg_mode` | qspi_en == 1 | QSPI mode |
| `cg_error` | bresp != OKAY | AXI slave error |
| `cg_cdc` | rx_fifo_almost_full | RX FIFO near full |

---

## 12. DFT Requirements

### 12.1 Scan Chain Specification

| Scan Chain | Clock Domain | Flop Count | IO Pins |
|------------|-------------|------------|---------|
| chain_spi | SPI_CLK | ~200 | scan_in0 / scan_out0 |
| chain_axi | AXI_CLK | ~500 | scan_in1 / scan_out1 |

### 12.2 Test Mode Behavior

| Signal | Function Mode | Test Mode | Description |
|--------|--------------|-----------|-------------|
| `test_mode_i` | 0 | 1 | 全局测试模式使能 |
| `scan_enable_i` | 0 | 1 | 扫描移位使能 |
| `scan_in_i` | — | data_in | 扫描链输入 |
| `scan_out_o` | — | data_out | 扫描链输出 |

### 12.3 Test Mode Rules

- **TMR1**: 所有 FFs 必须是可扫描替换的 (scan flip-flop)
- **TMR2**: 时钟在测试模式下由 test_clk 控制
- **TMR3**: 异步复位在测试模式下必须被屏蔽
- **TMR4**: 所有双向 I/O 在测试模式下必须配置为固定方向

### 12.4 MBIST

| Memory Instance | BIST Controller | Test Algorithm | Redundancy |
|----------------|----------------|----------------|------------|
| RX_FIFO | mbist_ctrl_0 | March C- | None |
| TX_FIFO | mbist_ctrl_0 | March C- | None |

### 12.5 JTAG / Boundary Scan

N/A — 模块级 DFT，JTAG 由 SoC 级提供。

---

## 13. Delivery Checklist

### 13.1 Deliverable Files

| # | File | Description | Status |
|---|------|-------------|--------|
| 1 | `spi2axi_top.sv` | 主 RTL 源代码 | ☐ Not started |
| 2 | `spi2axi.sdc` | 时序约束文件 | ☐ Draft |
| 3 | `spi2axi_tb.sv` | 自检测试台 | ☐ Not started |
| 4 | `spi2axi_lint.rpt` | Lint 检查报告 | ☐ Not started |
| 5 | `spi2axi_area.rpt` | 面积报告 | ☐ Not started |

### 13.2 Quality Gates

| Gate | Criteria | Entry | Exit |
|------|----------|-------|------|
| G1: Lint Clean | 0 errors, 0 warnings | RTL ready | Lint report |
| G2: Simulation Pass | All directed tests pass | Testbench ready | Test report |
| G3: Synthesis Clean | 0 DRC violations | SDC + RTL ready | Area report |
| G4: DFT Ready | Scan chain insertion verified | Synthesis done | DFT report |

### 13.3 Format Requirements

| Deliverable | Format | Header Required |
|-------------|--------|----------------|
| RTL source | SystemVerilog (.sv) | Yes |
| SDC | Synopsys SDC (.sdc) | Yes |
| Testbench | SystemVerilog (.sv) | Yes |

---

## 14. Revision History

| Version | Date | Author | Change Description |
|---------|------|--------|-------------------|
| V1.0 | 2026-05-20 | chip-spec-gen | 初稿 (单文档版本) |
| **V2.0** | **2026-05-20** | **chip-spec-gen** | **LLD 拆分版: 14 章 AI-Executable 结构 — 含 FSM 编码/转移/输出表、CSR bit-level 映射、SDC 约束、RTL 模板、验证计划** |

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| AXI | Advanced eXtensible Interface |
| CDC | Clock Domain Crossing |
| CSR | Control and Status Register |
| DFT | Design for Testability |
| FSM | Finite State Machine |
| LLD | Low-Level Design (微架构) |
| QSPI | Quad SPI |
| SDC | Synopsys Design Constraints |
| SVA | SystemVerilog Assertions |
| W1C | Write-1-to-Clear |

## Appendix B: Reference Documents

| Document | Version | Source | Description |
|----------|---------|--------|-------------|
| SPI2AXI SPEC.pdf | V1.0 | 本地 | 原始设计规格 |
| SPI2AXI HLD | V2.0 | chip-spec-gen | Block HLD (03_block_arch.HLD.md) |
| AMBA AXI4-Lite Protocol | ARM IHI 0022G | ARM | AXI 协议标准 |
| airhdl/spi-to-axi-bridge | — | GitHub | 开源参考设计 |

---

*本文档由 Chip Design Agent 生成 — AI-Executable LLD V2.0*
