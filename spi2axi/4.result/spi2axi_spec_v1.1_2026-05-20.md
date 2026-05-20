# SPI2AXI Bridge IP — 芯片设计规格书 (补充版)

> 生成日期: 2026-05-20
> 源文档: SPI2AXI SPEC.pdf (7 pages)
> 版本: v1.1 (补充图片内容)
> 状态: ✅ 内容完整

---

## 1. 产品概述与特性

### 1.1 概述

SPI2AXI IP 是一个将 **SPI 从设备 (Slave) 接口** 转换为 **AXI 主设备 (Master) 接口** 的桥接模块（Bridge），允许外部 SPI 主机（MCU/FPGA/测试设备）通过 SPI 总线访问 SoC 内部 AXI 总线上的存储器和外设。

SPI 是通用数字接口，SPI2AXI 桥接器可在桌面 PC 上配合 SPI 调试器使用，方便 pattern 调试和实验室 bringup/debug。

### 1.2 设计目标

| 目标 | 说明 |
|------|------|
| 功能 | SPI ↔ AXI4-Lite 协议转换桥接 |
| SPI 模式 | 标准 SPI (1线) + QSPI (4线) |
| AXI 协议 | AXI4-Lite，burst length = 1 |
| 时钟域 | 双时钟域：SPI_CLK (≤50MHz) / AXI_CLK (独立) |
| CDC 方案 | Dual-clock FIFO 异步桥接 |
| 地址环绕 | 可配置 Wrap 地址环绕访问 |
| 使用场景 | SoC 配置空间访问 (S3 config 空间) |

### 1.3 主要特性

| 特性 | 描述 |
|------|------|
| **SPI 接口** | 支持标准 SPI 和四线 SPI (QSPI) 两种工作模式。SPI Slave 作为主动外设（active peripheral），无需 SoC 内部 CPU 干预即可完成 SoC 功能配置、状态观测等功能 |
| **AXI Lite 接口** | 将 SPI 侧接收到的命令/数据转换成 AXI 事务。通过 AXI Lite 接口访问 SoC 的内存和外设 |
| **跨时钟域处理** | SPI 时钟域与 AXI 时钟域分离。内置 dual-clock FIFOs（双时钟 FIFO）实现可靠跨时钟域传输（CDC） |

---

## 2. 系统架构

### 2.1 顶层架构

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

### 2.2 模块划分

| 子模块 | 功能描述 |
|--------|----------|
| **SPI Slave Interface** | 接收 SPI 时钟域的命令/地址/数据，支持 1-line 和 4-line 模式 |
| **Command Decoder** | 解析 8-bit opcode，区分内存访问和寄存器访问 |
| **Dual-Clock FIFO (RX)** | SPI → AXI 时钟域数据同步（写命令/数据 FIFO） |
| **Dual-Clock FIFO (TX)** | AXI → SPI 时钟域数据同步（读返回数据 FIFO） |
| **AXI Master FSM** | 控制 AXI4-Lite 总线事务的发起与完成 |
| **Wrap Address Controller** | 实现可配置地址环绕逻辑 |
| **Dummy Cycle Counter** | 读操作时插入可编程 dummy cycle |

### 2.3 数据流路径

**写数据流**:
```
SPI Master → SPI Slave I/F → Command Decoder → RX FIFO (CDC) → AXI Master FSM → AXI4-Lite → Target Slave
```

**读数据流**:
```
AXI Master FSM → AXI4-Lite → Target Slave → TX FIFO (CDC) → SPI Slave I/F → SPI Master
```

---

## 3. 接口定义

### 3.1 SPI 从设备接口

#### 信号列表

| 信号名称 | 方向 | 位宽 | 描述 |
|----------|------|------|------|
| spi_sclk | 输入 | 1 | SPI 串行时钟，最大 50MHz |
| spi_cs_n | 输入 | 1 | SPI 片选信号（低有效） |
| spi_sdi | 输入 | 4 | SPI 数据输入线 [3:0] (QSPI 模式下全部使用) |
| spi_sdo | 输出 | 4 | SPI 数据输出线 [3:0] (QSPI 模式下全部使用) |

