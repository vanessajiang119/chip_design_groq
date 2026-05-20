# SPI2AXI Bridge — 模块架构蓝图 (HLD)

> **模块名称:** SPI2AXI Bridge
> **版本:** V2.0
> **日期:** 2026-05-20
> **状态:** Draft
> **对应 LLD 文档:** `04_block_micro.LLD.md`

---

## 1. Module Overview

### 1.1 Module Identity

| 属性 | 值 |
|------|-----|
| 模块全名 | SPI2AXI Bridge |
| 层次路径 | `top.chip.subsystem.spi2axi` |
| 功能分类 | 接口桥接 (Bridge IP) |
| 工艺节点 | N/A (RTL IP) |
| 目标频率 | SPI_CLK ≤ 50MHz, AXI_CLK ≥ 100MHz |
| 供电电压 | 取决于 SoC 集成 |

> **LLD 参考**: LLD Ch1.1 包含更详细的 PVT corner、面积、功耗目标

### 1.2 一句话摘要

SPI2AXI 是一个 SPI 从设备 (Slave) 到 AXI4-Lite 主设备 (Master) 的桥接模块，允许外部 SPI 主机通过 SPI 总线访问 SoC 内部 AXI 总线上的存储器和外设。

### 1.3 功能目标

- 支持标准 SPI (1线) 和 QSPI (4线) 两种工作模式
- 将 SPI 命令/地址/数据转换为 AXI4-Lite 总线事务
- 支持双时钟域异步 FIFO 实现可靠 CDC 传输
- 支持可配置地址环绕 (Address Wrap) 访问
- 支持读操作可编程 Dummy Cycle 插入

### 1.4 非功能目标

| 维度 | 目标 | 测量条件 |
|------|------|---------|
| 性能 | SPI 吞吐 ≥ 50Mbps (QSPI 模式) | 连续 back-to-back 传输 |
| 延迟 | AXI 读延迟 ≤ 32 dummy cycles 可配置 | 无竞争场景 |
| 面积 | < 50 kgates (预估) | 典型综合 |
| 可靠性 | CDC 路径使用 Gray-code + 2-flop 同步器 | 所有异步路径 |

### 1.5 Top-Level Port Groups Summary

| Port Group | Direction | Width | Clock Domain | Description |
|------------|-----------|-------|-------------|-------------|
| `spi_*` | in/out | 4 | SPI_CLK | SPI 从设备接口 (sclk, cs_n, sdi, sdo) |
| `axi_*` | in/out | 32+ | AXI_CLK | AXI4-Lite 主设备接口 (5 通道) |
| `clk_*` | input | 1 | — | 时钟输入 (spi_clk, axi_clk) |
| `rst_*` | input | 1 | — | 复位输入 |

> **LLD 参考**: LLD Ch1.2 的 Top-Level Ports Summary 包含更详细的 I/O Pad 属性

### 1.6 功能边界

- **范围内**: SPI Slave → AXI4-Lite Master 协议转换
- **范围内**: QSPI 4-line 模式、标准 SPI 1-line 模式
- **范围内**: 双时钟域异步 FIFO CDC
- **范围外**: AXI4-Full 协议支持 (仅 Lite)
- **范围外**: Burst 传输支持 (仅 single transfer, AxLEN=0)
- **范围外**: SPI Master 模式 (仅 Slave)

---

## 2. 外部接口定义

### 2.1 顶层 I/O 列表

