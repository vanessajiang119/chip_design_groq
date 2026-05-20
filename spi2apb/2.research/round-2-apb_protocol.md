# 调研报告 — Round 2: APB 2.0 协议

> 生成日期: 2026-05-20
> 研究方向: APB 2.0 协议规范、PSLVERR/PREADY 握手、40bit 地址/128bit 数据

---

## 1. APB 2.0 协议概述

APB (Advanced Peripheral Bus) 是 ARM AMBA 总线体系中的低功耗外设总线。APB 2.0 (AMBA 3 APB) 增加了 PREADY 和 PSLVERR 信号，支持流水线传输和错误响应。

### 1.1 APB 2.0 信号列表

| 信号 | 方向 (Master) | 宽度 | 功能 |
|------|--------------|------|------|
| PCLK | 输入 | 1 | 总线时钟 |
| PRESETn | 输入 | 1 | 复位 (低有效) |
| PADDR | 输出 | 40 | 地址总线 |
| PWRITE | 输出 | 1 | 传输方向 (1=写, 0=读) |
| PSEL | 输出 | 1 | 从机选择 |
| PENABLE | 输出 | 1 | 使能信号 |
| PWDATA | 输出 | 128 | 写数据总线 |
| PRDATA | 输入 | 128 | 读数据总线 |
| PREADY | 输入 | 1 | 从机就绪信号 |
| PSLVERR | 输入 | 1 | 从机错误信号 |

### 1.2 状态机

APB 2.0 master 状态机包含三个状态:

```
                 ┌────────────────────────────────────┐
                 │                                    │
                 v                                    │
  ┌──────┐  PSEL=1  ┌───────┐  PENABLE=1  ┌────────┐ │
  │ IDLE ├─────────>│ SETUP ├────────────>│ ACCESS ├─┘
  └──────┘          └───────┘  PREADY=0   └────────┘
     ^                                          │
     │                                          │ PREADY=1
     └──────────────────────────────────────────┘
```

- **IDLE**: 无传输，PSEL=0, PENABLE=0
- **SETUP**: PSEL=1, PENABLE=0（保持 1 个 PCLK 周期）
- **ACCESS**: PSEL=1, PENABLE=1，等待 PREADY。若 PREADY=0，保持当前状态；若 PREADY=1，完成传输

### 1.3 传输时序

#### 基本读传输 (无等待)
```
PCLK    ┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐
PADDR   ──<Addr>──────────
PWRITE  ──0───────────────
PSEL    ────┌───┐─────────
PENABLE ──────┌───┐───────
PRDATA  ──────────<Data>──
PREADY  ────────┌───┐─────
PSLVERR ────────0─────────
```
T0=T1: IDLE → SETUP (地址和写信号在 SETUP 边沿变化)
T1=T2: SETUP → ACCESS (PENABLE 拉高)
T2=T3: PREADY=1，传输完成，回到 IDLE 或下一笔 SETUP

#### 带等待的写传输
```
PCLK    ┌┐┌┐┌┐┌┐┌┐┌┐┌┐┌┐
PADDR   ──<Addr>──────────
PWRITE  ──1───────────────
PSEL    ────┌───────┐─────
PENABLE ──────┌───────┐───
PWDATA  ──<Data>──────────
PREADY  ────────0───1─────
PSLVERR ────────0───0─────
```
T2=PREADY=0: 等待一个周期
T3=PREADY=1: 传输完成

### 1.4 PSLVERR 错误响应

当从机检测到错误条件（如非法地址、保护违规）时，在 ACCESS 状态拉高 PSLVERR:
- PSLVERR 在传输的最后一个周期 (PREADY=1) 有效
- Master 应记录错误状态并可通过中断报告
- 即使 PSLVERR=1，传输仍视为完成

### 1.5 40bit 地址空间

40bit 地址总线支持 1TB 地址空间。地址以 16 字节对齐 (128bit 数据总线):
- 地址位 [3:0] 可忽略 (128bit 对齐)
- 实际有效地址位 [39:4]
- APB 传输最小粒度为 16 字节

### 1.6 128bit 数据总线

| 特性 | 说明 |
|------|------|
| 数据宽度 | 128 bit |
| 对齐要求 | 16 字节对齐 |
| 写数据选通 | APB 2.0 标准支持 `PSTRB` (可选)，本设计简化处理 |
| 传输大小 | 每次传输 128 bit，不支持字节/半字/字写入 |

## 2. APB 2.0 Master 设计要点

### 2.1 Master 状态机设计

```
STATE: IDLE → SETUP → ACCESS → (PREADY?) → IDLE/SETUP

状态编码:
- IDLE:    2'b00
- SETUP:   2'b01
- ACCESS:  2'b10
```

### 2.2 传输控制

| 条件 | 下一状态 | 说明 |
|------|---------|------|
| IDLE + transfer_req | SETUP | 请求传输 |
| IDLE + no_req | IDLE | 保持空闲 |
| SETUP (always) | ACCESS | SETUP 仅 1 周期 |
| ACCESS + !PREADY | ACCESS | 等待从机 |
| ACCESS + PREADY + more_req | SETUP | 背靠背传输 |
| ACCESS + PREADY + !more_req | IDLE | 传输完成 |

### 2.3 与 SPI 侧的地址映射

SPI 命令中的 24/32bit 地址需要映射到 40bit APB 地址空间:
- 映射基地址通过配置寄存器 `APB_BASE_ADDR` 设置
- SPI 地址相对于基地址的偏移
- 公式: APB_ADDR[39:0] = BASE_ADDR[39:0] + {16'h0, SPI_ADDR[23:0]}

### 2.4 时序约束

```
create_clock -name pclk -period 10.000 [get_ports pclk]
set_output_delay -clock pclk -max 4.0 [get_ports "paddr pwrite psel penable pwdata"]
set_input_delay -clock pclk -max 4.0 [get_ports "prdata pready pslverr"]
```

---

**参考**: ARM AMBA 3 APB Protocol Specification (IHI 0024C)