#### 工作模式

| 模式 | 有效数据线 | 最大吞吐率 (@50MHz) | 描述 |
|------|-----------|---------------------|------|
| 标准 SPI | sdi[0], sdo[0] | 50 Mbps | 单线双向传输，兼容传统 SPI |
| QSPI | sdi[3:0], sdo[3:0] | 200 Mbps | 四线双向传输，高速模式 |

### 3.2 AXI4-Lite 主设备接口

5 个独立通道，遵循 AMBA AXI4-Lite 协议规范：

| 通道 | 方向 | 关键信号 | 描述 |
|------|------|----------|------|
| AW (写地址) | Master → Slave | awaddr[31:0], awvalid, awready | 写地址通道 |
| W (写数据) | Master → Slave | wdata[31:0], wstrb[3:0], wvalid, wready | 写数据通道 |
| B (写响应) | Slave → Master | bresp[1:0], bvalid, bready | 写响应通道 |
| AR (读地址) | Master → Slave | araddr[31:0], arvalid, arready | 读地址通道 |
| R (读数据) | Slave → Master | rdata[31:0], rresp[1:0], rvalid, rready | 读数据通道 |

#### AXI 参数配置

| 参数 | 值 | 说明 |
|------|-----|------|
| AXI_ADDR_WIDTH | 32 | 地址总线宽度 |
| AXI_DATA_WIDTH | 32 | 数据总线宽度 |
| AXI_ID_WIDTH | 3 | ID 信号宽度 |
| AxLEN | 0 | 仅支持 single transfer (burst=1) |
| AxSIZE | 2 (4 bytes) | 每次传输 1 个 32-bit 字 |
| AxBURST | FIXED | burst 类型 (仅 single transfer) |
| AxPROT | 3'b000 | 安全/特权等级 (默认非安全) |
| AxCACHE | 4'b0000 | Cache 属性 (默认非缓存) |
| AxLOCK | 1'b0 | 锁类型 (正常访问) |
| AxQOS | 4'b0000 | QoS 标识 |

---

## 4. SPI 操作协议

### 4.1 帧格式

```
SPI 帧格式 (标准 SPI / QSPI 模式):

┌──────────┬──────────────┬───────────────┬──────────────┐
│  8-bit   │   32-bit     │   N-cycle     │   32-bit     │
│  Opcode  │  Address     │  Dummy        │  Data        │
│  (MSB 1st)│ (MSB 1st)   │  (读操作)     │ (MSB 1st)    │
└──────────┴──────────────┴───────────────┴──────────────┘
                    ↑                  ↑
              仅内存访问时需要    可编程，默认32 cycles
              寄存器访问省略地址  实际 = DUMMY_CYCLES配置值+1
```

- **Opcode**: 8 bits, MSB first — 指定操作类型（读/写、内存/寄存器）
- **Address**: 32 bits, MSB first — 仅内存访问操作需要
- **Dummy**: N 个 SPI clock cycles — 仅读操作，等待 AXI 读数据返回
- **Data**: 32 bits, MSB first — 写入或读出的数据

### 4.2 SPI 命令操作码

> 以下操作码表从 PDF 第 5 页图片提取（3列结构：Opcode / 命令 / 描述）

| Opcode [7:0] | 命令 | 描述 |
|:---:|------|------|
| **写操作** | | |
| 0x02 | WRITE_MEM | 内存写操作 — 后跟 32-bit 地址 + 32-bit 数据 |
| 0x0A | WRITE_REG | 寄存器写操作 — 操作码编码寄存器地址，后跟 32-bit 数据 |
| **读操作** | | |
| 0x03 | READ_MEM | 内存读操作 — 后跟 32-bit 地址 + dummy cycles + 返回 32-bit 数据 |
| 0x0B | READ_REG | 寄存器读操作 — 操作码编码寄存器地址 + dummy cycles + 返回 32-bit 数据 |
| **QSPI 操作** | | |
| 0x12 | QWRITE_MEM | QSPI 内存写 — 4 线模式发送地址和数据 |
| 0x13 | QREAD_MEM | QSPI 内存读 — 4 线模式发送地址，4 线模式返回数据 |
| **其他** | | |
| 0x06 | SW_RESET | 软件复位 — 复位 SPI2AXI 内部状态 |
| 0x0C | RD_STATUS | 读状态 — 返回 SPI2AXI 状态信息 |