| 信号名 | 方向 | 位宽 | 类型 | 时钟域 | 复位域 | 描述 |
|--------|------|------|------|--------|--------|------|
| spi_sclk | input | 1 | 时钟 | — | — | SPI 串行时钟，最大 50MHz |
| spi_cs_n | input | 1 | 数据 | spi_sclk | — | SPI 片选（低有效） |
| spi_sdi | input | 4 | 数据 | spi_sclk | — | SPI 数据输入 [3:0] (QSPI) |
| spi_sdo | output | 4 | 数据 | spi_sclk | — | SPI 数据输出 [3:0] (QSPI) |
| axi_clk | input | 1 | 时钟 | — | — | AXI 系统时钟，100MHz+ |
| axi_rst_n | input | 1 | 复位 | axi_clk | — | AXI 异步复位低有效 |
| axi_awaddr | output | 32 | 数据 | axi_clk | axi_rst_n | AXI 写地址 |
| axi_awvalid | output | 1 | 数据 | axi_clk | axi_rst_n | AXI 写地址有效 |
| axi_awready | input | 1 | 数据 | axi_clk | axi_rst_n | AXI 写地址就绪 |
| axi_wdata | output | 32 | 数据 | axi_clk | axi_rst_n | AXI 写数据 |
| axi_wstrb | output | 4 | 数据 | axi_clk | axi_rst_n | AXI 写选通 |
| axi_wvalid | output | 1 | 数据 | axi_clk | axi_rst_n | AXI 写数据有效 |
| axi_wready | input | 1 | 数据 | axi_clk | axi_rst_n | AXI 写数据就绪 |
| axi_bresp | input | 2 | 数据 | axi_clk | axi_rst_n | AXI 写响应 |
| axi_bvalid | input | 1 | 数据 | axi_clk | axi_rst_n | AXI 写响应有效 |
| axi_bready | output | 1 | 数据 | axi_clk | axi_rst_n | AXI 写响应就绪 |
| axi_araddr | output | 32 | 数据 | axi_clk | axi_rst_n | AXI 读地址 |
| axi_arvalid | output | 1 | 数据 | axi_clk | axi_rst_n | AXI 读地址有效 |
| axi_arready | input | 1 | 数据 | axi_clk | axi_rst_n | AXI 读地址就绪 |
| axi_rdata | input | 32 | 数据 | axi_clk | axi_rst_n | AXI 读数据 |
| axi_rresp | input | 2 | 数据 | axi_clk | axi_rst_n | AXI 读响应 |
| axi_rvalid | input | 1 | 数据 | axi_clk | axi_rst_n | AXI 读数据有效 |
| axi_rready | output | 1 | 数据 | axi_clk | axi_rst_n | AXI 读数据就绪 |

### 2.2 SPI 配置接口

- **协议**: SPI Slave (标准 SPI / QSPI)
- **接口类型**: 同步于 SPI_CLK
- **最大时钟频率**: 50MHz
- **数据宽度**: 1-bit (SPI) / 4-bit (QSPI)
- **传输时序**: Mode 0 (CPOL=0, CPHA=0)，上升沿采样，下降沿更新
- **帧格式**: [8-bit Opcode] + [32-bit Address] + [Dummy Cycles] + [32-bit Data]

> **LLD 参考**: LLD Ch2.2.1 包含精确的 cycle-level 写时序波形图

### 2.3 AXI4-Lite 数据面接口

- **协议**: AXI4-Lite (AMBA)
- **数据位宽**: 32-bit
- **突发长度**: 1 (single transfer, AxLEN=0)
- **地址宽度**: 32-bit
- **out-of-order**: 不支持
- **5 独立通道**: AW (写地址), W (写数据), B (写响应), AR (读地址), R (读数据)

> **LLD 参考**: LLD Ch2.2.2 包含 valid/ready 握手的 cycle-level 时序波形图

### 2.4 中断接口

本模块不带中断输出。状态通过 SPI Status Byte 返回。

### 2.5 其他专用接口

无。

---

## 3. 顶层架构框图

### 3.1 模块内部结构

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

### 3.2 子模块职责

| 子模块 | 职责 | 关键设计考量 | 复杂度 | 对应 LLD 章节 |
|--------|------|-------------|--------|--------------|
| SPI Slave Interface | 接收 SPI 串行命令/地址/数据，支持 1-line/4-line | 移位寄存器设计、位计数器 | 中 | LLD Ch3, Ch2 |
| Command Decoder | 解析 8-bit opcode，区分读/写操作 | opcode 编码表、控制路径 | 低 | LLD Ch3 |
| RX FIFO (Dual-Clock) | SPI→AXI 时钟域数据同步 | 异步 FIFO + Gray-code 指针 | 高 | LLD Ch8 |
| TX FIFO (Dual-Clock) | AXI→SPI 时钟域数据同步 | 异步 FIFO + Gray-code 指针 | 高 | LLD Ch8 |
| AXI Master FSM | 控制 AXI4-Lite 总线事务 | 5 通道握手协议、状态编码 | 高 | LLD Ch4 |
| Wrap Address Controller | 可配置地址环绕逻辑 | Wrap=N 窗口回绕计算 | 低 | LLD Ch6 |
| Dummy Cycle Counter | 读操作插入可编程 dummy cycle | 可配置 1~33 cycles | 低 | LLD Ch3 |

