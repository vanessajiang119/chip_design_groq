# SoC 顶层架构蓝图 — Top-Level Architecture Blueprint

> **芯片名称:**
> **版本:** V1.0
> **日期:**
> **状态:** Draft / Review / Final
> **Architecture Freeze:** <!-- YYYY-MM-DD -->

---

## 1. SoC 概述与目标

### 1.1 芯片定位
<!-- 一句话描述：该 SoC 面向什么市场、解决什么问题 -->
<!-- 示例：本芯片是一款面向 AIoT 边缘计算的异构 SoC，集成 RISC-V 应用处理器、NPU 加速器和低功耗蓝牙子系统，目标在 1W 功耗预算内提供 4TOPS 的推理性能。 -->

**一句话摘要**:

### 1.2 目标应用市场
- <!-- 智能家居 / 工业控制 / 汽车 / 移动 / AI 边缘 / 通信基础设施 -->

### 1.3 顶层设计目标

| 维度 | 目标 | 优先级 (P0/P1/P2) |
|------|------|-------------------|
| 性能 | <!-- e.g. 系统总吞吐 >= X Gbps --> | P0 |
| 功耗 | <!-- e.g. 典型功耗 < Y W --> | P0 |
| 面积 | <!-- e.g. 芯片面积 < Z mm² --> | P1 |
| 成本 | <!-- e.g. BOM 成本 < $W --> | P1 |
| 上市时间 | <!-- e.g. 2025 Q4 流片 --> | P0 |
| 兼容性 | <!-- e.g. pin-to-pin 兼容前代产品 --> | P2 |

### 1.4 关键性能指标 (KPI)

| KPI | 目标 | 测量方法 |
|-----|------|---------|
| DMIPS | <!-- 整数算力 --> | Dhrystone |
| TOPS / GFLOPS | <!-- AI / 浮点算力 --> | MLPerf / SPEC |
| 内存带宽 | <!-- GB/s --> | STREAM benchmark |
| 外设带宽 | <!-- e.g. PCIe Gen4 x4 = 8GB/s --> | — |
| 唤醒时间 | <!-- us --> | 低功耗模式到 Active |
| 启动时间 | <!-- ms --> | 上电到 OS 启动完成 |
| 典型功耗 | <!-- W --> | 典型应用场景负载 |

---

## 2. 顶层系统架构

### 2.1 SoC 顶层框图
```
┌────────────────────────────────────────────────────────────────────────────┐
│                            SoC_Name (Top)                                  │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Application  │  │     Core     │  │     GPU /    │  │    Video     │   │
│  │  Processor   │  │   Complex    │  │     NPU      │  │  Codec       │   │
│  │  (CPU Core)  │  │  (DSU/SCU)   │  │  Accelerator │  │  Engine      │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │                 │            │
│         └─────────────────┼─────────────────┼─────────────────┘            │
│                           │                 │                              │
│                          ┌▼─────────────────▼┐                             │
│                          │     Cache Coherent │                             │
│                          │     Interconnect   │                             │
│                          │    (CMN / CCI /   │                             │
│                          │     NoC / Bus)     │                             │
│                          └────────┬──────────┘                             │
│                                   │                                        │
│         ┌─────────────────────────┼────────────────────┐                   │
│         │                         │                    │                   │
│  ┌──────▼──────┐          ┌──────▼──────┐      ┌──────▼──────┐            │
│  │  Memory     │          │   I/O       │      │   System    │            │
│  │  Controller │          │  Coherent   │      │   Hub /    │            │
│  │  (DDR / HBM)│          │  Interconnect│     │   Peripheral│            │
│  └──────┬──────┘          └──────┬──────┘      │   Bus      │            │
│         │                       │              └──────┬──────┘            │
│         ▼                       ▼                     ▼                   │
│  ┌──────────────────────────────────────────────────────────────┐        │
│  │               Peripheral Subsystem & I/O                     │        │
│  │  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐  │        │
│  │  │PCIe│ │USB │ │ETH │ │UART│ │I2C │ │SPI │ │GPIO│ │PWM │  │        │
│  │  └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘  │        │
│  │  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌──────────┐   │        │
│  │  │I2S │ │CAN │ │SDIO│ │eMMC│ │QSPI│ │ADC │ │Security │   │        │
│  │  └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ │Subsystem │   │        │
│  │                                              └──────────┘   │        │
│  └──────────────────────────────────────────────────────────────┘        │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────────────┐  │
│  │   Clock /    │  │   Power /    │  │        Debug / Trace           │  │
│  │   Reset      │  │   PMU        │  │  ┌────┐ ┌──────┐ ┌─────────┐  │  │
│  │   Generator  │  │   Domain     │  │  │JTAG│ │ ETM  │ │ STM     │  │  │
│  └──────────────┘  └──────────────┘  │  └────┘ └──────┘ └─────────┘  │  │
│                                       └────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘

  ──► 高速数据通路 (cache coherent interconnect)
  ──► 外设总线 (APB / AHB-Lite / AXI4-Lite)
  ──► 低速控制/配置通路
```

