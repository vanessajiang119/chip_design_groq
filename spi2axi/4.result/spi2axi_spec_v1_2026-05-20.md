# SPI2AXI Bridge IP — 芯片设计规格书

> 生成日期: 2026-05-20
> 源文档: SPI2AXI SPEC.pdf
> 状态: 初稿 / v1

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
| 时钟域 | 双时钟域：SPI_CLK (50MHz) / AXI_CLK (独立) |
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

### 2.3 数据流

**写数据流**: SPI Master → SPI Slave I/F → Command Decoder → RX FIFO (CDC) → AXI Master FSM → AXI4-Lite → Target Slave

**读数据流**: AXI Master FSM → AXI4-Lite → Target Slave → TX FIFO (CDC) → SPI Slave I/F → SPI Master

---

## 3. 接口定义

### 3.1 SPI 从设备接口

#### 信号列表

| 信号名称 | 方向 | 位宽 | 描述 |
|----------|------|------|------|
| spi_sclk | 输入 | 1 | SPI 串行时钟，最大 50MHz |
| spi_cs_n | 输入 | 1 | SPI 片选信号（低有效） |
| spi_sdi | 输入 | 4 | SPI 数据输入线 [3:0] (QSPI 模式) |
| spi_sdo | 输出 | 4 | SPI 数据输出线 [3:0] (QSPI 模式) |

#### 工作模式

| 模式 | 数据线宽 | 描述 |
|------|----------|------|
| 标准 SPI | 1-bit (sdi[0]/sdo[0]) | 单线双向传输 |
| QSPI | 4-bit (sdi[3:0]/sdo[3:0]) | 四线双向传输，高速模式 |

### 3.2 AXI4-Lite 主设备接口

5 个独立通道，遵循 AMBA AXI4-Lite 协议规范：

| 通道 | 方向 | 关键信号 |
|------|------|----------|
| AW (写地址) | Master → Slave | awaddr, awvalid, awready |
| W (写数据) | Master → Slave | wdata, wstrb, wvalid, wready |
| B (写响应) | Slave → Master | bresp, bvalid, bready |
| AR (读地址) | Master → Slave | araddr, arvalid, arready |
| R (读数据) | Slave → Master | rdata, rresp, rvalid, rready |

**AXI 参数配置**:
| 参数 | 值 | 说明 |
|------|-----|------|
| AXI_ADDR_WIDTH | 32 | 地址总线宽度 |
| AXI_DATA_WIDTH | 32 | 数据总线宽度 |
| AXI_ID_WIDTH | 3 | ID 信号宽度 |
| AxLEN | 0 | 仅支持 single transfer (burst=1) |
| AxSIZE | 2 (4 bytes) | 每次传输 1 个 32-bit 字 |

---

## 4. 操作协议

### 4.1 SPI 命令格式

```
帧格式（标准 SPI / QSPI 模式）:

[8-bit Opcode] + [32-bit Address] + [Dummy Cycles] + [32-bit Data]

- Opcode:      8 bits, MSB first
- Address:    32 bits, MSB first (仅内存访问时需要)
- Dummy:      可编程 cycles (仅读操作)
- Data:       32 bits, MSB first
```

### 4.2 写操作流程

```
SPI Master                  SPI2AXI Bridge              AXI Slave
    |                            |                          |
    |--- 配置模式(1-line/4-line)-->|                          |
    |                            |                          |
    |--- 8'hXX (写Opcode) ------>|                          |
    |--- 32'hADDR (地址) ------->|                          |
    |                            |-- 解析命令, 同步到AXI域 -->|
    |                            |                          |
    |--- 32'hDATA (写数据) ------>|-- AW(AWADDR) ----------->|
    |                            |-- W(WSTRB, WDATA) ------>|
    |                            |                          |
    |                            |<-- B(BRESP) -------------|
    |<-- 完成响应 ----------------|                          |
```

### 4.3 读操作流程

```
SPI Master                  SPI2AXI Bridge              AXI Slave
    |                            |                          |
    |--- 配置模式(1-line/4-line)-->|                          |
    |                            |                          |
    |--- 8'hXX (读Opcode) ------>|                          |
    |--- 32'hADDR (地址) ------->|                          |
    |                            |-- 同步读请求到AXI域 ------>|
    |                            |-- AR(ARADDR) ----------->|
    |                            |                          |
    |                            |<-- R(RDATA, RRESP) ------|
    |                            |-- 数据写入TX FIFO ------->|
    |<== Dummy Cycles (等待) ====|                          |
    |<-- 32'hDATA (读出数据) -----|                          |
```

### 4.4 SPI 命令操作码

> **待补充**: PDF 第 5 页包含操作码编码表（图片格式）。需要从图片中提取：
> - 各操作码 [7:0] 对应的读/写命令
> - 内存访问 vs 寄存器访问的编码区分
> - 操作码格式规范

### 4.5 Dummy Cycle

- 默认配置: 32 cycles
- 实际 Dummy Cycle = DUMMY_CYCLES 配置值 + 1
- 可编程范围: 1 ~ 33 cycles
- 用途: 等待 AXI 读数据返回至 TX FIFO

---

## 5. 跨时钟域设计 (CDC)

### 5.1 时钟域划分

| 时钟域 | 时钟来源 | 频率 |
|--------|----------|------|
| SPI_CLK | 外部 SPI 主机提供 | ≤ 50MHz |
| AXI_CLK | SoC 内部时钟 | 系统时钟 (如 100MHz+) |

### 5.2 CDC 方案

**方案: Dual-Clock Asynchronous FIFO**