### 3.3 模块间关键数据路径带宽

| 路径 | 协议 | 位宽 | 时钟域 | 理论带宽 | 备注 |
|------|------|------|--------|---------|------|
| SPI I/F → RX FIFO | 内部并行总线 | 32 | SPI_CLK | 50Mbps (QSPI=200Mbps) | 入口 |
| RX FIFO → AXI Master | 内部 valid/ready | 64 | AXI_CLK | 取决于 AXI_CLK 频率 | CDC 路径 |
| AXI Master → AXI Slave | AXI4-Lite | 32 | AXI_CLK | 1 word/transaction | 瓶颈在 AXI 响应 |
| AXI Master → TX FIFO | 内部 valid/ready | 32 | AXI_CLK | 与 AXI_CLK 相同 | CDC 路径 |
| TX FIFO → SPI I/F | 内部并行总线 | 32 | SPI_CLK | SPI 串行速率 | 出口 |

---

## 4. 数据流与控制流

### 4.1 数据流路径

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

**数据流步骤**:
1. **命令接收**: SPI Slave I/F 接收 Opcode + Address，串行转并行
2. **命令译码**: Command Decoder 解析 opcode，路由到读/写路径
3. **CDC 同步**: 写命令通过 RX FIFO 同步到 AXI 域；读数据通过 TX FIFO 同步回 SPI 域
4. **AXI 事务**: AXI Master FSM 发起 AXI4-Lite 总线事务
5. **响应返回**: 写响应 BRESP 或读数据 RRESP 返回 SPI Master

> **LLD 参考**: LLD Ch5.2 包含流水线逐周期行为表

### 4.2 控制流

**主状态机**: 两个独立 FSM (SPI 接收 FSM + AXI Master FSM)

**SPI 接收 FSM 状态迁移**:
```
                    (CS 拉低)
   [IDLE] ──────────────► [PREP] ──► [OPCODE]
                      ^                 │ (8-bit 收完)
                      │                 ▼
                      │            [ADDR] ──► [DUMMY] ──► [DATA]
                      │              │        (读操作)      │ (32-bit 收完)
                      │              │                     ▼
                      │              └──(写操作)──────► [DONE]
                      │                                      │
                      └────── (CS 拉高) ◄─────────────────────┘
```

**AXI Master FSM 状态迁移**:
```
   [IDLE] ──► [WR_ADDR] ──► [WR_DATA] ──► [WR_RESP] ──► [IDLE]
      │                                                       ^
      └──► [RD_ADDR] ──► [RD_DATA] ──────────────────────────┘
```

| 状态 | 描述 | 入口动作 | 出口条件 | 对应 LLD 状态编码 |
|------|------|---------|---------|-----------------|
| IDLE | 等待 RX FIFO 非空/读请求 | — | rx_fifo 有数据或 read_request | `3'b000` |
| WR_ADDR | 发送 AW 通道地址 | awvalid=1, awaddr | awready==1 | `3'b001` |
| WR_DATA | 发送 W 通道数据 | wvalid=1, wdata | wready==1 | `3'b010` |
| WR_RESP | 等待 B 通道响应 | bready=1 | bvalid==1 | `3'b011` |
| RD_ADDR | 发送 AR 通道地址 | arvalid=1, araddr | arready==1 | `3'b100` |
| RD_DATA | 等待 R 通道数据 | rready=1 | rvalid==1 | `3'b101` |

> **LLD 参考**: LLD Ch4 包含完整 FSM 规格 — 状态编码表、状态转移矩阵、输出译码表

### 4.3 反压与流控策略

- **RX FIFO 满**: SPI 侧停止接收新命令 (等待 AXI 侧消费)
- **TX FIFO 空**: SPI 读数据阶段插入等待 (Dummy Cycle 已覆盖等待时间)
- **AXI 等待**: AXI Master FSM 在对应状态等待 ready/valid 信号

### 4.4 并发与冲突处理

- 不支持多通道并发 (SPI 单 master 单 slave 拓扑)
- 支持 Write-after-Read 顺序处理，无乱序

---

## 5. 主要特性与可配置参数

### 5.1 核心特性

