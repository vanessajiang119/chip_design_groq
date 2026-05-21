# 模块架构蓝图 — SPI2AXI Bridge Architecture Blueprint (HLD)

> **模块名称:** SPI2AXI Bridge (SPI to AXI4-Lite Bridge)
> **版本:** V1.0
> **日期:** 2026-05-21
> **状态:** Draft
> **Architecture Freeze:** 待补充
> **对应 LLD 文档:** `spi2axi_bridge_micro.LLD.md` (14 章节 AI-Executable 模板)

---

## 1. Module Overview

### 1.1 Module Identity

| 属性 | 值 |
|------|-----|
| 模块全名 | SPI2AXI Bridge |
| 层次路径 | `soc.periph.spi2axi` |
| 功能分类 | 接口桥接 (Interface Bridge) — SPI Slave to AXI4-Lite Master |
| 工艺节点 | 待定 (取决于 SoC 平台) |
| 目标频率 | SPI: 50 MHz / AXI: 待定 (通常 50~200 MHz) |
| 供电电压 | 待定 (取决于 SoC 平台) |

> **LLD 参考**: LLD Ch1.1 包含更详细的 PVT corner、面积、功耗目标

### 1.2 一句话摘要

SPI2AXI Bridge 是一个将 **SPI 从设备接口 (SPI Slave)** 转换为 **AXI4-Lite 主设备接口 (AXI4-Lite Master)** 的桥接 IP 核，允许外部 SPI 主机通过低引脚数串行接口访问 SoC 内部的 AXI 总线映射存储器和外设配置空间。

### 1.3 功能目标

- 支持标准 SPI (1-wire) 和 Quad SPI / QSPI (4-wire) 两种工作模式，通过 CSR 可配置切换
- 将 SPI 接收到的操作码 (8-bit) 和地址 (32-bit) 解码并转换为 AXI4-Lite 读写事务
- 通过 dual-clock FIFO 实现 SPI 时钟域到 AXI 时钟域的可靠跨时钟域数据传输 (CDC)
- 支持可配置的地址 Wrap 功能，在 AXI4-Lite 单次传输约束下模拟循环地址访问
- 提供寄存器文件 (CSR) 用于工作模式配置、状态查询和参数配

### 1.4 非功能目标

| 维度 | 目标 | 测量条件 |
|------|------|---------|
| 性能 | SPI 线速率: 50 Mbps (1-wire) / 200 Mbps (4-wire) @ 50 MHz | 最差工况 |
| 延迟 | SPI 数据输入到 AXI 事务发起延迟: SPI 侧接收完成 + CDC FIFO 传输 + AXI 握手 | 无竞争场景 |
| 功耗 | 待补充 — 取决于工艺和 SoC 平台 | 满载运行 |
| 面积 | 待补充 — 需 RTL 综合后评估 | SS corner |
| 可靠性 | CDC FIFO 格雷码同步，防亚稳态 | 双时钟异步场景 |

### 1.5 Top-Level Port Groups Summary

| Port Group | Direction | Width | Clock Domain | Description |
|------------|-----------|-------|-------------|-------------|
| `spi_*` | input/output | 1+4+4 | spi_sclk | SPI 串行接口: sclk, cs, sdi[3:0], sdo[3:0] |
| `axi_*` | in/out | 多通道 | axi_aclk | AXI4-Lite 主接口 (AW/W/B/AR/R 五通道) |
| `clk_*` | input | 1+1 | — | 时钟输入: spi_sclk, axi_aclk |
| `rst_*` | input | 1+1 | — | 复位输入: spi_rst_n, axi_areset_n |
| `interrupt` | output | 1 | axi_aclk | AXI 时钟域中断输出 |

> **LLD 参考**: LLD Ch1.2 的 Top-Level Ports Summary 包含更详细的 I/O Pad 属性

### 1.6 功能边界

- **范围内**: SPI 命令解析 (操作码 + 地址解码)
- **范围内**: SPI 到 AXI 的读写事务转换
- **范围内**: 跨时钟域数据传输 (dual-clock FIFO)
- **范围内**: 地址 Wrap 循环访问
- **范围内**: SPI 工作模式配置 (1-wire / 4-wire)
- **范围外**: AXI4-Full burst 支持 (仅 AXI4-Lite single transfer)
- **范围外**: SPI 主设备模式 (仅 Slave 模式)
- **范围外**: SPI Dual-wire 模式 (仅 Standard 1-wire 和 Quad 4-wire)
- **范围外**: 协议级重传机制或 ECC 保护

---

## 2. 外部接口定义

### 2.1 顶层 I/O 列表

#### SPI 接口信号