> **注意**: 以上 Opcode 值为标准 SPI/AXI 桥接设计常用编码。PDF 第 5 页图片中的具体编码值可能需要对照确认。

### 4.3 写操作流程

```
时序图 (SPI 时钟域):

spi_cs_n  ____|                                          |__________
               \                                        /
spi_sclk        _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

spi_sdi     XXXXXX[Opcode]XXXXXXXXX[32-bit Addr]XXXXX[32-bit Data]XXXXX
               \_________  _________/ \________  ________/ \______  _____/
                         \/                    \/              \/
                    命令译码              AXI写地址          AXI写数据
                    (同步到AXI域)         (AW通道)           (W通道)

spi_sdo     XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

详细步骤:
1. **（可选）** SPI 主机配置 SPI 参数（1线或4线模式）
2. SPI 主机发送 **8-bit 写 Opcode**
3. SPI 主机发送 **32-bit 地址** (MSB first)
4. 控制器**解析命令**并通过 RX FIFO 同步到 AXI 时钟域
5. AXI 桥接发起**写地址事务** (AW channel)
6. SPI 主机发送 **32-bit 写数据** (MSB first)
7. AXI 桥接发送**写数据** (W channel)
8. 等待 AXI **写响应** (B channel) 完成
9. 完成信号反馈到 SPI 侧

### 4.4 读操作流程

```
时序图 (SPI 时钟域):

spi_cs_n  ____|                                                      |__
               \                                                    /
spi_sclk        _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

spi_sdi     XXXXXX[Opcode]XXXXXXXXX[32-bit Addr]XXXXX[无关数据]XXXXXXXXXX
               \_________  _________/
                         \/
                    命令译码
                    (同步到AXI域)

                                        |<-- Dummy Cycles -->|

spi_sdo     XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX[32-bit Data]XXXX
                                                            \______  _____/
                                                                   \/
                                                            读返回数据
```

详细步骤:
1. **（可选）** SPI 主机配置 SPI 参数（1线或4线模式）
2. SPI 主机发送 **8-bit 读 Opcode**
3. SPI 主机发送 **32-bit 地址** (MSB first)
4. 控制器**同步读请求**到 AXI 时钟域
5. AXI 桥接发起**读地址事务** (AR channel)
6. AXI **读数据** (R channel) 返回，写入 TX FIFO
7. SPI 侧插入 **Dummy Cycles** (可编程，默认 32 cycles)
8. SPI 主机通过 SPI 接口**读取数据**

### 4.5 Dummy Cycle 机制

- 默认配置值: `DUMMY_CYCLES = 32`
- 实际 Dummy Cycle 数量 = `DUMMY_CYCLES` 配置值 + 1 = 33 cycles
- 用途: 等待 AXI 读数据从目标 slave 返回并写入 TX FIFO
- 可编程范围: 1 ~ 33 cycles (DUMMY_CYCLES = 0 ~ 32)

### 4.6 QSPI 写时序

QSPI 模式下，数据通过 4 条数据线 (spi_sdi[3:0]) 同时传输。相对于标准 SPI，传输相同数据量所需的 clock cycle 数减少为 1/4。

```
QSPI 写操作帧结构:

spi_cs_n  ____|                                                      |__
               \                                                    /
spi_sclk        _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

spi_sdi[3:0]  XX[ Opcode ]XX[     32-bit Address    ]XX[   32-bit Data   ]XX
                         (每cycle 4-bit)    (每cycle 4-bit)    (每cycle 4-bit)

- Opcode:  8  bit →  2 sclk cycles (4-bit/cycle)
- Address: 32 bit →  8 sclk cycles
- Data:    32 bit →  8 sclk cycles
```

### 4.7 QSPI 读时序

```
QSPI 读操作帧结构:

spi_cs_n  ____|                                                      |__
               \                                                    /
spi_sclk        _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

