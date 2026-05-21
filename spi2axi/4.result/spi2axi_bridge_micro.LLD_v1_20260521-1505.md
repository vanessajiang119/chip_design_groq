# 模块微架构规格书 — SPI2AXI Bridge Micro-Architecture LLD

> **模块名称:** SPI2AXI Bridge (SPI to AXI4-Lite Bridge)
> **版本:** V1.0
> **日期:** 2026-05-21
> **状态:** Draft
> **层次路径:** soc.periph.spi2axi
> **工艺节点:** 待定 (取决于 SoC 平台)
> **目标频率:** SPI 时钟: 50 MHz / AXI 时钟: 待定

---

## 1. Module Overview

### 1.1 Module Identity

| 属性 | 值 |
|------|-----|
| 模块全名 | SPI2AXI Bridge (SPI2AXI) |
| 层次路径 | `soc.periph.spi2axi` |
| 工艺 / PVT | 待定 (取决于 SoC 平台) |
| 目标频率 | SPI: 50 MHz / AXI: 待定 |
| 供电电压 | 待定 (取决于 SoC 平台) |
| 面积预算 | 待补充 (需 RTL 综合后评估) |
| 功耗预算 | 待补充 (需 RTL 综合后评估) |

### 1.2 Top-Level Ports Summary

| Port Group | Direction | Width | Description |
|------------|-----------|-------|-------------|
| `spi_sclk` | input | 1 | SPI 串行时钟 @ 50 MHz (max) |
| `spi_rst_n` | input | 1 | SPI 域异步复位, 低有效 |
| `spi_cs` | input | 1 | SPI 片选信号, 低有效 |
| `spi_sdi[3:0]` | input | 4 | SPI 数据输入 (1-wire 或 4-wire) |
| `spi_sdo[3:0]` | output | 4 | SPI 数据输出 (1-wire 或 4-wire) |
| `axi_aclk` | input | 1 | AXI 系统时钟 |
| `axi_areset_n` | input | 1 | AXI 域异步复位, 低有效 |
| `axi_*` | in/out | 多通道 | AXI4-Lite 主接口信号 (AW/W/B/AR/R) |
| `intr_o` | output | 1 | AXI 域中断输出 |

### 1.3 Module Features

- [x] Feature 1: Standard SPI (1-wire) Slave 模式支持
- [x] Feature 2: Quad SPI / QSPI (4-wire) Slave 模式支持 (通过 CSR 可选)
- [x] Feature 3: AXI4-Lite Master 接口 (5 通道独立握手)
- [x] Feature 4: Dual-clock CDC FIFO 跨时钟域传输 (cmd/wdata/rdata 三路独立)
- [x] Feature 5: 可编程 Dummy Cycles (读操作等待周期, 实际 = DUMMY_CYCLES + 1)
- [x] Feature 6: 可配置地址 Wrap 环绕访问
- [x] Feature 7: SPI 可直接访问的 CSR 寄存器文件
- [ ] Feature 8: 待补充 — 中断输出支持
- [ ] Feature 9: 待补充 — AXI 错误检测与上报

### 1.4 Design Assumptions

- A1: SPI 主机在 `spi_cs` 有效期间保持 `spi_sclk` 稳定
- A2: AXI 从设备在合理延迟内响应 (不会无限等待)
- A3: SPI 帧格式严格遵循 Opcode (8-bit) + Address (32-bit, 可选) + Data (32-bit) 序列
- A4: 配置寄存器仅在 FSM IDLE 状态下修改

---

## 2. Interface Specification

### 2.1 Port Signal Table

#### SPI 接口信号

| Signal Name | Direction | Width | Type | Clock Domain | Reset Domain | I/O Pad | Description |
|-------------|-----------|-------|------|-------------|-------------|---------|-------------|
| `spi_sclk` | input | 1 | clock | — | — | no | SPI 串行时钟，最高 50 MHz (由外部 SPI 主机提供) |
| `spi_rst_n` | input | 1 | reset async active-low | spi_sclk | — | no | SPI 域异步复位，低有效 |
| `spi_cs` | input | 1 | data | spi_sclk | spi_rst_n | no | SPI 片选，低有效 |
| `spi_sdi[0]` | input | 1 | data | spi_sclk | spi_rst_n | no | SPI 数据输入 (1-wire 模式) |
| `spi_sdi[3:0]` | input | 4 | data | spi_sclk | spi_rst_n | no | SPI 数据输入 (4-wire 模式) |
| `spi_sdo[0]` | output | 1 | data | spi_sclk | spi_rst_n | no | SPI 数据输出 (1-wire 模式) |
| `spi_sdo[3:0]` | output | 4 | data | spi_sclk | spi_rst_n | no | SPI 数据输出 (4-wire 模式) |

#### AXI4-Lite 主接口信号