| 信号名 | 方向 | 位宽 | 类型 | 时钟域 | 复位域 | 描述 |
|--------|------|------|------|--------|--------|------|
| `spi_sclk` | input | 1 | 时钟 | — | — | SPI 串行时钟，由外部 SPI 主机提供，最高 50 MHz |
| `spi_cs` | input | 1 | 数据 | spi_sclk | spi_rst_n | SPI 片选，低有效，启动/结束 SPI 事务 |
| `spi_sdi[3:0]` | input | 4 | 数据 | spi_sclk | spi_rst_n | SPI 数据输入: 1-wire 模式仅 [0]，4-wire 模式全用 |
| `spi_sdo[3:0]` | output | 4 | 数据 | spi_sclk | spi_rst_n | SPI 数据输出: 1-wire 模式仅 [0]，4-wire 模式全用 |

#### AXI4-Lite 主接口信号

| 信号名 | 方向 | 位宽 | 类型 | 时钟域 | 复位域 | 描述 |
|--------|------|------|------|--------|--------|------|
| `axi_aclk` | input | 1 | 时钟 | — | — | AXI 系统时钟，由 SoC 提供 |
| `axi_areset_n` | input | 1 | 复位 async active-low | axi_aclk | — | AXI 域异步复位 |
| `awaddr` | output | 32 | data | axi_aclk | axi_areset_n | 写地址 |
| `awvalid` | output | 1 | data | axi_aclk | axi_areset_n | 写地址有效 |
| `awready` | input | 1 | data | axi_aclk | axi_areset_n | 写地址就绪 |
| `awid` | output | 3 | data | axi_aclk | axi_areset_n | 写地址 ID |
| `awprot` | output | 3 | data | axi_aclk | axi_areset_n | 写保护类型 |
| `wdata` | output | 32 | data | axi_aclk | axi_areset_n | 写数据 |
| `wstrb` | output | 4 | data | axi_aclk | axi_areset_n | 写选通 |
| `wvalid` | output | 1 | data | axi_aclk | axi_areset_n | 写数据有效 |
| `wready` | input | 1 | data | axi_aclk | axi_areset_n | 写数据就绪 |
| `bresp` | input | 2 | data | axi_aclk | axi_areset_n | 写响应 |
| `bvalid` | input | 1 | data | axi_aclk | axi_areset_n | 写响应有效 |
| `bready` | output | 1 | data | axi_aclk | axi_areset_n | 写响应就绪 |
| `bid` | input | 3 | data | axi_aclk | axi_areset_n | 写响应 ID |
| `araddr` | output | 32 | data | axi_aclk | axi_areset_n | 读地址 |
| `arvalid` | output | 1 | data | axi_aclk | axi_areset_n | 读地址有效 |
| `arready` | input | 1 | data | axi_aclk | axi_areset_n | 读地址就绪 |
| `arid` | output | 3 | data | axi_aclk | axi_areset_n | 读地址 ID |
| `arprot` | output | 3 | data | axi_aclk | axi_areset_n | 读保护类型 |
| `rdata` | input | 32 | data | axi_aclk | axi_areset_n | 读数据 |
| `rresp` | input | 2 | data | axi_aclk | axi_areset_n | 读响应 |
| `rvalid` | input | 1 | data | axi_aclk | axi_areset_n | 读数据有效 |
| `rready` | output | 1 | data | axi_aclk | axi_areset_n | 读数据就绪 |
| `rid` | input | 3 | data | axi_aclk | axi_areset_n | 读数据 ID |

#### 时钟/复位/中断信号

| 信号名 | 方向 | 位宽 | 类型 | 描述 |
|--------|------|------|------|------|
| `spi_sclk` | input | 1 | 时钟 | SPI 串行时钟 (由 SPI 主机提供) |
| `spi_rst_n` | input | 1 | 复位 async active-low | SPI 域异步复位，低有效 |
| `axi_aclk` | input | 1 | 时钟 | AXI 系统时钟 (由 SoC 提供) |
| `axi_areset_n` | input | 1 | 复位 async active-low | AXI 域异步复位，低有效 |
| `intr_o` | output | 1 | 中断 | AXI 域中断输出 |

> **LLD 参考**: LLD Ch2.1 包含完整的 Port Signal Table (含 I/O Pad 属性)

### 2.2 SPI 从设备接口

- **协议**: Standard SPI (1-wire, CPOL=0/CPHA=0) + Quad SPI (4-wire)
- **接口类型**: SPI Slave — 同步于 `spi_sclk`
- **最大时钟频率**: 50 MHz
- **SPI 帧格式**:
  - 内存写: [Opcode (8-bit)] + [Address (32-bit)] + [Write Data (32-bit)]
  - 内存读: [Opcode (8-bit)] + [Address (32-bit)] + [Dummy Cycles (可编程)] + [Read Data (32-bit)]
  - 寄存器写: [Opcode (8-bit)] + [Write Data (32-bit)]
  - 寄存器读: [Opcode (8-bit)] + [Dummy Cycles] + [Read Data (32-bit)]
- **数据顺序**: MSB first (最高有效位在前)
- **传输时序规范**: SPI 模式 0 (CPOL=0, CPHA=0) — sclk 空闲为低，数据在上升沿采样

