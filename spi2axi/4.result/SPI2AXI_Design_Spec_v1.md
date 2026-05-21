# SPI2AXI Bridge 设计规格书

> SPI Slave to AXI4-Lite Master Bridge IP — 芯片调试与配置接口桥接模块
> 版本: v1.0 / 2026-05-21
> Block IP | SPI 50MHz / AXI4-Lite / QSPI

---

## 1. 模块概述 (Module Overview)

SPI2AXI IP 是一个将 SPI 从设备接口（SPI Slave）转换为 AXI 主设备接口（AXI4-Lite Master）的桥接模块。其核心设计目标是通过 SPI 总线实现对 SoC 内部 AXI 总线上的存储器和外设进行配置访问。

### 关键特性

| 特性类别 | 特性 | 描述 |
|---------|------|------|
| 接口协议 | SPI / QSPI | 支持 1-wire (标准 SPI) 和 4-wire (QSPI) 模式 |
| 接口协议 | AXI4-Lite | 5 通道 Master, AxLEN=0, AxSIZE=2, 32-bit |
| 跨时钟域 | Dual-Clock FIFO | 内置异步 FIFO 实现 SPI ↔ AXI CDC |
| 地址环绕 | Wrap 功能 | 可配置环绕窗口 (N×4 bytes) |
| 操作码 | Opcode-based | 8-bit opcode: READ/WRITE/REG_READ/REG_WRITE |

### 应用场景
- 系统调试和配置接口
- 低引脚数系统总线扩展
- 嵌入式系统固件更新
- 芯片测试和验证接口

![SPI2AXI 系统架构图](images/page1_img0.png)

---

## 2. 接口定义 (Interface Specification)

### SPI 接口信号

| 信号名称 | 方向 | 位宽 | 描述 |
|---------|------|------|------|
| spi_sclk | 输入 | 1 | SPI 串行时钟，最高 50MHz |
| spi_cs_n | 输入 | 1 | SPI 片选（低有效） |
| spi_sdi | 输入 | 4 | SPI 数据输入 (1-wire/4-wire) |
| spi_sdo | 输出 | 4 | SPI 数据输出 (1-wire/4-wire) |

### AXI4-Lite Master 接口

| 通道 | 信号前缀 | 描述 |
|------|---------|------|
| 写地址 (AW) | axi_aw* | awaddr[31:0], awvalid, awready, awprot[2:0] |
| 写数据 (W) | axi_w* | wdata[31:0], wstrb[3:0], wvalid, wready |
| 写响应 (B) | axi_b* | bresp[1:0], bvalid, bready |
| 读地址 (AR) | axi_ar* | araddr[31:0], arvalid, arready, arprot[2:0] |
| 读数据 (R) | axi_r* | rdata[31:0], rresp[1:0], rvalid, rready, rlast |

### 可配置参数

| 参数 | 默认值 | 描述 |
|------|--------|------|
| AXI_ADDR_WIDTH | 32 | AXI 地址总线宽度 |
| AXI_DATA_WIDTH | 32 | AXI 数据总线宽度 |
| AXI_ID_WIDTH | 3 | AXI ID 信号宽度 |
| DUMMY_CYCLES | 32 | SPI 读虚拟周期数 |

---

## 3. 子模块划分 (Sub-Module Partition)

| 子模块 | 类型 | 时钟域 | 职责 |
|--------|------|--------|------|
| spi_slave | 接口 | SPI (50MHz) | SPI 协议层处理，串并转换 |
| cmd_decoder | Ctrl FSM | SPI (50MHz) | 8-bit opcode 解码，AXI 传输控制 |
| async_fifo | FIFO | 双时钟 | 跨时钟域数据缓冲 (写FIFO + 读FIFO) |
| axi_master | 接口 | AXI | AXI4-Lite 5 通道 Master 引擎 |
| config_regs | 配置 | SPI | SPI 侧配置寄存器组 |
| wrap_ctrl | 地址控制 | AXI | 地址环绕逻辑 |

---

## 4. FSM 设计 (FSM Design)

### 状态编码

| 状态 | 编码 | 描述 |
|------|------|------|
| IDLE | 3'b000 | 空闲，等待 spi_cs_n 拉低 |
| OPCODE | 3'b001 | 接收 8-bit 操作码 |
| ADDR | 3'b010 | 接收 32-bit 地址 (MSB first) |
| DUMMY | 3'b011 | 插入可编程 dummy cycles |
| DATA | 3'b100 | 32-bit 数据传输 (MSB first) |
| RESPONSE | 3'b101 | AXI 写响应/读数据返回处理 |

