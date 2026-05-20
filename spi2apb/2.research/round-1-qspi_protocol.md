# 调研报告 — Round 1: QSPI 协议

> 生成日期: 2026-05-20
> 研究方向: QSPI 命令格式、时序约束、200MHz 接口要求

---

## 1. QSPI (Quad SPI) 协议概述

QSPI (Quad Serial Peripheral Interface) 是标准 SPI 的增强版本，支持 4-bit 并行数据 I/O，相比标准 SPI 可提供 4 倍数据传输速率。

### 1.1 QSPI 信号线

| 信号 | 方向 (从机视角) | 功能 |
|------|-----------------|------|
| SCLK | 输入 | 串行时钟，最高 200MHz |
| CS_N | 输入 | 片选 (低有效) |
| MOSI / IO0 | 输入/输出 | 主出从入 / 双向数据线 0 |
| MISO / IO1 | 输入/输出 | 主入从出 / 双向数据线 1 |
| IO2 | 输入/输出 | 双向数据线 2 (Quad 模式) |
| IO3 | 输入/输出 | 双向数据线 3 (Quad 模式) |

### 1.2 SPI Mode 0/3

| 模式 | CPOL | CPHA | 时钟极性 | 时钟相位 |
|------|------|------|---------|---------|
| Mode 0 | 0 | 0 | SCLK 空闲低电平 | 数据在上升沿采样 |
| Mode 3 | 1 | 1 | SCLK 空闲高电平 | 数据在上升沿采样 |

要求: Mode 0/3 可配，通过配置寄存器 `SPI_MODE` 位域选择。

### 1.3 QSPI 命令格式

标准 QSPI 命令序列包含三个阶段: 命令字节 → 地址字节 → 数据字节

#### 基本命令集

| 命令 | 编码 | 类型 | 地址 | 数据 I/O | 说明 |
|------|------|------|------|---------|------|
| READ | 0x03 | Standard SPI | 3/4 字节 | 1-bit (MOSI/MISO) | 标准读，不连续 |
| FAST_READ | 0x0B | Standard SPI | 3/4 字节 | 1-bit (MISO) | 快速读，8 个 dummy cycle |
| QUAD_OUTPUT | 0x6B | Quad SPI | 3/4 字节 | 4-bit (IO0-IO3) | Quad 输出读，8 dummy cycles |
| QUAD_IO | 0xEB | Quad SPI | 4-bit 地址 | 4-bit (IO0-IO3) | Quad IO 读，命令后 IO 切换 |
| WRITE | 0x02 | Standard SPI | 3/4 字节 | 1-bit (MOSI) | 标准写 |
| QUAD_INPUT | 0x32 | Quad SPI | 3/4 字节 | 4-bit (IO0-IO3) | Quad 输入写 |
| WRITE_ENABLE | 0x06 | — | 无 | 无 | 写使能 |

#### 命令序列时序

**READ (0x03) 时序**:
```
CS_N   \_________________________________________________/
SCLK   ┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐...
IO0    ──<Cmd:03><Addr[23:16]><Addr[15:8]><Addr[7:0]>───
IO1    ───────────────────────────────<Data[7:0]><Data>──
```

**QUAD_IO (0xEB) 时序**:
```
CS_N   \_______________________________________________________/
SCLK   ┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐...
IO0-3  <Cmd:EB><Addr[23:16]><Addr[15:8]><Addr[7:0]>┊DC┊<Data>
       └─── 1-bit ───┴──────── 4-bit ───────────┘┊  ┊└ 4-bit ─
```

### 1.4 200MHz 时序约束

200MHz QSPI 从机接口的关键时序参数如下:

| 参数 | 最小值 | 最大值 | 说明 |
|------|--------|-------|------|
| SCLK 频率 | — | 200 MHz | 时钟周期 5ns |
| SCLK 高电平宽度 | 2.0 ns | — | 占空比 40%/60% |
| SCLK 低电平宽度 | 2.0 ns | — | 占空比 40%/60% |
| CS_N setup to SCLK | 2.0 ns | — | 片选建立时间 |
| CS_N hold from SCLK | 2.0 ns | — | 片选保持时间 |
| Data input setup | 1.0 ns | — | 输入数据建立时间 |
| Data input hold | 1.0 ns | — | 输入数据保持时间 |
| Data output valid | — | 3.0 ns | 输出数据有效时间 |

### 1.5 QSPI 从机设计要点

- **时钟域**: SCLK 为外部输入时钟，需同步到系统时钟域 (或保持异步)
- **数据采样**: Mode 0/3 模式下均在 SCLK 上升沿采样，下降沿驱动
- **双向 IO 控制**: Quad 模式使用 IO0-IO3 双向端口，需 tristate 控制
- **CS_N 去抖**: CS_N 高有效间隔至少 1 SCLK 周期
- **突发传输**: 支持连续地址突发读/写

## 2. 时序约束分析

### 2.1 输入路径约束

```
create_clock -name sclk -period 5.000 [get_ports sclk]
set_input_delay -clock sclk -max 1.0 [get_ports "io0 io1 io2 io3 cs_n"]
set_input_delay -clock sclk -min 0.5 [get_ports "io0 io1 io2 io3 cs_n"]
```

### 2.2 输出路径约束

```
set_output_delay -clock sclk -max 3.0 [get_ports "io0 io1 io2 io3"]
set_output_delay -clock sclk -min 1.0 [get_ports "io0 io1 io2 io3"]
```

---

**参考来源**: JEDEC Standard SPI Flash 协议、常见 SPI Controller 设计文档
