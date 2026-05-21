# 模块架构蓝图 — Architecture Blueprint (HLD)

> **模块名称:** SPI2AXI Bridge (spi2axi_bridge_top)
> **版本:** V1.0
> **日期:** 2026-05-21
> **状态:** Draft
> **Architecture Freeze:** <!-- YYYY-MM-DD -->
> **对应 LLD 文档:** `spi2axi_bridge_micro.LLD.md` (14 章节 AI-Executable 模板)

---

## 1. Module Overview

### 1.1 Module Identity
<!-- 区别于 LLD Ch1.1 (侧重实现细节), 此处聚焦架构级定位 -->

| 属性 | 值 |
|------|-----|
| 模块全名 | SPI2AXI Bridge (spi2axi_bridge_top) |
| 层次路径 | `soc.periph_bus.spi2axi_bridge` |
| 功能分类 | 接口桥接 (SPI Slave to AXI4-Lite Master) |
| 工艺节点 | 待补充 |
| 目标频率 | SPI: 50MHz / AXI: 取决于 SoC 系统时钟 |
| 供电电压 | 待补充 |

> **LLD 参考**: LLD Ch1.1 包含更详细的 PVT corner、面积、功耗目标

### 1.2 一句话摘要

SPI2AXI Bridge IP 是一个将 SPI 从设备（Slave）接口转换为 AXI4-Lite 主设备（Master）接口的桥接模块，允许外部 SPI 主机通过标准的 SPI 或 Quad-SPI（QSPI）总线协议，无需 SoC 内部 CPU 干预即可直接访问 AXI 总线上的存储器映射寄存器空间和外设，广泛用于 SoC 的系统调试、配置管理、固件更新以及芯片测试验证等场景。

### 1.3 功能目标
<!-- 该模块要实现的核心功能清单，4~6 条，每条以动词开头 -->

- **支持标准 SPI 和 Quad-SPI (QSPI) 双模协议**: 提供 1 线标准 SPI 和 4 线 QSPI 两种工作模式，通过 SPI 侧配置寄存器动态切换数据线宽度，适应不同引脚数和带宽需求的系统应用场景。
- **将 SPI 总线命令透明转换为 AXI4-Lite 总线事务**: 解析 SPI 主机发送的 8-bit 操作码和 32-bit 地址，生成对应的 AXI4-Lite 写地址/写数据/读地址通道事务，实现 SPI 协议到 AXI 协议的完整语义映射。
- **实现 SPI 时钟域到 AXI 时钟域的可靠跨时钟域数据传输**: 采用双时钟异步 FIFO（dual-clock async FIFO）架构，在 SPI 时钟域（最高 50MHz）和 AXI 系统时钟域之间提供具有格雷码指针同步的可靠 CDC 传输通道，确保跨时钟域数据的完整性和准确性。
- **支持可配置的地址环绕（Wrap）访问模式**: 提供软件可编程的地址环绕功能，Wrap=N 时以 N 个 32-bit 字（4×N 字节）为窗口进行地址回绕访问，适用于循环缓冲区或配置寄存器组的批量读取/写入操作。
- **提供 SPI 侧配置寄存器和状态反馈机制**: 通过 SPI 操作码编码的寄存器地址空间，支持 SPI 工作模式选择、传输状态查询、Wrap 参数配置等功能，使外部 SPI 主机能够完全控制桥接器的行为并获取当前状态信息。

### 1.4 非功能目标

| 维度 | 目标 | 测量条件 |
|------|------|---------|
| 性能 | 标准 SPI 模式峰值吞吐量 >= 6.25 MB/s (50MHz / 8bit-per-byte × 1-lane) | 连续 back-to-back 传输，无片选间隔 |
| 性能 | QSPI 模式峰值吞吐量 >= 25 MB/s (50MHz / 8bit-per-byte × 4-lane) | 连续 back-to-back 传输，4 线全双工 |
| 延迟 | SPI 命令到 AXI 事务发起延迟 <= 5 个 AXI 时钟周期 | 无 FIFO 竞争，AXI Slave 零等待响应 |
| 延迟 | SPI 读操作端到端延迟 <= DUMMY_CYCLES + 10 个 SPI 时钟周期 | 最小 Dummy Cycles 配置，AXI 读零等待 |
| 功耗 | 动态功耗 < 待补充 mW | 满载运行，典型工艺节点 |
| 面积 | 面积预算 < 待补充 kgates | 典型工艺节点，不含 FIFO SRAM |
| 可靠性 | 跨时钟域数据传输零误码 | 异步 FIFO 格雷码指针同步，CDC 路径 SVA 断言 |

### 1.5 Top-Level Port Groups Summary
<!-- 顶层端口按功能分组概要，详细信号列表见 §2.1 -->

| Port Group | Direction | Width | Clock Domain | Description |
|------------|-----------|-------|-------------|-------------|
| `spi_*` | in/out | 1~4 | spi_sclk | SPI 接口信号组：时钟、片选、数据输入/输出 |
| `axi_*` | in/out | 1~32 | axi_aclk | AXI4-Lite 五通道主设备接口信号组 |
| `clk_*` | input | 1 | — | 时钟输入组：spi_sclk, axi_aclk |
| `rst_*` | input | 1 | — | 异步复位输入组：spi_rst_n, axi_rst_n |
| `cfg_*` | input | 1~3 | axi_aclk | 配置参数输入组：AXI_ADDR_WIDTH, AXI_DATA_WIDTH, AXI_ID_WIDTH, DUMMY_CYCLES |

> **LLD 参考**: LLD Ch1.2 的 Top-Level Ports Summary 包含更详细的 I/O Pad 属性

### 1.6 功能边界
<!-- 明确什么在范围内、什么不在范围内，防止设计膨胀 -->

- **范围内**: SPI 标准模式（1-line）和 Quad-SPI 模式（4-line）的读写操作
- **范围内**: AXI4-Lite 五通道（AW/W/B/AR/R）协议转换与握手管理
- **范围内**: SPI 时钟域与 AXI 时钟域之间的异步 FIFO CDC 同步
- **范围内**: 可配置地址环绕（Wrap）功能的地址计算与边界检测
- **范围内**: SPI 侧配置寄存器的读写访问（操作码编码寄存器空间）
- **范围外**: AXI4-Full 协议支持（不支持 out-of-order 传输和可变突发长度）
- **范围外**: SPI 主设备（Master）模式 — 本模块仅作为 SPI Slave 工作
- **范围外**: 多 SPI 片选支持 — 仅支持单 SPI Slave 选择
- **范围外**: 中断输出机制 — 本模块为纯轮询/查询方式的状态反馈

---

## 2. 外部接口定义

### 2.1 顶层 I/O 列表