| 特性类别 | 特性 | 详细描述 | 可选/必选 |
|---------|------|---------|----------|
| 协议支持 | SPI Slave | 标准 SPI + QSPI 模式，MSB-first | 必选 |
| 协议支持 | AXI4-Lite Master | 5 通道，single transfer | 必选 |
| 数据模式 | 全双工 SPI | 同时收发数据 | 必选 |
| 地址模式 | 地址环绕 (Wrap) | 可配置窗口大小 0~255 words | 可选 |
| CDC | 双时钟异步 FIFO | Gray-code 指针 + 2-flop 同步 | 必选 |
| 时序 | 可编程 Dummy Cycle | 1~33 cycles | 可选 |
| SPI 模式 | 4 种 CPOL/CPHA | 所有模式支持 | 可选 |

### 5.2 可配置参数

| 参数名 | HDL 类型 | 默认值 | 取值范围 | 描述 | 影响 |
|--------|---------|--------|---------|------|------|
| AXI_ADDR_WIDTH | int | 32 | 32 | AXI 地址总线宽度 | 固定 |
| AXI_DATA_WIDTH | int | 32 | 32 | AXI 数据总线宽度 | 固定 |
| AXI_ID_WIDTH | int | 3 | 1~8 | AXI ID 信号宽度 | 面积↑ |
| RX_FIFO_DEPTH | int | 8 | 4~64 | RX FIFO 深度 | 面积↑·反压↓ |
| TX_FIFO_DEPTH | int | 8 | 4~64 | TX FIFO 深度 | 面积↑·反压↓ |
| SPI_CPOL | bit | 0 | 0/1 | SPI 时钟极性 | 设计时固定 |
| SPI_CPHA | bit | 0 | 0/1 | SPI 时钟相位 | 设计时固定 |
| DUMMY_CYCLES | int | 32 | 1~63 | 读操作默认 dummy cycles | 性能↓ |

### 5.3 配置寄存器摘要

| 偏移 | 名称 | 属性 | 复位值 | 功能描述 |
|------|------|------|--------|---------|
| 0x00 | SPI_CTRL | RW | 0x0000_0000 | SPI 控制寄存器 (SPI_EN, QSPI_EN) |
| 0x04 | SPI_STATUS | RO/W1C | 0x0000_0001 | 状态寄存器 (READY, BUSY, SLVERR, TIMEOUT) |
| 0x08 | WRAP_CFG | RW | 0x0000_0000 | 地址环绕配置 (WRAP_SIZE) |
| 0x0C | DUMMY_CFG | RW | 0x0000_0020 | Dummy cycle 配置 (DUMMY_CYCLES) |
| 0x10 | SPI_DATA | RW | 0x0000_0000 | SPI 数据直通寄存器 |

> **LLD 参考**: LLD Ch7 包含完整 bit-level CSR 映射

### 5.4 操作模式

| 模式 | 编码 | 描述 | 典型使用 |
|------|------|------|---------|
| 标准 SPI | CPOL=0, CPHA=0 | 1-line 双向传输 | 默认模式 |
| QSPI | QSPI_EN=1 | 4-line 双向传输，4x 吞吐量 | 高速配置访问 |
| Wrap | WRAP_SIZE>0 | 地址环绕访问 | Config 空间循环访问 |

---

## 6. 时钟、复位与电源架构

### 6.1 时钟域概述

| 时钟域 | 源 | 频率 | 目标模块 | 同步关系 |
|--------|------|------|---------|---------|
| SPI_CLK | 外部 SPI Master | ≤ 50MHz | SPI Slave I/F, Command Decoder, Dummy Counter | 独立 (异步) |
| AXI_CLK | SoC PLL | ≥ 100MHz | AXI Master FSM, Wrap Controller | 主系统时钟 |

> **LLD 参考**: LLD Ch8.1 包含完整的时钟域定义，LLD Ch8.3 包含 CDC 路径及同步方案表

### 6.2 复位结构

| 复位信号 | 类型 | 域 | 描述 |
|---------|------|-----|------|
| spi_rst_n | Async, active-low | SPI_CLK | SPI 侧异步复位 |
| axi_rst_n | Async, active-low | AXI_CLK | AXI 侧异步复位 |

### 6.3 电源模式

| 模式 | 描述 | 时钟状态 | 可唤醒 |
|------|------|---------|--------|
| Active | 全速运行 | 全部开启 | N/A |
| Idle | 无 SPI 传输 | SPI_CLK 门控 (cs_n=1) | SPI CS 拉低 |