### 2.2 主要子系统摘要

| 子系统 | 主要模块 | 功能职责 | 关键指标 | 复杂度评估 |
|--------|---------|---------|---------|-----------|
| CPU Complex | CPU Core(s), DSU/SCU, L1/L2 Cache | 通用计算与控制 | X DMIPS @ Y GHz | 高 |
| 加速器 | GPU / NPU / DSP / Video Codec | 专用计算加速 | X TOPS / X GFLOPS | 高 |
| 内存子系统 | DDR/HBM Controller, L3 Cache, SRAM | 数据存储与带宽供给 | X GB/s 带宽 | 中 |
| 互联架构 | NoC / CMN / Bus Fabric | 数据通路与一致性管理 | X Gbps 总带宽 | 高 |
| I/O 子系统 | PCIe / USB / Ethernet | 片外高速通信 | X Gbps 单端口 | 中 |
| 外设子系统 | UART / I2C / SPI / GPIO / PWM | 低速控制与连接 | X 个实例 | 低 |
| 安全子系统 | Crypto / OTP / TRNG / Secure Boot | 安全启动与数据保护 | 符合 X 标准 | 中 |
| 时钟/复位/Power | PLL / PMU / Reset Controller | 时钟生成、功耗管理 | X 个电源域 | 中 |
| 调试子系统 | JTAG / ETM / STM / CoreSight | 调试与性能分析 | 符合 CoreSight 规范 | 中 |

### 2.3 系统启动流程

```
  [POR] ──► [Boot ROM] ──► [XIP Flash / eMMC] ──► [DDR Init] ──► [Load Bootloader]
    │                                                                    │
    ▼                                                                    ▼
  [Power-On-Reset]        [BootROM 执行]         [加载 FSBL]           [DDR 初始化完成]
                                                                    │
                                                                    ▼
                                                       [Load OS / App] ──► [Normal Run]
```

**启动阶段详细说明**:
1. **BOOTROM**: <!-- 片内 BootROM 执行，初始化基本时钟与 PLL -->
2. **FSBL**: <!-- 从 SPI Flash / eMMC / SD 卡加载 First Stage Bootloader -->
3. **DDR Init**: <!-- 初始化 DDR PHY 与控制器，配置内存映射 -->
4. **SSBL/OS**: <!-- 加载 Second Stage Bootloader 或直接加载操作系统 -->
5. **安全启动**: <!-- 是否启用 Secure Boot? 签名验证在哪个阶段? -->

---

## 3. 处理器子系统 (CPU Complex)

### 3.1 CPU 核心配置

| 参数 | 规格 |
|------|------|
| 架构 | <!-- RISC-V RV64GC / ARM Cortex-X4 / ARM Cortex-A78 --> |
| 核心数 | <!-- 1 / 4 / 8 Core --> |
| 微架构 | <!-- 顺序 / 乱序执行 --> |
| ISA 扩展 | <!-- RISC-V: V(向量), Zk(加密) / ARM: NEON, SVE2 --> |
| 流水线 | <!-- 解码/发射宽度、流水线级数 --> |
| L1 I-Cache | <!-- 32KB / 64KB, 关联度, line size --> |
| L1 D-Cache | <!-- 32KB / 64KB, 关联度, line size --> |
| L2 Cache | <!-- 256KB / 512KB per core or shared --> |
| L3 Cache | <!-- 2MB / 4MB / 8MB, shared --> |
| 缓存一致性 | <!-- MESI / MOESI / CHI --> |
| 最大频率 | <!-- GHz --> |

### 3.2 核心互联 (DSU / SCU)

| 特性 | 描述 |
|------|------|
| 互联类型 | <!-- DSU-120 / CMN-700 / CCIX --> |
| Core 接口 | <!-- ACE / CHI / AXI4 --> |
| 一致性协议 | <!-- MOESI / MESI --> |
| Snoop 滤波器 | <!-- 有/无, 大小 --> |
| 内存地址映射 | <!-- 有多少个 address region --> |
| 监测点 (Watchpoint) | <!-- 数量 --> |

### 3.3 CPU 性能预期

| 指标 | 预期值 | 条件 |
|------|--------|------|
| DMIPS / Core | <!-- > X DMIPS --> | Dhrystone @ Y GHz |
| CoreMark / Core | <!-- > X CoreMark --> | CoreMark @ Y GHz |
| SPECint 2006 | <!-- 分数 --> | SPECint |
| 内存延迟 (L1 hit) | <!-- N cycles --> | |
| 内存延迟 (L2 hit) | <!-- N cycles --> | |
| 内存延迟 (L3 hit) | <!-- N cycles --> | |
| 内存延迟 (DDR) | <!-- N cycles --> | |

---