| 信号名 | 方向 | 位宽 | 类型 | 时钟域 | 复位域 | 描述 |
|--------|------|------|------|--------|--------|------|
| spi_sclk | input | 1 | 时钟 | — | — | SPI 串行时钟输入，由外部 SPI Master 提供，最高频率 50MHz |
| spi_cs_n | input | 1 | 片选 | spi_sclk | — | SPI 片选信号，低电平有效，为高时复位 SPI Slave 内部状态 |
| spi_sdi | input | 4 | 数据 | spi_sclk | spi_rst_n | SPI 串行数据输入，1 线模式使用 bit[0]，4 线模式使用 bit[3:0] |
| spi_sdo | output | 4 | 数据 | spi_sclk | spi_rst_n | SPI 串行数据输出，1 线模式使用 bit[0]，4 线模式使用 bit[3:0] |
| axi_aclk | input | 1 | 时钟 | — | — | AXI 系统时钟输入，由 SoC 时钟管理单元提供 |
| axi_rst_n | input | 1 | 复位 | axi_aclk | — | AXI 域异步复位，低电平有效，同步释放 |
| axi_awid | output | AXI_ID_WIDTH | 地址 | axi_aclk | axi_rst_n | AXI 写地址通道 ID |
| axi_awaddr | output | AXI_ADDR_WIDTH | 地址 | axi_aclk | axi_rst_n | AXI 写地址通道地址 |
| axi_awlen | output | 8 | 控制 | axi_aclk | axi_rst_n | AXI 突发长度，固定为 0 (single transfer) |
| axi_awsize | output | 3 | 控制 | axi_aclk | axi_rst_n | AXI 突发大小，固定为 2 (4 bytes) |
| axi_awburst | output | 2 | 控制 | axi_aclk | axi_rst_n | AXI 突发类型，固定为 INCR (Wrap 模式下由 wrap_ctrl 调整) |
| axi_awvalid | output | 1 | 握手 | axi_aclk | axi_rst_n | AXI 写地址有效 |
| axi_awready | input | 1 | 握手 | axi_aclk | — | AXI 写地址就绪 |
| axi_wdata | output | AXI_DATA_WIDTH | 数据 | axi_aclk | axi_rst_n | AXI 写数据 |
| axi_wstrb | output | AXI_DATA_WIDTH/8 | 数据 | axi_aclk | axi_rst_n | AXI 写选通，固定为全 1 |
| axi_wvalid | output | 1 | 握手 | axi_aclk | axi_rst_n | AXI 写数据有效 |
| axi_wready | input | 1 | 握手 | axi_aclk | — | AXI 写数据就绪 |
| axi_bid | input | AXI_ID_WIDTH | 响应 | axi_aclk | — | AXI 写响应 ID |
| axi_bresp | input | 2 | 响应 | axi_aclk | — | AXI 写响应：OKAY=2'b00, EXOKAY=2'b01, SLVERR=2'b10, DECERR=2'b11 |
| axi_bvalid | input | 1 | 握手 | axi_aclk | — | AXI 写响应有效 |
| axi_bready | output | 1 | 握手 | axi_aclk | axi_rst_n | AXI 写响应就绪 |
| axi_arid | output | AXI_ID_WIDTH | 地址 | axi_aclk | axi_rst_n | AXI 读地址通道 ID |
| axi_araddr | output | AXI_ADDR_WIDTH | 地址 | axi_aclk | axi_rst_n | AXI 读地址 |
| axi_arlen | output | 8 | 控制 | axi_aclk | axi_rst_n | AXI 读突发长度，固定为 0 |
| axi_arsize | output | 3 | 控制 | axi_aclk | axi_rst_n | AXI 读突发大小，固定为 2 |
| axi_arburst | output | 2 | 控制 | axi_aclk | axi_rst_n | AXI 读突发类型，固定为 INCR |
| axi_arvalid | output | 1 | 握手 | axi_aclk | axi_rst_n | AXI 读地址有效 |
| axi_arready | input | 1 | 握手 | axi_aclk | — | AXI 读地址就绪 |
| axi_rid | input | AXI_ID_WIDTH | 数据 | axi_aclk | — | AXI 读数据 ID |
| axi_rdata | input | AXI_DATA_WIDTH | 数据 | axi_aclk | — | AXI 读数据 |
| axi_rresp | input | 2 | 响应 | axi_aclk | — | AXI 读响应 |
| axi_rvalid | input | 1 | 握手 | axi_aclk | — | AXI 读数据有效 |
| axi_rready | output | 1 | 握手 | axi_aclk | axi_rst_n | AXI 读数据就绪 |

> **LLD 参考**: LLD Ch2.1 包含完整的 Port Signal Table (含 I/O Pad 属性)

### 2.2 配置接口

- **协议**: SPI Slave（标准 SPI / Quad-SPI）
- **接口类型**: 异步（与 AXI 时钟域无相位关系）
- **最大时钟频率**: 50 MHz (SPI sclk)
- **地址空间**: 通过 8-bit 操作码（opcode）编码的寄存器空间 + 32-bit 地址的存储器空间
- **寄存器深度**: 8 个 32-bit 寄存器（SPI 侧配置/状态寄存器）
- **传输时序规范**: SPI 模式 0（CPOL=0, CPHA=0），在 spi_sclk 上升沿采样数据，下降沿更新数据输出。片选信号 spi_cs_n 为低时启动一次传输，为高时终止传输并复位 Slave 内部状态。
- **Cycle-Level 时序**:
  - **写操作帧格式**: OPCODE(8-bit) + ADDR(32-bit) + DATA(32-bit) — 标准 SPI 模式下共需 72 个 SCLK 周期（1-line），QSPI 模式下共需 18 个 SCLK 周期（4-line）
  - **读操作帧格式**: OPCODE(8-bit) + ADDR(32-bit) + DUMMY(N+1 cycles) + DATA(32-bit) — Dummy 周期用于等待 AXI 读数据返回，实际 Dummy 周期数 = DUMMY_CYCLES 配置值 + 1

> **LLD 参考**: LLD Ch2.2.1 包含精确的 cycle-level 写时序波形图 (含 wait states 处理)

### 2.3 数据面接口

- **协议**: AXI4-Lite (Master)
- **数据位宽**: 32-bit (由 AXI_DATA_WIDTH 参数固定)
- **数据通道数**: 5 个独立通道（AW, W, B, AR, R）
- **最大突发长度**: 1 beat (AxLEN=0, AXI4-Lite 仅支持 single transfer)
- **Out-of-order**: 否（AXI4-Lite 不支持 out-of-order，且 ID 宽度仅用于标识）
- **关键时序要求**:
  - 写事务：AW 和 W 通道可以独立发起 valid，AXI Slave 必须在 B 通道返回写响应
  - 读事务：AR 通道发起读地址，AXI Slave 在 R 通道返回数据 + 响应
  - 地址通道必须等待 awready/arready 信号就绪后才能开始下一个地址传输
  - 写数据通道的 wdata 与写地址通道的 awaddr 在逻辑上关联，但时序上可独立握手

> **LLD 参考**: LLD Ch2.2.2 包含 valid/ready 握手的 cycle-level 时序波形图和背压行为分析

### 2.4 中断接口

本模块在架构层面**不包含**专用的中断输出端口。SPI2AXI Bridge 的设计目标是通过 SPI 总线提供同步的状态查询机制，SPI 主机通过读取 SPI 侧状态寄存器来获取传输完成或错误状态信息。这种轮询设计适用于系统调试和配置场景，避免了中断线在跨时钟域和跨芯片边界上的同步复杂性。若需要中断支持，建议在 SoC 级添加 GPIO 中断控制器模块，通过 AXI 读操作间接获取状态信息。

| 中断输出 | 类型 | 事件源 | 清除机制 |
|---------|------|--------|---------|
| intr_o | 无 | N/A | N/A — 本模块无中断输出，状态查询通过 SPI 读寄存器轮询实现 |

> **LLD 参考**: LLD Ch2.4 包含完整的中断事件表（触发类型、极性、聚合方式）

### 2.5 其他专用接口

SPI2AXI Bridge 不包含 MIPI、DDR、SerDes 等专用高速接口。所有功能由 SPI 接口（配置/数据面）和 AXI4-Lite 接口（数据面）两个标准数字接口完成。此外，模块接收来自 SoC 顶层的一组静态配置参数（见 §5.2 可配置参数表），这些参数通过 HDL 参数化方式在模块例化时确定，不通过运行时动态配置。

---

## 3. 顶层架构框图

### 3.1 模块内部结构
<!-- 子模块划分和互联关系 -->

```
+----------------------------------------------------------------------------------+
|                        spi2axi_bridge_top (SPI2AXI Bridge)                       |
|                                                                                  |
|  +-----------------+     +--------------+     +-----------------+               |
|  |                 |     |              |     |                 |               |
|  |   spi_slave     |---->| cmd_decoder  |---->|   axi_master     |---------->   |
|  |  SPI Slave I/F  |     |  Cmd FSM     |     | AXI4-Lite Master|  AXI Bus      |
|  |  1-line/4-line  |<----|              |<----|  5-channel      |<-----------   |
|  +--------+--------+     +------+-------+     +--------+--------+               |
|           |                     |                       |                        |
|           v                     v                       v                        |
|  +----------------------------------------------------------------------+        |
|  |                       async_fifo (Dual-Clock CDC)                    |        |
|  |  +-------------+  +-------------+  +-------------+  +-------------+  |        |
|  |  | Write Cmd   |  | Write Data  |  | Read Addr   |  | Read Data   |  |        |
|  |  | FIFO        |  | FIFO        |  | FIFO        |  | FIFO        |  |        |
|  |  |(SPI->AXI)   |  |(SPI->AXI)   |  |(SPI->AXI)   |  |(AXI->SPI)   |  |        |
|  |  +-------------+  +-------------+  +-------------+  +-------------+  |        |
|  +----------------------------------------------------------------------+        |
|           ^                        ^                                              |
|           |                        |                                              |
|  +--------+--------+     +--------+--------+                                    |
|  |   config_regs   |     |   wrap_ctrl     |                                    |
|  |  SPI Config/    |     |  Address Wrap   |                                    |
|  |  Status Regs    |     |  Controller     |                                    |
|  +-----------------+     +-----------------+                                    |
|                                                                                  |
|  +--------------------------------------------------------------------------+    |
|  |               Clock / Reset Synchronization Logic                         |    |
|  |  (spi_sclk domain + axi_aclk domain | async reset, sync deassertion)     |    |
|  +--------------------------------------------------------------------------+    |
+----------------------------------------------------------------------------------+

  SPI Master --> spi_sclk/spi_cs_n/spi_sdi --> spi_slave --> cmd_decoder --> async_fifo --> axi_master --> [AXI Bus / SoC]
         <-- spi_sdo <---------------------------- spi_slave <---- cmd_decoder <-- async_fifo <-- axi_master <-- [AXI Bus]
```