> **LLD 参考**: LLD Ch8 (Clock & Reset) 包含复位同步器 SystemVerilog 实现模板

---

## 7. 性能/功耗/面积目标

### 7.1 性能目标

| 指标 | 符号 | 目标值 | 条件 |
|------|------|--------|------|
| SPI 工作频率 | Fmax_spi | 50MHz | SPI_CLK |
| AXI 工作频率 | Fmax_axi | 100MHz | AXI_CLK |
| QSPI 峰值吞吐 | Tput_peak | 200 Mbps | QSPI 4-line 连续传输 |
| 标准 SPI 峰值吞吐 | Tput_peak | 50 Mbps | 1-line 连续传输 |
| AXI 写延迟 | Lat_write | 2 cycles | AXI 无等待 |
| AXI 读延迟 | Lat_read | 2~32 cycles | 取决于 Dummy Cycle 配置 |

### 7.2 功耗预算

N/A — RTL IP，功耗取决于工艺和集成方式。

### 7.3 面积预算

| 模块 | 预估门数 | 说明 |
|------|---------|------|
| SPI Slave Interface | ~5 kgates | 移位寄存器 + 位计数器 |
| Command Decoder | ~1 kgates | 组合逻辑 |
| RX FIFO (8x64) | ~10 kgates | 异步 FIFO |
| TX FIFO (8x32) | ~8 kgates | 异步 FIFO |
| AXI Master FSM | ~3 kgates | 7 状态 FSM |
| Wrap Controller | ~2 kgates | 地址计算 |
| CSR | ~2 kgates | 5 个 32-bit 寄存器 |
| **总计** | **~31 kgates** | 不含时钟树/扫描链 |

---

## 8. 应用场景

### 8.1 典型用例

**用例 1: SoC 配置空间访问**
- **触发条件**: 外部 SPI Master 发送写/读命令
- **数据量**: 单次 4 字节 (32-bit)
- **操作序列**:
  1. SPI Master 拉低 CS
  2. 发送 8-bit Opcode (0x00=Write / 0x01=Read)
  3. 发送 32-bit Address
  4. 写: 发送 32-bit Data → 读: Dummy Cycles + 接收 32-bit Data
  5. 接收 Status Byte
  6. SPI Master 拉高 CS
- **关键要求**: AXI 读延迟 ≤ 32 dummy cycles

**用例 2: 系统调试与 Bringup**
- **触发条件**: 实验室调试阶段
- **操作序列**: 通过 SPI 调试器连接，访问 SoC 内部所有 AXI 映射寄存器
- **关键要求**: 支持通过 SPI Status Byte 返回 AXI SLVERR/DECERR 状态

### 8.2 异常场景

- **AXI 超时**: AXI 总线无响应 → TIMEOUT 标志位置位，返回错误 status
- **AXI SLVERR/DECERR**: AXI Slave 返回错误 → 错误码透传到 SPI Status Byte
- **非法 Opcode**: 非 0x00/0x01 → 返回 SLVERR
- **CS 异常跳变**: CS 在非 DONE 状态拉高 → FSM 强制回到 IDLE

### 8.3 使用限制

- 仅支持 AXI4-Lite (不支持 AXI4-Full burst)
- 仅支持 single transfer (AxLEN=0)
- 不支持 unaligned 地址访问
- 不支持 SPI Master 模式 (仅 Slave)
- 不支持多通道并发

> **LLD 参考**: LLD Ch8 (Clock & Reset), LLD Ch9 (SDC), LLD Ch12 (DFT) 包含详细约束

---

## 9. 假设与约束

### 9.1 关键假设

| # | 假设 | 影响 | 验证方式 |
|---|------|------|---------|
| A1 | SPI Master 遵循 SPI Mode 0 (CPOL=0, CPHA=0) | 时序正确性 | 验证所有 4 种模式 |
| A2 | AXI Slave 在合理周期内响应 | 无 AXI 死锁 | 验证 AXI 超时机制 |
| A3 | SPI 帧格式固定: Opcode+Addr+Data | 数据解析正确 | 验证帧格式 |

### 9.2 设计约束

**时序约束**:
- SPI_CLK: max 50MHz, 由外部 SPI Master 提供
- AXI_CLK: min 100MHz, SoC PLL 提供
- CDC 路径: 标记为 false path (除 FIFO 指针外)

**物理约束**:
- RTL IP, 无特定物理约束