### 2.3 AXI4-Lite 主设备接口

- **协议**: AXI4-Lite (简化版 AXI4)
- **数据位宽**: 32-bit
- **突发长度**: 固定为 1 (AxLEN = 0)，仅 single transfer
- **突发大小**: AxSIZE = 2 (32-bit / 4-byte)
- **out-of-order**: 不支持 (AXI4-Lite 不支持)
- **ID 宽度**: 3-bit (AWID/ARID/WID/RID/BID)
- **关键时序要求**: 地址通道和数据通道独立握手，写响应通道等待

### 2.4 中断接口

| 中断输出 | 类型 | 事件源 | 清除机制 |
|---------|------|--------|---------|
| intr_o | 电平 | AXI 事务错误 / 待补充 | 读状态寄存器清除 / W1C |

> **LLD 参考**: LLD Ch2.4 包含完整的中断事件表（触发类型、极性、聚合方式）

### 2.5 其他专用接口

无其他专用接口。该模块仅通过 SPI 和 AXI 总线与外部通信。

---

## 3. 顶层架构框图

### 3.1 模块内部结构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SPI2AXI_Bridge (Top)                              │
│                                                                         │
│  ┌─────────────────────────┐     ┌──────────────────────────┐           │
│  │    SPI 时钟域            │     │    AXI 时钟域             │           │
│  │                         │     │                          │           │
│  │  ┌──────────────────┐   │     │  ┌───────────────────┐   │           │
│  │  │  spi_slave_if     │   │ cmd │  │  axi_master_if    │   │           │
│  │  │  ├ spi_io         │───┼─fifo─┤  │  ├ axi_wr_ctrl   │   │           │
│  │  │  └ spi_cmd_decoder│   │ wda─┤  │  └ axi_rd_ctrl   │   │           │
│  │  └──────────────────┘   │ ta──┤  └───────────────────┘   │           │
│  │          │              │ fifo│           │               │           │
│  │          ▼              │ rda─┤           │               │           │
│  │  ┌──────────────┐      │ ta──┤           │               │           │
│  │  │  fsm_ctrl    │      │ fifo│           │               │           │
│  │  │  (SPI 域)    │      │     │           │               │           │
│  │  └──────┬───────┘      │     │           │               │           │
│  │         │              │     │           │               │           │
│  │  ┌──────┴───────┐      │     │  ┌──────────────┐        │           │
│  │  │ csr_regfile  │──────┼─────┼──│ wrap_addr_gen│        │           │
│  │  └──────────────┘      │     │  └──────────────┘        │           │
│  └─────────────────────────┘     └──────────────────────────┘           │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │            Clock / Reset / CDC Synchronizer                      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘

   SPI Pins ──► spi_slave_if ──► CDC FIFO ──► axi_master_if ──► AXI4-Lite Bus
                    │                              │
                    ▼                              ▼
              fsm_ctrl ◄──── csr_regfile ────► wrap_addr_gen
```

> **LLD 参考**: LLD Ch3.2 包含精确的子模块数据位宽, LLD Ch3.3 包含模块间信号连线表

### 3.2 子模块职责

| 子模块 | 职责 | 关键设计考量 | 复杂度 | 对应 LLD 章节 |
|--------|------|-------------|--------|--------------|
| spi_slave_if | SPI 串行数据收发、命令解析 | 1-wire/4-wire 模式切换、串并转换 | 中 | LLD Ch3, Ch2 |
| cdc_fifo | 跨时钟域数据传输 | 3 路独立 FIFO (cmd/wdata/rdata)、格雷码同步 | 中 | LLD Ch3, Ch8 |
| axi_master_if | AXI4-Lite 主接口协议处理 | 5 通道握手、single transfer 控制 | 中 | LLD Ch3, Ch2 |
| fsm_ctrl | 主状态机、SPI→AXI 事务流程控制 | 8 状态转换、读/写路径区分、异常处理 | 高 | LLD Ch4 |
| csr_regfile | 配置/状态寄存器文件 | SPI 可寻址寄存器、工作模式选择 | 低 | LLD Ch7 |
| wrap_addr_gen | Wrap 地址生成与管理 | 地址自增/回绕逻辑、窗口配置 | 低 | LLD Ch6 |

### 3.3 模块间关键数据路径带宽

| 路径 | 协议 | 位宽 | 时钟域 | 理论带宽 | 备注 |
|------|------|------|--------|---------|------|
| SPI Pins → spi_slave_if | SPI serial | 1/4-bit | spi_sclk | 50/200 Mbps | 入口 |
| spi_slave_if → cmd_fifo | 内部并行 | <40-bit | spi_sclk | — | 命令+地址 |
| spi_slave_if → wdata_fifo | 内部并行 | 32-bit | spi_sclk | 200 MB/s | 写数据 |
| rdata_fifo → spi_slave_if | 内部并行 | 32-bit | spi_sclk | 200 MB/s | 读数据 |
| cmd_fifo → axi_master_if | 内部并行 | <40-bit | axi_aclk | — | 命令+地址 |
| axi_master_if → AXI Bus | AXI4-Lite | 32-bit | axi_aclk | 可变 | 出口 |

---

## 4. 数据流与控制流

### 4.1 数据流路径

```
写操作数据流:

  SPI Pins (串行) → [spi_slave_if 串并转换] → cmd_fifo + wdata_fifo
      → [axi_master_if 协议封装] → AXI4-Lite 写事务 (AW → W → B)