> **LLD 参考**: LLD Ch3.2 包含精确的子模块数据位宽, LLD Ch3.3 包含模块间信号连线表（信号名、方向、位宽、源/目标模块）

### 3.2 子模块职责

| 子模块 | 职责 | 关键设计考量 | 复杂度 | 对应 LLD 章节 |
|--------|------|-------------|--------|--------------|
| spi_slave | SPI 物理层接口：1线和4线模式串并/并串转换，SCLK 边沿采样控制，片选管理 | SPI 模式0时序，1线/4线动态切换，多bit数据线方向控制 | 中 | LLD Ch3, Ch2 |
| cmd_decoder | 命令解析 FSM：8-bit 操作码解码，帧格式控制(IDLE→OPCODE→ADDR→DUMMY→DATA→RESPONSE) | 状态编码优化，异常状态处理，超时检测 | 高 | LLD Ch4 |
| async_fifo | 跨时钟域 CDC 桥接：dual-clock 异步 FIFO，格雷码指针同步，空/满标志生成 | 格雷码跨时钟域同步，FIFO 深度匹配，避免 metastability | 高 | LLD Ch3, Ch8 |
| axi_master | AXI4-Lite 主设备接口：5 通道握手协议管理，地址/数据/响应处理 | 握手协议合规性，Wrap 地址注入，错误响应处理 | 中 | LLD Ch3, Ch2 |
| config_regs | SPI 侧寄存器文件：模式选择寄存器，状态寄存器，Wrap 配置寄存器 | 操作码地址编码，寄存器位域属性，复位值管理 | 低 | LLD Ch7 |
| wrap_ctrl | 地址环绕控制器：Wrap 计数，边界检测，地址回绕计算 | 起始地址对齐检查，Wrap 窗口边界判定，地址生成 | 低 | LLD Ch6, Ch10 |
| Clock/Reset | 时钟门控、复位同步器：异步复位同步释放，跨时钟域路径隔离 | 两级同步器实现，复位域交叉，CDC 路径 false path | 低 | LLD Ch8 |

### 3.3 模块间关键数据路径带宽

| 路径 | 协议 | 位宽 | 时钟域 | 理论带宽 | 备注 |
|------|------|------|--------|---------|------|
| SPI Master → spi_slave | SPI (1-line) | 1-bit serial | spi_sclk(50MHz) | 6.25 MB/s | 串行输入，入口 |
| SPI Master → spi_slave | QSPI (4-line) | 4-bit serial | spi_sclk(50MHz) | 25 MB/s | 串行输入，QSPI 模式 |
| spi_slave → async_fifo | 内部并行总线 | 32-bit | spi_sclk | 200 MB/s | 串并转换后并行写入 |
| async_fifo → axi_master | 内部并行总线 | 32-bit | axi_aclk | 取决于 AXI 频率 | CDC 后 AXI 侧读取 |
| axi_master → AXI Bus | AXI4-Lite | 32-bit | axi_aclk | 取决于 AXI 频率与 Slave 响应 | 出口，受 Slave 响应延迟影响 |
| AXI Bus → axi_master | AXI4-Lite | 32-bit | axi_aclk | 取决于 AXI 频率 | 读返回数据的入口 |
| async_fifo → spi_slave | 内部并行总线 | 32-bit | spi_sclk | 200 MB/s | 读返回数据写入 SPI TX FIFO |
| spi_slave → SPI Master | SPI (1-line/4-line) | 1~4-bit serial | spi_sclk(50MHz) | 6.25~25 MB/s | 串行输出，出口瓶颈 |

---

## 4. 数据流与控制流

### 4.1 数据流路径

SPI2AXI Bridge 的核心数据流分为写数据流和读数据流两条独立路径，分别对应 AXI 写事务和 AXI 读事务的完整生命周期。

**写数据流路径**:

```
[SPI Master] → spi_sdi → [spi_slave: 串并转换] → [cmd_decoder: 命令解析]
                                                        |
                                                        v
                                              +---------------------+
                                              |   async_fifo:       |
                                              |  Write Cmd FIFO     |◄── 写命令（opcode + addr）
                                              |  Write Data FIFO    |◄── 写数据（32-bit data word）
                                              +---------+-----------+
                                                        | (CDC: spi_sclk → axi_aclk)
                                                        v
                                              +---------------------+
                                              |   axi_master:       |
                                              |  AW Channel: awaddr |----► AXI Bus
                                              |  W Channel:  wdata  |----► AXI Bus
                                              |  B Channel:  bresp  |◄---- AXI Bus
                                              +---------------------+
```

写数据流详细步骤:
1. **数据接收**: SPI Master 通过 spi_sdi 线发送 8-bit 操作码（WRITE 类型），随后发送 32-bit 目标地址（MSB first），最后发送 32-bit 写数据（MSB first）。spi_slave 模块在 spi_sclk 上升沿逐位采样，完成串行到并行的格式转换。
2. **命令解析**: cmd_decoder 将接收到的完整帧（opcode + addr + data）解析为 AXI 写事务的控制信息，包括写地址、写数据和写选通信号。
3. **CDC 同步**: 解析后的写命令和写数据分别写入 async_fifo 中的 Write Cmd FIFO 和 Write Data FIFO，通过格雷码指针同步机制将数据从 spi_sclk 时钟域传递到 axi_aclk 时钟域。
4. **AXI 事务发起**: axi_master 从异步 FIFO 中读取写地址和写数据，通过 AW 通道发送 axi_awaddr（同时置位 axi_awvalid），通过 W 通道发送 axi_wdata（同时置位 axi_wvalid），等待 AXI Slave 的 awready 和 wready 握手确认。
5. **写响应处理**: AXI Slave 通过 B 通道返回 axi_bresp（OKAY/SLVERR/DECERR），axi_master 检测到 axi_bvalid 后完成写事务，错误响应码经 CDC 反馈到 SPI 侧状态寄存器。

**读数据流路径**:

```
[SPI Master] → spi_sdi → [spi_slave: 串并转换] → [cmd_decoder: 命令解析]
                                                        |
                                                        v
                                              +---------------------+
                                              |   async_fifo:       |
                                              |  Read Addr FIFO     |◄── 读命令（opcode + addr）
                                              +---------+-----------+
                                                        | (CDC: spi_sclk → axi_aclk)
                                                        v
                                              +---------------------+
                                              |   axi_master:       |
                                              |  AR Channel: araddr |----► AXI Bus
                                              |  R Channel:  rdata  |◄---- AXI Bus
                                              +---------+-----------+
                                                        | (CDC: axi_aclk → spi_sclk)
                                                        v
                                              +---------------------+
                                              |   async_fifo:       |
                                              |  Read Data FIFO     |──► [spi_slave: 并串转换] → spi_sdo
                                              +---------------------+
```

读数据流详细步骤:
1. **读命令接收**: SPI Master 发送 8-bit 读操作码和 32-bit 目标地址，spi_slave 完成串并转换，cmd_decoder 解析为读事务控制信息。
2. **Dummy 周期插入**: 在 ADDR 阶段完成后，cmd_decoder 进入 DUMMY 状态，插入可编程数量的虚拟 SCLK 周期（实际 Dummy 周期数 = DUMMY_CYCLES 配置值 + 1），用于等待 AXI 读数据通过 CDC FIFO 返回。
3. **CDC 同步（SPI→AXI）**: 读地址通过 async_fifo 中的 Read Addr FIFO 同步到 AXI 时钟域。
4. **AXI 读事务**: axi_master 通过 AR 通道发送 axi_araddr，等待 axi_arready 握手，然后等待 AXI Slave 通过 R 通道返回 axi_rdata 和 axi_rresp。
5. **CDC 同步（AXI→SPI）**: 读返回数据写入 async_fifo 中的 Read Data FIFO，从 axi_aclk 时钟域同步回 spi_sclk 时钟域。
6. **数据输出**: 在 DUMMY 周期结束后，spi_slave 从 Read Data FIFO 读取返回数据，通过并串转换将 32-bit 并行数据逐位（1线）或逐 nibble（4线）从 spi_sdo 输出。

> **LLD 参考**: LLD Ch5.2 包含流水线逐周期行为表（每级每周期 S/H/B/F 状态），LLD Ch5.3 包含 stall/hold/flush 条件及传播路径

**关键流水线阶段**:

| 阶段 | 操作 | 延迟(cycle) | 吞吐(per cycle) | 资源 |
|------|------|-------------|-----------------|------|
| SPI_IF | SPI 串行数据接收（串并转换） | 8(1-line)/2(4-line) per byte | 1/8(1-line) 或 1/2(4-line) byte | spi_slave 移位寄存器 |
| CMD_DEC | 命令解码 + 控制信号生成 | 1 | 1 命令 | cmd_decoder FSM |
| CDC_W | 写路径异步 FIFO 写入+同步 | 2~5 (可变) | 1 数据字/同步周期 | async_fifo 写端口 |
| AXI_AW | AXI 写地址通道握手 | 1~N (取决于 Slave) | 1 地址 | axi_master AW 通道 |
| AXI_W | AXI 写数据通道握手 | 1~N (取决于 Slave) | 1 数据字 | axi_master W 通道 |
| AXI_B | AXI 写响应等待 | 1~N (取决于 Slave) | 1 响应 | axi_master B 通道 |
| AXI_AR | AXI 读地址通道握手 | 1~N (取决于 Slave) | 1 地址 | axi_master AR 通道 |
| AXI_R | AXI 读数据接收 | 1~N (取决于 Slave) | 1 数据字 | axi_master R 通道 |
| CDC_R | 读路径异步 FIFO 同步 | 2~5 (可变) | 1 数据字/同步周期 | async_fifo 读端口 |
| SPI_DO | SPI 并行→串行数据输出 | 8(1-line)/2(4-line) per word | 1/8(1-line) 或 1/2(4-line) word | spi_slave 移位寄存器 |

### 4.2 控制流

SPI2AXI Bridge 的控制核心是 cmd_decoder 模块中的命令解码有限状态机（FSM），它管理从 SPI 命令接收到 AXI 事务完成的完整控制流程。

> **LLD 参考**: LLD Ch4 包含完整 FSM 规格 — 状态编码表(§4.1)、状态转移矩阵(§4.2)、输出译码表(§4.3)、SystemVerilog RTL 模板(§4.4)，包括未使用编码的安全解码策略

**主状态机状态迁移**:

```
                        +----------------------------------------------------------+
                        |                                                          |
                        v                                                          |
  [IDLE] --(spi_cs_n=0)---> [OPCODE] --(8-bit done)---> [ADDR] --(32-bit done)------+
                        |                    +------------------+                 |
                        |                    |   (mem access: RD/WR)              |
                        |                    v                                    |
                        |              +-------------+                           |
                        |              |  [DUMMY]    | (if read opcode)           |
                        |              | (N+1 cycles)|                           |
                        |              +------+------+                           |
                        |                     | (dummy done)                     |
                        |                     v                                  |
                        |              +-------------+                           |
                        |              |   [DATA]    | 32-bit data (MSB first)   |
                        |              +------+------+                           |
                        |                     | (data done)                      |
                        |                     v                                  |
                        |              +-------------+                           |
                        |              | [RESPONSE]  | AXI B/R channel response  |
                        |              +------+------+                           |
                        |                     | (resp done OR spi_cs_n=1)        |
                        |                     v                                  |
                        |                    [IDLE] <------------------------------+
                        |
                        |  (spi_cs_n=1 at any state) --> [IDLE] (abort)
                        |  (AXI slave error) --> [ERROR] --(spi_cs_n=1)--> [IDLE]
```

| 状态 | 描述 | 入口动作 | 出口条件 | 对应 LLD 状态编码 |
|------|------|---------|---------|-----------------|
| IDLE | 空闲等待，SPI Slave 已准备好接收新的传输 | 清除所有内部状态标志，复位位计数器 | spi_cs_n 变为低电平 | 待 LLD 定义 |
| OPCODE | 接收 8-bit 操作码，高位（MSB）先传输 | 使能 spi_sdi 移位寄存器，启动位计数 | 8-bit 操作码接收完成 | 待 LLD 定义 |
| ADDR | 接收 32-bit 目标地址，仅内存访问命令需要 | 使能地址移位寄存器，启动 32-bit 计数 | 32-bit 地址接收完成（REG_READ/REG_WRITE 跳过此状态） | 待 LLD 定义 |
| DUMMY | 插入可编程数量的虚拟 SCLK 周期，等待 AXI 读数据返回 | 启动 Dummy 周期计数器（配置值+1），SPI 数据输出保持高阻 | Dummy 周期计数完成或 AXI 读数据已就绪 | 待 LLD 定义 |
| DATA | 数据传输阶段，接收写数据或发送读数据 | 写操作：接收 32-bit 写数据；读操作：发送 32-bit 读数据 | 32-bit 数据传输完成 | 待 LLD 定义 |
| RESPONSE | 写响应处理或读操作完成确认 | 写操作：等待 AXI B 通道响应；读操作：确认 R 通道数据有效 | 响应接收完成或 spi_cs_n 拉高 | 待 LLD 定义 |
| ERROR | 错误状态，AXI Slave 返回错误响应 | 记录错误码到状态寄存器，终止当前传输 | spi_cs_n 拉高（片选结束）复位到 IDLE | 待 LLD 定义 |

### 4.3 反压与流控策略

SPI2AXI Bridge 作为 SPI Slave 到 AXI Master 的桥接器，其数据流控制面临两个异步时钟域之间的带宽匹配问题，需要有效的反压和流控机制来避免数据丢失。

- **反压传播路径**: 当 AXI Slave 响应延迟较高或 AXI 总线处于繁忙状态时，axi_master 的写响应返回延迟增加，导致 Write Data FIFO 和 Write Cmd FIFO 的消耗速率降低。FIFO 满标志信号反馈到 cmd_decoder，阻止 SPI 侧继续接收新的写命令和数据。在极端情况下，反压信号最终传播到 spi_slave 模块，SPI 主机将观察到 SDO 数据线上的状态变化或传输超时。完整的反压传播链为：AXI Slave 响应慢 → axi_master 握手延迟 → async_fifo 满 → cmd_decoder 暂停 → spi_slave 保持当前状态。

- **FIFO 水位管理**: async_fifo 中的每个 FIFO 实例都提供空（empty）和满（full）标志信号。读路径的 Read Data FIFO 在非空状态下通知 spi_slave 有数据可输出；写路径的 Write Data FIFO 在非满状态下允许 SPI 侧继续写入。建议 FIFO 深度配置为 4~8 个条目，以吸收短期的 AXI 总线延迟抖动，同时避免过大的面积开销。

- **Credit 机制**: 本模块不采用 credit 类型的流控机制。SPI 侧的传输是同步帧驱动的，每个 SPI 帧（由片选信号界定）对应一个完整的 AXI 事务。SPI 主机在发起传输前不需要预分配 credit，但需要在读操作中正确配置 DUMMY_CYCLES 参数以确保等待时间足够覆盖 AXI 读延迟。

- **超时机制**: 建议在 cmd_decoder 中添加 AXI 响应超时检测逻辑。当 cmd_decoder 在 DATA 或 RESPONSE 状态等待 AXI 侧反馈时，若超过预设的超时阈值（例如 1024 个 AXI 时钟周期）仍未收到响应，则触发超时错误，置位状态寄存器的超时错误标志位，并将 FSM 返回 IDLE 状态。

### 4.4 并发与冲突处理

- **多通道并发**: SPI2AXI Bridge 在任意时刻仅处理一个 SPI 命令/数据帧。这是由 SPI Slave 协议的单帧特性决定的——单个片选有效期内只能发起一个完整的操作序列。因此模块内部不存在多通道并发问题，cmd_decoder 在完成当前帧的所有状态迁移之前不会接收新的命令。

- **读写冲突**: 读写操作由 SPI 帧中的操作码区分，在时序上天然互斥。读操作和写操作不会在 SPI 协议层面同时发生。AXI 总线侧，axi_master 的 AR 通道和 AW 通道可以独立悬挂 outstanding 事务（AXI4-Lite 虽然不支持多 beat burst，但允许地址通道独立握手），但由于 cmd_decoder 是串行处理 SPI 帧的，AR 和 AW 通道不会同时被激活。

- **原子操作**: SPI2AXI Bridge 不提供硬件级的原子操作支持（如 read-modify-write）。对于需要原子访问的场景，建议在 SPI 主机侧软件实现互斥机制，或依赖 AXI Slave 端提供的硬件原子支持。

---

## 5. 主要特性与可配置参数

### 5.1 核心特性