| Signal Name | Direction | Width | Type | Clock Domain | Reset Domain | I/O Pad | Description |
|-------------|-----------|-------|------|-------------|-------------|---------|-------------|
| `axi_aclk` | input | 1 | clock | — | — | no | AXI 系统时钟 |
| `axi_areset_n` | input | 1 | reset async active-low | axi_aclk | — | no | AXI 域异步复位，低有效 |
| `awaddr` | output | AXI_ADDR_WIDTH | data | axi_aclk | axi_areset_n | no | AXI 写地址 |
| `awvalid` | output | 1 | data | axi_aclk | axi_areset_n | no | AXI 写地址有效 |
| `awready` | input | 1 | data | axi_aclk | axi_areset_n | no | AXI 写地址就绪 |
| `awid` | output | AXI_ID_WIDTH | data | axi_aclk | axi_areset_n | no | AXI 写地址 ID |
| `awprot` | output | 3 | data | axi_aclk | axi_areset_n | no | AXI 写保护类型 (固定 3'b000) |
| `wdata` | output | AXI_DATA_WIDTH | data | axi_aclk | axi_areset_n | no | AXI 写数据 |
| `wstrb` | output | AXI_DATA_WIDTH/8 | data | axi_aclk | axi_areset_n | no | AXI 写选通 (固定 4'b1111) |
| `wvalid` | output | 1 | data | axi_aclk | axi_areset_n | no | AXI 写数据有效 |
| `wready` | input | 1 | data | axi_aclk | axi_areset_n | no | AXI 写数据就绪 |
| `bresp` | input | 2 | data | axi_aclk | axi_areset_n | no | AXI 写响应 |
| `bvalid` | input | 1 | data | axi_aclk | axi_areset_n | no | AXI 写响应有效 |
| `bready` | output | 1 | data | axi_aclk | axi_areset_n | no | AXI 写响应就绪 |
| `bid` | input | AXI_ID_WIDTH | data | axi_aclk | axi_areset_n | no | AXI 写响应 ID |
| `araddr` | output | AXI_ADDR_WIDTH | data | axi_aclk | axi_areset_n | no | AXI 读地址 |
| `arvalid` | output | 1 | data | axi_aclk | axi_areset_n | no | AXI 读地址有效 |
| `arready` | input | 1 | data | axi_aclk | axi_areset_n | no | AXI 读地址就绪 |
| `arid` | output | AXI_ID_WIDTH | data | axi_aclk | axi_areset_n | no | AXI 读地址 ID |
| `arprot` | output | 3 | data | axi_aclk | axi_areset_n | no | AXI 读保护类型 (固定 3'b000) |
| `rdata` | input | AXI_DATA_WIDTH | data | axi_aclk | axi_areset_n | no | AXI 读数据 |
| `rresp` | input | 2 | data | axi_aclk | axi_areset_n | no | AXI 读响应 |
| `rvalid` | input | 1 | data | axi_aclk | axi_areset_n | no | AXI 读数据有效 |
| `rready` | output | 1 | data | axi_aclk | axi_areset_n | no | AXI 读数据就绪 |
| `rid` | input | AXI_ID_WIDTH | data | axi_aclk | axi_areset_n | no | AXI 读数据 ID |

### 2.2 Cycle-Level Timing Diagrams

#### 2.2.1 SPI Frame Timing (Standard SPI 1-wire, CPOL=0, CPHA=0)

```
SPI 写内存帧格式:
spi_cs       ████████████████████████████████████████████████████▁▁▁
spi_sclk     ▁▁██▁██▁██▁██▁██▁██▁██▁██▁...▁██▁██▁██▁██▁██▁██▁██▁█
spi_sdi[0]   XXX< Opcode 8-bit >X<    Address 32-bit   >X<  WData 32-bit  >X
spi_sdo[0]   ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ

             |-- 8 sclk cycles --|-- 32 sclk cycles ----|-- 32 sclk cycles --|
```

**Cycle Description (SPI 写)**:
- **Phase 1 (Opcode)**: 8 个 spi_sclk 周期，spi_sdi 串行接收 8-bit 操作码 (MSB first)
- **Phase 2 (Address)**: 32 个 spi_sclk 周期，spi_sdi 串行接收 32-bit 地址 (MSB first, 内存访问)
- **Phase 3 (Write Data)**: 32 个 spi_sclk 周期，spi_sdi 串行接收 32-bit 写数据 (MSB first)

```
SPI 读内存帧格式 (含 Dummy Cycles):
spi_cs       ███████████████████████████████████████████████████████████████▁
spi_sclk     ▁██▁██▁...▁██▁██▁██▁...▁██▁██▁██▁...▁██▁██▁██▁...▁██▁██▁
spi_sdi[0]   X<Opcode>X< Address 32-bit >XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
spi_sdo[0]   ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ<    RData 32-bit     >

             |-8-|------- 32 --------|------- Dummy Cycles -------|---- 32 ---|
```

**Cycle Description (SPI 读)**:
- **Phase 1 (Opcode)**: 8 个 spi_sclk 周期接收操作码
- **Phase 2 (Address)**: 32 个 spi_sclk 周期接收地址 (MSB first)
- **Phase 3 (Dummy Cycles)**: DUMMY_CYCLES + 1 个 spi_sclk 周期等待 AXI 读数据返回
- **Phase 4 (Read Data)**: 32 个 spi_sclk 周期，spi_sdo 串行发送 32-bit 读数据 (MSB first)

#### 2.2.2 AXI4-Lite Write Transaction Timing

```
Clock Cycle:       T0         T1         T2         T3         T4         T5
axi_aclk          █▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█
awvalid           █████████████___________________________________________
awaddr            XXXXXXXXX<AWADDR>XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
awready           █████████████___________________________________________
wvalid            ________________██████████████████████████████████▁_______
wdata             XXXXXXXXXXXXXXXX<WDATA>XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
wready            ________________██████████████████████████████████▁_______
bvalid            ____________________________________________██████████___
bresp             XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX<OKAY>XXXXXX__
bready            ____________________________________________██████████___
```

**Write Transaction Cycle Description**:
- **T0**: awvalid 和 awready 同时有效，写地址在 T0 上升沿捕获 (零等待)
- **T2**: wvalid 和 wready 同时有效，写数据在 T2 上升沿捕获
- **T4**: bvalid 和 bready 同时有效，写响应在 T4 上升沿捕获，写事务完成

#### 2.2.3 AXI4-Lite Read Transaction Timing

```
Clock Cycle:       T0         T1         T2         T3         T4         T5
axi_aclk          █▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█
arvalid           █████████████___________________________________________
araddr            XXXXXXXXX<ARADDR>XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
arready           █████████████___________________________________________
rvalid            ____________________________________________████████████___
rdata             XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX<RDATA>XXXXXX__
rresp             XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX<OKAY>XXXXXX__
rready            ____________________________________________████████████___
```

**Read Transaction Cycle Description**:
- **T0**: arvalid 和 arready 同时有效，读地址在 T0 上升沿捕获
- **T4**: rvalid 和 rready 同时有效，读数据在 T4 上升沿捕获，读事务完成

### 2.3 Backpressure Behavior

| Condition | Backpressure Action | Latency Impact | RTL Implementation |
|-----------|--------------------|----------------|-------------------|
| wdata_fifo 满 | SPI 域暂停发送写数据 | SPI 时钟等待 | `wdata_fifo_full → spi_tx_hold` |
| rdata_fifo 空 | SPI 域等待读数据 | 插入额外 spi_sclk 周期 | `rdata_fifo_empty → spi_rx_stall` |
| cmd_fifo 满 | SPI 域暂停命令写入 | SPI 时钟等待 | `cmd_fifo_full → cmd_hold` |
| AXI AW/W ready 低 | AXI 等待握手 | 取决于 AXI 从设备 | `axi_awready & axi_wready → advance` |
| AXI B valid 低 | AXI 等待写响应 | 取决于 AXI 从设备 | `axi_bvalid → capture_bresp` |
| AXI R valid 低 | AXI 等待读数据 | 取决于 AXI 从设备 | `axi_rvalid → capture_rdata` |

### 2.4 Interrupt Interface

| Interrupt | Source Event | Trigger Type | Clear Mechanism | Polarity |
|-----------|-------------|-------------|-----------------|----------|
| `intr_o` | AXI 事务错误 (bresp/rresp != OKAY) | Level | W1C to INT_STAT register | Level high |
| `intr_o` | 事务完成 (待定 — 可选) | Level | W1C to INT_STAT register | Level high |

> **Interrupt Aggregation**: 所有中断事件通过 OR 树合并为一个输出。每个事件有独立的 enable 位和 status 位。

---

## 3. Sub-Module Partition

### 3.1 Block Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          SPI2AXI_Bridge (Top)                                 │
│                                                                              │
│  ┌─────────────────── SPI Clock Domain ────────────────────┐                 │
│  │                                                         │                 │
│  │  ┌──────────────────────┐      ┌────────────────────┐  │                 │
│  │  │ spi_slave_if         │      │  fsm_ctrl          │  │                 │
│  │  │  ┌────────────────┐  │      │  state:            │  │                 │
│  │  │  │ spi_io         │  │      │  IDLE/OPCODE/ADDR  │  │                 │
│  │  │  │ - shift_reg    │──┼──────┤  DUMMY/DATA/AXI_WR │  │                 │
│  │  │  │ - mode_sel     │  │      │  AXI_RD/DONE       │  │                 │
│  │  │  └───────┬────────┘  │      └────────┬───────────┘  │                 │
│  │  │          │           │               │              │                 │
│  │  │  ┌───────┴────────┐  │      ┌────────┴───────────┐  │                 │
│  │  │  │ spi_cmd_decoder│  │      │  csr_regfile       │  │                 │
│  │  │  │ - opcode_decode│  │      │  - CTRL/STATUS/CFG │  │                 │
│  │  │  │ - addr_latch   │  │      │  - mode/wrap/dummy │  │                 │
│  │  │  └────────────────┘  │      └────────────────────┘  │                 │
│  │  └──────────────────────┘                               │                 │
│  └─────────────────────────────────────────────────────────┘                 │
│                               │ cmd/wdata/rdata                              │
│                               ▼                                               │
│  ┌──────────────────── CDC FIFO ──────────────────────┐                      │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐         │                      │
│  │  │ cmd_fifo │  │wdata_fifo│  │rdata_fifo│         │                      │
│  │  │ DP:4-16  │  │ DP:4-64  │  │ DP:4-64  │         │                      │
│  │  │ W:40bit  │  │ W:32bit  │  │ W:32bit  │         │                      │
│  │  └────┬─────┘  └────┬─────┘  └────▲─────┘         │                      │
│  └───────┼─────────────┼──────────────┼────────────────┘                      │
│          │             │              │                                       │
│  ┌───────┼─────────── AXI Clock Domain ─┼──────────────────┐                 │
│  │       │             │              │                    │                 │
│  │  ┌────┴─────────────┴──────────────┴──────┐             │                 │
│  │  │  axi_master_if                         │             │                 │
│  │  │  ┌──────────────────┐ ┌──────────────┐ │             │                 │
│  │  │  │ axi_wr_ctrl      │ │ axi_rd_ctrl  │ │             │                 │
│  │  │  │ - AW channel mst │ │ - AR channel │ │             │                 │
│  │  │  │ - W channel mst  │ │ - R channel  │ │             │                 │
│  │  │  │ - B channel mst  │ │              │ │             │                 │
│  │  │  └──────────────────┘ └──────────────┘ │             │                 │
│  │  └────────────────────┬───────────────────┘             │                 │
│  │                       │                                 │                 │
│  │  ┌────────────────────┴───────────────────┐             │                 │
│  │  │  wrap_addr_gen                         │             │                 │
│  │  │  - addr_increment                      │             │                 │
│  │  │  - addr_wrap_detect                    │             │                 │
│  │  └────────────────────────────────────────┘             │                 │
│  └─────────────────────────────────────────────────────────┘                 │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │           Clock & Reset / CDC Synchronizer                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Sub-Module Responsibilities

| Sub-Module | Input From | Output To | Width | Function |
|------------|-----------|-----------|-------|----------|
| spi_io | SPI Pins (spi_sdi) | spi_cmd_decoder, cmd_fifo, wdata_fifo | 1/4-bit → 8/32-bit | SPI 串行数据收发，1-wire/4-wire 模式串并/并串转换 |
| spi_cmd_decoder | spi_io | fsm_ctrl, cmd_fifo | 8-bit opcode + 32-bit addr | SPI 命令解析: 操作码解码、地址锁存、寄存器/内存访问区分 |
| fsm_ctrl | spi_cmd_decoder, csr_regfile | spi_io, cdc_fifo, axi_master_if, wrap_addr_gen | — | 主状态机，控制 SPI 到 AXI 转换全流程 |
| csr_regfile | SPI write (通过 fsm_ctrl) | fsm_ctrl, wrap_addr_gen | 32-bit | 配置/状态寄存器: mode_sel, wrap_en, dummy_cfg |
| cmd_fifo | spi_slave_if (SPI clk) | axi_master_if (AXI clk) | cmd_width (≈40) | 命令/地址跨时钟域传输，SPI→AXI |
| wdata_fifo | spi_slave_if (SPI clk) | axi_master_if (AXI clk) | 32-bit | 写数据跨时钟域传输，SPI→AXI |
| rdata_fifo | axi_master_if (AXI clk) | spi_slave_if (SPI clk) | 32-bit | 读数据跨时钟域传输，AXI→SPI |
| axi_wr_ctrl | cmd_fifo, wdata_fifo | AXI AW/W/B channels | 32-bit addr + 32-bit data | AXI 写事务控制: AW→W→B 握手 |
| axi_rd_ctrl | cmd_fifo | AXI AR/R channels | 32-bit addr | AXI 读事务控制: AR→R 握手 |
| wrap_addr_gen | csr_regfile | axi_master_if | 32-bit addr | Wrap 地址生成: 地址自增、回绕判断 |

### 3.3 Inter-Module Signal Table

| Signal | Width | Source | Sink | Description |
|--------|-------|--------|------|-------------|
| `opcode_decoded` | 3 | spi_cmd_decoder | fsm_ctrl | 解码的操作码类型: 000=写内存, 001=读内存, 010=写Reg, 011=读Reg |
| `addr_captured` | 32 | spi_cmd_decoder | cmd_fifo | 捕获的 32-bit 地址 |
| `addr_valid` | 1 | spi_cmd_decoder | cmd_fifo | 地址捕获完成标志 |
| `wdata_captured` | 32 | spi_io | wdata_fifo | 捕获的 32-bit 写数据 |
| `wdata_valid` | 1 | spi_io | wdata_fifo | 写数据捕获完成标志 |
| `rdata_from_fifo` | 32 | rdata_fifo | spi_io | 从 AXI 域返回的读数据 |
| `rdata_valid` | 1 | rdata_fifo | spi_io | 读数据有效标志 |
| `cmd_fifo_rd` | cmd_width | cmd_fifo | axi_master_if | 命令+地址 (FIFO 读出) |
| `cmd_fifo_empty` | 1 | cmd_fifo | axi_master_if | 命令 FIFO 空标志 |
| `cmd_fifo_full` | 1 | cmd_fifo | fsm_ctrl | 命令 FIFO 满标志 |
| `wdata_fifo_rd` | 32 | wdata_fifo | axi_wr_ctrl | 写数据 (FIFO 读出) |
| `wdata_fifo_empty` | 1 | wdata_fifo | axi_wr_ctrl | 写数据 FIFO 空标志 |
| `rdata_fifo_wr` | 32 | axi_rd_ctrl | rdata_fifo | AXI 读数据写入 FIFO |
| `rdata_fifo_full` | 1 | rdata_fifo | axi_rd_ctrl | 读数据 FIFO 满标志 |
| `csr_mode_sel` | 1 | csr_regfile | spi_io | SPI 模式选择: 0=1-wire, 1=4-wire |
| `csr_wrap_en` | 1 | csr_regfile | wrap_addr_gen | Wrap 使能 |
| `csr_dummy_cfg` | 8 | csr_regfile | fsm_ctrl | Dummy cycles 配置值 |
| `fsm_state` | 4 | fsm_ctrl | 所有模块 | FSM 当前状态 (用于输出控制) |
| `axi_tx_done` | 1 | axi_master_if | fsm_ctrl | AXI 事务完成标志 |
| `axi_error` | 1 | axi_master_if | fsm_ctrl | AXI 事务错误标志 |
| `wrap_addr_out` | 32 | wrap_addr_gen | axi_master_if | Wrap 计算后的地址 |
| `wrap_en` | 1 | wrap_addr_gen | axi_master_if | Wrap 模式使能信号 |

---

## 4. FSM Specification

### 4.1 State Encoding Table

| State Name | Encoding | Description |
|------------|----------|-------------|
| `IDLE` | `4'b0000` | 空闲/复位状态, 等待 spi_cs 有效和命令输入 |
| `OPCODE` | `4'b0001` | 接收 8-bit 操作码, 解码读/写操作 |
| `ADDR` | `4'b0010` | 接收 32-bit 地址 (仅内存访问时需要, MSB first) |
| `DUMMY` | `4'b0011` | 读操作插入虚拟等待周期 (可编程, 由 DUMMY_CYCLES 配置) |
| `DATA` | `4'b0100` | SPI 数据传输阶段 (32-bit, MSB first) |
| `AXI_WR` | `4'b0101` | AXI 写事务执行 (AW→W→B 握手) |
| `AXI_RD` | `4'b0110` | AXI 读事务执行 (AR→R 握手) |
| `DONE` | `4'b0111` | 事务完成, 返回 IDLE |
| `4'b1000` | — | **RESERVED** (decode to IDLE for safety) |
| `4'b1001`~`4'b1111` | — | **RESERVED** (decode to IDLE for safety) |

> **Safety**: 未使用的编码 (1000~1111) 必须解码为 IDLE，防止 FSM 锁死。

### 4.2 State Transition Matrix

| Current State | Condition | Next State | Transition Action |
|--------------|-----------|------------|------------------|
| `IDLE` | `spi_cs == 1 (无效)` | `IDLE` | 保持 |
| `IDLE` | `spi_cs == 0` | `OPCODE` | 复位 opcode 移位计数器，开始接收操作码 |
| `OPCODE` | `opcode_rcvd == 0` | `OPCODE` | 持续移位接收 |
| `OPCODE` | `opcode_rcvd == 1` | `ADDR` | 锁存操作码，解码读写类型 |
| `OPCODE` | `opcode_rcvd == 1 && is_reg_access` | `DATA` | 寄存器访问跳过 ADDR 状态 |
| `ADDR` | `addr_rcvd == 0` | `ADDR` | 持续移位接收地址 |
| `ADDR` | `addr_rcvd == 1 && is_read` | `DUMMY` | 地址接收完成 (读操作) |
| `ADDR` | `addr_rcvd == 1 && is_write` | `DATA` | 地址接收完成 (写操作) |
| `DUMMY` | `dummy_cnt < DUMMY_CYCLES` | `DUMMY` | 等待 dummy 周期 |
| `DUMMY` | `dummy_cnt == DUMMY_CYCLES` | `DATA` | dummy 结束 (注: 实际周期 = cfg + 1) |
| `DATA` | `data_xfer_done == 0` | `DATA` | 持续数据传输 (32 cycles) |
| `DATA` | `data_xfer_done == 1 && is_write` | `AXI_WR` | 写数据接收完成 |
| `DATA` | `data_xfer_done == 1 && is_read` | `AXI_RD` | 读数据发送完成 (但 AXI 读必须提前启动) |
| `AXI_WR` | `axi_bvalid == 0` | `AXI_WR` | 等待写响应 |
| `AXI_WR` | `axi_bvalid == 1 && bresp == OKAY` | `DONE` | 写事务成功 |
| `AXI_WR` | `axi_bvalid == 1 && bresp != OKAY` | `DONE` | 写事务完成但存在错误 (记录错误标志) |
| `AXI_RD` | `axi_rvalid == 0` | `AXI_RD` | 等待读数据 (dummy 期间已启动 AR) |
| `AXI_RD` | `axi_rvalid == 1 && rresp == OKAY` | `DATA` / `DONE` | 读数据返回, 送往 SPI TX |
| `DONE` | (无条件) | `IDLE` | 置位完成标志, 清除临时寄存器 |

> **Transition Rules**:
> - 所有状态在 `spi_rst_n` 或 `axi_areset_n` 断言时无条件回到 `IDLE`
> - `spi_cs` 在任何状态提前释放 → 无条件回到 `IDLE` (事务中止)
> - 优先级: `spi_cs_release > error > normal_transition`

### 4.3 Output Decode Table

| Output Signal | IDLE | OPCODE | ADDR | DUMMY | DATA | AXI_WR | AXI_RD | DONE |
|---------------|------|--------|------|-------|------|--------|--------|------|
| `shift_en` | 0 | 1 | 1 | 0 | 1 | 0 | 0 | 0 |
| `cmd_fifo_wr` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| `wdata_fifo_wr` | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| `rdata_fifo_rd` | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| `axi_ar_valid` | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| `axi_aw_valid` | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| `axi_w_valid` | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| `dummy_cnt_en` | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| `done_flag_set` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

> **Output Decode Logic**: 纯组合逻辑 `always_comb`，不引入额外 clock 周期。

### 4.4 FSM RTL Implementation Template

```systemverilog
//=============================================================================
// FSM: SPI2AXI Bridge Main Controller
// SPI Clock Domain (spi_sclk)
//=============================================================================
typedef enum logic [3:0] {
    ST_IDLE    = 4'b0000,
    ST_OPCODE  = 4'b0001,
    ST_ADDR    = 4'b0010,
    ST_DUMMY   = 4'b0011,
    ST_DATA    = 4'b0100,
    ST_AXI_WR  = 4'b0101,
    ST_AXI_RD  = 4'b0110,
    ST_DONE    = 4'b0111
} state_t;

state_t state_q, next_state;

// State register (sequential)
always_ff @(posedge spi_sclk or negedge spi_rst_n) begin
    if (!spi_rst_n)
        state_q <= ST_IDLE;
    else if (!spi_cs)  // cs release → abort
        state_q <= ST_IDLE;
    else
        state_q <= next_state;
end

// Next state logic (combinational)
always_comb begin
    next_state = state_q;  // default: stay
    unique case (state_q)
        ST_IDLE:   if (!spi_cs)        next_state = ST_OPCODE;
        ST_OPCODE: if (opcode_rcvd) begin
                       if (is_reg_acc) next_state = ST_DATA;
                       else            next_state = ST_ADDR;
                   end
        ST_ADDR:   if (addr_rcvd) begin
                       if (is_read)    next_state = ST_DUMMY;
                       else            next_state = ST_DATA;
                   end
        ST_DUMMY:  if (dummy_done)     next_state = ST_DATA;
        ST_DATA:   if (data_done) begin
                       if (is_write)   next_state = ST_AXI_WR;
                       else            next_state = ST_AXI_RD;
                   end
        ST_AXI_WR: if (axi_bvalid)    next_state = ST_DONE;
        ST_AXI_RD: if (axi_rvalid)    next_state = ST_DONE;
        ST_DONE:                       next_state = ST_IDLE;
        default:                       next_state = ST_IDLE;  // safety decode
    endcase
end

// Output decode (combinational)
always_comb begin
    shift_en      = (state_q == ST_OPCODE || state_q == ST_ADDR || state_q == ST_DATA);
    cmd_fifo_wr   = (state_q == ST_ADDR && addr_rcvd);
    wdata_fifo_wr = (state_q == ST_DATA && data_done && is_write);
    rdata_fifo_rd = (state_q == ST_DATA && rdata_valid && is_read);
    axi_ar_valid  = (state_q == ST_DUMMY);
    axi_aw_valid  = (state_q == ST_AXI_WR);
    axi_w_valid   = (state_q == ST_AXI_WR);
    dummy_cnt_en  = (state_q == ST_DUMMY);
    done_flag_set = (state_q == ST_DONE);
end
```

---

## 5. Pipeline Specification

### 5.1 Pipeline Stage Definition

SPI2AXI Bridge 的事务处理为**串行执行模式**（非流水线），每次处理一个 SPI 事务，转换为对应的 AXI 事务。由于 AXI4-Lite 仅支持 single transfer，整体以事务为单元顺序执行。以下是按功能阶段的定义：

| Stage Name | Stage ID | Data Width | Latency (cycles) | Description |
|------------|----------|-----------|-----------------|-------------|
| `STG_SPI_RX` | 0 | 1/4-bit → 8/32-bit | 8 + 32 (可变) | SPI 串行数据接收: 操作码 + 地址 |
| `STG_CMD_DEC` | 1 | 8/32-bit | 1 (组合) | 命令解码: 操作码解析、地址锁存 |
| `STG_CDC_XFER` | 2 | cmd_width / 32-bit | 2~8 (FIFO 延迟) | CDC FIFO 写入/读出 |
| `STG_AXI_TXN` | 3 | 32-bit | 2~N (AXI 握手延迟) | AXI 事务执行 (写: AW→W→B / 读: AR→R) |
| `STG_SPI_TX` | 4 | 32-bit | 32 (读数据返回路径) | SPI 串行数据发送 (读操作) |

### 5.2 Cycle-by-Cycle Behavior Table (SPI 写内存事务示例, 1-wire, no wait states)

| Cycle (spi_sclk) | STG_SPI_RX | STG_CMD_DEC | STG_CDC_XFER | STG_AXI_TXN | Description |
|------------------|------------|-------------|--------------|-------------|-------------|
| 1~8 | S: 接收 Opcode | B | B | B | 8-bit 操作码移位接收 |
| 9 | S: 接收 Addr bit31 | S: 解码 Opcode | B | B | 操作码完成, 开始地址 |
| 10~40 | S: 接收 Addr bit30~0 | B | B | B | 32-bit 地址移位接收 |
| 41 | S: 接收 Data bit31 | S: 锁存地址 | S: cmd_fifo 写 | B | 地址完成, 写入 cmd_fifo |
| 42~72 | S: 接收 Data bit30~0 | B | B | B | 32-bit 数据移位接收 |
| 73 | B | B | S: wdata_fifo 写 | B | 数据完成, 写入 wdata_fifo |
| 74~75 | B | B | S: cmd_fifo 读 | B | 命令跨时钟域传输 |
| 76~77 | B | B | S: wdata_fifo 读 | S: AW 通道发地址 | AXI 写地址发 |
| 78~79 | B | B | B | S: W 通道发数据 | AXI 写数据发送 |
| 80~81 | B | B | B | S: B 通道等响应 | AXI 写响应接收 |
| 82 | B | B | B | S: 完成 | 返回 IDLE |

### 5.3 Stall / Hold / Flush Conditions

| Condition | Action | Stages Affected | Recovery |
|-----------|--------|----------------|----------|
| wdata_fifo 满 | Stall (暂停) | STG_SPI_RX (hold) | 下游取走后恢复 |
| cmd_fifo 满 | Stall (暂停) | STG_SPI_RX (hold) | 下游取走后恢复 |
| rdata_fifo 空 | Stall (暂停) | STG_SPI_TX (hold) | AXI 读数据返回后恢复 |
| AXI 从设备未就绪 | Wait (等待) | STG_AXI_TXN (hold) | AXI ready 拉高后恢复 |
| SPI 片选提前释放 | Flush (冲刷) | 所有 stage 清空 | 回到 IDLE |

**Stall 传播 (写路径)**:
```
AXI write backpressure ←─ STG_AXI_TXN hold ←─ STG_CDC_XFER hold ←─ STG_SPI_RX hold
```

### 5.4 Bypass Paths

SPI2AXI 没有传统流水线的数据旁路需求，因为事务为串行执行模式。但有以下优化路径：

| Bypass From | Bypass To | Condition | Latency Saved |
|-------------|-----------|-----------|---------------|
| AXI_RD → rdata_fifo | SPI_TX | AXI 读数据在 dummy 周期内返回 | 减少 SPI 读延迟 |
| cmd_fifo (直接路径) | AXI_TXN | FIFO 非空且 AXI 空闲 | 1~2 spi_sclk 周期 |

---

## 6. Datapath Specification

### 6.1 SPI 数据通路

#### 6.1.1 SPI 接收通路 (Serial → Parallel)

| 组件 | 宽度 | 功能 | 控制信号 |
|------|------|------|---------|
| `opcode_shift_reg` | 8-bit | 操作码串行移位接收 (MSB first) | `opcode_shift_en`, `opcode_rcvd` |
| `addr_shift_reg` | 32-bit | 地址串行移位接收 (MSB first) | `addr_shift_en`, `addr_rcvd` |
| `wdata_shift_reg` | 32-bit | 写数据串行移位接收 (MSB first) | `data_shift_en`, `data_rcvd` |

**移位逻辑**:
- 1-wire 模式: 每 spi_sclk 周期移位 1-bit (spi_sdi[0])
- 4-wire 模式: 每 spi_sclk 周期移位 4-bit (spi_sdi[3:0])
- 移位方向: MSB first (左移, LSB 输入新数据)

```systemverilog
// Shift register template (1-wire mode)
always_ff @(posedge spi_sclk or negedge spi_rst_n) begin
    if (!spi_rst_n)
        opcode_reg <= 8'b0;
    else if (opcode_shift_en)
        opcode_reg <= {opcode_reg[6:0], spi_sdi[0]};
end

// Shift register template (4-wire mode)
always_ff @(posedge spi_sclk or negedge spi_rst_n) begin
    if (!spi_rst_n)
        addr_reg <= 32'b0;
    else if (addr_shift_en_4w)
        addr_reg <= {addr_reg[27:0], spi_sdi[3:0]};
end
```

#### 6.1.2 SPI 发送通路 (Parallel → Serial)

| 组件 | 宽度 | 功能 | 控制信号 |
|------|------|------|---------|
| `rdata_shift_reg` | 32-bit | 读数据串行移位发送 (MSB first) | `rdata_shift_en`, `rdata_sent` |

**发送逻辑**:
- 从 rdata_fifo 读取 32-bit 数据，加载到移位寄存器
- 1-wire 模式: 每 spi_sclk 周期输出 1-bit (spi_sdo[0])
- 4-wire 模式: 每 spi_sclk 周期输出 4-bit (spi_sdo[3:0])
- 输出顺序: MSB first (先发送 bit 31, 最后 bit 0)

#### 6.1.3 SPI 操作码解码

| Opcode[7:0] (MSB first) | 操作类型 | 地址字段 | 地址宽度 | 描述 |
|-------------------------|---------|---------|---------|------|
| `0x02` | 写内存 | 32-bit 地址 | 32 | 标准 SPI 写内存 |
| `0x03` | 读内存 | 32-bit 地址 | 32 | 标准 SPI 读内存 |
| `0x42` | 写寄存器 | 操作码编码 | 0 | SPI CSR 写 |
| `0x43` | 读寄存器 | 操作码编码 | 0 | SPI CSR 读 |

> **注**: 操作码值需根据具体设计确定。上述为建议编码。QSPI 模式使用不同的操作码集。

### 6.2 Mux Select Encoding

| Mux Name | Select Width | Select Value | Source | Destination |
|----------|-------------|--------------|--------|-------------|
| `mux_addr_src` | 1 | 0: spi_addr_reg | axi_master_if (araddr/awaddr) | 内存访问地址 |
| | | 1: wrap_addr_out | | Wrap 计算后地址 |
| `mux_data_src` | 1 | 0: wdata_fifo_out | axi_w_data | AXI 写数据 |
| | | 1: csr_wr_data | | CSR 写 (未使用) |
| `mux_rdata_dest` | 1 | 0: rdata_fifo_out → spi_tx | spi_sdo | SPI 发送数据 |
| | | 1: rdata_fifo_out → csr_rd_data | CSR | CSR 读数据 (未使用) |

### 6.3 Datapath Widths

| Datapath Segment | Width | Rationale |
|-----------------|-------|-----------|
| SPI 串行输入 (1-wire) | 1 | 标准 SPI 单线数据输入 |
| SPI 串行输入 (4-wire) | 4 | QSPI 4 线数据输入 |
| SPI 串行输出 (1-wire) | 1 | 标准 SPI 单线数据输出 |
| SPI 串行输出 (4-wire) | 4 | QSPI 4 线数据输出 |
| 操作码寄存器 | 8 | 8-bit SPI 命令操作码 |
| 地址寄存器 | 32 | 32-bit AXI 地址 |
| 数据寄存器 | 32 | 32-bit AXI 数据 |
| cmd_fifo 宽度 | 40 | 32-bit addr + 3-bit opcode + 1-bit r/w + 4-bit 预留 |
| wdata_fifo 宽度 | 32 | 32-bit 写数据 |
| rdata_fifo 宽度 | 32 | 32-bit 读数据 |
| dummy 计数器 | 8 | 支持最大 255 个 dummy cycle |

### 6.4 Datapath RTL Implementation Template

```systemverilog
//=============================================================================
// Datapath: SPI Shift Register + Address Mux
//=============================================================================

// SPI 1-wire mode shift register for address
logic [31:0] addr_shift_reg;
always_ff @(posedge spi_sclk or negedge spi_rst_n) begin
    if (!spi_rst_n)
        addr_shift_reg <= 32'b0;
    else if (addr_shift_en)
        addr_shift_reg <= {addr_shift_reg[30:0], spi_sdi[0]};
end

// SPI 4-wire mode shift register for address
logic [31:0] addr_shift_reg_4w;
always_ff @(posedge spi_sclk or negedge spi_rst_n) begin
    if (!spi_rst_n)
        addr_shift_reg_4w <= 32'b0;
    else if (addr_shift_en_4w)
        addr_shift_reg_4w <= {addr_shift_reg_4w[27:0], spi_sdi[3:0]};
end

// Address Mux: SPI address vs Wrap address
always_comb begin
    unique case (wrap_en)
        1'b0: axi_addr = addr_captured;
        1'b1: axi_addr = wrap_addr_out;
    endcase
end

// SPI TX shift register (read data output)
logic [31:0] rdata_shift_reg;
always_ff @(posedge spi_sclk or negedge spi_rst_n) begin
    if (!spi_rst_n)
        rdata_shift_reg <= 32'b0;
    else if (rdata_load)
        rdata_shift_reg <= rdata_from_fifo;  // parallel load
    else if (rdata_shift_en_1w)
        rdata_shift_reg <= {rdata_shift_reg[30:0], 1'b0};
    else if (rdata_shift_en_4w)
        rdata_shift_reg <= {rdata_shift_reg[27:0], 4'b0};
end

// SPI output mux
always_comb begin
    if (spi_mode_1w) begin
        spi_sdo[0] = rdata_shift_reg[31];
        spi_sdo[3:1] = 3'b0;
    end else begin
        spi_sdo = rdata_shift_reg[31:28];
    end
end
```

---

## 7. CSR Register Map

### 7.1 Address Map Overview

SPI 侧配置寄存器，通过 SPI 操作码直接编址访问 (无需 32-bit 地址字段):

| Opcode | Register Name | Width | Attribute | Reset Value | Description |
|--------|---------------|-------|-----------|-------------|-------------|
| — | CTRL | 32 | RW | `0x0000_0000` | 控制寄存器 |
| — | STATUS | 32 | RO | `0x0000_0001` | 状态寄存器 |
| — | DUMMY_CFG | 32 | RW | `0x0000_0020` | 虚拟周期配置 |
| — | WRAP_CFG | 32 | RW | `0x0000_0000` | Wrap 配置寄存器 |
| — | FIFO_STATUS | 32 | RO | — | FIFO 状态寄存器 |

> **CSR 编码约定**: 未定义的操作码读返回 0，写忽略。防止非法地址访问导致功能异常。

### 7.2 Bit-Level Field Definitions

#### 7.2.1 CTRL — Control Register

| Bit Field | Bit(s) | Attribute | Reset | HW Set Condition | HW Clear Condition | Description |
|-----------|--------|-----------|-------|-------------------|-------------------|-------------|
| `mode_sel` | 0 | RW | 1'b0 | 软件写 1 | 软件写 0 | SPI 模式选择: 0=1-wire, 1=4-wire |
| `wrap_en` | 1 | RW | 1'b0 | 软件写 1 | 软件写 0 | Wrap 功能使能 |
| `soft_rst` | 2 | RW (自清除) | 1'b0 | 软件写 1 | 下一时钟自动清除 | 软复位 (自清除) |
| `reserved` | 31:3 | RES | 29'b0 | — | — | 读返回 0 |

> **Self-Clear Bit**: `soft_rst` 在置位后的下一个时钟周期自动清除（需要一个 HW clear 条件）。

#### 7.2.2 STATUS — Status Register

| Bit Field | Bit(s) | Attribute | Reset | HW Set Condition | HW Clear Condition | Description |
|-----------|--------|-----------|-------|-------------------|-------------------|-------------|
| `idle` | 0 | RO | 1'b1 | FSM → IDLE | FSM ≠ IDLE | 模块空闲中 |
| `busy` | 1 | RO | 1'b0 | FSM → OPCODE~AXI | FSM → IDLE | 模块忙碌中 |
| `done` | 2 | W1C | 1'b0 | FSM → DONE | 软件写 1 清除 | 事务完成 |
| `axi_error` | 3 | W1C | 1'b0 | AXI bresp/rresp != OKAY | 软件写 1 清除 | AXI 错误标志 |
| `reserved` | 31:4 | RES | 28'b0 | — | — | 读返回 0 |

> **W1C (Write-1-to-Clear)**: 软件向该位写 1 时清除；写 0 无影响。硬件设置优先级高于软件清除。

#### 7.2.3 DUMMY_CFG — Dummy Cycle Configuration

| Bit Field | Bit(s) | Attribute | Reset | Description |
|-----------|--------|-----------|-------|-------------|
| `dummy_cycles` | 7:0 | RW | 8'd32 | 虚拟周期配置值 (实际 Dummy = 此值 + 1) |
| `reserved` | 31:8 | RES | 24'b0 | 读返回 0 |

#### 7.2.4 WRAP_CFG — Wrap Configuration

| Bit Field | Bit(s) | Attribute | Reset | Description |
|-----------|--------|-----------|-------|-------------|
| `wrap_size` | 7:0 | RW | 8'd0 | Wrap 窗口大小 N (words), 0=disable, N=窗口大小 |
| `reserved` | 31:8 | RES | 24'b0 | 读返回 0 |

#### 7.2.5 FIFO_STATUS — FIFO Status

| Bit Field | Bit(s) | Attribute | Reset | HW Set Condition | HW Clear Condition | Description |
|-----------|--------|-----------|-------|-------------------|-------------------|-------------|
| `cmd_fifo_empty` | 0 | RO | 1'b1 | cmd_fifo empty | cmd_fifo not empty | 命令 FIFO 空标志 |
| `cmd_fifo_full` | 1 | RO | 1'b0 | cmd_fifo full | cmd_fifo not full | 命令 FIFO 满标志 |
| `wdata_fifo_empty` | 2 | RO | 1'b1 | wdata_fifo empty | wdata_fifo not empty | 写数据 FIFO 空标志 |
| `wdata_fifo_full` | 3 | RO | 1'b0 | wdata_fifo full | wdata_fifo not full | 写数据 FIFO 满标志 |
| `rdata_fifo_empty` | 4 | RO | 1'b1 | rdata_fifo empty | rdata_fifo not empty | 读数据 FIFO 空标志 |
| `rdata_fifo_full` | 5 | RO | 1'b0 | rdata_fifo full | rdata_fifo not full | 读数据 FIFO 满标志 |
| `reserved` | 31:6 | RES | 26'b0 | — | — | 读返回 0 |

### 7.3 CSR RTL Implementation Template

```systemverilog
//=============================================================================
// CSR Read/Write Logic (SPI Clock Domain)
//=============================================================================

// SPI CSR write decode
always_ff @(posedge spi_sclk or negedge spi_rst_n) begin
    if (!spi_rst_n) begin
        ctrl_reg      <= 32'b0;
        dummy_cfg_reg <= 32'h0000_0020;
        wrap_cfg_reg  <= 32'b0;
    end else if (csr_write_en) begin
        unique case (csr_addr)  // opcode-based addressing
            ADDR_CTRL:      ctrl_reg      <= csr_wr_data;
            ADDR_DUMMY_CFG: dummy_cfg_reg <= csr_wr_data;
            ADDR_WRAP_CFG:  wrap_cfg_reg  <= csr_wr_data;
            default: ;  // ignore reserved addresses
        endcase
    end
end

// CSR read mux (combinational)
always_comb begin
    unique case (csr_addr)
        ADDR_CTRL:       csr_rd_data = ctrl_reg;
        ADDR_STATUS:     csr_rd_data = status_reg;
        ADDR_DUMMY_CFG:  csr_rd_data = dummy_cfg_reg;
        ADDR_WRAP_CFG:   csr_rd_data = wrap_cfg_reg;
        ADDR_FIFO_STATUS: csr_rd_data = fifo_status_reg;
        default:         csr_rd_data = 32'b0;  // reserved → safe value
    endcase
end
```

### 7.4 UVM Register Model Alignment

| Register Name | UVM Register Name | Width | Access Policy |
|---------------|-------------------|-------|---------------|
| CTRL | `uvm_ctrl` | 32 | `UVM_REG` |
| STATUS | `uvm_status` | 32 | `UVM_RO` |
| DUMMY_CFG | `uvm_dummy_cfg` | 32 | `UVM_REG` |
| WRAP_CFG | `uvm_wrap_cfg` | 32 | `UVM_REG` |
| FIFO_STATUS | `uvm_fifo_status` | 32 | `UVM_RO` |

---

## 8. Clock & Reset Architecture

### 8.1 Clock Domains

| Domain Name | Source | Frequency | Divider | Duty Cycle | Jitter (pk-pk) |
|-------------|--------|-----------|---------|------------|----------------|
| `spi_sclk` | 外部 SPI 主机 | 50 MHz (max) | N/A | ~50/50 | 取决于 SPI 主机 |
| `axi_aclk` | SoC PLL | 待定 | 待定 | 50/50 | <100ps |

### 8.2 Clock Relationships

| Domain A | Domain B | Relationship | Synchronous? | CDC Method |
|----------|----------|--------------|-------------|------------|
| `spi_sclk` | `axi_aclk` | 无固定比例 | No | Dual-clock FIFO (格雷码指针) |
| `axi_aclk` | `spi_sclk` | 无固定比例 | No | Dual-clock FIFO (格雷码指针) |

### 8.3 CDC Paths

| Source Domain | Dest Domain | Signal(s) | Width | CDC Scheme | Latency |
|-------------|------------|-----------|-------|------------|---------|
| spi_sclk | axi_aclk | cmd_fifo 数据 | 40 | async FIFO (dual-clock) | 2~4 axi cycles |
| spi_sclk | axi_aclk | wdata_fifo 数据 | 32 | async FIFO (dual-clock) | 2~4 axi cycles |
| axi_aclk | spi_sclk | rdata_fifo 数据 | 32 | async FIFO (dual-clock) | 2~4 spi cycles |
| axi_aclk | spi_sclk | intr_o | 1 | 2-flop synchronizer | 2~3 spi cycles |

> **CDC FIFO 设计要点**:
> - 使用 dual-clock FIFO 内置的同步器（通常为两级或三级同步链）
> - 空/满标志的同步使用格雷码 (Gray Code) 指针
> - 防止亚稳态传播，保证跨时钟域数据传输的可靠性
> - cmd_fifo 和 wdata_fifo: 写时钟 = spi_sclk, 读时钟 = axi_aclk
> - rdata_fifo: 写时钟 = axi_aclk, 读时钟 = spi_sclk

### 8.4 Reset Architecture

| Reset Signal | Type | Domain | Assert | Deassert | Description |
|-------------|------|--------|--------|----------|-------------|
| `spi_rst_n` | Async, active-low | spi_sclk | async | synchronous | SPI 域复位输入 — 复位 SPI 接口逻辑、SPI 侧寄存器 |
| `axi_areset_n` | Async, active-low | axi_aclk | async | synchronous | AXI 域复位输入 — 复位 AXI 主接口、AXI 侧寄存器 |
| `spi_rst_sync_n` | Async, active-low | spi_sclk | async | sync to spi_sclk | SPI 域复位同步器输出 |
| `axi_rst_sync_n` | Async, active-low | axi_aclk | async | sync to axi_aclk | AXI 域复位同步器输出 |

```systemverilog
//=============================================================================
// Reset Synchronizer for SPI Clock Domain
//=============================================================================
// Async assert, synchronous deassert for spi_sclk domain
logic spi_rst_sync_r1, spi_rst_sync_n;
always_ff @(posedge spi_sclk or negedge spi_rst_n) begin
    if (!spi_rst_n) begin
        spi_rst_sync_r1 <= 1'b0;
        spi_rst_sync_n  <= 1'b0;
    end else begin
        spi_rst_sync_r1 <= 1'b1;
        spi_rst_sync_n  <= spi_rst_sync_r1;
    end
end

//=============================================================================
// Reset Synchronizer for AXI Clock Domain
//=============================================================================
logic axi_rst_sync_r1, axi_rst_sync_n;
always_ff @(posedge axi_aclk or negedge axi_areset_n) begin
    if (!axi_areset_n) begin
        axi_rst_sync_r1 <= 1'b0;
        axi_rst_sync_n  <= 1'b0;
    end else begin
        axi_rst_sync_r1 <= 1'b1;
        axi_rst_sync_n  <= axi_rst_sync_r1;
    end
end
```

---

## 9. Timing Constraints (SDC)

### 9.1 Master Clock Definitions

```tcl
#=============================================================================
# SDC: SPI2AXI Bridge Timing Constraints
#=============================================================================
# 文件: spi2axi.sdc
# 生成: chip-pipeline s7_timing_closure
# 工艺: <technology_node>
# 版本: V1.0

#---------------------------------------------------------------------------
# 1. Clock Definitions
#---------------------------------------------------------------------------

# SPI clock - provided by external SPI master (50 MHz)
create_clock -name spi_sclk -period 20.0 [get_ports spi_sclk]

# AXI clock - provided by SoC (assume 100 MHz, adjust as needed)
create_clock -name axi_aclk -period 10.0 [get_ports axi_aclk]

#---------------------------------------------------------------------------
# 2. Clock Groups (asynchronous)
#---------------------------------------------------------------------------

# SPI clock domain and AXI clock domain are asynchronous
set_clock_groups -asynchronous \
    -group [get_clocks spi_sclk] \
    -group [get_clocks axi_aclk]

#---------------------------------------------------------------------------
# 3. Input Delays (SPI interface)
#---------------------------------------------------------------------------

# SPI input signals relative to spi_sclk
set_input_delay -clock spi_sclk -max 5.0 [get_ports {spi_sdi[*] spi_cs}]
set_input_delay -clock spi_sclk -min 1.0 [get_ports {spi_sdi[*] spi_cs}]

# AXI input signals relative to axi_aclk
set_input_delay -clock axi_aclk -max 4.0 [get_ports {awready wready bresp bvalid bid arready rdata rresp rvalid rid}]
set_input_delay -clock axi_aclk -min 0.5 [get_ports {awready wready bresp bvalid bid arready rdata rresp rvalid rid}]

#---------------------------------------------------------------------------
# 4. Output Delays (SPI interface)
#---------------------------------------------------------------------------

# SPI output signals relative to spi_sclk
set_output_delay -clock spi_sclk -max 5.0 [get_ports {spi_sdo[*]}]
set_output_delay -clock spi_sclk -min 1.0 [get_ports {spi_sdo[*]}]

# AXI output signals relative to axi_aclk
set_output_delay -clock axi_aclk -max 4.0 [get_ports {awaddr awvalid awid awprot wdata wstrb wvalid bready araddr arvalid arid arprot rready}]
set_output_delay -clock axi_aclk -min 0.5 [get_ports {awaddr awvalid awid awprot wdata wstrb wvalid bready araddr arvalid arid arprot rready}]

#---------------------------------------------------------------------------
# 5. False Paths
#---------------------------------------------------------------------------

# CDC FIFO paths - covered by dual-clock FIFO synchronizers
set_false_path -from [get_clocks spi_sclk] -to [get_clocks axi_aclk]
set_false_path -from [get_clocks axi_aclk] -to [get_clocks spi_sclk]

# Async reset signals
set_false_path -from [get_ports spi_rst_n] -to [get_clocks axi_aclk]
set_false_path -from [get_ports axi_areset_n] -to [get_clocks spi_sclk]

# Async reset synchronizer input paths
set_false_path -from [get_ports spi_rst_n]
set_false_path -from [get_ports axi_areset_n]

# Interrupt output (no timing requirement)
set_false_path -to [get_ports intr_o]

#---------------------------------------------------------------------------
# 6. Multicycle Paths
#---------------------------------------------------------------------------

# CSR read path can take multiple cycles (if needed)
# set_multicycle_path -setup 2 -from [get_clocks spi_sclk] \
#     -to [get_pins <csr_regfile_reg>/D]

#---------------------------------------------------------------------------
# 7. Clock Transition / Load
#---------------------------------------------------------------------------

set_clock_transition -rise 0.1 [get_clocks spi_sclk]
set_clock_transition -fall 0.1 [get_clocks spi_sclk]
set_clock_transition -rise 0.1 [get_clocks axi_aclk]
set_clock_transition -fall 0.1 [get_clocks axi_aclk]

set_ideal_network [get_ports spi_rst_n]
set_ideal_network [get_ports axi_areset_n]
set_ideal_network [get_ports spi_sclk]
set_ideal_network [get_ports axi_aclk]

#---------------------------------------------------------------------------
# 8. Maximum Constraints
#---------------------------------------------------------------------------

set_max_fanout 20 [current_design]
set_max_transition 0.5 [current_design]
```

### 9.2 SDC Constraint Derivation Guide

| Constraint Type | Derivation Method | Typical Value |
|----------------|-------------------|---------------|
| `create_clock -name spi_sclk -period 20.0` | 1 / 50 MHz | 20.0 ns |
| `create_clock -name axi_aclk -period 10.0` | 1 / 100 MHz (假设值, 待确认) | 10.0 ns |
| `set_input_delay -max 5.0 (SPI)` | 0.5 × (Tcycle - board_delay) | 5.0 ns |
| `set_input_delay -min 1.0 (SPI)` | PCB 跟踪延迟 min | 1.0 ns |
| `set_false_path CDC` | 异步时钟域 | — |

---

## 10. Implementation Notes

### 10.1 Coding Style

| Rule | Requirement | Rationale |
|------|------------|-----------|
| **R10.1** | Use `always_ff @(posedge clk or negedge rst_n)` for sequential logic | 统一风格, 便于综合 |
| **R10.2** | Use `always_comb` for combinational logic (not `always @(*)`) | SystemVerilog 最佳实践 |
| **R10.3** | Non-blocking (`<=`) in sequential, blocking (`=`) in combinational | 竞争条件防范 |
| **R10.4** | No latches inferred (check synthesis report) | 组合逻辑必须覆盖所有 case |
| **R10.5** | `unique case` for one-hot muxes, `priority case` for priority encoders | 综合工具优化提示 |
| **R10.6** | No `for` loops with variable bounds | 综合必须可展开 |
| **R10.7** | No `initial` blocks in synthesizable code | 综合工具忽略 |
| **R10.8** | All flops must have a reset value | DFT 扫描链要求 |
| **R10.9** | All FSMs must decode unused states to safe state | 防止锁死 |
| **R10.10** | Separate SPI clock domain and AXI clock domain into separate always blocks | 跨时钟域分离 |

### 10.2 Module Parameterization

| Parameter | Default | Type | Description |
|-----------|---------|------|-------------|
| `AXI_ADDR_WIDTH` | 32 | int | AXI 地址总线宽度 |
| `AXI_DATA_WIDTH` | 32 | int | AXI 数据总线宽度 (AXI4-Lite 固定 32) |
| `AXI_ID_WIDTH` | 3 | int | AXI ID 信号宽度 |
| `DUMMY_CYCLES` | 32 | int | SPI 读操作虚拟周期数 (实际 = 此值 + 1) |
| `CMD_FIFO_DEPTH` | 4 | int | 命令 FIFO 深度 (power of 2) |
| `DATA_FIFO_DEPTH` | 8 | int | 数据 FIFO 深度 (power of 2) |
| `SPI_MODE_4W_EN` | 1 | bit | QSPI (4-wire) 使能 |

### 10.3 Synthesis Pragmas

```systemverilog
// Synthesis pragma conventions:
//
// synopsys full_case       - force all case items covered (use carefully)
// synopsys parallel_case   - force parallel mux (not priority)
// synopsys translate_off   - simulation-only code
// synopsys translate_on    - resume synthesis

// Example: exclude debug logic from synthesis
// synopsys translate_off
`ifdef VERILATOR
    logic [31:0] spi_debug_counter;
    always_ff @(posedge spi_sclk) begin
        if (spi_debug_en) spi_debug_counter <= spi_debug_counter + 1;
    end
`endif
// synopsys translate_on
```

### 10.4 Area / Speed Trade-offs

| Optimization | Technique | Area Impact | Timing Impact | When to Use |
|-------------|-----------|-------------|---------------|-------------|
| SPI mode mux | Shared shift reg for 1-wire/4-wire | -5% | 0 | Area constrained |
| Separate shift regs | Dedicated 1-wire/4-wire shift regs | +5% | +10% Fmax | Timing critical |
| FIFO depth tuning | Minimize FIFO depth to fit max transaction | -10% | 0 | Small area target |
| Clock gating | AND gate + latch on spi_sclk | -15% dynamic power | -2% Fmax | Low power modes |

---

## 11. Verification Guidance

### 11.1 Directed Test Scenarios

| Test ID | Scenario | Stimulus | Expected Behavior | Coverage Point |
|---------|----------|----------|-------------------|----------------|
| T01 | SPI 写寄存器 (1-wire) | 写操作码 + 32-bit 数据 | CSR 寄存器值更新, STATUS.idle=0→1 | CSR 写通路 |
| T02 | SPI 读寄存器 (1-wire) | 读操作码 + dummy + 读数据 | spi_sdo 输出寄存器值 | CSR 读通路 |
| T03 | SPI 写内存 (1-wire) | 写操作码 + 32-bit 地址 + 32-bit 数据 | AXI AW→W→B 事务完成 | AXI 写通路 |
| T04 | SPI 读内存 (1-wire) | 读操作码 + 32-bit 地址 + dummy | AXI AR→R, spi_sdo 输出读数据 | AXI 读通路 |
| T05 | QSPI 写内存 | 4-wire 模式下写内存 | 4-bit 并行传输, AXI 写完成 | QSPI 模式 |
| T06 | QSPI 读内存 | 4-wire 模式下读内存 | 4-bit 并行传输, 数据正确 | QSPI 模式 |
| T07 | Wrap 地址回绕 | Wrap=3 时连续写, 检查地址序列 | 地址序列: addr, addr+4, addr+8, addr, addr+4... | Wrap 功能 |
| T08 | CDC FIFO 满 | SPI 连续写, AXI 时钟较慢 | cmd_fifo/wdata_fifo 满, 反压生效 | FIFO 满行为 |
| T09 | Dummy Cycle 配置 | 配置不同的 DUMMY_CYCLES | 实际等待 = DUMMY_CYCLES + 1 | Dummy 可编程性 |
| T10 | SPI 模式切换 | 1-wire ↔ 4-wire 动态切换 | 模式切换后数据正确 | 模式切换 |
| T11 | AXI 错误响应 | AXI 从设备返回 SLVERR | STATUS.axi_error 置位, intr_o 有效 | AXI 错误处理 |
| T12 | SPI 片选异常释放 | 数据传输中 cs 提前释放 | 事务中止, 回到 IDLE, 无死锁 | 异常恢复 |
| T13 | 复位行为 | 复位断言, 检查各模块状态 | 所有寄存器复位, FSM→IDLE | 复位正确性 |
| T14 | 连续事务 | 背靠背 SPI 事务 | 事务间无数据污染, 正确衔接 | 事务连续性 |

### 11.2 Assertion Checkers

```systemverilog
//=============================================================================
// Formal Assertions (SVA)
//=============================================================================

// A1: FSM never enters reserved state
`ifdef FORMAL
    assert_fsm_safe: assert property (
        @(posedge spi_sclk) disable iff (!spi_rst_n)
        state_q inside {ST_IDLE, ST_OPCODE, ST_ADDR, ST_DUMMY,
                       ST_DATA, ST_AXI_WR, ST_AXI_RD, ST_DONE}
    );
`endif

// A2: AXI AWVALID should not be asserted without AWREADY handshake
assert_axi_aw_handshake: assert property (
    @(posedge axi_aclk) disable iff (!axi_areset_n)
    $rose(awvalid) |-> ##[1:10] awready
);

// A3: AXI ARVALID should not be asserted without ARREADY handshake
assert_axi_ar_handshake: assert property (
    @(posedge axi_aclk) disable iff (!axi_areset_n)
    $rose(arvalid) |-> ##[1:10] arready
);

// A4: FIFO should not overflow
assert_fifo_overflow: assert property (
    @(posedge spi_sclk) disable iff (!spi_rst_n)
    !(cmd_fifo_full && cmd_fifo_wr)
);

// A5: FIFO should not underflow
assert_fifo_underflow: assert property (
    @(posedge axi_aclk) disable iff (!axi_areset_n)
    !(cmd_fifo_empty && cmd_fifo_rd)
);

// A6: Data integrity check - write then read same address
assert_data_integrity: assert property (
    @(posedge axi_aclk) disable iff (!axi_areset_n)
    // Write data should match read data (simplified)
    (rvalid && rready) |-> (rresp inside {OKAY, SLVERR, DECERR})
);
```

### 11.3 Functional Coverage Points

| Cover Group | Cover Point | Description |
|-------------|-------------|-------------|
| `cg_fsm_all` | state_q | 所有 FSM 状态被覆盖 |
| `cg_fsm_trans` | $past(state_q) → state_q | 所有状态跳转被覆盖 |
| `cg_mode` | ctrl_reg[0] | SPI 1-wire / 4-wire 模式 |
| `cg_wrap` | wrap_en && wrap_size | 不同 Wrap 配置组合 |
| `cg_dummy` | dummy_cfg_reg[7:0] | 不同 Dummy 配置值 |
| `cg_axi_write` | awvalid && awready | AXI 写事务发生 |
| `cg_axi_read` | arvalid && arready | AXI 读事务发生 |
| `cg_axi_error` | bresp != OKAY || rresp != OKAY | AXI 错误发生 |
| `cg_fifo_full` | cmd_fifo_full || wdata_fifo_full || rdata_fifo_full | FIFO 满场景 |
| `cg_back2back` | 连续两次事务 | 背靠背 SPI 事务 |

---

## 12. DFT Requirements

### 12.1 Scan Chain Specification

| Scan Chain | Clock Domain | Flop Count | Chain Length | IO Pins |
|------------|-------------|------------|-------------|---------|
| chain_spi | spi_sclk | 待补充 | 待补充 | `scan_in_spi / scan_out_spi` |
| chain_axi | axi_aclk | 待补充 | 待补充 | `scan_in_axi / scan_out_axi` |

### 12.2 Test Mode Behavior

| Signal | Function Mode | Test Mode | Description |
|--------|--------------|-----------|-------------|
| `test_mode_i` | 0 | 1 | 全局测试模式使能 |
| `scan_enable_i` | 0 | 1 | 扫描移位使能 |
| `scan_in_spi` | — | data_in | SPI 域扫描链输入 |
| `scan_out_spi` | — | data_out | SPI 域扫描链输出 |
| `scan_in_axi` | — | data_in | AXI 域扫描链输入 |
| `scan_out_axi` | — | data_out | AXI 域扫描链输出 |

### 12.3 Test Mode Rules

- **TMR1**: 所有 FFs 必须是可扫描替换的 (scan flip-flop)
- **TMR2**: SPI 域时钟在测试模式下由 `test_clk_spi` 控制
- **TMR3**: AXI 域时钟在测试模式下由 `test_clk_axi` 控制
- **TMR4**: 异步复位在测试模式下必须被屏蔽 (`test_mode_i → rst_n mux`)
- **TMR5**: SPI 时钟域和 AXI 时钟域使用独立的扫描链 (异步时钟域)
- **TMR6**: 内部 CDC FIFO 在测试模式下应可旁路或透明

### 12.4 MBIST (if applicable)

| Memory Instance | BIST Controller | Test Algorithm | Redundancy |
|----------------|----------------|----------------|------------|
| cmd_fifo | `mbist_ctrl_cmd` | March C- | None |
| wdata_fifo | `mbist_ctrl_wdata` | March C- | None |
| rdata_fifo | `mbist_ctrl_rdata` | March C- | None |

### 12.5 JTAG / Boundary Scan

| Feature | Support | Description |
|---------|---------|-------------|
| IEEE 1149.1 | 依赖 SoC | SPI 接口信号可通过 JTAG 边界扫描访问 |
| IEEE 1500 | 依赖 SoC | Core wrapper for embedded cores |
| BYPASS instruction | 依赖 SoC | Bypass register for board-level test |

---

## 13. Delivery Checklist

### 13.1 Deliverable Files

| # | File | Description | Status | Reviewer |
|---|------|-------------|--------|----------|
| 1 | `spi2axi_top.v` | 顶层模块 (模块实例化和互联) | 待完成 | |
| 2 | `spi_slave_if.v` | SPI 从设备接口模块 | 待完成 | |
| 3 | `cdc_fifo.v` | 双时钟域 FIFO 模块 | 待完成 | |
| 4 | `axi_master_if.v` | AXI4-Lite 主接口模块 | 待完成 | |
| 5 | `wrap_addr_gen.v` | Wrap 地址生成器 | 待完成 | |
| 6 | `csr_regfile.v` | 配置寄存器文件 | 待完成 | |
| 7 | `fsm_ctrl.v` | 主状态机控制器 | 待完成 | |
| 8 | `spi2axi.sdc` | 时序约束文件 | 待完成 (框架已定义) | |
| 9 | `spi2axi_tb.v` | 模块级测试平台 | 待完成 | |
| 10 | `spi2axi_test_seq.v` | 测试序列定义 | 待完成 | |

### 13.2 Quality Gates

| Gate | Criteria | Entry | Exit |
|------|----------|-------|------|
| **G1: Lint Clean** | 0 errors, 0 warnings | RTL ready | Lint report |
| **G2: Simulation Pass** | All directed tests pass | Testbench ready | Test report |
| **G3: Synthesis Clean** | 0 DRC violations, no latch inferred | SDC + RTL ready | Area/timing report |
| **G4: DFT Ready** | Scan chain insertion verified | Synthesis done | DFT report |
| **G5: Timing Clean** | WNS >= 0 at target frequency | Physical data | STA report |

### 13.3 Format Requirements

| Deliverable | Format | Header Required | Reviewed By |
|-------------|--------|----------------|-------------|
| RTL source | Verilog/SystemVerilog (.v) | Yes (copyright + module header) | Design lead |
| SDC | Synopsys SDC (.sdc) | Yes (version + generation info) | PD engineer |
| Testbench | SystemVerilog (.v) | Yes | Verification lead |
| Report | Plain text (.rpt) | Yes (date + tool version) | Tech lead |

---

## 14. Revision History

| Version | Date | Author | Change Description | Reviewer |
|---------|------|--------|-------------------|----------|
| V0.1 | 2026-05-21 | — | 初稿 — Phase 3 Working, 从切片数据整理为 LLD 格式 | |

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| AXI | Advanced eXtensible Interface (ARM AMBA 总线协议) |
| CDC | Clock Domain Crossing (跨时钟域) |
| CSR | Control and Status Register (控制状态寄存器) |
| DFT | Design for Testability (可测试性设计) |
| Dummy Cycle | SPI 读操作中插入的虚拟等待周期 |
| FIFO | First-In First-Out (先进先出缓冲器) |
| FSM | Finite State Machine (有限状态机) |
| HLD | High-Level Design (架构设计) |
| LLD | Low-Level Design (微架构设计) |
| MBIST | Memory Built-In Self-Test (存储器内建自测试) |
| MSB | Most Significant Bit (最高有效位) |
| PPA | Performance, Power, Area (性能, 功耗, 面积) |
| QSPI | Quad SPI (四线 SPI) |
| SDC | Synopsys Design Constraints (时序约束) |
| SPI | Serial Peripheral Interface (串行外设接口) |
| STA | Static Timing Analysis (静态时序分析) |
| SVA | SystemVerilog Assertions (断言) |
| W1C | Write-1-to-Clear (写 1 清除寄存器属性) |
| WNS | Worst Negative Slack (最差负松弛) |
| Wrap | 地址环绕访问模式 |

## Appendix B: Reference Documents

| Document | Version | Source | Description |
|----------|---------|--------|-------------|
| SPI2AXI Architecture HLD | V1.0 | `spi2axi_bridge_arch.HLD.md` | 模块架构 HLD |
| AMBA AXI4-Lite Protocol Spec | ARM IHI 0022D | ARM | AXI4-Lite 协议标准 |
| SPI Block Guide V03.06 | Motorola | SPI 协议标准 |
| SPI2AXI Slice Data | V0.1 | `2.slice/*.md` | 切片分析数据 |

---

*本文档由 Chip Design Agent 生成 — SPI2AXI Bridge Micro-Architecture LLD V1.0*