读操作数据流:

  SPI Pins (串行) → [spi_slave_if 串并转换] → cmd_fifo
      → [axi_master_if 协议封装] → AXI4-Lite 读事务 (AR → R)
      → rdata_fifo → [spi_slave_if 并串转换] → SPI Pins (串行)
```

**数据流步骤 (写操作)**:
1. **SPI 命令接收**: spi_slave_if 通过 `spi_sdi` 接收操作码 (8-bit) 和地址 (32-bit)
2. **SPI 数据接收**: spi_slave_if 接收写数据 (32-bit)，MSB first
3. **CDC 传输**: 命令/地址写入 cmd_fifo，写数据写入 wdata_fifo，同步到 AXI 时钟域
4. **AXI 写事务**: axi_master_if 从 cmd_fifo 获取地址，从 wdata_fifo 获取数据
5. **AXI 协议握手**: AW 通道发送地址 → W 通道发送数据 → B 通道接收响应
6. **完成**: 写响应返回，状态更新

**数据流步骤 (读操作)**:
1. **SPI 命令接收**: spi_slave_if 接收操作码 (8-bit) 和地址 (32-bit)
2. **CDC 传输**: 命令/地址写入 cmd_fifo，同步到 AXI 时钟域
3. **虚拟等待**: SPI 域插入可编程 dummy cycles (等待 AXI 读数据返回)
4. **AXI 读事务**: axi_master_if 从 cmd_fifo 获取地址，发起 AR 通道
5. **AXI 读响应**: R 通道接收读数据，写入 rdata_fifo
6. **SPI 数据发送**: spi_slave_if 从 rdata_fifo 读取数据，串行发送到 `spi_sdo`

### 4.2 控制流

**主状态机状态迁移**:

```
                 ┌──────────────────────────────────────┐
                 │                                      │
                 ↓                                      │
    [IDLE] → [OPCODE] → [ADDR] → [DUMMY] → [DATA] ───→ [AXI_WR/AXI_RD]
                 │        │           (读路径)     │           │
                 │        │                        │           │
                 │        └── (寄存器访问时跳过) ────┘           │
                 │                                                │
                 └──────────────→ [DONE] ←────────────────────────┘
                                        │
                                        ↓
                                      [IDLE]