| 特性类别 | 特性 | 详细描述 | 可选/必选 |
|---------|------|---------|----------|
| 协议支持 | 标准 SPI 模式（1-line） | 单条数据线 spi_sdi[0]/spi_sdo[0] 进行串行数据传输，每 SCLK 周期传输 1 bit | 必选 |
| 协议支持 | Quad-SPI 模式（4-line） | 四条数据线 spi_sdi[3:0]/spi_sdo[3:0] 并行传输，每 SCLK 周期传输 4 bit | 可选 |
| 协议支持 | AXI4-Lite Master | 5 通道独立握手，支持 single transfer (AxLEN=0, AxSIZE=2)，返回 OKAY/SLVERR/DECERR 响应 | 必选 |
| 数据模式 | MSB-first 传输 | SPI 命令帧（操作码、地址、数据）均以最高有效位（MSB）在先的顺序传输 | 必选 |
| 数据模式 | 写操作帧格式 | OPCODE(8-bit) + ADDR(32-bit) + DATA(32-bit) = 72 SCLK (1-line) / 18 SCLK (4-line) | 必选 |
| 数据模式 | 读操作帧格式 | OPCODE(8-bit) + ADDR(32-bit) + DUMMY(N+1) + DATA(32-bit) | 必选 |
| 错误处理 | AXI Slave 错误响应处理 | 检测 SLVERR 和 DECERR 响应码，记录到 SPI 侧状态寄存器 | 必选 |
| 错误处理 | SPI 传输异常终止 | spi_cs_n 在传输中途拉高 → FSM 立即回到 IDLE，丢弃当前帧 | 必选 |
| 调试能力 | SPI 侧状态寄存器查询 | 通过 SPI 读寄存器获取 FIFO 状态、传输状态、错误码 | 必选 |
| 低功耗 | 无数据时自动门控 | 当无 SPI 传输时，SPI 侧逻辑仅在 SCLK 跳变时活动 | 可选 |

### 5.2 可配置参数

| 参数名 | HDL 类型 | 默认值 | 取值范围 | 描述 | 影响 |
|--------|---------|--------|---------|------|------|
| `AXI_ADDR_WIDTH` | int | 32 | 12~64 | AXI 地址总线位宽，决定可寻址的 AXI 空间大小 | 面积↑·可寻址空间↑ |
| `AXI_DATA_WIDTH` | int | 32 | 32 (fixed) | AXI 数据总线位宽，当前固定为 32-bit (AXI4-Lite 标准宽度) | 固定 |
| `AXI_ID_WIDTH` | int | 3 | 1~8 | AXI ID 信号位宽，用于标识 AXI 事务来源 | 面积↑·标识能力↑ |
| `DUMMY_CYCLES` | int | 32 | 0~255 | SPI 读操作虚拟周期数，实际 Dummy 周期 = DUMMY_CYCLES + 1 | 延迟↑·AXI 读等待时间↑ |
| `FIFO_DEPTH` | int | 8 | 2~64 | 异步 FIFO 深度，以条目数为单位，每个条目 32-bit | 面积↑·反压容忍度↑ |
| `WRAP_ENABLE` | bit | 1 | 0/1 | 使能地址环绕功能，为 0 时 wrap_ctrl 输出直通 | 面积↓·功能↓ |
| `DEFAULT_WRAP` | int | 0 | 0~1024 | 默认环绕窗口大小（字数），0 表示无环绕 | — |
| `SPI_MODE` | int | 0 | 0~3 | SPI 模式选择（CPOL/CPHA 配置），当前固定为 Mode 0 | 固定 |

### 5.3 配置寄存器摘要

SPI2AXI Bridge 的配置寄存器通过 SPI 操作码进行地址编码，SPI 主机通过发送 REG_READ 和 REG_WRITE 操作码来访问这些寄存器。寄存器空间映射到操作码编码地址，不同于 AXI 存储器地址空间。

| 操作码 | 名称 | 属性 | 复位值 | 功能描述 |
|--------|------|------|--------|---------|
| 待 LLD 定义 | CTRL | RW | 0x0000_0000 | 控制寄存器：SPI 模式选择（1-line/4-line）、软复位、传输使能 |
| 待 LLD 定义 | STATUS | RO | 0x0000_0001 | 状态寄存器：FIFO 空/满标志、当前传输忙碌、错误标志、错误码 |
| 待 LLD 定义 | WRAP_CFG | RW | 0x0000_0000 | Wrap 配置寄存器：Wrap 使能、Wrap 窗口大小 N |
| 待 LLD 定义 | DUMMY_CFG | RW | 0x0000_0020 | Dummy 周期配置，写入 DUMMY_CYCLES 值 (默认 32) |
| 待 LLD 定义 | FIFO_STATUS | RO | 0x0000_0000 | FIFO 状态寄存器：各 FIFO 的填充等级、空/满标志 |
| 待 LLD 定义 | SCRATCH | RW | 0x0000_0000 | 调试暂存寄存器，可供软件读写测试通路完整性 |
| 待 LLD 定义 | VERSION | RO | 0x0000_0100 | 版本寄存器，标识 IP 版本号和修订信息 |

> **LLD 参考**: LLD Ch7 包含完整 bit-level CSR 映射 — 每位域的 offset/width/attribute/HW set-clear 条件/reset 值 (§7.2)，CSR RTL 实现模板 (§7.3)，以及 UVM 寄存器模型对齐表 (§7.4)

### 5.4 操作模式

| 模式 | 编码 | 描述 | 典型使用 |
|------|------|------|---------|
| Standard SPI | 0 | 标准 1-line SPI 模式，spi_sdi[0] 单线输入，spi_sdo[0] 单线输出 | 通用系统调试与配置，兼容大多数 SPI 主机 |
| Quad-SPI (QSPI) | 1 | 4-line SPI 模式，spi_sdi[3:0] 四线输入，spi_sdo[3:0] 四线输出 | 高速固件更新和批量数据传输 |
| Wrap 禁用 | 0 | 地址持续递增，无回绕行为，每笔 AXI 事务地址在上次基础上 +4 | 线性地址空间访问 |
| Wrap 使能 | 1 | 启用地址环绕，在配置的 N 字窗口内循环访问 | 循环缓冲区或寄存器组批量操作 |

---

## 6. 时钟、复位与电源架构

### 6.1 时钟域概述

SPI2AXI Bridge 包含两个完全异步的时钟域，它们之间没有固定的相位关系或频率比例要求。异步 FIFO（CDC 桥接器）是这两个时钟域之间的唯一数据交换通道。

| 时钟域 | 源 | 频率 | 目标模块 | 同步关系 |
|--------|------|------|---------|---------|
| `spi_sclk` | 外部 SPI Master | ≤ 50 MHz | spi_slave, cmd_decoder, config_regs, wrap_ctrl (SPI 侧) | 异步域，与 AXI 时钟无相位关系 |
| `axi_aclk` | SoC 时钟管理单元 | 取决于 SoC 设计 | axi_master, async_fifo (AXI 读端口) | 异步域，与 SPI 时钟无相位关系 |

SPI 时钟域（spi_sclk）由外部 SPI Master 提供，其频率和占空比由外部主机的时钟源决定，最高不超过 50MHz。由于 SPI 时钟来自芯片外部，在布局布线时需要考虑 ESD 保护电路和 I/O Pad 延迟对时钟路径的影响。AXI 时钟域（axi_aclk）由 SoC 系统时钟管理单元提供，其频率取决于 SoC 的整体时序预算和 AXI 总线的工作频率要求。两个时钟域之间的频率比值不确定——AXI 时钟可能比 SPI 时钟更快或更慢，因此异步 FIFO 的深度必须能够吸收最差情况下的时钟速率差异。

> **LLD 参考**: LLD Ch8.1 包含完整的时钟域定义（含抖动、占空比），LLD Ch8.3 包含跨时钟域 CDC 路径及同步方案表

### 6.2 复位结构

| 复位信号 | 类型 | 域 | 描述 |
|---------|------|-----|------|
| `spi_rst_n` | Async, active-low | spi_sclk | SPI 域异步复位输入，低有效，在 spi_sclk 域内同步释放 |
| `axi_rst_n` | Async, active-low | axi_aclk | AXI 域异步复位输入，低有效，在 axi_aclk 域内同步释放 |

复位采用经典的异步断言（asynchronous assert）和同步释放（synchronous deassertion）策略。每个时钟域拥有独立的复位输入信号 `*_rst_n`，该信号在对应的时钟域内经过两级同步器同步后产生本地复位信号。复位时所有 SPI 侧的 FSM、移位寄存器、FIFO 指针重置到初始状态（IDLE）；AXI 侧的所有通道状态寄存器、FIFO 读写指针重置到初始值。异步 FIFO 内部采用独立的复位逻辑，每个时钟域分别复位各自的读写指针和同步器状态。

> **LLD 参考**: LLD Ch8.4 包含复位同步器 SystemVerilog 实现模板

### 6.3 电源模式

SPI2AXI Bridge 作为一个小型桥接 IP，通常集成在 SoC 的 always-on 或 peripherals 电源域中。模块本身不包含独立的电源管理单元，其电源模式由 SoC 级电源管理单元（PMU）控制。

| 模式 | 描述 | 时钟状态 | 可唤醒 |
|------|------|---------|--------|
| Active | 全速运行状态，SPI 和 AXI 时钟均运行，桥接器正常工作 | 全部开启 | N/A |
| Idle | 无 SPI 传输的空闲状态，无数据流经过 CDC FIFO，FIFO 处于空状态 | 全部开启但无活动 | spi_cs_n 片选信号 |
| Sleep | 低功耗待机状态，模块时钟被 SoC 级门控关闭，桥接器不响应 SPI 请求 | 全部关闭 | 需要 SoC 级唤醒机制重新开启时钟 |