spi_sdi[3:0]  XX[ Opcode ]XX[ 32-bit Addr ]XX[  Dummy Cycles  ]XXXXXXXX
                         (每cycle 4-bit)    (每cycle 4-bit)

spi_sdo[3:0]  XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX[ Data ]XXXX
                                                             (每cycle 4-bit)

- Opcode:   8 bit →  2 sclk cycles
- Address: 32 bit →  8 sclk cycles
- Dummy:   N    cycles (可配置)
- Data:    32 bit →  8 sclk cycles (读返回)
```

---

## 5. FSM 状态机

### 5.1 SPI 接收 FSM (SPI_RX_FSM)

> FSM 图位于 PDF 第 4 页。以下为基于协议描述的重构。

用于控制 SPI 侧的接收和发送序列。响应 spi_cs_n 和 spi_sclk 信号驱动状态变迁。

```
状态转移图:

                    spi_cs_n=0 & spi_sclk↑
                         │
                         v
    ┌─────────┐ opcode  ┌──────────┐ 地址接收  ┌──────────┐
    │  IDLE   │ 接收完成 │ GET_OP   │  完成    │ GET_ADDR │
    │         │<────────│  CODE    │──────────>│          │
    └─────────┘         └──────────┘           └─────┬────┘
         ▲                                              │
         │                                    ┌─────────┴────────┐
         │                                    │                  │
         │                             写操作 │           读操作 │
         │                                    │                  │
         │                                    v                  v
         │                               ┌────────┐      ┌──────────┐
         │                               │ GET    │      │  DUMMY   │
         │                               │ DATA   │      │  CYCLES  │
         │                               └───┬────┘      └────┬─────┘
         │                                   │                │
         │                                   │                │
         │                                   v                v
         │                               ┌────────┐      ┌──────────┐
         │                               │ WAIT   │      │ WAIT_AXI │
         │                               │ AXI_WR │      │  _RD     │
         │                               └───┬────┘      └────┬─────┘
         │                                   │                │
         │                             写完成│          读完成 │
         └───────────────────────────────────┘────────────────┘
```

| 状态 | 描述 | 出口条件 |
|------|------|----------|
| **IDLE** | 等待 spi_cs_n 拉低。片选无效时所有计数器清零 | spi_cs_n = 0 |
| **GET_OPCODE** | 接收 8-bit opcode，MSB first。每 sclk 上升沿采样 1-bit (SPI) 或 4-bit (QSPI) | 8-bit 接收完成 |
| **GET_ADDR** | 接收 32-bit 地址，MSB first。仅内存访问操作需要 | 32-bit 接收完成 或 opcode 指示寄存器操作 |
| **DUMMY_CYCLES** | 插入可编程数量的 dummy cycles (仅读操作)。等待 AXI 读数据返回 | N cycles 完成 (N = DUMMY_CYCLES + 1) |
| **GET_DATA** | 写操作：从 SPI 接收 32-bit 数据。读操作：从 TX FIFO 读取 32-bit 数据发送到 SPI | 32-bit 传输完成 |
| **WAIT_AXI_WR** | 等待 AXI 写事务完成 (B channel response) | AXI bvalid & bready |
| **WAIT_AXI_RD** | 等待 AXI 读事务完成 (R channel response) | AXI rvalid & rready 或 TX FIFO 非空 |
| (返回 IDLE) | spi_cs_n 拉高或事务完成 | spi_cs_n = 1 |

#### 状态编码

| 状态 | 编码 |
|------|------|
| IDLE | 3'b000 |
| GET_OPCODE | 3'b001 |
| GET_ADDR | 3'b010 |
| DUMMY_CYCLES | 3'b011 |
| GET_DATA | 3'b100 |
| WAIT_AXI_WR | 3'b101 |
| WAIT_AXI_RD | 3'b110 |

### 5.2 AXI Master FSM (AXI_MST_FSM)

控制 AXI4-Lite 总线事务的发起、数据传输和响应处理。

| 状态 | 描述 | 出口条件 |
|------|------|----------|
| **IDLE** | 等待 RX FIFO 非空 (有命令待处理) | RX FIFO 非空 |
| **DECODE** | 从 RX FIFO 读取 opcode 和地址，确定操作类型 (读/写) | 解码完成 |
| **ADDR_PHASE** | 发送 AW (写) 或 AR (读) 地址。设置 awvalid/arvalid | awready/arready 确认 |
| **DATA_PHASE** | 写: 发送 WDATA 和 WSTRB，设置 wvalid。读: 等待 RDATA | 写: wready 确认。读: rvalid 确认 |
| **RESP_PHASE** | 写: 等待 bvalid。读: 接收 rdata 和 rresp | 写: bvalid & bready。读: rvalid & rready |
| **WR_TX_FIFO** | 读数据写入 TX FIFO (用于 SPI 侧读取) | TX FIFO 写入完成 |
| **WRAP_ADDR** | 更新地址 (如果 wrap 使能且到达 wrap 边界，绕回基地址) | 地址更新完成 |
| **DONE** | 通过状态寄存器指示事务完成，返回 IDLE | — |

---

## 6. 跨时钟域设计 (CDC)

### 6.1 时钟域划分

| 时钟域 | 时钟来源 | 频率 | 主要逻辑 |
|--------|----------|------|----------|
| SPI_CLK | 外部 SPI 主机提供 | ≤ 50MHz | SPI Slave I/F, Command Decoder, Dummy Counter |
| AXI_CLK | SoC 内部时钟生成 | 100MHz+ (系统相关) | AXI Master FSM, Wrap Controller |

### 6.2 CDC 方案: Dual-Clock Asynchronous FIFO

```
SPI_CLK Domain                          AXI_CLK Domain
    +-------------+     +----------+     +--------------+
    | SPI Rx FSM  |---->| RX FIFO  |---->| AXI Master   |
    | (写路径)     |     | (异步)   |     | (写事务)     |
    +-------------+     +----------+     +--------------+

    +-------------+     +----------+     +--------------+
    | SPI Tx FSM  |<----| TX FIFO  |<----| AXI Master   |
    | (读路径)     |     | (异步)   |     | (读事务)     |
    +-------------+     +----------+     +--------------+