```
SPI_CLK Domain                     AXI_CLK Domain
    +--------+     +-----------+     +---------+
    | SPI    |---->| RX FIFO   |---->| AXI    |
    | Rx FSM |     | (async)   |     | Master |
    +--------+     +-----------+     +---------+

    +---------+    +-----------+     +--------+
    | SPI     |<---| TX FIFO   |<----| AXI    |
    | Tx FSM  |    | (async)   |     | Rd FSM |
    +---------+    +-----------+     +--------+
```

- RX FIFO: SPI 写入，AXI 读取（写命令/数据 path）
- TX FIFO: AXI 写入，SPI 读取（读返回数据 path）
- 使用 dual-clock SRAM 或寄存器阵列实现
- 空/满标志独立时钟域生成（同步器链）

### 5.3 同步器设计

- 至少 2 级 flip-flop 同步器链
- 格雷码指针 (Gray code pointer) 跨时钟域传递

---

## 6. FSM 状态机

### 6.1 SPI 接收 FSM

> **待补充**: PDF 第 4 页包含 FSM 图（图片格式）
>
> 建议状态:
> - IDLE: 等待 spi_cs_n 拉低
> - GET_OPCODE: 接收 8-bit opcode
> - GET_ADDR: 接收 32-bit 地址
> - DUMMY: 插入 dummy cycles (读操作)
> - SEND_DATA: 发送/接收 32-bit 数据
> - WAIT_AXI: 等待 AXI 事务完成

### 6.2 AXI Master FSM

> **待补充**:
> - IDLE: 等待 RX FIFO 非空
> - ADDR_PHASE: 发送 AW/AR 地址
> - DATA_PHASE: 发送 W 数据 / 接收 R 数据
> - RESP_PHASE: 等待 B/R 响应
> - WRITE_TX: 读数据写入 TX FIFO
> - DONE: 事务完成

---

## 7. 地址 Wrap 功能

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

```verilog
// 伪代码
if (wrap_en && (current_addr == base_addr + (wrap_size - 1) * 4))
    next_addr = base_addr;
else
    next_addr = current_addr + 4;
```

---

## 8. 可配置参数

| 参数名 | 默认值 | 可编程 | 描述 |
|--------|--------|--------|------|
| AXI_ADDR_WIDTH | 32 | 设计时固定 | AXI 地址总线宽度 |
| AXI_DATA_WIDTH | 32 | 设计时固定 | AXI 数据总线宽度 |
| AXI_ID_WIDTH | 3 | 设计时固定 | AXI ID 信号宽度 |
| DUMMY_CYCLES | 32 | 运行时/设计时 | SPI 读虚拟周期数 (实际 = cfg + 1) |
| WRAP_SIZE | 0 | 运行时/设计时 | 地址环绕窗口大小 (0=disabled) |
| SPI_MODE | SPI/QSPI | 运行时 | SPI 工作模式选择 |
| CLK_RATIO | - | 设计时 | SPI_CLK:AXI_CLK 频率比 |

---

## 9. 时序分析

### 9.1 QSPI 写时序

> **图片参考**: PDF 第 6 页包含 QSPI 写时序图
>
> 预期时序:
> - spi_cs_n 拉低开始传输
> - spi_sclk 每个上升沿采样 spi_sdi 数据
> - spi_sdo 在 spi_sclk 下降沿更新
> - QSPI 模式下，每个 sclk 传输 4-bit (sdi[3:0])

### 9.2 QSPI 读时序

> **图片参考**: PDF 第 6 页包含 QSPI 读时序图
>
> 预期时序:
> - 发送 opcode + 地址 (QSPI 模式)
> - 插入 dummy cycles
> - spi_sdo 在 dummy 后返回数据

---

## 10. 寄存器映射 (CSR)

> **待补充**: PDF 第 5 页包含 SPI 侧寄存器设定表（图片格式）
>
> 建议寄存器列表:
> | 偏移地址 | 名称 | 位宽 | 描述 |
> |----------|------|------|------|
> | 0x00 | SPI_CTRL | 32 | SPI 控制寄存器 |
> | 0x04 | SPI_STATUS | 32 | SPI 状态寄存器 |
> | 0x08 | WRAP_CFG | 32 | 地址环绕配置 |
> | 0x0C | DUMMY_CFG | 32 | Dummy cycle 配置 |
> | 0x10 | SPI_DATA | 32 | SPI 数据寄存器 |

---

## 11. 应用场景

- **系统调试和配置接口**: 通过 SPI 接口访问 SoC 配置空间 (S3 config)
- **低引脚数系统总线扩展**: 4-pin SPI 即可扩展 AXI 总线访问能力
- **嵌入式系统固件更新**: 外部 SPI 主机通过桥接器更新 SoC 固件
- **芯片测试和验证接口**: 实验室 bringup 和 debug 的标准接口

---

## 12. 验证计划 (建议)

| 验证项 | 描述 |
|--------|------|
| SPI 协议兼容性 | 标准 SPI / QSPI 模式基本功能 |
| AXI4-Lite 协议合规 | 5 通道握手协议全覆盖 |
| CDC 功能验证 | 双时钟 FIFO 数据完整性 |
| 命令解码 | 所有 opcode 正确译码 |
| Wrap 地址环绕 | 不同 Wrap 配置的功能正确性 |
| 时序收敛 | SPI 50MHz, AXI 目标频率 STA |
| 边界测试 | FIFO 满/空、AXI 响应错误、CS 异常跳变 |

---

## 13. 修订历史

| 版本 | 日期 | 作者 | 描述 |
|------|------|------|------|
| v1 | 2026-05-20 | chip-spec-gen | 初稿，基于 SPI2AXI SPEC.pdf 生成 |