---

## 7. 性能/功耗/面积目标
### 7.1 性能目标

> **待补充** — 以下为估算值，需在实际工艺库下完成综合后更新。

| 指标 | 符号 | 目标值 | 条件 |
|------|------|--------|------|
| 工作频率 | Fmax_spi | ≥ 50 MHz | 典型工艺 corner |
| 工作频率 | Fmax_axi | ≥ 100 MHz | 典型工艺 corner |
| 峰值吞吐 | Tput_peak_spi | 6.25 MB/s (1-line) / 25 MB/s (4-line) | 连续 back-to-back 传输，零 AXI 等待 |
| 持续吞吐 | Tput_sust_spi | 预估为峰值的 60%~80% | 含操作码/地址/控制开销的持续传输 |
| 最小延迟 | Lat_min_read | DUMMY_CYCLES + ~10 SPI cycles | 无 FIFO 竞争，AXI 读立即返回 |
| 最大延迟 | Lat_max_read | DUMMY_CYCLES + ~100 SPI cycles | AXI 总线竞争 + FIFO 同步等待 |
| 命令解析延迟 | Lat_cmd_decode | 1 SPI clock cycle | 操作码解码组合逻辑延迟 |

### 7.2 功耗预算

> **待补充** — 需在选定工艺节点和综合后通过 PrimeTime PX 获取准确功耗数据。以下为架构级预估。

| 电源域 | 电压 | Active | Idle | Sleep | 占比 |
|--------|------|--------|------|-------|------|
| VDD_CORE | 待补充 | 待补充 mW | 待补充 uW | 待补充 uW | 待补充 % |
| **总计** | | **待补充 mW** | **待补充 uW** | **待补充 uW** | **100%** |

### 7.3 面积预算

> **待补充** — 需在选定工艺节点和综合后获取精确面积数据。以下为架构级预估。

| 模块 | 组合逻辑 | 时序逻辑 | SRAM | 总计 | 比例 |
|------|---------|---------|------|------|------|
| spi_slave | 待补充 gates | 待补充 gates | — | 待补充 kgates | 待补充 % |
| cmd_decoder | 待补充 gates | 待补充 gates | — | 待补充 kgates | 待补充 % |
| async_fifo (×4) | 待补充 gates | 待补充 gates | 待补充 kB | 待补充 kgates | 待补充 % |
| axi_master | 待补充 gates | 待补充 gates | — | 待补充 kgates | 待补充 % |
| config_regs | 待补充 gates | 待补充 gates | — | 待补充 kgates | 待补充 % |
| wrap_ctrl | 待补充 gates | 待补充 gates | — | 待补充 kgates | 待补充 % |
| Clock/Reset | 待补充 gates | 待补充 gates | — | 待补充 kgates | 待补充 % |
| **总计** | **待补充 gates** | **待补充 gates** | **待补充 kB** | **待补充 kgates** | **100%** |

---

## 8. 应用场景

> **LLD 参考**: LLD Ch1.3 包含模块特性清单, LLD Ch11.1 包含定向测试场景表

### 8.1 典型用例

**用例 1: SoC 系统调试和配置接口**

这是 SPI2AXI Bridge 最核心的应用场景。在 SoC 开发和调试阶段，外部调试主机（如 FPGA 开发板上的微控制器或 PC 上的 SPI 调试器）通过 SPI 总线连接到目标 SoC 的 SPI2AXI Bridge 模块，实现对 SoC 内部寄存器空间的非侵入式在线调试访问。

- **触发条件**: 外部调试主机通过 SPI 总线发起一次 AXI 寄存器访问请求。
- **数据量**: 1 个 32-bit 字（单次 AXI4-Lite transfer）。
- **操作序列**:
  1. 外部调试主机通过 SPI 发送 REG_WRITE 操作码，写入 SPI2AXI Bridge 的 CTRL 寄存器，配置 SPI 为 1-line 标准模式。
  2. 调试主机通过 SPI 发起 WRITE 操作：发送 WRITE 操作码 (8-bit) + 目标寄存器地址 (32-bit) + 写入数据 (32-bit)。
  3. SPI2AXI Bridge 解析命令，将 WRITE 操作转换为 AXI4-Lite 写事务（AW 和 W 通道），等待写响应。
  4. 调试主机通过 SPI 发起 READ 操作：发送 READ 操作码 (8-bit) + 目标寄存器地址 (32-bit)。
  5. 桥接器进入 DUMMY 状态（等待 AXI 读返回），完成后在 DATA 阶段通过 spi_sdo 返回目标寄存器的当前值（32-bit）。
  6. 调试主机验证读回值与预期一致，确认 SoC 寄存器配置正确。
- **退出条件**: SPI 主机拉高 spi_cs_n 终止传输。
- **关键要求**: 读操作端到端延迟可控（通过 DUMMY_CYCLES 参数调节），延迟确定性要求高。

**用例 2: 嵌入式系统固件批量更新**

在嵌入式系统的固件升级场景中，外部编程器通过 QSPI 4-line 高速模式向 SoC 的 Flash 或 SRAM 空间批量写入固件镜像数据。

- **触发条件**: 系统进入固件更新模式，外部编程器连接到 SPI2AXI 接口。
- **数据量**: 通常为数千至数兆字节（固件镜像大小）。
- **操作序列**:
  1. 外部编程器通过 SPI 发送 REG_WRITE，配置 CTRL 寄存器选择 QSPI 4-line 模式，配置 WRAP_CFG 为合适的窗口大小。
  2. 编程器连续发送 WRITE 帧，每帧包含 WRITE 操作码 + 目标地址 + 4 字节数据。
  3. 若地址跨越连续的 Flash 编程区域，可通过 Wrap 功能自动在循环缓冲区边界回绕。
  4. 每完成一帧写入，编程器可选择发送 REG_READ 查询 STATUS 寄存器，确认写响应状态（OKAY/SLVERR）。
  5. 所有数据写入完成后，编程器发送 REG_READ 读取 VERSION 或 SCRATCH 寄存器，验证桥接器功能完好。
- **退出条件**: 所有固件数据写入完成，编程器释放 SPI 总线。
- **关键要求**: QSPI 模式下达到 25 MB/s 的峰值吞吐量，支持连续帧之间快速切换（片选电平切换时间最小化）。

**用例 3: 芯片 ATE 测试中的配置通路验证**

在芯片量产测试的 ATE（Automatic Test Equipment）环节，SPI2AXI Bridge 可以作为测试配置通路，允许 ATE 通过少量的 SPI 测试引脚访问芯片内部的测试寄存器。

- **触发条件**: ATE 上电后通过 SPI 总线向 SPI2AXI Bridge 发送配置命令。
- **数据量**: 少量配置命令和状态反馈，每笔 1~4 字节。
- **操作序列**:
  1. ATE 通过 SPI 发送 REG_WRITE 配置 SPI2AXI 到 1-line 标准模式。
  2. ATE 发送 WRITE 操作向目标 AXI 测试寄存器写入测试模式配置。
  3. ATE 发送 READ 操作回读测试状态，验证芯片内部测试逻辑的状态。
- **退出条件**: 完成所有测试配置项。
- **关键要求**: SPI 引脚数最小化（仅需 4 个测试引脚：SCLK, CS, SDI, SDO），可靠性高，复位状态确定。

### 8.2 异常场景

- **SPI 传输中途片选异常拉高**: spi_cs_n 在传输中途被 SPI Master 拉高时（例如由电磁干扰或 SPI Master 异常引起），cmd_decoder FSM 立即从当前状态回到 IDLE，丢弃当前正在处理的不完整帧。SPI 侧移位寄存器和位计数器复位到初始值，等待下一次片选有效。已写入异步 FIFO 的数据将保留在 FIFO 中，由后续的新帧处理或由复位操作清空。
- **AXI Slave 响应错误 (SLVERR/DECERR)**: axi_master 在写响应通道 B 或读数据通道 R 检测到 AXI Slave 返回 SLVERR（从设备错误）或 DECERR（解码错误）时，将错误码锁存到内部寄存器，并通过 CDC 同步回 SPI 侧状态寄存器（STATUS 寄存器中的 error_code 字段）。SPI 主机在后续的 STATUS 寄存器查询中可读取到错误信息，决定是否重试。
- **SPI 写操作时 AXI Write Data FIFO 已满**: 当 AXI Slave 处理速度跟不上 SPI 写入速率时，Write Data FIFO 可能达到满状态。cmd_decoder 检测到 fifo_full 标志后暂停向 FIFO 写入，SPI 侧保持当前的 DATA 阶段状态。SPI Master 的 SCLK 将因 SPI Slave 无法采样下一个数据位而被拉伸（在标准 SPI 协议中 SPI Slave 无法拉伸 SCLK，此处 SPI Master 需在读 SDO 状态线检测到 FIFO 满标志后暂停发送）。建议在设计中增加 SDO 状态指示线功能，允许 SPI Master 通过额外的状态查询来判断传输进度。
- **非法操作码检测**: cmd_decoder 接收到未定义的操作码时，记录错误标识到 STATUS 寄存器的 error_code 字段，终止当前帧处理，等待片选释放后回到 IDLE 状态。非法操作码不会触发任何 AXI 事务。
- **软复位恢复**: 外部 SPI 主机可以随时通过 REG_WRITE 向 CTRL 寄存器写入软复位位（soft_rst=1）。该操作触发 cmd_decoder 在所有状态下回到 IDLE，异步 FIFO 的读写指针复位到初始位置，配置寄存器恢复到复位值。软复位不影响 axi_aclk 域的逻辑，axi_master 当前正在处理的 AXI 事务将在超时后由 AXI Slave 的默认响应处理逻辑处理。