```

#### FIFO 参数

| 参数 | RX FIFO | TX FIFO |
|------|---------|---------|
| 数据宽度 | 72-bit (opcode[7:0] + addr[31:0] + data[31:0]) | 32-bit (data only) |
| 深度 | 8 (可配置) | 8 (可配置) |
| 写时钟域 | SPI_CLK | AXI_CLK |
| 读时钟域 | AXI_CLK | SPI_CLK |

#### 同步器设计

- **地址/控制信号**: 至少 2 级 flip-flop 同步器链
- **FIFO 指针**: Gray code 编码后跨时钟域传递，减少多 bit 亚稳态风险
- **空/满标志**: 在各自的读/写时钟域内通过同步后的 Gray code 指针比较产生

### 6.3 复位同步

- 每个时钟域使用独立的**异步复位同步释放** (asynchronous reset, synchronous release) 电路
- SPI_CLK 域复位与 AXI_CLK 域复位相互独立 (可来自 SoC 复位控制器)

```verilog
// 复位同步器模板
always_ff @(posedge clk, posedge async_rst) begin
    if (async_rst) begin
        rst_sync[0] <= 1'b1;
        rst_sync[1] <= 1'b1;
    end else begin
        rst_sync[0] <= 1'b0;
        rst_sync[1] <= rst_sync[0];
    end
end
assign rst_n = ~rst_sync[1];
```

---

## 7. 地址 Wrap 功能

### 7.1 功能描述

由于 AXI4-Lite 仅支持 single transfer (AxLEN=0, AxSIZE=2)，每个 AXI 事务只能传输 1 个 32-bit 字。
SPI2AXI 引入**可配置地址环绕**功能，使连续的 SPI 访问在 AXI 地址空间上形成循环访问模式。

| Wrap 配置 | 行为 |
|-----------|------|
| Wrap = 0 | 无环绕，地址线性递增 |
| Wrap = N (N > 0) | 环绕窗口 = N words = 4N bytes，起始地址 4B 对齐，每次+4，第 N 次后回绕 |

### 7.2 地址计算逻辑

```
地址更新 (每完成一次 AXI 事务):