## 4. 内存子系统

### 4.1 片外内存接口

| 接口 | 协议 | 通道数 | 位宽 | 最大带宽 | 最大容量 | ECC |
|------|------|--------|------|---------|---------|-----|
| DDR | <!-- DDR4/DDR5/LPDDR5/HBM --> | <!-- 1/2/4ch --> | <!-- 16/32/64bit --> | <!-- X GB/s --> | <!-- GB --> | <!-- 是/否 --> |

### 4.2 片内内存 (SRAM / eMRAM / eFlash)

| 内存实例 | 容量 | 位宽 | 访问延迟 | 用途 |
|---------|------|------|---------|------|
| BootROM | <!-- 64KB --> | 32 | 1 cycle | 启动代码 |
| TCM | <!-- 128KB --> | 64 | 1 cycle | CPU 紧耦合内存 |
| Shared SRAM0 | <!-- 512KB --> | 128 | 2 cycles | 数据暂存 |
| Shared SRAM1 | <!-- 256KB --> | 64 | 2 cycles | 外设 DMA buffer |
| eFlash / eMRAM | <!-- 2MB --> | — | 可变 | 非易失存储 |

### 4.3 内存地址映射

| 起始地址 | 结束地址 | 大小 | 目标 | 属性 | 描述 |
|---------|---------|------|------|------|------|
| 0x0000_0000 | 0x0000_FFFF | 64KB | BootROM | RO, XN 不可执行 | 启动 ROM |
| 0x0010_0000 | 0x0011_FFFF | 128KB | TCM | RW, Cacheable | CPU TCM |
| 0x0800_0000 | 0x0FFF_FFFF | 128MB | DDR | RW, Cacheable | DDR 区域 |
| 0x1000_0000 | 0x1FFF_FFFF | 256MB | PCIe Config | RW, Device | PCIe 配置空间 |
| 0x2000_0000 | 0x2FFF_FFFF | 256MB | PCIe MMIO | RW, Device | PCIe BAR 空间 |
| 0x4000_0000 | 0x400F_FFFF | 1MB | Peripheral | RW, Device | 外设寄存器空间 |
| 0x5000_0000 | 0x5007_FFFF | 512KB | Shared SRAM | RW, Cacheable | 共享内存 |
| 0x6000_0000 | 0x600F_FFFF | 1MB | NPU Registers | RW, Device | NPU 控制寄存器 |
| 0x7000_0000 | 0x700F_FFFF | 1MB | Crypto Registers | RW, Secure | 加密引擎寄存器 |
| 0xE000_0000 | 0xE00F_FFFF | 1MB | Debug | RW, Device | 调试接口 |
| 0xFFFF_0000 | 0xFFFF_FFFF | 64KB | System Registers | RW, Secure | 系统控制寄存器 |

> 注：此地址映射在 SoC 顶层 `system_addr_map.vh` 中维护，所有模块的地址解码必须与此一致。

### 4.4 DDR 控制器配置

| 参数 | 配置 |
|------|------|
| PHY 类型 | <!-- DDR PHY / DFI 接口版本 --> |
| 频率 | <!-- MHz --> |
| 时序参数 | <!-- CL-tRCD-tRP-tRAS --> |
| 调度策略 | <!-- 自适应 / 固定优先级 / round-robin --> |
| QoS | <!-- 支持多少个 region/优先级 --> |
| 低功耗模式 | <!-- 支持 self-refresh/deep-power-down? --> |

---

## 5. 互联架构 (Interconnect / NoC / Bus Fabric)

### 5.1 互联拓扑

```
  [CPU Complex]────┐                  ┌────[GPU/NPU]
                   │                  │
                   ▼                  ▼
              ┌──────────────────────────────┐
              │     Cache Coherent           │
              │     Interconnect (CMN/NoC)   │
              │                              │
              │   ┌─────────┐ ┌─────────┐   │
              │   │XP/CHI I/F│ │ACE/ACEL│   │
              │   └─────────┘ └─────────┘   │
              └──────────────────────────────┘
                        │          │
               ┌────────┘          └─────────┐
               ▼                              ▼
        ┌───────────┐                  ┌───────────┐
        │ DDR Ctrl  │                  │ I/O Coherent│
        │           │                  │ Hub/Noc    │
        └───────────┘                  └───────────┘
                                               │
                          ┌────────────────────┼───────────────┐
                          ▼                    ▼               ▼
                   ┌──────────┐         ┌──────────┐    ┌──────────┐
                   │ High Perf│         │  Periph  │    │ Security │
                   │ I/F Bus │         │  Bus     │    │ Bus      │
                   │ (AXI4)  │         │ (AHB-L)  │    │ (AXI4-S) │
                   └──────────┘         └──────────┘    └──────────┘
```

### 5.2 总线/互联矩阵参数