### 8.3 使用限制
<!-- 本节内容为 **待补充** 估算值，需在详细设计阶段确认 -->

- **最大 outstanding 事务数**: 本模块最多支持 1 个 outstanding AXI 事务。由于 cmd_decoder 采用串行帧处理方式，在当前 SPI 帧完成（写响应收到或读数据返回）之前，不会发起新的 AXI 事务。这是由 SPI Slave 协议的单帧特性决定的设计约束。
- **不支持 unaligned 地址访问**: AXI4-Lite 配置为 AxSIZE=2（4 字节传输），所有 AXI 地址必须按 4 字节对齐。SPI 主机发送的 32-bit 地址中低 2 位会被忽略（内部强制对齐到 4 字节边界）。若需要字节级访问粒度，建议在 AXI 总线后端通过额外的桥接逻辑实现字节选通。
- **不支持动态修改 FIFO 深度**: 异步 FIFO 的深度通过 HDL 参数 `FIFO_DEPTH` 在例化时静态确定，运行时不可修改。FIFO 深度的选择需在综合前根据预期的 AXI 延迟特性和 SPI 传输速率进行权衡。
- **DUMMY_CYCLES 必须满足 AXI 读延迟要求**: SPI 读操作时，DUMMY_CYCLES 的配置值必须足够大，以覆盖最差情况下的 AXI 读返回延迟（含 CDC 同步时间、AXI 总线仲裁延迟、Slave 响应时间）。若 Dummy 周期不足，spi_slave 在 DATA 阶段将从空的 Read Data FIFO 中读出无效数据。软件应设置 DUMMY_CYCLES 值为最大预期 AXI 读延迟的 1.5~2 倍。
- **跨时钟域路径同步延迟**: SPI 时钟域到 AXI 时钟域经过异步 FIFO 的格雷码指针同步，每次同步过程需要 2~3 个目标时钟域的时钟周期。这是为了克服时钟域边界上的 metastability 风险而必需的延迟，在时序分析和 DUMMY_CYCLES 配置时需要计入。

> **LLD 参考**: LLD Ch8 (Clock & Reset), LLD Ch9 (SDC), LLD Ch12 (DFT) 包含时序约束、CDC、DFT 等约束的详细规格

---

## 9. 假设与约束

### 9.1 关键假设
<!-- 以下为 **待补充** 的关键假设项，需在实际项目启动时与系统组确认 -->

| # | 假设 | 影响 | 验证方式 |
|---|------|------|---------|
| A1 | SPI Master 发送的帧格式符合本模块规范：操作码(8-bit) + 地址(32-bit, 内存操作) + 可选虚拟周期 + 数据(32-bit) | 不符合规范的操作序列会导致命令解析错误，fifo 状态异常 | UVM 场景验证注入合法和非法帧格式 |
| A2 | 配置寄存器只能在 SPI 片选低电平期间由 SPI 主机通过 REG_READ/REG_WRITE 操作码访问 | 片选高电平时寄存器访问操作行为未定义 | Formal 断言检查寄存器访问时机 |
| A3 | AXI Slave 在合理时间内（< 1024 个 AXI 时钟周期）返回写响应和读数据 | AXI Slave 无响应将导致 cmd_decoder 超时并进入 ERROR 状态 | UVM 注入延迟响应，验证超时机制 |
| A4 | SPI 时钟速率不高于 50MHz | 超过 50MHz 可能因 I/O Pad 延迟和组合逻辑延迟导致采样时序违例 | STA 分析最差 corner |
| A5 | SPI 时钟与 AXI 时钟之间无固定的频率比例关系，且两个时钟在模块工作期间持续提供 | 时钟停止会导致异步 FIFO 的格雷码同步失效，模块功能异常 | 验证时钟门控和恢复场景 |
| A6 | AXI 总线地址空间中的目标 Slave 已经存在且可以被正常访问 | 访问不存在的地址将收到 DECERR 响应，被记录为错误 | UVM 错误注入验证 |
| A7 | SPI Master 在读操作时会提供足够的 Dummy 周期 | Dummy 周期不足会导致读数据返回不完整或取到无效数据 | 验证边界条件：DUMMY=0 和 DUMMY=min |

### 9.2 设计约束
**时序约束**:
- 输入延迟: max 5.0 ns from SPI I/O Pad to spi_slave module input (包含 ESD 和 PAD 延迟)
- 输出延迟: max 5.0 ns from spi_slave module output to SPI I/O Pad
- 异步路径: spi_sclk ↔ axi_aclk 之间的所有路径标记为 false path，通过异步 FIFO 的格雷码同步器处理
- AXI 接口时序: 遵循 AXI4-Lite 协议标准的 valid/ready 握手时序要求

**物理约束**:
- 面积约束: 模块总面积待补充 um²（取决于工艺节点和 FIFO 深度）
- 电源域: 同 SoC 逻辑核心电源域（VDD_CORE）
- 布局约束: 建议靠近 SoC 边界放置，缩短 SPI I/O Pad 到模块的距离，减少片外时序延迟

**工具约束**:
- 综合: 不使用 `synopsys_translate_off` 划分的关键代码，所有 RTL 代码的综合编译开关保持透明
- DFT: 所有时序单元（FF）需可扫描链插入，异步 FIFO 的格雷码指针寄存器的扫描链连接需特殊处理
- STA: 建立/保持时间需满足 50MHz (spi_sclk) 和最差 corner 下的 AXI 目标频率

### 9.3 外部依赖

| 依赖模块 | 依赖类型 | 接口 | 版本要求 | 风险 |
|---------|---------|------|---------|------|
| SoC AXI 总线矩阵 | 数据通路 | AXI4-Lite | 兼容 ARM AMBA 4 AXI4-Lite 规范 | 低 |
| SoC 时钟管理单元 (CMU) | 时钟 | axi_aclk | 频率 ≥ 预期最小值，占空比 50% ±5% | 低 |
| SPI I/O Pad | 物理接口 | SPI 信号 | 支持 3.3V/1.8V 电平标准，最高 50MHz 切换 | 中 |
| SoC 复位控制器 | 控制 | spi_rst_n, axi_rst_n | 异步低有效 | 低 |

### 9.4 开放问题
| # | 问题 | 影响域 | 建议方案 | 责任人 | 截止日期 |
|---|------|--------|---------|--------|---------|
| Q01 | 是否需要支持 SPI Mode 1/2/3（当前仅支持 Mode 0）？ | 功能/面积 | SPI Mode 作为可配置参数，综合前静态选择 | 待定 | 待定 |
| Q02 | AXI 时钟目标频率未定，影响 SDC 约束和 FIFO 深度设计 | 时序/验证 | 等待系统组确认 SoC 总线频率规划 | 待定 | 待定 |
| Q03 | FIFO 深度和类型选择——是否使用 SRAM 实现还是 register-based？ | 面积/功耗 | 小深度 (≤8) 用 register-based，大深度用 SRAM | 待定 | 待定 |
| Q04 | Wrap 功能是否需要支持动态修改 Wrap 窗口大小？ | 功能/控制 | 当前设计 WRAP_CFG 为 RW 寄存器，运行时可通过 SPI 修改 | 待定 | 待定 |

---

## 10. 设计决策记录 (Architecture Decision Record)
<!-- 记录关键的架构决策和权衡，供评审和后续查阅 -->