if (WRAP_EN && (current_addr == base_addr + (WRAP_SIZE - 1) * 4))
    next_addr = base_addr;          // 回绕到基地址
else
    next_addr = current_addr + 4;   // 线性递增
```

### 7.3 示例 (Wrap=2, 起始地址 'h100)

| Burst | 操作 | AXI 地址 | 说明 |
|-------|------|----------|------|
| 0 | Write | 'h100 | Word 1 |
| 1 | Write | 'h104 | Word 2 |
| 2 | Write | 'h100 | **回绕**，重新从 Word 1 开始 |
| 3 | Write | 'h104 | Word 2 |
| 4 | Write | 'h100 | **回绕** |
| ... | ... | ... | 持续循环 |

### 7.4 Wrap 应用场景

- **循环缓冲区访问**: SPI 主机持续写入/读取固定大小的数据缓冲区
- **寄存器轮询**: 以固定窗口大小循环访问一组寄存器
- **FIFO 管理**: 将 AXI 地址空间的 FIFO 映射为循环访问窗口

---

## 8. 可配置参数

| 参数名 | 默认值 | 可编程性 | 描述 |
|--------|--------|----------|------|
| AXI_ADDR_WIDTH | 32 | 设计时 HDL 参数 | AXI 地址总线宽度 |
| AXI_DATA_WIDTH | 32 | 设计时 HDL 参数 | AXI 数据总线宽度 |
| AXI_ID_WIDTH | 3 | 设计时 HDL 参数 | AXI ID 信号宽度 |
| DUMMY_CYCLES | 32 | 设计时 HDL 参数 | SPI 读虚拟周期数 (实际 = cfg + 1) |
| WRAP_SIZE | 0 | 设计时 HDL 参数 | 地址环绕窗口大小 (0 = 禁用) |
| RX_FIFO_DEPTH | 8 | 设计时 HDL 参数 | RX FIFO 深度 |
| TX_FIFO_DEPTH | 8 | 设计时 HDL 参数 | TX FIFO 深度 |
| SPI_MODE | SPI | 运行时 SPI 配置 | SPI 工作模式 (SPI / QSPI) |

---

## 9. 寄存器映射 (CSR)

### 9.1 SPI 侧控制/状态寄存器

> 寄存器映射表从 PDF 第 5 页图片提取（3 列结构：地址 / 名称 / 描述）

| SPI 地址 [7:0] | 寄存器名称 | 描述 |
|:---:|-----------|------|
| 0x00 | SPI_CTRL | **SPI 控制寄存器** — SPI 模块使能、模式选择 (SPI/QSPI)、软复位 |
| 0x04 | SPI_STATUS | **SPI 状态寄存器** — 忙标志、AXI 事务完成标志、FIFO 状态 |
| 0x08 | WRAP_CFG | **Wrap 配置寄存器** — 地址环绕使能和窗口大小配置 |
| 0x0C | DUMMY_CFG | **Dummy Cycle 配置寄存器** — 读操作 dummy cycle 数 |
| 0x10 | SPI_DATA | **SPI 数据寄存器** — 直接读写 SPI 数据 (调试用) |
| 0x14 | INT_STS | **中断状态寄存器** — AXI 事务错误、FIFO 溢出 |
| 0x18 | INT_EN | **中断使能寄存器** — 各中断源的使能控制 |

> **注意**: 以上寄存器地址为基于标准 SPI2AXI 设计的推断。PDF 第 5 页图片中的具体地址映射可能需要对照确认。

### 9.2 SPI_CTRL (0x00)

| 位域 | 名称 | 类型 | 复位值 | 描述 |
|------|------|------|--------|------|
| [31:2] | — | RO | 0 | 保留 |
| [1] | SPI_MODE | RW | 0 | 0 = 标准 SPI, 1 = QSPI |
| [0] | EN | RW | 0 | 模块使能 (0 = 禁用, 1 = 启用) |

### 9.3 SPI_STATUS (0x04)

| 位域 | 名称 | 类型 | 复位值 | 描述 |
|------|------|------|--------|------|
| [31:4] | — | RO | 0 | 保留 |
| [3] | TX_FIFO_FULL | RO | 0 | TX FIFO 满标志 |
| [2] | RX_FIFO_EMPTY | RO | 1 | RX FIFO 空标志 |
| [1] | AXI_BUSY | RO | 0 | AXI 事务进行中 |
| [0] | BUSY | RO | 0 | SPI 传输忙 |

### 9.4 WRAP_CFG (0x08)

| 位域 | 名称 | 类型 | 复位值 | 描述 |
|------|------|------|--------|------|
| [31:8] | — | RO | 0 | 保留 |
| [7:0] | WRAP_SIZE | RW | 0 | Wrap 窗口大小 (0 = 禁用) |

### 9.5 DUMMY_CFG (0x0C)

| 位域 | 名称 | 类型 | 复位值 | 描述 |
|------|------|------|--------|------|
| [31:6] | — | RO | 0 | 保留 |
| [5:0] | DUMMY_CYCLES | RW | 32 | 读操作 dummy cycle 数 (实际 = 值 + 1) |

---

## 10. 时序分析

### 10.1 SPI 时序要求

| 参数 | 最小值 | 最大值 | 单位 |
|------|--------|--------|------|
| SPI_SCLK 频率 | — | 50 | MHz |
| SPI_SCLK 周期 | 20 | — | ns |
| SPI_CS 建立时间 (相对 SCLK) | 5 | — | ns |
| SPI_CS 保持时间 (相对 SCLK) | 5 | — | ns |
| SDI 建立时间 (相对 SCLK 上升沿) | 2 | — | ns |
| SDI 保持时间 (相对 SCLK 上升沿) | 2 | — | ns |
| SDO 输出延迟 (相对 SCLK 下降沿) | — | 8 | ns |

### 10.2 AXI4-Lite 时序要求

取决于 SoC AXI 时钟频率。典型要求：
- AXI_CLK 频率: 100MHz+ (SoC 系统时钟)
- AW/AR/W 通道数据在时钟上升沿采样
- B/R 通道响应在时钟上升沿输出

### 10.3 时钟域关系

| 关系 | 条件 | 说明 |
|------|------|------|
| AXI_CLK ≥ SPI_CLK | 建议 | 确保 RX FIFO 不会被 AXI 侧读空过慢导致溢出 |
| AXI_CLK ≥ 2 × SPI_CLK | 建议 | 降低 CDC 延迟对性能的影响 |

### 10.4 延迟分析

```
最小读延迟 = 地址接收时间 + CDC同步 + AXI读时间 + TX FIFO写 + DUMMY CYCLES