### 状态转移
IDLE → OPCODE → ADDR → DUMMY → DATA → RESPONSE → IDLE

任意状态下 spi_cs_n 拉高 → IDLE (异常终止)

![SPI2AXI FSM 状态图](images/page4_img1.png)

---

## 5. 流水线设计 (Pipeline Design)

### 写操作序列
1. (可选) 配置 SPI 参数 (1线/4线模式)
2. SPI Master 发送写命令和地址
3. 控制器解析命令并同步到 AXI 时钟域
4. AXI 桥接发起写地址事务
5. 通过 FIFO 传输写数据
6. 等待 AXI 写响应完成

### 读操作序列
1. (可选) 配置 SPI 参数
2. SPI Master 发送读命令和地址
3. 控制器同步读请求到 AXI 时钟域
4. AXI 桥接发起读地址事务
5. 从 AXI 总线读取数据到 TX FIFO
6. 通过 SPI 接口返回读取的数据

---

## 6. 数据通路 (Datapath)

### 写数据通路
SPI SDI → 串并转换 → 写命令FIFO → CDC异步FIFO → AXI写数据通道 → AXI Slave

### 读数据通路
AXI Slave → AXI读数据通道 → CDC异步FIFO → TX FIFO → 并串转换 → SPI SDO

### 串并转换参数

| 模式 | 每SCLK传输位数 | 32-bit需SCLK数 |
|------|---------------|----------------|
| Standard SPI (1-wire) | 1 bit | 32 SCLK |
| Quad SPI (4-wire) | 4 bits | 8 SCLK |

---

## 7. 配置寄存器 (Configuration Registers)

| 地址 | 寄存器名称 | 属性 | 复位值 | 描述 |
|------|-----------|------|--------|------|
| 0x00 | SPI_CTRL | RW | 0x0000_0000 | SPI 控制: bit[0]=mode_sel |
| 0x04 | WRAP_CFG | RW | 0x0000_0000 | Wrap 配置: bit[7:0]=wrap_size |
| 0x08 | DUMMY_CFG | RW | 0x0000_0020 | Dummy 周期配置 |
| 0x0C | STATUS | RO | 0x0000_0001 | 状态: ready/busy/wr_done/rd_done |
| 0x10 | IP_ID | RO | 0x53495252 | IP 标识 "SIRR" |

![SPI 操作码表](images/page5_img0.png)
![SPI 寄存器设定](images/page5_img1.png)

---

## 8. 时钟与复位 (Clock & Reset)

| 时钟域 | 时钟源 | 频率 | 目标模块 |
|--------|--------|------|---------|
| SPI 时钟域 | 外部 SPI Master | 最高 50MHz | spi_slave, cmd_decoder, config_regs |
| AXI 时钟域 | SoC 系统时钟 | 取决于配置 | axi_master, wrap_ctrl |

CDC 路径: 写数据→异步FIFO, 读请求→脉冲同步器, 读返回→异步FIFO

---

## 9. 时序约束 (SDC Constraints)

关键 SDC 命令:
- `create_clock -name spi_sclk -period 20.0 [get_ports spi_sclk]`
- `create_clock -name axi_aclk -period 10.0 [get_ports axi_aclk]`
- `set_clock_groups -asynchronous -group [get_clocks spi_sclk] -group [get_clocks axi_aclk]`
- `set_false_path -from [get_clocks spi_sclk] -to [get_clocks axi_aclk]`
- `set_false_path -from [get_clocks axi_aclk] -to [get_clocks spi_sclk]`

---

## 10. 地址环绕 (Address Wrap)

- Wrap=0: 无环绕，地址持续递增
- Wrap=N: 环绕窗口 = N×4 字节

示例: Wrap=2, 起始地址 'h100
```
Burst 0: 'h100 → Burst 1: 'h104 → Burst 2: 'h100 → Burst 3: 'h104 → ...
```

![QSPI 写时序](images/page6_img0.png)
![QSPI 读时序](images/page6_img1.png)

---

## 11. 验证计划 (Verification Plan) — 待补充

建议验证点: SPI/QSPI 读写, 操作码解码, 地址环绕, Dummy 周期, CDC 传输, 寄存器访问, 异常处理

## 12. DFT 设计 (DFT Design) — 待补充

建议: 扫描链插入, 测试模式 MUX, 异步 FIFO MBIST

---

*Generated 2026-05-21 by chip-spec-gen · Based on SPI2AXI SPEC.pdf*