| 互联实例 | 协议 | 主端口 | 从端口 | 总带宽 | 一致性 |
|---------|------|--------|--------|--------|--------|
| Core Interconnect | <!-- CHI / ACE --> | <!-- N --> | <!-- M --> | <!-- Gbps --> | 支持 |
| I/O Coherent Hub | <!-- ACE-Lite / AXI4 --> | <!-- N --> | <!-- M --> | <!-- Gbps --> | ACE-Lite |
| High Perf Bus | <!-- AXI4 --> | <!-- N --> | <!-- M --> | <!-- Gbps --> | 无 |
| Peripheral Bus | <!-- AHB-Lite / APB --> | <!-- 1 --> | <!-- K --> | <!-- Gbps --> | 无 |
| Security Bus | <!-- AXI4-S --> | <!-- N --> | <!-- M --> | <!-- Gbps --> | 可选 |

### 5.3 关键 QoS 策略
- **CPU 流量优先级**: <!-- 高 / 中 / 低 -->
- **NPU/GPU 带宽保障**: <!-- 最小保证带宽, 最大延迟限制 -->
- **实时流量 (e.g. Display)**: <!-- 硬实时 deadline 要求 -->
- **尽力而为 (BE) 流量**: <!-- 空闲带宽分享策略 -->
- **Starvation 防止**: <!-- aging 机制 / 反压阈值 -->

---

## 6. 外部接口 (I/O Subsystem)

### 6.1 高速 I/O

| 接口 | 实例数 | 协议版本 | 最大速率 | PHY 类型 | 单端/差分 | 用途 |
|------|--------|---------|---------|---------|----------|------|
| PCIe | <!-- N --> | <!-- Gen3/4/5 x1/x2/x4 --> | <!-- GT/s --> | <!-- PCIe PHY --> | 差分 | 外接加速器/SSD/NIC |
| USB | <!-- N --> | <!-- USB 3.2 / 2.0 --> | <!-- Gbps --> | <!-- USB PHY --> | 差分 | 外设连接 |
| Ethernet | <!-- N --> | <!-- RGMII / SGMII / XGMII --> | <!-- Gbps --> | <!-- SERDES --> | 差分 | 网络通信 |
| HDMI / DP | <!-- N --> | <!-- HDMI 2.1 / DP 1.4 --> | <!-- Gbps --> | <!-- TX PHY --> | 差分 | 显示输出 |

### 6.2 低速 I/O

| 接口 | 实例数 | 模式 | 最大速率 | 电气特性 | 用途 |
|------|--------|------|---------|---------|------|
| UART | <!-- N --> | <!-- 标准/流控 --> | <!-- bps --> | <!-- LVCMOS 1.8V --> | 调试控制台 |
| I2C | <!-- N --> | <!-- master/slave --> | <!-- kHz --> | <!-- OD 1.8V --> | 板级控制 |
| SPI | <!-- N --> | <!-- master/slave, quad --> | <!-- MHz --> | <!-- LVCMOS --> | Flash / 传感器 |
| GPIO | <!-- N pins --> | <!-- input/output/interrupt --> | <!-- MHz --> | <!-- LVCMOS 1.8/3.3V --> | 通用控制 |
| I2S | <!-- N --> | <!-- master/slave --> | <!-- kHz sample --> | <!-- LVCMOS --> | 音频 |
| CAN | <!-- N --> | <!-- CAN 2.0 / CAN-FD --> | <!-- Mbps --> | <!-- 差分 --> | 车载通信 |
| SDIO / eMMC | <!-- N --> | <!-- SD 3.0 / eMMC 5.1 --> | <!-- MB/s --> | <!-- LVCMOS 1.8/3.3V --> | 存储卡 / Flash |
| QSPI | <!-- N --> | <!-- Single/Dual/Quad --> | <!-- MHz --> | <!-- LVCMOS --> | 代码存储 |

### 6.3 I/O MUX / Pin Muxing
<!-- 芯片有限数量的管脚如何在多个外设之间共享 -->
| Pad Group | 功能 A | 功能 B | 功能 C | 默认 |
|----------|--------|--------|--------|------|
| GPIO[0:3] | UART0 TX/RX | I2C0 SDA/SCL | GPIO | GPIO |
| GPIO[4:7] | SPI0 CS/CLK/MOSI/MISO | I2S0 | GPIO | SPI |
| GPIO[8:11] | PWM0~3 | GPIO | JTAG | GPIO |
| <!-- ... --> | | | | |

---

## 7. 时钟与复位架构

### 7.1 时钟方案

```
  [外部晶振 25MHz]
         │
    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
    │  PLL0   │    │  PLL1   │    │  PLL2   │
    │ CPU PLL │    │  DDR    │    │  Periph │
    └────┬────┘    └────┬────┘    └────┬────┘
         │              │              │
         ▼              ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ CPU clk  │  │ DDR clk  │  │ Periph   │
    │ X.Y GHz  │  │ Z MHz    │  │ clk(W MHz)│
    └──────────┘  └──────────┘  └──────────┘
         │                            │
     ┌───▼───┐                   ┌────▼────┐
     │ 分频器 │  ──► Core clk     │ 分频器   │  ──► AXI / AHB / APB
     └───────┘                    └─────────┘
```