**工具约束**:
- 不使用 `synopsys_translate_off` 划分关键代码
- 所有 FF 需可扫描链插入

### 9.3 外部依赖

| 依赖模块 | 依赖类型 | 接口 | 风险 |
|---------|---------|------|------|
| AXI 总线矩阵 | 数据通路 | AXI4-Lite | 低 |
| SPI Master (外部) | 控制 | SPI/QSPI | 低 |

### 9.4 开放问题

| # | 问题 | 影响域 | 建议方案 |
|---|------|--------|---------|
| Q01 | 是否需要支持 SPI Mode 1/2/3? | 功能 | 设计时固定为 Mode 0, 可选参数化 |
| Q02 | Wrap 地址是否支持运行时修改? | 功能 | 仅 IDLE 状态可修改 |

---

## 10. 设计决策记录 (Architecture Decision Record)

| ADR# | 决策 | 选项 | 选择理由 | 后果 |
|------|------|------|---------|------|
| 001 | 选择 AXI4-Lite 而非 AXI4-Full | AXI4-Lite / AXI4-Full | SPI2AXI 访问配置空间，无需 burst | 吞吐受限但面积小 |
| 002 | 选择 Dual-Clock Async FIFO + Gray-code | 握手同步 / FIFO | FIFO 解耦良好，适合连续数据流 | 面积增加但 CDC 可靠 |
| 003 | SPI 编码采用固定 opcode 0x00/0x01 | 可变 / 固定 | 简单可靠，匹配 airhdl 参考设计 | 欠缺灵活性 |
| 004 | Dummy Cycle 放在地址之后数据之前 | 地址前/地址后 | 符合 QSPI 标准时序，含 Turnaround | 读延迟固定 |

---

## 11. 验证特性映射指引

### 11.1 Feature 到验证项的映射

| # | 来源章节 | Feature | 设计侧验证关注点 | 验证侧验证方法 |
|---|---------|---------|----------------|---------------|
| F01 | §1.3 / §5.4 | SPI/QSPI 模式功能正确性 | 两种模式数据路径 | UVM scoreboard |
| F02 | §2.2 / §5.3 | CSR 寄存器读写 | RW/RO/W1C 属性、复位值 | UVM reg_model |
| F03 | §3.1 / §4.1 | 数据通路完整性 | 数据写读一致性 | UVM scoreboard |
| F04 | §4.2 / §2.3 | AXI4-Lite 协议合规 | 5 通道握手协议 | Formal assertion |
| F05 | §6.2 | CDC 功能验证 | 双时钟 FIFO 数据完整性 | 随机频率比测试 |
| F06 | §5.2 / §7 | Wrap 地址环绕 | Wrap=0/1/2/N | 地址计算检查 |
| F07 | §4.3 | Opcode 译码 | 0x00/0x01/非法 opcode | 正确路由 |
| F08 | §8.2 | 异常与错误恢复 | TIMEOUT, SLVERR, DECERR | Error injection |

### 11.2 无需验证的 Feature

- 测试专用通路 (scan_mode) — 由 DFT 验证覆盖
- 纯组合逻辑的中间信号 — 端到端数据完整性已覆盖

### 11.3 断言建议

- **接口协议断言**: AXI valid/ready 时序合规性、地址对齐
- **状态机断言**: illegal 状态、非法跳转
- **数据完整性断言**: FIFO 空读/满写
- **CDC 断言**: 同步器路径无 X 传播

---

## 附录 A: 术语表

| 术语 | 含义 |
|------|------|
| AXI | Advanced eXtensible Interface |
| CDC | Clock Domain Crossing |
| CSR | Control and Status Register |
| FSM | Finite State Machine |
| LLD | Low-Level Design |
| QSPI | Quad SPI (4-wire) |
| SPI | Serial Peripheral Interface |
| W1C | Write-1-to-Clear |

## 附录 B: 参考文档

| 文档 | 版本 | 来源 | 说明 |
|------|------|------|------|
| SPI2AXI SPEC.pdf | V1.0 | 本地 | 原始设计规格 |
| AMBA AXI4-Lite Protocol Spec | ARM IHI 0022G | ARM | AXI 协议标准 |
| airhdl/spi-to-axi-bridge | — | GitHub (Apache 2.0) | 开源参考设计 |

---

*本文档由 Chip Design Agent 生成 — SPI2AXI Block HLD V2.0*