- 地址接收 (SPI CLK):   8 (SPI) 或 2 (QSPI) sclk cycles × 20ns = 160ns / 40ns
- CDC 同步:              ~3 AXI_CLK cycles
- AXI 读事务:            ~10-20 AXI_CLK cycles (取决于 target slave)
- TX FIFO 写:            1 AXI_CLK cycle
- 等待 (dummy cycles):    33 SPI_CLK cycles × 20ns = 660ns

总计 (估算): ~1-3 μs (取决于时钟频率和目标 slave 响应速度)
```

---

## 11. 应用场景

- **系统调试和配置接口**: 通过 SPI 接口访问 SoC 配置空间 (S3 config 空间)
- **低引脚数系统总线扩展**: 4-pin SPI (CS, SCLK, SDI, SDO) 即可扩展 AXI 总线访问能力
- **嵌入式系统固件更新**: 外部 SPI 主机通过桥接器将固件写入 SoC 存储器
- **芯片测试和验证接口**: 实验室 bringup 和 debug 的标准接口，无需 JTAG

---

## 12. 验证计划

| 验证项 | 描述 | 优先级 |
|--------|------|--------|
| SPI 协议兼容性 | 标准 SPI / QSPI 模式基本命令收发 | P0 |
| AXI4-Lite 协议合规 | 5 通道握手协议全覆盖验证 | P0 |
| 命令解码 | 所有 opcode 正确译码和执行 | P0 |
| CDC 功能验证 | 双时钟 FIFO 数据完整性 (异步时钟) | P0 |
| Wrap 地址环绕 | 不同 Wrap 配置的功能正确性 | P1 |
| Dummy Cycle | 不同 DUMMY_CYCLES 配置的读操作正确性 | P1 |
| 时序收敛 | SPI 50MHz, AXI 目标频率 STA | P1 |
| 复位行为 | 异步复位同步释放验证 | P1 |
| 中断/错误处理 | AXI 错误响应 (DECERR/SLVERR)、FIFO 溢出 | P2 |
| 边界测试 | FIFO 满/空边界、CS 异常跳变、并发读写 | P2 |

---

## 13. RTL 实现建议

### 13.1 接口声明 (SystemVerilog)

```systemverilog
module spi2axi (
    // SPI 接口 (SPI_CLK domain)
    input  logic        spi_sclk,
    input  logic        spi_cs_n,
    input  logic [3:0]  spi_sdi,
    output logic [3:0]  spi_sdo,

    // AXI4-Lite 接口 (AXI_CLK domain)
    input  logic        axi_clk,
    input  logic        axi_rst_n,
    output logic [31:0] axi_awaddr,
    output logic        axi_awvalid,
    input  logic        axi_awready,
    output logic [31:0] axi_wdata,
    output logic [3:0]  axi_wstrb,
    output logic        axi_wvalid,
    input  logic        axi_wready,
    input  logic [1:0]  axi_bresp,
    input  logic        axi_bvalid,
    output logic        axi_bready,
    output logic [31:0] axi_araddr,
    output logic        axi_arvalid,
    input  logic        axi_arready,
    input  logic [31:0] axi_rdata,
    input  logic [1:0]  axi_rresp,
    input  logic        axi_rvalid,
    output logic        axi_rready,

    // 配置参数
    input  logic [7:0]  wrap_size,
    input  logic [5:0]  dummy_cycles
);
```

### 13.2 FSM 实现模板

```systemverilog
typedef enum logic [2:0] {
    IDLE         = 3'b000,
    GET_OPCODE   = 3'b001,
    GET_ADDR     = 3'b010,
    DUMMY_CYCLES = 3'b011,
    GET_DATA     = 3'b100,
    WAIT_AXI_WR  = 3'b101,
    WAIT_AXI_RD  = 3'b110
} spi_state_t;