### 7.2 时钟域列表

| 时钟域 | 频率 | 来源 | 扇出 | 门控支持 | 用途 |
|--------|------|------|------|---------|------|
| cpu_clk | <!-- GHz --> | CPU PLL | CPU Complex, SCU | 每核门控 | CPU 核心 |
| core_clk | <!-- MHz --> | PLL1 / 分频 | 互联, L3, DDR Ctrl | 全局门控 | 核心逻辑 |
| periph_clk | <!-- MHz --> | PLL2 | AHB, APB, 外设 | 外设级门控 | 外设总线 |
| mem_clk | <!-- MHz --> | DDR PLL | DDR PHY, Ctrl | — | DDR 接口 |
| osc_clk | <!-- kHz/MHz --> | 外部晶振 | PMU, WDT, RTC | — | 常开域 |
| usb_clk | <!-- MHz --> | PLL2 | USB 控制器 | 是 | USB |
| eth_clk | <!-- MHz --> | 外部提供 / PLL2 | ETH MAC | 是 | Ethernet |

### 7.3 时钟门控策略
| 域 | 门控粒度 | 门控条件 | 唤醒延迟 |
|----|---------|---------|---------|
| CPU per-core | per-core 时钟门控 | WFI 指令 | ~10 cycles |
| NPU | 模块级门控 | 空闲 > N cycles | ~100 cycles |
| Peripheral | per-IP 门控 | IP idle | ~5 cycles |
| DDR | PHY 时钟门控 | self-refresh | ~1 us |

### 7.4 复位域

| 复位 | 类型 | 极性 | 作用于 | 描述 |
|------|------|------|--------|------|
| POR | 上电复位 | 低 | 所有逻辑 | 上电时产生 |
| SYSRST | 系统复位 | 低 | 系统逻辑 (不含 DBG) | WDT 超时或软件触发 |
| CPURST | CPU 复位 | 低 | CPU Complex | 单核复位 |
| DBGRST | 调试复位 | 低 | JTAG/Debug | nTRST |
| DDR_RST | DDR 复位 | 低 | DDR PHY & Ctrl | |

---

## 8. 功耗管理架构

### 8.1 电源域划分

```
  ┌─────────────────────────────────────────────────────────────┐
  │                      VDD_CORE (0.75~0.9V)                    │
  │  ┌────────────────────────┐ ┌────────────┐ ┌────────────┐  │
  │  │    CPU Domain          │ │  GPU/NPU  │ │  Periph    │  │
  │  │  (可关断, 2 uW/FF)     │ │  (可关断)  │ │  (可门控)  │  │
  │  └────────────────────────┘ └────────────┘ └────────────┘  │
  │  ┌──────────────────────────────────────────────────────┐  │
  │  │              Always-On Domain                        │  │
  │  │  (PMU, RTC, WDT, GPIO wake, Pad control, retention) │  │
  │  └──────────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────────┘
  ┌─────────────────────────────────────────────────────────────┐
  │                    VDD_IO (1.8V / 3.3V)                     │
  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
  │  │  High-Speed  │ │  Regular     │ │  Analog      │       │
  │  │  I/O (DDR)   │ │  GPIO/I2C/   │ │  PLL/ADC/    │       │
  │  │              │ │  SPI/UART    │ │  SerDes     │       │
  │  └──────────────┘ └──────────────┘ └──────────────┘       │
  └─────────────────────────────────────────────────────────────┘
```

### 8.2 电源域详情

| 电源域 ID | 电源轨 | 典型电压 | 可关断 | 保留 | 包含模块 |
|-----------|--------|---------|--------|------|---------|
| PD_CPU | VDD_CORE | 0.75~0.9V | 是 (per cluster) | L2 cache retention | CPU 簇, SCU |
| PD_GPU | VDD_CORE | 0.75~0.9V | 是 | Fence register | GPU/NPU |
| PD_PERI | VDD_CORE | 0.75~0.9V | 否 (可门控) | — | 一般外设 |
| PD_AON | VDD_CORE | 0.75V | 否 | 全部 | PMU, RTC, IWDT, Pad Ctrl |
| PD_IO | VDD_IO | 1.8/3.3V | 否 | — | I/O pads |
| PD_DDR | VDD_IO | 1.1~1.8V | 是 | PHY retention | DDR PHY |

### 8.3 功耗状态 (System Power Modes)