| ADR# | 决策 | 选项 | 选择理由 | 后果 | 日期 |
|------|------|------|---------|------|------|
| 001 | 选择 AXI4-Lite 而非 AXI4-Full | AXI4-Lite / AXI4-Full | SPI2AXI 面向 SoC 调试和配置场景，仅需要单 beat 传输和简单的地址/数据通道，AXI4-Lite 提供了足够的协议能力且实现复杂度远低于 AXI4-Full | 不支持突发传输和 out-of-order，但面积和验证工作量大幅减少 | 2026-05-21 |
| 002 | SPI 模式和 QSPI 模式复用同一组物理引脚 | 独立引脚 / 复用引脚 | 通过动态配置选择 1-line 或 4-line 模式，复用 spi_sdi[3:0] 和 spi_sdo[3:0] 引脚，避免了额外的引脚开销 | 4-line 模式下 1 线和 4 线功能互斥，必须在传输前通过寄存器配置 | 2026-05-21 |
| 003 | 命令解码 FSM 采用串行帧处理而非流水线预取 | 串行帧处理 / 流水线预取 | SPI 协议天然是按帧串行处理的，每个片选有效区间只传输一个命令帧，无需流水线预取；串行处理也简化了 AXI 事务管理 | 不支持连续帧的流水线并行处理，但设计复杂度大幅简化 | 2026-05-21 |
| 004 | 使用异步 FIFO 而非握手同步器做 CDC | 异步 FIFO / 双锁存器握手 / DMUX 同步 | 数据量较大（32-bit × 深度），异步 FIFO 的格雷码指针同步提供更高的吞吐能力和更低的同步延迟 | 需要额外的格雷码编码/解码逻辑和空满标志生成，面积略大于简单握手同步 | 2026-05-21 |

---

## 11. 验证特性映射指引

<!-- 本节的目的是: 设计团队从架构层面识别需要验证的特性，验证团队据此提取验证计划 -->

> **LLD 参考**: LLD Ch11 包含定向测试场景表(§11.1)、SVA 断言模板(§11.2)、功能覆盖率点(§11.3)

### 11.1 Feature 到验证项的映射

| # | 来源章节 | Feature | 设计侧验证关注点 | 验证侧验证方法 | 覆盖率目标 |
|---|---------|---------|----------------|---------------|-----------|
| F01 | §1.3 / §5.4 | 所有操作模式的功能正确性 (1-line SPI / 4-line QSPI) | 各模式下 SPI 数据传输正确性、模式切换、数据线方向控制 | UVM scoreboard 数据完整性检查 | 100% 模式 × 数据组合 |
| F02 | §1.3 / §5.2 / §5.3 | 所有 SPI 命令操作码的解析和执行 (READ/WRITE/REG_READ/REG_WRITE) | 每种操作码对应的 FSM 状态迁移、AXI 事务生成 | UVM 定向测试 + 随机测试 | 100% 操作码编码 |
| F03 | §2.1 / §2.2 / §2.3 | SPI 接口和 AXI 接口的协议时序合规性 | SPI Mode 0 上升沿采样/下降沿更新，AXI valid/ready 握手 | Formal assertion 检查时序协议 | 100% 协议规则覆盖 |
| F04 | §2.3 / §3.3 | AXI4-Lite 5 通道握手协议 | AW/W/B/AR/R 各通道的 valid/ready 交叉握手，无协议违例 | Formal assertion + UVM monitor | 100% 握手组合 |
| F05 | §3.1 / §4.1 / §6.1 | 跨时钟域数据传输完整性 (CDC) | SPI 域写入数据在 AXI 域正确读出，无数据丢失或损坏 | UVM 随机数据 + FIFO 满/空边界测试 | 100% CDC 路径 |
| F06 | §3.1 / §8.1 | 地址环绕功能 (Wrap=0, Wrap=N) | 地址计算正确性、N 字边界检测和回绕行为 | UVM 定向 + 随机地址测试 | 100% Wrap 配置 × 地址组合 |
| F07 | §2.2 / §5.3 | SPI 侧配置寄存器读写访问 | RW/RO 属性、复位值、位域访问 | UVM reg_model 后门/前门访问 | 100% 寄存器、100% 位域 |
| F08 | §4.2 / §8.2 | FSM 异常状态处理 (超时、非法 opcode、片选异常) | 每种错误场景下的 FSM 行为、错误码记录、恢复路径 | UVM error injection + Formal | 100% 错误码 × 状态组合 |
| F09 | §4.3 / §8.2 | 反压与流控 (FIFO 满/空处理) | FIFO full 时的写入阻止、FIFO empty 时的读出保护 | UVM 注入背压 + 边界测试 | 所有 FIFO 状态组合 |
| F10 | §7.1 / §4.2 | 性能指标验证 (延迟、吞吐量) | SPI 读操作 Dummy 周期数是否满足 AXI 读延迟要求 | UVM performance monitor | 吞吐 ≥ 6.25MB/s(SPI), 25MB/s(QSPI) |
| F11 | §8.2 | AXI Slave 错误响应处理 (SLVERR/DECERR) | 错误响应码的正确采样和状态寄存器更新 | UVM 注入 AXI 错误响应 | 100% 错误码类型 |
| F12 | §9.1 | 假设违例验证 | 每个关键假设被违反时模块的鲁棒性 | Formal / UVM injection | 每个假设被覆盖 |

### 11.2 无需验证的 Feature

- **测试专用通路 (scan_mode, mbist_mode 等)**: 由 DFT 团队的扫描链测试和 MBIST 验证覆盖，不在功能验证范围内。
- **纯组合逻辑的中间信号**: SPI 串并转换的组合逻辑输出、地址加法器的中间结果等，通过端到端数据完整性验证已间接覆盖。
- **异步 FIFO 内部格雷码指针编码/解码**: 作为成熟的 CDC 设计模式，格雷码 FIFO 的功能正确性通过异步 FIFO 的独立验证组件（VIP）覆盖，不在 SPI2AXI 功能验证中重复验证。

### 11.3 断言 (Assertion) 建议
<!-- 建议添加到 RTL 的关键断言 -->

- **接口协议断言**:
  - SPI 协议：spi_sclk 上升沿采样时 spi_sdi 数据稳定、spi_cs_n 高电平时 spi_sdo 输出高阻
  - AXI 协议：valid 信号置位后必须保持直到 ready 置位、awvalid/awready 与 wvalid/wready 之间的关系
  - AXI 写响应：bvalid 必须在 awready 和 wready 之后出现
- **状态机断言**:
  - FSM 状态编码 one-hot 检查（如果采用 one-hot 编码）
  - 非法状态检测：FSM 进入未定义状态时触发 error
  - 状态转移合法性：特定状态下只能接受特定输入条件
- **数据完整性断言**:
  - FIFO 空读：FIFO empty 时 rd_en 信号无效
  - FIFO 满写：FIFO full 时 wr_en 信号无效
  - SPI 写入数据与 AXI 写出数据一致性
- **安全断言**:
  - 关键寄存器（CTRL 等）只能在特定操作码下被修改
  - 复位后所有状态机必须在 IDLE 状态
  - FIFO 读写指针差不超过 FIFO 深度

---

## 附录 A: 术语表

| 术语 | 含义 |
|------|------|
| SPI | Serial Peripheral Interface — 串行外设接口 |
| QSPI | Quad Serial Peripheral Interface — 四线串行外设接口 |
| AXI | Advanced eXtensible Interface — ARM AMBA 高级可扩展接口 |
| AXI4-Lite | AXI4 轻量级版本，支持单次传输，无 out-of-order |
| CDC | Clock Domain Crossing — 跨时钟域传输 |
| FIFO | First-In First-Out — 先进先出缓冲器 |
| FSM | Finite State Machine — 有限状态机 |
| PPA | Performance, Power, Area — 性能、功耗、面积 |
| WC | Worst-Case (corner) — 最差工艺角 |
| MSB | Most Significant Bit — 最高有效位 |
| CSR | Control and Status Register — 控制和状态寄存器 |
| W1C | Write-1-to-Clear — 写 1 清除 |
| SLVERR | Slave Error — AXI 从设备错误 |
| DECERR | Decode Error — AXI 地址解码错误 |
| ATE | Automatic Test Equipment — 自动测试设备 |
| DFT | Design for Test — 可测试性设计 |
| MBIST | Memory Built-In Self-Test — 存储器内建自测试 |

## 附录 B: 参考文档

| 文档 | 版本 | 来源 | 说明 |
|------|------|------|------|
| SPI2AXI SPEC.pdf | Rev 1.0 | 产品规格书 | SPI2AXI IP 原始设计规格 |
| ARM AMBA AXI and ACE Protocol Specification | ARM IHI 0022E | ARM 官方 | AXI4/AXI4-Lite/AXI4-Stream 协议规范 |
| SPI2AXI Bridge Planning Report | V1.0 | 1.planning/ | 规划阶段输出文档 |
| SPI2AXI Bridge Slice Documents (14 files) | V1.0 | 2.slice/ | 切片分析阶段输出文档 |
| 03_block_arch.HLD.md Template | V1.0 | agents/template/ | 模块架构蓝图模板 |

---

*本文档由 Chip Design Agent 自动生成*