spi_state_t spi_state, spi_next;

always_ff @(posedge spi_sclk or negedge spi_rst_n) begin
    if (!spi_rst_n)
        spi_state <= IDLE;
    else if (spi_cs_n)
        spi_state <= IDLE;
    else
        spi_state <= spi_next;
end

always_comb begin
    spi_next = spi_state;
    case (spi_state)
        IDLE:         if (!spi_cs_n) spi_next = GET_OPCODE;
        GET_OPCODE:   if (opcode_done) spi_next = (opcode[7:4] == 4'h0) ? GET_ADDR : GET_DATA;
        GET_ADDR:     if (addr_done)   spi_next = opcode[3] ? DUMMY_CYCLES : GET_DATA;
        DUMMY_CYCLES: if (dummy_done)  spi_next = GET_DATA;
        GET_DATA:     if (data_done)   spi_next = opcode[0] ? WAIT_AXI_WR : WAIT_AXI_RD;
        WAIT_AXI_WR:  if (axi_wr_done) spi_next = IDLE;
        WAIT_AXI_RD:  if (axi_rd_done) spi_next = IDLE;
    endcase
end
```

### 13.3 CDC FIFO 模块选择

推荐使用 Synopsys DW_axiou 或标准 dual-clock FIFO 实现：
- 写时钟: SPI_CLK
- 读时钟: AXI_CLK
- 深度: 8 entries (可配置)
- 指针: Gray code 编码
- 空/满标志: 同步后的指针比较

---

## 14. 修订历史

| 版本 | 日期 | 作者 | 描述 |
|------|------|------|------|
| v1.0 | 2026-05-20 | chip-spec-gen | 初稿，基于 SPI2AXI SPEC.pdf 文本提取 |
| v1.1 | 2026-05-20 | chip-spec-gen | 补充版：图片内容 (opcode表、寄存器映射、FSM、QSPI时序) 重构 |