| 电源状态 | CPU | GPU/NPU | DDR | Periph | Always-On | 功耗 | 唤醒时间 | 进入条件 |
|---------|-----|---------|-----|--------|-----------|------|---------|---------|
| Active | On | On | Active | On | On | <!-- W --> | — | 正常运行 |
| CPU_Sleep | Retention | On | Active | On | On | <!-- mW --> | <!-- us --> | CPU idle, NPU 工作 |
| System_Sleep | Off | Off | Self-Refresh | Off | On | <!-- mW --> | <!-- ms --> | 浅睡眠 |
| Deep_Sleep | Off | Off | Off | Off | On (minimal) | <!-- uW --> | <!-- ms --> | 深度睡眠 |
| Shutdown | Off | Off | Off | Off | Off (RTC only) | <!-- nW --> | <!-- s --> | 完全关断 |

### 8.4 PMU (Power Management Unit) 特性
- **支持的唤醒源**: <!-- GPIO interrupt, RTC alarm, WDT, Ethernet magic packet, USB resume -->
- **上电序列**: <!-- 各电源域上电顺序要求 -->
- **掉电序列**: <!-- 各电源域掉电顺序要求 -->
- **隔离策略**: <!-- 电源域关断时输出隔离单元的放置 -->
- **状态保持**: <!-- retention register 的位置和数量 -->

---

## 9. 安全架构

### 9.1 安全子系统框图
```
  ┌──────────────────────────────────────────────┐
  │              Security Subsystem               │
  │                                                │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
  │  │  Crypto  │  │   OTP   │  │   TRNG   │    │
  │  │  Engine  │  │  (eFuse) │  │          │    │
  │  └──────────┘  └──────────┘  └──────────┘    │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
  │  │ Secure   │  │  PUF     │  │  Secure  │    │
  │  │  BootROM │  │  Module  │  │  Timer   │    │
  │  └──────────┘  └──────────┘  └──────────┘    │
  │                                                │
  │  ┌─────────────────────────────────────┐      │
  │  │  Security Bus / TrustZone Filter    │      │
  │  └─────────────────────────────────────┘      │
  └────────────────────────────────────────────────┘
```

### 9.2 安全特性

| 特性 | 支持 | 说明 |
|------|------|------|
| Secure Boot | 是/否 | RSA-4096 签名验证 / ECDSA P-384 |
| TrustZone / 物理隔离 | 是/否 | 支持安全世界和普通世界隔离 |
| 加密加速 | <!-- AES / SM4 / SM3 / RSA / ECC --> | 硬件加速器 |
| TRNG | 是/否 | 符合 NIST SP 800-22 / AIS-31 |
| OTP / eFuse | <!-- 大小 --> | 存储根密钥、芯片 ID |
| PUF | 是/否 | 物理不可克隆函数 |
| 安全 JTAG | 是/否 | 需要密码或签名认证 |
| 防侧信道 | 是/否 | 时序掩码 / 功耗掩码 |
| 安全传感器 | 是/否 | 电压/温度/频率毛刺检测 |

### 9.3 安全启动流程
1. **OTP 验证**: BootROM 读取 OTP 中的根公钥 HASH
2. **FSBL 签名验证**: 验证 FSBL 镜像的数字签名
3. **DDR 初始化**: 仅限安全世界访问 DDR
4. **SSBL/OS 验证**: 逐级验证
5. **运行时**: TrustZone / 物理内存保护单元在运行时保持隔离

---

## 10. 调试与追踪

### 10.1 调试架构

```
  [JTAG/SWD] ──► [TAP Controller] ──► [DAP (Debug Access Port)]
                      │                        │
                      ├── [CPU Core Debug]     ├── [System Memory Access]
                      ├── [ETM / Trace]        ├── [Peripheral Debug]
                      ├── [CTI/CTM]            └── [Security Debug Ctrl]
                      └── [CoreSight Components]
```

### 10.2 调试特性

| 特性 | 规格 |
|------|------|
| 调试接口 | <!-- JTAG (IEEE 1149.1) / SWD (Serial Wire Debug) --> |
| TAP IR 长度 | <!-- bits --> |
| 断点/观测点 | <!-- HW breakpoint N, watchpoint N --> |
| ETM Trace | <!-- 支持 / 不支持 --> |
| 带宽 (Trace) | <!-- Gbps --> |
| CoreSight | <!-- 兼容版本 --> |
| 安全调试 | <!-- 需要认证? 支持 Secure JTAG? --> |
| 性能计数器 | <!-- N 个 PMU 事件计数器 --> |

---

## 11. 性能与资源预算

### 11.1 SoC 级性能 —— 应用场景分解

| 场景 | CPU 负载 | 加速器负载 | 内存带宽 | 功耗 | 描述 |
|------|---------|-----------|---------|------|------|
| <!-- 场景 A --> | <!-- % --> | <!-- % --> | <!-- GB/s --> | <!-- W --> | <!-- 典型AI推理 --> |
| <!-- 场景 B --> | <!-- % --> | <!-- % --> | <!-- GB/s --> | <!-- W --> | <!-- 视频播放 --> |
| <!-- 场景 C --> | <!-- % --> | <!-- % --> | <!-- GB/s --> | <!-- W --> | <!-- 待机 --> |

