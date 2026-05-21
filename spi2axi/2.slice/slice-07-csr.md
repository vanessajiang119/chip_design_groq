<!-- Source: source_raw.md 第5页, source_spec.md 第7章 -->
<!-- Chapter: 配置寄存器 (CSR) -->

# 配置寄存器 (CSR)

## 概述

SPI2AXI 模块包含 SPI 侧配置寄存器，用于配置 SPI 工作模式和 AXI 操作参数。寄存器通过 SPI 接口进行读写访问。

## SPI 命令操作码

SPI 命令操作码用于编码读/写操作及寄存器地址：

![SPI 命令操作码](images/page5_img0.png)
<!-- 第5页图片：SPI 命令操作码格式/编码表，展示读/写操作对应的操作码值及寄存器地址编码 -->

## SPI 侧寄存器设定

![SPI 侧寄存器设定](images/page5_img1.png)
<!-- 第5页图片：SPI 侧寄存器映射表，列出各寄存器的地址偏移、名称、位宽、读写属性和功能描述 -->

- SPI 侧寄存器用于配置工作模式
- 包括但不限于：
  - 1-wire / 4-wire 模式选择
  - 其他 SPI 协议参数

## 可配置参数

| 参数 (Parameter) | 默认值 (Default) | 描述 (Description) |
|---|---|---|
| `AXI_ADDR_WIDTH` | 32 | AXI 地址总线宽度 |
| `AXI_DATA_WIDTH` | 32 | AXI 数据总线宽度 |
| `AXI_ID_WIDTH` | 3 | AXI ID 信号宽度 |
| `DUMMY_CYCLES` | 32 | SPI 读操作虚拟周期数，实际 Dummy Cycle = 此处配置值 + 1 |

## SPI 寄存器读写

- 寄存器地址由操作码直接编码（无需 32-bit 地址字段）
- 寄存器访问时，FSM 跳过 ADDR 状态直接进入 DATA 状态
- 写寄存器：操作码 + 写数据 (32-bit)
- 读寄存器：操作码 + 虚拟周期 + 读数据 (32-bit)

## 建议寄存器列表

**待补充** — 具体寄存器地址映射、位域定义、复位值需在 LLD 阶段详细定义：

| 偏移地址 | 寄存器名称 | 位宽 | 属性 | 默认值 | 描述 |
|---|---|---|---|---|---|
| 0x00 | CTRL | 32 | R/W | 0x0 | 控制寄存器（模式选择、Wrap使能、软复位） |
| 0x04 | STATUS | 32 | RO | — | 状态寄存器（FIFO状态、忙标志、错误标志） |
| 0x08 | DUMMY_CFG | 32 | R/W | 0x20 | 虚拟周期配置（对应 DUMMY_CYCLES 参数） |
| 0x0C | WRAP_CFG | 32 | R/W | 0x0 | Wrap 配置寄存器（Wrap 窗口大小 N） |
| 0x10 | FIFO_STATUS | 32 | RO | — | FIFO 状态寄存器（空/满标志、计数） |

![SPI 寄存器配置关系](images/page5_img2.png)
<!-- 第5页另一张图片：SPI 寄存器配置关系图或参数配置说明 -->