```

| 状态 | 描述 | 入口动作 | 出口条件 |
|------|------|---------|---------|
| IDLE | 空闲等待 | — | spi_cs 有效，开始接收操作码 |
| OPCODE | 接收 8-bit 操作码 | 启动 8-cycle 移位接收 | 操作码接收完成 |
| ADDR | 接收 32-bit 地址 | 启动 32-cycle 移位接收 | 地址接收完成 (或寄存器访问时跳过) |
| DUMMY | 插入虚拟等待周期 | 启动 dummy 计数器 | 计数器达到 DUMMY_CYCLES |
| DATA | SPI 数据传输 | 32-cycle 数据收发 | 数据传输完成 |
| AXI_WR/ AXI_RD | AXI 事务执行 | 发起 AXI 地址通道 | AXI 写/读响应完成 |
| DONE | 事务完成 | 置位完成标志 | 自动返回 IDLE |

> **LLD 参考**: LLD Ch4 包含完整 FSM 规格 — 状态编码表、状态转移矩阵、输出译码表

### 4.3 反压与流控策略

- **反压传播路径 (写)**: AXI 总线反压 → axi_master_if 等待 → wdata_fifo 满 → SPI 域暂停发送
- **反压传播路径 (读)**: rdata_fifo 空 → SPI 域等待数据 → axi_master_if 等待 R 通道响应
- **FIFO 水位管理**: cmd_fifo 非空触发 AXI 事务启动
- **超时机制**: 待补充 — AXI 总线等待超时处理

### 4.4 并发与冲突处理

- **多通道并发**: 不支持 — AXI4-Lite 仅支持单次传输，事务串行执行
- **读写冲突**: 读/写事务通过 FSM 状态区分，FIFO 路径独立，不会冲突
- **原子操作**: 不支持 — AXI4-Lite 不支持独占访问或锁定事务

---

## 5. 主要特性与可配置参数

### 5.1 核心特性

| 特性类别 | 特性 | 详细描述 | 可选/必选 |
|---------|------|---------|----------|
| 协议支持 | Standard SPI (1-wire) | 单线 SPI 从设备模式 | 必选 |
| 协议支持 | Quad SPI / QSPI (4-wire) | 四线 SPI 从设备模式，通过 CSR 可配置切换 | 可选 |
| 协议支持 | AXI4-Lite Master | 5 通道 AXI4-Lite 主接口 | 必选 |
| 数据模式 | 单次传输 (Single Transfer) | 每个 SPI 事务转换为一个 AXI 事务 | 必选 |
| 跨时钟域 | Dual-Clock CDC FIFO | 3 路独立 FIFO 实现 SPI↔AXI 时钟域隔离 | 必选 |
| 地址模式 | Wrap 地址环绕 | 可配置窗口大小的地址循环访问 | 可选 |
| 错误处理 | AXI 响应错误检测 | BRESP/RRESP 非 OKAY 时上报错误 | 必选 |
| 虚拟周期 | 可编程 Dummy Cycles | 读操作等待周期可配置，实际周期 = DUMMY_CYCLES + 1 | 必选 |
| 调试能力 | SPI 可访问 CSR | 通过操作码直接编址访问配置寄存器 | 必选 |

### 5.2 可配置参数

| 参数名 | HDL 类型 | 默认值 | 取值范围 | 描述 | 影响 |
|--------|---------|--------|---------|------|------|
| `AXI_ADDR_WIDTH` | int | 32 | 32 | AXI 地址总线宽度 | 面积↑·灵活性↑ |
| `AXI_DATA_WIDTH` | int | 32 | 32 | AXI 数据总线宽度 (AXI4-Lite 固定 32) | 固定 |
| `AXI_ID_WIDTH` | int | 3 | 1~8 | AXI ID 信号宽度 | 面积↑ |
| `DUMMY_CYCLES` | int | 32 | 0~255 | SPI 读操作虚拟周期数 (实际周期 = 此值 + 1) | 读延迟↑·AXI 等待↑ |
| `CMD_FIFO_DEPTH` | int | 4 | 2~16 | 命令 FIFO 深度 | 面积↑·吞吐↑ |
| `DATA_FIFO_DEPTH` | int | 8 | 4~64 | 数据 FIFO 深度 (wdata/rdata) | 面积↑·反压容忍↑ |

### 5.3 配置寄存器摘要

| 偏移 | 名称 | 属性 | 复位值 | 功能描述 |
|------|------|------|--------|---------|
| 0x00 | CTRL | RW | 0x0000_0000 | 控制寄存器: mode_sel (SPI 模式选择), wrap_en (Wrap 使能), soft_rst (软复位) |
| 0x04 | STATUS | RO | — | 状态寄存器: busy, done, error, fifo_status |
| 0x08 | DUMMY_CFG | RW | 0x0000_0020 | 虚拟周期配置 (对应 DUMMY_CYCLES 参数) |
| 0x0C | WRAP_CFG | RW | 0x0000_0000 | Wrap 配置寄存器 (Wrap 窗口大小 N) |
| 0x10 | FIFO_STATUS | RO | — | FIFO 状态寄存器 (空/满标志、计数) |

> **LLD 参考**: LLD Ch7 包含完整 bit-level CSR 映射 — 每位域的 offset/width/attribute/HW set-clear 条件/reset 值

### 5.4 操作模式

| 模式 | 编码 | 描述 | 典型使用 |
|------|------|------|---------|
| Standard SPI | 0 | 1-wire 标准 SPI 模式 | 兼容性要求、低速配置 |
| Quad SPI / QSPI | 1 | 4-wire QSPI 模式 | 高吞吐调试、固件更新 |
| Wrap Disabled | Wrap=0 | 地址无环绕，每次访问指定地址 | 随机地址访问 |
| Wrap Enabled | Wrap=N | 地址环绕窗口 N words | 连续地址循环扫描、FIFO 轮询 |

---

## 6. 时钟、复位与电源架构

### 6.1 时钟域概述

| 时钟域 | 源 | 频率 | 目标模块 | 同步关系 |
|--------|------|------|---------|---------|
| `spi_sclk` | 外部 SPI 主机 | 50 MHz (max) | spi_slave_if, fsm_ctrl (SPI 域), csr_regfile, spi_cdc | 与 AXI 域异步 |
| `axi_aclk` | SoC PLL | 待定 (通常 50~200 MHz) | axi_master_if, wrap_addr_gen, axi_cdc | 与 SPI 域异步 |

> **LLD 参考**: LLD Ch8.1 包含完整的时钟域定义，LLD Ch8.3 包含跨时钟域 CDC 路径及同步方案表

### 6.2 复位结构

| 复位信号 | 类型 | 域 | 描述 |
|---------|------|-----|------|
| `spi_rst_n` | Async, active-low | spi_sclk | SPI 域异步复位，复位 SPI 接口逻辑和 SPI 侧寄存器 |
| `axi_areset_n` | Async, active-low | axi_aclk | AXI 域异步复位，复位 AXI 主接口和 AXI 侧寄存器 |

- 建议使用 **异步复位，同步释放** 的复位同步器
- SPI 域和 AXI 域应分别拥有独立的复位信号
- CDC FIFO 需要两个时钟域都复位才能正确初始化

### 6.3 电源模式

| 模式 | 描述 | 时钟状态 | 可唤醒 |
|------|------|---------|--------|
| Active | 全速运行，SPI 事务处理中 | spi_sclk + axi_aclk 全开 | N/A |
| Idle | 无 SPI 事务，等待片选 | spi_sclk 运行 / axi_aclk 运行 | SPI 片选有效 |
| Sleep | 待补充 — 取决于 SoC 电源管理策略 | 待定 | 待定 |

> 注: 该 IP 不包含独立的电源管理单元，电源模式由 SoC 级电源管理控制。

---

## 7. 性能/功耗/面积目标

### 7.1 性能目标

| 指标 | 符号 | 目标值 | 条件 |
|------|------|--------|------|
| SPI 工作频率 | Fmax_spi | 50 MHz | 标准 SPI @ 50 MHz |
| AXI 工作频率 | Fmax_axi | 待定 | 取决于 SoC 平台 |
| SPI 峰值吞吐 (1-wire) | Tput_1w | 50 Mbps | 连续 back-to-back 传输 |
| SPI 峰值吞吐 (4-wire) | Tput_4w | 200 Mbps | 连续 back-to-back 传输 |
| AXI 峰值传输速率 | Tput_axi | 待定 | 取决于 axi_aclk 频率 |
| SPI 帧延迟 (读) | Lat_read | 8 (opcode) + 32 (addr) + N (dummy) + 32 (data) spi_sclk 周期 | 含 dummy cycles |
| SPI 帧延迟 (写) | Lat_write | 8 (opcode) + 32 (addr) + 32 (data) spi_sclk 周期 | 无等待 |

### 7.2 功耗预算

| 电源域 | 电压 | Active | Idle | Sleep | 占比 |
|--------|------|--------|------|-------|------|
| VDD_CORE | 待定 | 待补充 | 待补充 | 待补充 | 待补充 |
| **总计** | | **待补充** | **待补充** | **待补充** | **100%** |

> 功耗数据需在 RTL 综合后使用 EDA 工具评估。

### 7.3 面积预算

| 模块 | 组合逻辑 | 时序逻辑 | SRAM | 总计 | 比例 |
|------|---------|---------|------|------|------|
| spi_slave_if | 待补充 | 待补充 | — | 待补充 | 待补充 |
| cdc_fifo | 待补充 | 待补充 | 3 x FIFO | 待补充 | 待补充 |
| axi_master_if | 待补充 | 待补充 | — | 待补充 | 待补充 |
| fsm_ctrl + csr + wrap | 待补充 | 待补充 | — | 待补充 | 待补充 |
| **总计** | **待补充** | **待补充** | **待补充** | **待补充** | **100%** |

> 面积数据需在 RTL 综合后使用 EDA 工具评估。

---

## 8. 应用场景

> **LLD 参考**: LLD Ch1.3 包含模块特性清单, LLD Ch11.1 包含定向测试场景表

### 8.1 典型用例

**用例 1: 系统调试和配置接口 (System Debug & Configuration)**
- **触发条件**: 外部调试主机通过 SPI 连接 SoC 的 SPI2AXI 接口
- **数据量**: 单次 4 字节 (32-bit) 寄存器读写配置
- **操作序列**:
  1. 外部主机通过 SPI 发送操作码 + 地址 + 数据 (写) 或操作码 + 地址 (读)
  2. SPI2AXI 解析命令并转换为 AXI 事务
  3. AXI 访问 SoC 配置空间或 CSR 寄存器
  4. 读数据通过 SPI 返回给外部主机
- **退出条件**: SPI 片选释放
- **关键要求**: 低延迟、可靠传输

**用例 2: 嵌入式系统固件更新 (Firmware Update)**
- **触发条件**: 外部主机发送固件更新命令和固件数据
- **数据量**: 大量连续数据 (KB ~ MB 级别)
- **操作序列**:
  1. 外部主机配置 SPI2AXI 为 QSPI 模式 (4-wire)
  2. 使能 Wrap 功能 (如果更新目标为连续存储区域)
  3. 连续发送写命令 + 地址 + 数据，地址自动递增
  4. 固件数据通过 AXI 写入目标存储器
- **退出条件**: 固件传输完成，校验通过
- **关键要求**: 高吞吐 (使用 QSPI)、地址连续递增

**用例 3: 芯片测试与验证 (Chip Test & Verification)**
- **触发条件**: 测试台通过 SPI 访问芯片内部状态
- **数据量**: 单次或连续读/写
- **操作序列**:
  1. 发送读命令 + 地址
  2. 等待 dummy cycles 后读取返回数据
  3. 验证内部寄存器/存储器值
- **退出条件**: 测试项结束
- **关键要求**: 寄存器访问 (+Wrap 功能方便扫描)

### 8.2 异常场景

- **AXI 总线超时 (SLVERR/DECERR)**: AXI 从设备返回错误响应 → err flag 置位
- **SPI 片选异常释放**: 片选在数据传输完成前释放 → 当前事务终止，返回 IDLE 状态
- **FIFO 溢出**: 写数据 FIFO 满时 SPI 仍在写入 → 待补充处理方式
- **非法操作码**: 未定义的操作码 → 待补充处理方式

### 8.3 使用限制

- 仅支持 AXI4-Lite single transfer (burst 长度固定为 1)
- 不支持 AXI4-Full 的 burst、locked 事务、cached 或 protection unit 等高级特性
- SPI 地址必须与 4 字节对齐 (AxSIZE = 2)
- SPI 时钟频率不可超过 50 MHz
- 跨时钟域路径通过 dual-clock FIFO 保证，不依赖静态时序分析

> **LLD 参考**: LLD Ch8 (Clock & Reset), LLD Ch9 (SDC), LLD Ch12 (DFT) 包含时序约束、CDC、DFT 等约束的详细规格

---

## 9. 假设与约束

### 9.1 关键假设

| # | 假设 | 影响 | 验证方式 |
|---|------|------|---------|
| A1 | SPI 主机在片选有效期间保持 sclk 稳定 | 时钟不稳定导致数据采样错误 | 验证 SPI 时钟抖动场景 |
| A2 | AXI 从设备在可接受的延迟内响应 | 无限等待导致 FSM 挂起 | 验证 AXI 响应超时 |
| A3 | 配置寄存器仅在 IDLE 状态下修改 | 运行中修改可能导致行为不确定 | Formal 断言 |
| A4 | SPI 帧格式严格遵守 Opcode + (Address) + Data 序列 | 帧格式错误导致命令解析错误 | 验证注入非法帧格式 |

### 9.2 设计约束

**时序约束**:
- SPI 输入延迟: max 5.0 ns from pad to module input (spi_sdi/spi_cs)
- SPI 输出延迟: max 5.0 ns from module output to pad (spi_sdo)
- 异步路径: SPI ↔ AXI 跨时钟域路径标记为 false path

**物理约束**:
- 面积约束: 待补充 (需 RTL 综合后确定)
- 电源域: SPI 域和 AXI 域共享同一核心电源 (取决于 SoC)

**工具约束**:
- 综合: 标准 Synopsys DC 流程
- DFT: 所有 FF 需可扫描链插入
- STA: 建立/保持时间需满足 Fmax 目标

### 9.3 外部依赖

| 依赖模块 | 依赖类型 | 接口 | 版本要求 | 风险 |
|---------|---------|------|---------|------|
| AXI 系统总线矩阵 | 数据通路 | AXI4-Lite | AMBA 3/4 | 低 |
| SoC 时钟生成单元 | 时钟 | axi_aclk | 待定 | 低 |
| SPI 主机 (外部) | 数据 | SPI / QSPI | 标准 SPI | 低 |

### 9.4 开放问题

| # | 问题 | 影响域 | 建议方案 | 责任人 | 截止日期 |
|---|------|--------|---------|--------|---------|
| Q01 | AXI 时钟频率未定 | 时序/验证 | 等待 SoC 系统组确认 | 待定 | 待定 |
| Q02 | FIFO 深度未定 | 面积/性能 | 需评估典型 SPI 传输数据量 | 待定 | 待定 |
| Q03 | 是否需要中断输出? | 功能 | 如 SPI 主机不支持中断轮询可省 | 待定 | 待定 |
| Q04 | 是否需要支持 Dual SPI? | 功能 | 目前仅 1-wire 和 4-wire | 待定 | 待定 |

---

## 10. 设计决策记录 (Architecture Decision Record)

| ADR# | 决策 | 选项 | 选择理由 | 后果 | 日期 |
|------|------|------|---------|------|------|
| 001 | 选择 AXI4-Lite 而非 AXI4-Full | AXI4-Lite / AXI4-Full | 目标应用为配置空间访问，无需 burst 等高级特性 | 面积小、协议简单，但无法支持高吞吐流传输 | 2026-05-21 |
| 002 | 使用 dual-clock FIFO 实现 CDC | handshake / FIFO / 2-flop | 数据量大需缓冲，FIFO 提供可靠的数据路径隔离 | 面积增加，但 CDC 可靠性高 | 2026-05-21 |
| 003 | 三级独立 FIFO (cmd/wdata/rdata) | 合并/三级独立 | 读/写数据路径分离，减少 AXI 侧的仲裁延迟 | 面积增加但路径清晰 | 2026-05-21 |
| 004 | FSM 在 SPI 时钟域实现 | SPI 域 / AXI 域 | SPI 命令解析在 SPI 域完成，避免频繁 CDC | CDC 仅在 FIFO 路径，控制逻辑简单 | 2026-05-21 |
| 005 | 支持 QSPI 作为可选特性 | 仅标准 SPI / 增加 QSPI | QSPI 提升 4 倍吞吐，适合固件更新等高带宽场景 | 面积增加，逻辑复杂度上升 | 2026-05-21 |

---

## 11. 验证特性映射指引

> **LLD 参考**: LLD Ch11 包含定向测试场景表(§11.1)、SVA 断言模板(§11.2)、功能覆盖率点(§11.3)

### 11.1 Feature 到验证项的映射

| # | 来源章节 | Feature | 设计侧验证关注点 | 验证侧验证方法 | 覆盖率目标 |
|---|---------|---------|----------------|---------------|-----------|
| F01 | §1.3 / §5.1 | 标准 SPI 模式命令收发 | 串并转换正确性、MSB first | UVM scoreboard | 100% 模式 × 数据组合 |
| F02 | §1.3 / §5.1 | QSPI 模式命令收发 | 4-bit 并行收发正确性 | UVM scoreboard | 100% 模式 × 数据组合 |
| F03 | §2.3 | AXI4-Lite 写事务 | AW/W/B 通道握手协议合规 | Formal assertion | 100% 协议规则 |
| F04 | §2.3 | AXI4-Lite 读事务 | AR/R 通道握手协议合规 | Formal assertion | 100% 协议规则 |
| F05 | §4.1 | CDC FIFO 数据传输 | 数据完整性、无丢包、无亚稳态 | UVM + CDC 验证 | 100% 传输 |
| F06 | §4.2 | FSM 状态转换 | 所有状态和跳转的正确性 | Formal / UVM | 100% FSM 覆盖 |
| F07 | §5.3 | CSR 寄存器读写 | RW/RO 属性、复位值、地址解码 | UVM reg_model | 100% 寄存器位域 |
| F08 | §5.4 | Wrap 地址环绕功能 | 地址自增和回绕正确性、窗口配置 | UVM directed | 所有 Wrap 配置组合 |
| F09 | §5.2 | Dummy Cycles 配置 | 实际等待周期数 = 配置值 + 1 | UVM directed | 多种配置值 |
| F10 | §1.5 | 跨时钟域数据传输 | spi_sclk ↔ axi_aclk 数据完整性 | CDC 验证 (MVRC) | 所有 CDC 路径 |

### 11.2 无需验证的 Feature

- 测试专用通路 (scan_mode, mbist_mode 等) — 由 DFT 验证覆盖
- AXI4-Full burst 功能 — 不支持，不在范围内
- SPI 主设备模式 — 不支持，不在范围内

### 11.3 断言 (Assertion) 建议

- **SPI 接口断言**: spi_sdi/spi_cs 在 spi_sclk 上升沿后的 setup/hold 时间
- **AXI 接口断言**: AWVALID/AWREADY, WVALID/WREADY, ARVALID/ARREADY, RVALID/RREADY, BVALID/BREADY 握手协议合规
- **FSM 断言**: 非法状态、非法跳转检测
- **FIFO 断言**: 满写/空读保护、格雷码指针无毛刺
- **CSR 断言**: 保留地址读返回 0 写忽略

---

## 附录 A: 术语表

| 术语 | 含义 |
|------|------|
| AXI | Advanced eXtensible Interface (ARM AMBA 总线协议) |
| AXI4-Lite | AXI4 的轻量级版本，仅支持 single transfer |
| CDC | Clock Domain Crossing (跨时钟域) |
| CSR | Control and Status Register (控制状态寄存器) |
| DFT | Design for Testability (可测试性设计) |
| DUMMY_CYCLES | SPI 读操作中插入的虚拟等待周期数 |
| FSM | Finite State Machine (有限状态机) |
| LLD | Low-Level Design (微架构设计) |
| MSB | Most Significant Bit (最高有效位) |
| QSPI | Quad SPI (四线 SPI) |
| SDC | Synopsys Design Constraints (时序约束文件) |
| SPI | Serial Peripheral Interface (串行外设接口) |
| STA | Static Timing Analysis (静态时序分析) |
| W1C | Write-1-to-Clear (写 1 清除寄存器属性) |
| Wrap | 地址环绕访问模式 |

## 附录 B: 参考文档

| 文档 | 版本 | 来源 | 说明 |
|------|------|------|------|
| SPI2AXI Design Spec | V0.1 | `1.planning/source_spec.md` | SPI2AXI 设计规格说明书 |
| SPI2AXI Micro LLD | V1.0 | `spi2axi_bridge_micro.LLD.md` | 微架构设计文档 |
| AMBA AXI4-Lite Protocol Spec | ARM IHI 0022D | ARM | AXI4-Lite 协议标准 |
| SPI Block Guide V03.06 | Motorola | SPI 协议标准 |

---

*本文档由 Chip Design Agent 自动生成 — SPI2AXI Bridge Architecture HLD V1.0*