### 11.2 面积预算 (Top-Level)

| 子系统 | 组合逻辑(kgates) | 时序逻辑(kgates) | SRAM(kB) | 面积合计(mm²) | 比例 |
|--------|-----------------|-----------------|----------|--------------|------|
| CPU Complex | | | | | <!-- % --> |
| GPU/NPU | | | | | <!-- % --> |
| Memory Subsystem | | | | | <!-- % --> |
| Interconnect | | | | | <!-- % --> |
| I/O Subsystem | | | | | <!-- % --> |
| Security | | | | | <!-- % --> |
| PMU/Clocking | | | | | <!-- % --> |
| Debug | | | | | <!-- % --> |
| Pad Ring | | | — | | <!-- % --> |
| **总计** | | | | **<!-- mm² -->** | **100%** |

### 11.3 功耗预算 (SoC Level)

| 子系统 | Active (W) | Idle (mW) | Sleep (uW) | 备注 |
|--------|-----------|-----------|------------|------|
| CPU Complex | <!-- W --> | <!-- mW --> | <!-- uW --> | DVFS: 0.7~0.9V |
| GPU/NPU | <!-- W --> | <!-- mW --> | <!-- uW --> | 频率可调 |
| Memory (DDR + Ctrl) | <!-- W --> | <!-- mW --> | <!-- uW --> | DDR self-refresh |
| Interconnect | <!-- W --> | <!-- mW --> | <!-- uW --> | 时钟门控 |
| I/O (PHY + Ctrl) | <!-- W --> | <!-- mW --> | <!-- uW --> | 未使用的 PHY 关断 |
| Security | <!-- W --> | <!-- uW --> | <!-- uW --> | |
| PMU + Clocking | <!-- W --> | <!-- mW --> | <!-- uW --> | PLL bypass |
| Debug | <!-- W --> | <!-- uW --> | <!-- uW --> | |
| 漏电流 (总计) | — | <!-- mW --> | <!-- uW --> | SS corner @125°C |
| **总计** | **<!-- W -->** | **<!-- mW -->** | **<!-- uW -->** | |

### 11.4 热预算
| 参数 | 值 |
|------|-----|
| Tj 最大值 | <!-- 125°C / 105°C --> |
| 散热方案 | <!-- 风冷 / 被动散热 / 液冷 --> |
| 热阻 θja | <!-- °C/W --> |
| 热点分布 | <!-- 哪个子系统最热 --> |

---

## 12. 功耗/性能/面积权衡 (PPA Trade-off)
<!-- 关键 PPA 权衡决策，供评审讨论 -->

| # | 权衡 | 选择 | 选择理由 | 放弃的理由 |
|---|------|------|---------|-----------|
| 1 | CPU 级数 vs 频率 | L1 cache 容量大但延迟稍高 | 面积受限, 无法承受高频率下的功耗 | 单线程峰值性能略低 |
| 2 | DDR 通道数 vs 面积 | 单通道 x32 | 面积约束高于带宽需求 | 内存带宽受限 |
| 3 | 缓存一致性范围 | 仅 CPU complex 之间 | NPU 不需要一致访存 | NPU 需要软件 cache flush |
| 4 | 功耗模式粒度 | 3 级睡眠 | PMU 设计复杂度有限 | Deep sleep 唤醒延迟较长 |

---

## 13. SoC 设计约束与开放问题

### 13.1 设计约束

| 类别 | 约束 |
|------|------|
| 工艺 | <!-- 12nm FinFET / 28nm Planar --> |
| 芯片尺寸 | <!-- max X mm × Y mm --> |
| 封装 | <!-- BGA-784, 0.8mm pitch --> |
| 管脚数 | <!-- N 个信号管脚, M 个电源/地 --> |
| 电源轨数量 | <!-- 组 --> |
| DVFS 支持 | <!-- 是/否, 电压步长 --> |
| 温度范围 | <!-- 商用: 0~85°C / 工业: −40~105°C --> |

### 13.2 外部依赖

| 依赖项 | 来源 | 版本 | 关键日期 | 风险等级 |
|--------|------|------|---------|---------|
| <!-- DDR PHY IP --> | <!-- Synopsys / Cadence --> | <!-- rev --> | <!-- 交付日 --> | 中 |
| <!-- PCIe PHY --> | <!-- 第三方 --> | <!-- rev --> | <!-- 交付日 --> | 低 |
| <!-- EDA 工具 --> | <!-- 支持工艺 --> | <!-- 版本 --> | — | 低 |
| <!-- Foundry PDK --> | <!-- 制造商 --> | <!-- 版本 --> | <!-- 发布日 --> | 低 |

### 13.3 开放问题

| # | 问题 | 影响 | 建议方案 | 责任人 | 截止日期 |
|---|------|------|---------|--------|---------|
| Q01 | DDR 频率最终定为 LPDDR5-6400 还是 LPDDR4X-4267? | 带宽 ±50%, 功耗 ±30% | 待系统级仿真后决策 | | |
| Q02 | NPU 是否需要独立电源域? | 面积功耗优化 vs PMU 复杂度 | 建议加, 增加 ~5% PMU 面积 | | |
| Q03 | 是否需要板载 eMMC 控制器? | BOM 成本 | 可外接 eMMC 芯片, 不需要片内控制器 | | |

---

## 14. 验证特性指引 (SoC 级)

<!-- 本节将 SoC 顶层的宏观架构特性映射到可验证的 Feature，供 DV 团队提取 SoC 级验证计划 -->

### 14.1 SoC 级验证特性映射

| # | 来源章节 | Feature | 设计侧关注点 | 验证方法 | 覆盖率目标 |
|---|---------|---------|------------|---------|-----------|
| F01 | §2.3 | 启动流程 | BootROM → DDR Init → Bootloader → OS | 系统级 UVM / FPGA Prototype | 所有启动介质 |
| F02 | §4.3 | 地址映射正确性 | 每个地址区域访问对齐、属性 | UVM 系统级测试 | 100% 区域 × R/W |
| F03 | §5.3 | QoS / 带宽隔离 | 高优先级不被低优先级阻塞 | UVM traffic generator | 所有 QoS 配置 |
| F04 | §7.2 | 时钟频率/门控 | 各域频率正确、门控唤醒正确 | Formal / UVM | 所有时钟域 × 门控模式 |
| F05 | §8.3 | 功耗状态切换 | 所有电源状态的进入/退出 | UVM power sequence | 100% 状态转换 |
| F06 | §8.3 | 唤醒源 | 所有唤醒源的正确响应 | UVM | 100% 唤醒源 |
| F07 | §9.3 | 安全启动 | 签名验证失败→拒绝启动 | Formal / UVM | 所有签名场景 |
| F08 | §9.2 | TrustZone 隔离 | 非安全访问安全区域→拒绝 | Formal | 100% 隔离规则 |
| F09 | §6.3 | Pin Muxing | 所有复用组合无冲突 | Formal / UVM | 100% 配置组合 |
| F10 | §13.1 | DVFS 电压频率扫描 | 各 V/F 对功能正确 | 系统级测试 | 所有 DVFS 点 |
| F11 | §8.4 | 上电/掉电序列 | 电源域上下电顺序合规 | UVM power sequence | 100% 序列要求 |

### 14.2 无需 SoC 级验证的内容
- <!-- 单个模块内部功能 — 由模块级验证覆盖 -->
- <!-- DFT 模式下的功能 — 由 DFT ATPG/MBIST 覆盖 -->
- <!-- 软件兼容性 — 由软件测试覆盖 -->

---

## 附录 A: IP 清单

| IP | 类型 | 来源 | 版本 | 状态 | 交付日期 |
|----|------|------|------|------|---------|
| <!-- CPU Core --> | 处理器 | <!-- ARM / SiFive / 自研 --> | <!-- rev --> | <!-- 已交付/开发中 --> | |
| <!-- DDR Ctrl --> | 内存控制 | <!-- Synopsys / Cadence --> | <!-- rev --> | | |
| <!-- PCIe Ctrl --> | 高速 I/O | <!-- 第三方 --> | <!-- rev --> | | |
| <!-- ... --> | | | | | |

## 附录 B: 管脚列表摘要

| 管脚名 | 位置 | 方向 | 电压域 | 功能 | 复用 |
|--------|------|------|--------|------|------|
| <!-- PAD_NAME --> | <!-- A1 --> | I/O | VDD_IO | <!-- 功能描述 --> | <!-- 是否复用 --> |

## 附录 C: 术语表

| 术语 | 含义 |
|------|------|
| CMN | Coherent Mesh Network (ARM) |
| DSU | DynamIQ Shared Unit (ARM) |
| NoC | Network-on-Chip |
| PMU | Power Management Unit |
| OTP | One-Time Programmable (eFuse) |
| TRNG | True Random Number Generator |
| PUF | Physically Unclonable Function |
| DVFS | Dynamic Voltage and Frequency Scaling |
| WFI | Wait For Interrupt (CPU 指令) |

## 附录 D: 参考文档

| 文档 | 版本 | 来源 | 说明 |
|------|------|------|------|
| <!-- 芯片级规格书 01_product.PRD.md --> | <!-- V1.0 --> | <!-- link --> | 芯片级设计规格 |
| <!-- 工艺设计套件 --> | <!-- rev --> | <!-- Foundry --> | PDK 文档 |
| <!-- IP 数据手册 --> | <!-- rev --> | <!-- IP vendor --> | 各 IP 集成手册 |

---

*本文档由 Chip Design Agent 自动生成*
