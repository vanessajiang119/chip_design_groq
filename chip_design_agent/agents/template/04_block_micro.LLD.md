# 模块微架构规格书 — AI-Executable LLD Template

> **模块名称:**
> **版本:** V1.0
> **日期:**
> **状态:** Draft / Review / Final
> **层次路径:** (top.chip.subsystem.module)
> **工艺节点:**
> **目标频率:**

---

## 1. Module Overview

### 1.1 Module Identity
<!-- 一句话精确定义该模块的身份和职责 -->

| 属性 | 值 |
|------|-----|
| 模块全名 | `<ModuleName>` |
| 层次路径 | `<top.chip.subsystem.module>` |
| 工艺 / PVT | `<工艺节点>, SS/0.9V/125°C (worst case)` |
| 目标频率 | `<MHz>` |
| 供电电压 | `<VDD_CORE=V, VDD_IO=V>` |
| 面积预算 | `<kgates / um²>` |
| 功耗预算 | `<mW active / mW idle>` |

### 1.2 Top-Level Ports Summary

| Port Group | Direction | Width | Description |
|------------|-----------|-------|-------------|
| `clk` | input | 1 | 主时钟 @ `<freq>` MHz |
| `rst_n` | input | 1 | 异步复位, 低有效 |
| `bus_*` | in/out | `<W>` | 总线接口信号组 |
| `data_*` | in/out | `<W>` | 数据面信号组 |
| `ctrl_*` | in/out | `<W>` | 控制/状态信号组 |
| `interrupt` | output | 1 | 中断输出 |

### 1.3 Module Features
<!-- 功能特性清单，每条应能直接映射到 RTL 的 feature enable 或 ifdef -->
- [ ] Feature 1: `<简要描述>`
- [ ] Feature 2: `<简要描述>`
- [ ] Feature 3: `<简要描述>`

### 1.4 Design Assumptions
<!-- 关键假设，不成立则功能不正确 -->
- A1: `<假设描述>`
- A2: `<假设描述>`

---

## 2. Interface Specification

### 2.1 Port Signal Table

| Signal Name | Direction | Width | Type | Clock Domain | Reset Domain | I/O Pad | Description |
|-------------|-----------|-------|------|-------------|-------------|---------|-------------|
| `clk_i` | input | 1 | clock | — | — | no | 全局时钟 |
| `rst_ni` | input | 1 | reset async active-low | — | — | no | 异步复位 |
| <!-- example: apb_paddr_i --> | input | 12 | data | clk_i | rst_ni | no | APB 地址总线 |
| <!-- example: apb_pwdata_i --> | input | 32 | data | clk_i | rst_ni | no | APB 写数据 |
| <!-- example: apb_prdata_o --> | output | 32 | data | clk_i | rst_ni | no | APB 读数据 |
| <!-- ... --> | | | | | | | |

### 2.2 Cycle-Level Timing Diagrams

#### 2.2.1 Bus Write Timing
<!-- 用 ASCII waveform 精确描述每个 clock 周期的信号行为 -->
```
Clock Cycle:      T0        T1        T2        T3        T4
clk_i           █▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█
                ───┘     └───┘     └───┘     └───┘     └───
psel_i          __________███_____________________________
penable_i       ___________________███____________________
pwrite_i        __________███_____________________________
paddr_i         XXXXXXXX<ADDR>XXXXXXXXXXXXXXXXXXXXXXXXXXXX
pwdata_i        XXXXXXXX<DATA>XXXXXXXXXXXXXXXXXXXXXXXXXXXX
pready_o        ___________________███____________________
pslverr_o       __________________________________________
prdata_o        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**Cycle Description**:
- **T0**: psel 和 paddr/pwrite 在时钟上升沿前有效
- **T1**: penable 拉高，数据在 pwdata 上有效
- **T2**: 模块将 pready 拉高一个周期，写操作完成
- **T3~T4**: 总线回到 IDLE

> **Write with Wait States**: 当模块无法在 T2 完成时，pready 保持低电平，penable 保持高，直到模块准备好：
> ```
> Clock Cycle:      T0    T1    T2    T3    T4    T5
> psel_i          _____███_________________________
> penable_i       _____________███___███___███_____
> paddr_i         XXXXX<ADDR>XXXXXXXXXXXXXXXXXXXXXX
> pwdata_i        XXXXX<DATA>XXXXXXXXXXXXXXXXXXXXXX
> pready_o        _____________________________███_
> ```

#### 2.2.2 Bus Read Timing
<!-- 读时序，包括 prdata 有效的精确时刻 -->
```
Clock Cycle:      T0        T1        T2        T3        T4
clk_i           █▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█
psel_i          __________███_____________________________
penable_i       ___________________███____________________
pwrite_i        __________0_______________________________
paddr_i         XXXXXXXX<ADDR>XXXXXXXXXXXXXXXXXXXXXXXXXXXX
pready_o        ___________________███____________________
prdata_o        XXXXXXXXXXXXXXXXXX<RDATA>XXXXXXXXXXXXXXXXX
```

**Read Cycle**:
- T0: psel, paddr 有效，pwrite=0
- T1: penable 拉高
- T2: pready 拉高，prdata 在 T2 上升沿后有效
- After T2: 寄存器读数据被采样

#### 2.2.3 Data Path Handshake (Valid/Ready)
```
Clock Cycle:      T0    T1    T2    T3    T4    T5    T6    T7
clk_i           █▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█▁█
src_valid       ███████_______________________███████_____
src_data        XX<D0>XXXXXXXXXXXXXXXXXXXXXXXXX<D1><D2>XXX
dst_ready       ████████████___________________███████_____
dst_valid       ________________███████___________________
dst_data        XXXXXXXXXXXXXX<D0>XXXXXXXXXXXXXXXXXXXXXXXXX
```

**Handshake Rules**:
1. `src_valid` 和 `src_data` 在 T0 上升沿前有效
2. `dst_ready` 在 T1 上升沿采样 valid && ready → 传输发生
3. 当 `src_valid && dst_ready` 在同一个周期为高时，数据在时钟上升沿被捕获
4. 背压条件: `dst_ready` 拉低 → 上游保持数据
5. 背压释放: `dst_ready` 恢复高 → 传输继续

### 2.3 Backpressure Behavior

| Condition | Backpressure Action | Latency Impact | RTL Implementation |
|-----------|--------------------|----------------|-------------------|
| 输出 FIFO 半满 | 下一周期暂停输入采样 | 1 cycle drain | `valid_i & ready_o → stall_nxt` |
| 输出 FIFO 几乎满 | 立即暂停(零周期容忍) | 0 cycle | `almost_full → stall` (组合) |
| 输出 FIFO 满 | 丢弃(报错) | — | `full → error_flag` |
| 输入 FIFO 空 | 输出端插入气泡(管道气泡) | 1 cycle | `empty → valid_o = 0` |

### 2.4 Interrupt Interface

| Interrupt | Source Event | Trigger Type | Clear Mechanism | Polarity |
|-----------|-------------|-------------|-----------------|----------|
| `intr_o` | Event_X | Pulse (1 cycle) | Write-1-clear to INT_STAT | Level high |
| `intr_o` | Event_Y | Level | Auto-clear on read | Level high |

> **Interrupt Aggregation**: 所有中断事件通过 OR 树合并为一个输出。每个事件有独立的 enable 位和 status 位。

---

## 3. Sub-Module Partition

### 3.1 Block Diagram
```
┌─────────────────────────────────────────────────────────────────────┐
│                       <Module_Name>                                  │
│                                                                     │
│  ┌─────────────────────┐    ┌──────────────────────────────────┐    │
│  │  SubModule_A        │    │  SubModule_B                     │    │
│  │  ┌───────────────┐  │    │  ┌────────────────────────────┐  │    │
│  │  │ comb_logic    │──┼────┼──┤ pipeline_stage0            │  │    │
│  │  └───────────────┘  │    │  ├────────────────────────────┤  │    │
│  │                     │    │  │ pipeline_stage1            │  │    │
│  └─────────────────────┘    │  ├────────────────────────────┤  │    │
│                             │  │ pipeline_stage2            │  │    │
│  ┌─────────────────────┐    │  └────────────────────────────┘  │    │
│  │  CSR_Block          │    └──────────────────────────────────┘    │
│  │  reg [31:0] ctrl    │                                           │
│  │  reg [31:0] stat    │    ┌──────────────────────────────────┐    │
│  │  reg [31:0] conf    │    │  FSM_Controller                  │    │
│  └─────────┬───────────┘    │  state: {IDLE, BUSY, DONE, ERR} │    │
│            │ csr_bus        └──────────────┬───────────────────┘    │
│            ▼                               │ ctrl_signals           │
│  ┌─────────────────────────────────────────┴────────────────────┐   │
│  │               Clock & Reset / Power Ctrl                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Sub-Module Responsibilities

| Sub-Module | Input From | Output To | Width | Function |
|------------|-----------|-----------|-------|----------|
| SubModule_A | bus interface | SubModule_B | `<W>` | 协议解析、地址译码 |
| SubModule_B | SubModule_A, CSR | CSR, SubModule_C | `<W>` | 核心数据处理流水线 |
| SubModule_C | SubModule_B | bus/data output | `<W>` | 输出组合、错误检测 |
| CSR_Block | bus write | all modules | 32 | 配置/状态寄存器文件 |
| FSM_Controller | CSR, SubModule_B status | all modules | — | 主状态机 |

### 3.3 Inter-Module Signal Table

| Signal | Width | Source | Sink | Description |
|--------|-------|--------|------|-------------|
| `csr_ctrl_enable` | 1 | CSR | FSM | 模块使能位 |
| `csr_ctrl_mode` | 2 | CSR | FSM | 模式选择: 00=manual, 01=auto, 10/11=reserved |
| `fsm_state_busy` | 1 | FSM | CSR | 状态机 busy 指示 |
| `pipe_data_valid` | 1 | SubModule_B | SubModule_C | 流水线输出有效 |
| `pipe_data` | `<W>` | SubModule_B | SubModule_C | 流水线数据 |
| `error_flag` | 1 | SubModule_C | CSR | 错误标志 |

---

## 4. FSM Specification

### 4.1 State Encoding Table

| State Name | Encoding | Description |
|------------|----------|-------------|
| `IDLE` | `3'b000` | 空闲/复位状态, 等待 enable |
| `SETUP` | `3'b001` | 配置加载/初始化 |
| `BUSY` | `3'b010` | 核心处理中 |
| `WAIT` | `3'b011` | 等待外部条件 |
| `DONE` | `3'b100` | 操作完成，准备提交结果 |
| `ERROR` | `3'b101` | 错误状态 |
| `3'b110` | — | **RESERVED** (decode to IDLE for safety) |
| `3'b111` | — | **RESERVED** (decode to IDLE for safety) |

> **Safety**: 未使用的编码 (110, 111) 必须解码为 IDLE 或 ERROR，防止 FSM 锁死。

### 4.2 State Transition Matrix

| Current State | Condition | Next State | Transition Action |
|--------------|-----------|------------|------------------|
| `IDLE` | `enable == 1` | `SETUP` | 清除所有状态标志 |
| `IDLE` | `enable == 0` | `IDLE` | 保持(无操作) |
| `SETUP` | `cfg_loaded == 1` | `BUSY` | 锁存配置参数 |
| `SETUP` | `cfg_loaded == 0` | `SETUP` | 等待配置加载 |
| `SETUP` | `timeout == 1` | `ERROR` | 配置超时报错 |
| `BUSY` | `done == 0 && error == 0` | `BUSY` | 持续处理 |
| `BUSY` | `done == 1` | `DONE` | 设置完成标志 |
| `BUSY` | `error == 1` | `ERROR` | 捕获错误码 |
| `BUSY` | `backpressure == 1` | `WAIT` | 暂停处理，保存中间状态 |
| `WAIT` | `backpressure == 0` | `BUSY` | 恢复处理 |
| `DONE` | `sw_clear == 1` | `IDLE` | 软件写清除 |
| `ERROR` | `sw_reset == 1` | `IDLE` | 软件复位 |

> **Transition Rules**:
> - 所有状态在 `rst_ni` 断言时无条件回到 `IDLE`
> - 优先级: `error > done > backpressure`
> - 每个时钟周期只评估一次状态迁移

### 4.3 Output Decode Table

| Output Signal | IDLE | SETUP | BUSY | WAIT | DONE | ERROR |
|---------------|------|-------|------|------|------|-------|
| `busy_o` | 0 | 0 | 1 | 1 | 0 | 0 |
| `done_o` | 0 | 0 | 0 | 0 | 1 | 0 |
| `error_o` | 0 | 0 | 0 | 0 | 0 | 1 |
| `pipe_en` | 0 | 0 | 1 | 0 | 0 | 0 |
| `clr_all_flags` | 1 | 0 | 0 | 0 | 0 | 0 |

> **Output Decode Logic**: 纯组合逻辑 `always_comb`，不引入额外 clock 周期。

### 4.4 FSM RTL Implementation Template

```systemverilog
//=============================================================================
// FSM: <ModuleName>_ctrl_fsm
//=============================================================================
typedef enum logic [2:0] {
    ST_IDLE  = 3'b000,
    ST_SETUP = 3'b001,
    ST_BUSY  = 3'b010,
    ST_WAIT  = 3'b011,
    ST_DONE  = 3'b100,
    ST_ERROR = 3'b101
} state_t;

state_t state_q, next_state;

// State register (sequential)
always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni)
        state_q <= ST_IDLE;
    else
        state_q <= next_state;
end

// Next state logic (combinational)
always_comb begin
    next_state = state_q;  // default: stay
    unique case (state_q)
        ST_IDLE:  if (enable_i)    next_state = ST_SETUP;
        ST_SETUP: if (cfg_loaded)  next_state = ST_BUSY;
                   else if (timeout) next_state = ST_ERROR;
        ST_BUSY:  if (error_i)     next_state = ST_ERROR;
                   else if (done_i)    next_state = ST_DONE;
                   else if (bpressure) next_state = ST_WAIT;
        ST_WAIT:  if (!bpressure)  next_state = ST_BUSY;
        ST_DONE:  if (sw_clear)    next_state = ST_IDLE;
        ST_ERROR: if (sw_reset)    next_state = ST_IDLE;
        default:  next_state = ST_IDLE;  // safety decode
    endcase
end

// Output decode (combinational)
always_comb begin
    busy_o   = (state_q == ST_BUSY  || state_q == ST_WAIT);
    done_o   = (state_q == ST_DONE);
    error_o  = (state_q == ST_ERROR);
    pipe_en  = (state_q == ST_BUSY);
    // ...
end
```

---

## 5. Pipeline Specification

### 5.1 Pipeline Stage Definition

| Stage Name | Stage ID | Data Width | Latency (cycles) | Description |
|------------|----------|-----------|-----------------|-------------|
| `STG_IN` | 0 | `<W>` | 1 | 输入采样 + valid/ready 握手 |
| `STG_ALIGN` | 1 | `<W>` | 1 | 数据对齐/字节交换 |
| `STG_PROC` | 2 | `<W>` | N-1 | 核心处理（多周期） |
| `STG_OUT` | 3 | `<W>` | 1 | 输出缓冲 + valid 生成 |

### 5.2 Cycle-by-Cycle Behavior Table

下表描述了每个流水线级在每个时钟周期的行为。S=Setup, H=Hold, B=Bubble, F=Flush:

| Cycle | STG_IN (stage 0) | STG_ALIGN (stage 1) | STG_PROC (stage 2) | STG_OUT (stage 3) |
|-------|------------------|--------------------|-----------------|-----------------|
| 1 | S: 采样输入数据 | B: 气泡(无效) | B: 气泡(无效) | B: 气泡(无效) |
| 2 | S: 采样下一个 | S: 转发 stage0 数据 | B: 气泡 | B: 气泡 |
| 3 | S: 持续采样 | S: 持续转发 | S: 处理 stage1 数据 | B: 气泡 |
| 4 | S | S | H: 多周期处理中 | B: 气泡 |
| 5 | S | S | S: 处理完成 | S: 输出 stage2 结果 |
| 6 | S | S | S | S: 输出有效, valid_o=1 |

### 5.3 Stall / Hold / Flush Conditions

| Condition | Action | Stages Affected | Recovery |
|-----------|--------|----------------|----------|
| 输出 FIFO 满 | Stall (暂停) | STG_OUT (hold) | 下游取走后恢复 |
| 上游数据未就绪 | Bubble (气泡) | STG_IN 插入气泡 | 上游 valid=1 时恢复 |
| 全局 flush 信号 | Flush (冲刷) | 所有 stage 清空 | flush 释放后正常流水 |
| 检测到错误 | Flush (冲刷) | 清空所有 pending 数据 | error 处理完成后 |

**Stall 传播**:
```
STG_OUT stall ←─ STG_PROC hold ←─ STG_ALIGN hold ←─ STG_IN hold
```
当 STG_OUT 暂停时，stall 信号逐级向上游传播，确保流水线不会丢失数据。

### 5.4 Bypass Paths

| Bypass From | Bypass To | Condition | Latency Saved |
|-------------|-----------|-----------|---------------|
| STG_PROC output | STG_ALIGN input | 数据相关性 + 同一周期 | 2 cycles |
| STG_OUT output | STG_IN input | 回环模式 | 1 cycle |

---

## 6. Datapath Specification

### 6.1 ALU / Operation Table

| Operation | Opcode | Width | Latency | Description |
|-----------|--------|-------|---------|-------------|
| ADD | 4'b0000 | 32 | 1 | 加法 |
| SUB | 4'b0001 | 32 | 1 | 减法 |
| AND | 4'b0010 | 32 | 1 | 按位与 |
| OR | 4'b0011 | 32 | 1 | 按位或 |
| XOR | 4'b0100 | 32 | 1 | 按位异或 |
| SHL | 4'b0101 | 32 | 1 | 逻辑左移 |
| SHR | 4'b0110 | 32 | 1 | 逻辑右移 |
| CMP_EQ | 4'b1000 | 1 | 1 | 相等比较(输出 1-bit) |
| CMP_GT | 4'b1001 | 1 | 1 | 大于比较(输出 1-bit) |

### 6.2 Mux Select Encoding

| Mux Name | Select Width | Select Value | Source | Destination |
|----------|-------------|--------------|--------|-------------|
| `mux_datain_src` | 2 | 00: bus_data | data pipeline input | 数据路径入口 |
| | | 01: csr_data | | |
| | | 10: bypass_data | | |
| `mux_result_sel` | 2 | 00: alu_result | ALU 输出 | 输出寄存器/FIFO |
| | | 01: shift_result | | |
| | | 10: const_zero | | |

### 6.3 Datapath Widths

| Datapath Segment | Width | Rationale |
|-----------------|-------|-----------|
| 输入总线接口 | 32 | APB/AXI-Lite 标准位宽 |
| ALU 输入 A | 32 | 与总线位宽对齐 |
| ALU 输入 B | 32 | |
| ALU 结果 | 32 | |
| 比较器输出 | 1 | 单 bit 比较结果 |
| 内部计数器 | 32 | 计时/计数上限 |

### 6.4 Datapath RTL Implementation Template

```systemverilog
//=============================================================================
// Datapath: ALU + Mux
//=============================================================================

// Input mux
always_comb begin
    unique case (mux_datain_src_q)
        2'b00:   alu_a = bus_data_i;
        2'b01:   alu_a = csr_data_i;
        2'b10:   alu_a = bypass_data;
        default: alu_a = '0;
    endcase
end

// ALU
always_comb begin
    alu_result = '0;
    unique case (alu_opcode_q)
        4'b0000: alu_result = alu_a + alu_b;
        4'b0001: alu_result = alu_a - alu_b;
        4'b0010: alu_result = alu_a & alu_b;
        4'b0011: alu_result = alu_a | alu_b;
        4'b0100: alu_result = alu_a ^ alu_b;
        4'b0101: alu_result = alu_a << shift_amt;
        4'b0110: alu_result = alu_a >> shift_amt;
        default: alu_result = '0;
    endcase
end
```

---

## 7. CSR Register Map

### 7.1 Address Map Overview

| Address Offset | Register Name | Width | Attribute | Reset Value | Description |
|---------------|---------------|-------|-----------|-------------|-------------|
| `0x00` | CTRL | 32 | RW | `0x0000_0000` | 控制寄存器 |
| `0x04` | STATUS | 32 | RO/W1C | `0x0000_0000` | 状态寄存器 |
| `0x08` | INT_EN | 32 | RW | `0x0000_0000` | 中断使能 |
| `0x0C` | INT_STAT | 32 | W1C | `0x0000_0000` | 中断状态 |
| `0x10` | CONF0 | 32 | RW | `0x0000_0001` | 配置寄存器 0 |
| `0x14` | CONF1 | 32 | RW | `0x0000_0000` | 配置寄存器 1 |
| `0x18` | DATA_IN | 32 | WO | `0x0000_0000` | 数据输入 |
| `0x1C` | DATA_OUT | 32 | RO | `0x0000_0000` | 数据输出 |
| `0x20`–`0xFF` | — | — | RES | — | Reserved (返回 0) |

> **CSR 编码约定**: 未使用的地址空间必须返回 0 读值，写忽略。防止非法地址访问导致功能异常。

### 7.2 Bit-Level Field Definitions

#### 7.2.1 CTRL (0x00) — Control Register

| Bit Field | Bit(s) | Attribute | Reset | HW Set Condition | HW Clear Condition | Description |
|-----------|--------|-----------|-------|-------------------|-------------------|-------------|
| `enable` | 0 | RW | 1'b0 | 软件写 1 | 软件写 0 | 模块全局使能 |
| `soft_rst` | 1 | RW | 1'b0 | 软件写 1 | 软件写 0 | 软复位(自清除) |
| `mode` | 3:2 | RW | 2'b00 | 软件配置 | 软件配置 | 00=manual, 01=auto, 10/11=inv |
| `reserved` | 31:4 | RES | 28'b0 | — | — | 读返回 0 |

> **Self-Clear Bit**: `soft_rst` 在置位后的下一个时钟周期自动清除（需要一个 HW clear 条件）。

#### 7.2.2 STATUS (0x04) — Status Register

| Bit Field | Bit(s) | Attribute | Reset | HW Set Condition | HW Clear Condition | Description |
|-----------|--------|-----------|-------|-------------------|-------------------|-------------|
| `busy` | 0 | RO | 1'b0 | FSM → BUSY | FSM → IDLE/DONE/ERR | 模块忙碌中 |
| `done` | 1 | W1C | 1'b0 | FSM → DONE | 软件写 1 清除 | 操作完成 |
| `error` | 2 | W1C | 1'b0 | FSM → ERROR | 软件写 1 清除 | 错误标志 |
| `fifo_full` | 3 | RO | 1'b0 | FIFO 满 | FIFO 非满 | FIFO 满标志 |
| `fifo_empty` | 4 | RO | 1'b0 | FIFO 空 | FIFO 非空 | FIFO 空标志 |
| `reserved` | 31:5 | RES | 27'b0 | — | — | 读返回 0 |

> **W1C (Write-1-to-Clear)**: 软件向该位写 1 时清除；写 0 无影响。硬件设置优先级高于软件清除。

#### 7.2.3 INT_EN (0x08) — Interrupt Enable

| Bit Field | Bit(s) | Attribute | Reset | Description |
|-----------|--------|-----------|-------|-------------|
| `done_int_en` | 0 | RW | 1'b0 | done 事件中断使能 |
| `error_int_en` | 1 | RW | 1'b0 | error 事件中断使能 |
| `reserved` | 31:2 | RES | 30'b0 | — |

#### 7.2.4 INT_STAT (0x0C) — Interrupt Status

| Bit Field | Bit(s) | Attribute | Reset | HW Set Condition | HW Clear Condition | Description |
|-----------|--------|-----------|-------|-------------------|-------------------|-------------|
| `done_int` | 0 | W1C | 1'b0 | FSM → DONE & INT_EN[0]=1 | 软件写 1 | Done 中断挂起 |
| `error_int` | 1 | W1C | 1'b0 | FSM → ERROR & INT_EN[1]=1 | 软件写 1 | Error 中断挂起 |
| `reserved` | 31:2 | RES | 30'b0 | — | — | — |

#### 7.2.5 CONF0 (0x10) — Configuration Register 0

| Bit Field | Bit(s) | Attribute | Reset | Description |
|-----------|--------|-----------|-------|-------------|
| `threshold` | 7:0 | RW | 8'd16 | FIFO 水位阈值 |
| `burst_len` | 11:8 | RW | 4'd8 | 突发长度 (1~16) |
| `reserved` | 31:12 | RES | 20'b0 | — |

### 7.3 CSR RTL Implementation Template

```systemverilog
//=============================================================================
// CSR Read/Write Logic
//=============================================================================

// Write decode
always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
        ctrl_reg       <= 32'b0;
        int_en_reg     <= 32'b0;
        conf0_reg      <= 32'h0000_0010;
        // ... other RW registers
    end else if (write_en) begin
        unique case (write_addr)
            ADDR_CTRL:   ctrl_reg   <= write_data;
            ADDR_INT_EN: int_en_reg <= write_data;
            ADDR_CONF0:  conf0_reg  <= write_data;
            default: ;  // ignore reserved addresses
        endcase
    end
end

// Read mux (combinational)
always_comb begin
    unique case (read_addr)
        ADDR_CTRL:    read_data = ctrl_reg;
        ADDR_STATUS:  read_data = status_reg;
        ADDR_INT_EN:  read_data = int_en_reg;
        ADDR_INT_STAT: read_data = int_stat_reg;
        ADDR_CONF0:   read_data = conf0_reg;
        default:      read_data = 32'b0;  // reserved → safe value
    endcase
end
```

### 7.4 UVM Register Model Alignment

| Register Name | UVM Register Name | Width | Access Policy |
|---------------|-------------------|-------|---------------|
| CTRL | `uvm_ctrl` | 32 | `UVM_REG` |
| STATUS | `uvm_status` | 32 | `UVM_RO` |
| INT_EN | `uvm_int_en` | 32 | `UVM_REG` |
| INT_STAT | `uvm_int_stat` | 32 | `UVM_W1C` |
| CONF0 | `uvm_conf0` | 32 | `UVM_REG` |

---

## 8. Clock & Reset Architecture

### 8.1 Clock Domains

| Domain Name | Source | Frequency | Divider | Duty Cycle | Jitter (pk-pk) |
|-------------|--------|-----------|---------|------------|----------------|
| `clk_core` | PLL output | `<FREQ>` MHz | 1 | 50/50 | <100ps |
| `clk_bus` | PLL output | `<FREQ/2>` MHz | 2 | 50/50 | <100ps |
| `clk_slow` | clk_core div | `<FREQ/4>` MHz | 4 | 50/50 | <200ps |

### 8.2 Clock Relationships

| Domain A | Domain B | Relationship | Synchronous? | CDC Method |
|----------|----------|--------------|-------------|------------|
| `clk_core` | `clk_bus` | Integer ratio (2:1) | Yes | Phase-aware |
| `clk_core` | `clk_slow` | Integer ratio (4:1) | Yes | Phase-aware |
| `clk_core` | `ext_clk` | Unknown | No | 2-flop synchronizer |

### 8.3 CDC Paths

| Source Domain | Dest Domain | Signal(s) | Width | CDC Scheme | Latency |
|-------------|------------|-----------|-------|------------|---------|
| `clk_core` | `ext_clk` | `intr_o` | 1 | 2-flop sync + toggle | 2~3 cycles |
| `ext_clk` | `clk_core` | `ext_data_valid` | 1 | 2-flop sync | 2 cycles |
| `ext_clk` | `clk_core` | `ext_data` | 32 | async FIFO (2-deep) | 4~8 cycles |

### 8.4 Reset Architecture

| Reset Signal | Type | Domain | Assert | Deassert | Description |
|-------------|------|--------|--------|----------|-------------|
| `rst_ni` | Async, active-low | global | async | synchronous | SoC 级复位输入 |
| `rst_core_n` | Async, active-low | `clk_core` | async | sync to clk_core | 内核复位同步 |
| `rst_bus_n` | Async, active-low | `clk_bus` | async | sync to clk_bus | 总线复位同步 |
| `soft_rst_n` | Sync | `clk_core` | sync | sync | 软复位(CSR 控制) |

```systemverilog
//=============================================================================
// Reset Synchronizer Template
//=============================================================================
// Async assert, synchronous deassert for clk_core domain
logic rst_core_n_r1, rst_core_n;
always_ff @(posedge clk_core_i or negedge rst_ni) begin
    if (!rst_ni) begin
        rst_core_n_r1 <= 1'b0;
        rst_core_n    <= 1'b0;
    end else begin
        rst_core_n_r1 <= 1'b1;
        rst_core_n    <= rst_core_n_r1;
    end
end
```

---

## 9. Timing Constraints (SDC)

### 9.1 Master Clock Definitions

```tcl
#=============================================================================
# SDC: <Module_Name> Timing Constraints
#=============================================================================
# 文件: <module_name>.sdc
# 生成: chip-pipeline s7_timing_closure
# 工艺: <technology_node>
# 版本: V1.0

#---------------------------------------------------------------------------
# 1. Clock Definitions
#---------------------------------------------------------------------------

# Primary clock: core clock
create_clock -name clk_core -period <period_ns> \
    [get_ports clk_core_i]

# Bus clock (derived from core)
create_clock -name clk_bus -period [expr {<period_ns> * 2}] \
    [get_ports clk_bus_i]

# Generated clock: slow clock from divider
# create_generated_clock -name clk_slow -source [get_ports clk_core_i] \
#     -divide_by 4 [get_pins <divider_reg>/Q]

#---------------------------------------------------------------------------
# 2. Clock Groups (asynchronous / exclusive)
#---------------------------------------------------------------------------

# These clocks do not need timing analysis between them
set_clock_groups -asynchronous \
    -group { clk_core clk_bus } \
    -group { clk_slow }

#---------------------------------------------------------------------------
# 3. Input Delays
#---------------------------------------------------------------------------

# Bus interface inputs (relative to clk_core)
set_input_delay -clock clk_core -max <max_in_delay_ns> \
    [get_ports apb_*]
set_input_delay -clock clk_core -min <min_in_delay_ns> \
    [get_ports apb_*]

# Data inputs
set_input_delay -clock clk_core -max <max_in_delay_ns> \
    [get_ports data_* -filter "direction==in"]
set_input_delay -clock clk_core -min <min_in_delay_ns> \
    [get_ports data_* -filter "direction==in"]

#---------------------------------------------------------------------------
# 4. Output Delays
#---------------------------------------------------------------------------

set_output_delay -clock clk_core -max <max_out_delay_ns> \
    [get_ports apb_*]
set_output_delay -clock clk_core -min <min_out_delay_ns> \
    [get_ports apb_*]

set_output_delay -clock clk_core -max <max_out_delay_ns> \
    [get_ports data_* -filter "direction==out"]
set_output_delay -clock clk_core -min <min_out_delay_ns> \
    [get_ports data_* -filter "direction==out"]

#---------------------------------------------------------------------------
# 5. False Paths
#---------------------------------------------------------------------------

# Async reset synchronization (already handled by sync cell)
set_false_path -from [get_ports rst_ni]
set_false_path -to [get_ports rst_ni]

# Test mode signals (not timing-critical in functional mode)
set_false_path -from [get_ports test_mode_i]

# Status outputs (no timing requirement)
set_false_path -to [get_ports intr_o]

# CDC paths (covered by synchronizers)
set_false_path -from [get_clocks clk_core] -to [get_clocks ext_clk]
set_false_path -from [get_clocks ext_clk] -to [get_clocks clk_core]

#---------------------------------------------------------------------------
# 6. Multicycle Paths
#---------------------------------------------------------------------------

# Slow status register reads can take 2 cycles
set_multicycle_path -setup 2 -from [get_clocks clk_core] \
    -to [get_pins <status_reg_reg>/D]
set_multicycle_path -hold 1 -from [get_clocks clk_core] \
    -to [get_pins <status_reg_reg>/D]

#---------------------------------------------------------------------------
# 7. Clock Transition / Load
#---------------------------------------------------------------------------

set_clock_transition -rise 0.1 [get_clocks clk_core]
set_clock_transition -fall 0.1 [get_clocks clk_core]

set_ideal_network [get_ports rst_ni]
set_ideal_network [get_ports clk_*]
```

### 9.2 SDC Constraint Derivation Guide

| Constraint Type | Derivation Method | Typical Value |
|----------------|-------------------|---------------|
| `create_clock -period` | 1 / target_frequency | 10ns @ 100MHz |
| `set_input_delay -max` | 0.5 × (Tcycle - Tcq_max - Tsu) | 2~4ns |
| `set_input_delay -min` | 0.5 × Thold | 0.5~1ns |
| `set_output_delay -max` | Tsu of receiving flop + routing | 2~4ns |
| `set_output_delay -min` | Thold of receiving flop + routing | 0.5~1ns |
| `set_false_path` | Async crossings, test pins, reset | — |
| `set_multicycle_path` | Multi-cycle register transfers | setup=N, hold=N-1 |

---

## 10. Implementation Notes

### 10.1 Coding Style

| Rule | Requirement | Rationale |
|------|------------|-----------|
| **R10.1** | Use `always_ff @(posedge clk or negedge rst_n)` for sequential logic | 统一风格，便于综合 |
| **R10.2** | Use `always_comb` for combinational logic (not `always @(*)`) | SystemVerilog 最佳实践 |
| **R10.3** | Non-blocking (`<=`) in sequential, blocking (`=`) in combinational | 竞争条件防范 |
| **R10.4** | No latches inferred (check synthesis report) | 组合逻辑必须覆盖所有 case |
| **R10.5** | `unique case` for one-hot muxes, `priority case` for priority encoders | 综合工具优化提示 |
| **R10.6** | No `for` loops with variable bounds | 综合必须可展开 |
| **R10.7** | No `initial` blocks in synthesizable code | 综合工具忽略 |
| **R10.8** | All flops must have a reset value | DFT 扫描链要求 |
| **R10.9** | All FSMs must decode unused states to safe state | 防止锁死 |

### 10.2 Module Parameterization

| Parameter | Default | Type | Description |
|-----------|---------|------|-------------|
| `DATA_WIDTH` | 32 | int | 数据路径位宽 |
| `FIFO_DEPTH` | 16 | int | FIFO 深度 (power of 2) |
| `NUM_CHANNELS` | 1 | int | 通道数 |
| `EN_PIPELINE` | 1 | bit | 流水线使能 |
| `EN_BYPASS` | 0 | bit | 旁路使能 |

```systemverilog
//=============================================================================
// Module Declaration Template
//=============================================================================
module <module_name> #(
    parameter int DATA_WIDTH   = 32,
    parameter int FIFO_DEPTH   = 16,
    parameter int NUM_CHANNELS = 1,
    parameter bit EN_PIPELINE  = 1'b1,
    parameter bit EN_BYPASS    = 1'b0
) (
    input  logic                  clk_i,
    input  logic                  rst_ni,
    // Bus interface
    input  logic                  psel_i,
    input  logic                  penable_i,
    input  logic                  pwrite_i,
    input  logic [31:0]           paddr_i,
    input  logic [31:0]           pwdata_i,
    output logic                  pready_o,
    output logic [31:0]           prdata_o,
    output logic                  pslverr_o,
    // Data interface
    input  logic [DATA_WIDTH-1:0] data_i,
    input  logic                  data_valid_i,
    output logic                  data_ready_o,
    output logic [DATA_WIDTH-1:0] data_o,
    output logic                  data_valid_o,
    input  logic                  data_ready_i,
    // Control
    output logic                  intr_o
);
```

### 10.3 Synthesis Pragmas

```systemverilog
// Synthesis pragma conventions:
//
// synopsys full_case       - force all case items covered (use carefully)
// synopsys parallel_case   - force parallel mux (not priority)
// synopsys translate_off   - simulation-only code
// synopsys translate_on    - resume synthesis

// Example: exclude debug logic from synthesis
// synopsys translate_off
`ifdef VERILATOR
    logic [31:0] debug_counter;
    always_ff @(posedge clk_i) begin
        if (debug_enable) debug_counter <= debug_counter + 1;
    end
`endif
// synopsys translate_on
```

### 10.4 Area / Speed Trade-offs

| Optimization | Technique | Area Impact | Timing Impact | When to Use |
|-------------|-----------|-------------|---------------|-------------|
| Pipeline registers | Insert reg between comb stages | +5% | +25% Fmax | Timing critical paths |
| Resource sharing | Shared ALU for multiple ops | -15% | -5% Fmax | Area constrained |
| Retiming | Move reg across comb logic | 0% | +10% Fmax | Balanced |
| Flatten hierarchy | Inline submodules | +5% | +15% Fmax | Final synthesis |
| Clock gating | AND gate + latch on clock | -20% dynamic power | -2% Fmax | Low power modes |

---

## 11. Verification Guidance

### 11.1 Directed Test Scenarios

| Test ID | Scenario | Stimulus | Expected Behavior | Coverage Point |
|---------|----------|----------|-------------------|----------------|
| T01 | Basic write/read CSR | Write all R/W regs, read back | Match written values | 100% reg access |
| T02 | Enable module | Set enable=1, provide data | FSM→SETUP→BUSY | FSM transition |
| T03 | Back-to-back transfers | 100 consecutive valid/ready | No data loss, no bubbles | Pipeline throughput |
| T04 | Backpressure | Stall output for 10 cycles | Pipeline holds, no overflow | Stall propagation |
| T05 | Interrupt generation | Trigger all events | int_o asserted, INT_STAT set | 100% interrupt cov |
| T06 | Error injection | Force error condition | FSM→ERROR, error flag set | Error recovery |
| T07 | Soft reset | Assert soft_rst mid-operation | All regs to reset, FSM→IDLE | Reset behavior |
| T08 | Concurrent channels | All channels active simultaneously | Channel isolation, fair arb | Arbitration |

### 11.2 Assertion Checkers

```systemverilog
//=============================================================================
// Formal Assertions (SVA)
//=============================================================================

// A1: valid must not be X during normal operation
`ifdef FORMAL
    assert_valid_not_x: assert property (
        @(posedge clk_i) disable iff (!rst_ni)
        !$isunknown(data_valid_i)
    );
`endif

// A2: ready should not be asserted when not ready
assert_ready_valid: assert property (
    @(posedge clk_i) disable iff (!rst_ni)
    data_ready_o |=> ##[0:1] data_ready_o || !data_valid_i
);

// A3: FSM never enters reserved state
assert_fsm_safe: assert property (
    @(posedge clk_i) disable iff (!rst_ni)
    state_q inside {ST_IDLE, ST_SETUP, ST_BUSY, ST_WAIT, ST_DONE, ST_ERROR}
);

// A4: Interrupt cleared only by SW
assert_int_clear: assert property (
    @(posedge clk_i) disable iff (!rst_ni)
    $rose(intr_o) |=> intr_o throughout
        (##[1:$] $fell(intr_o) [->1])
);
```

### 11.3 Functional Coverage Points

| Cover Group | Cover Point | Description |
|-------------|-------------|-------------|
| `cg_fsm` | state_q == ST_ERROR | Error state reached |
| `cg_fsm` | state_q == ST_WAIT | Backpressure triggered |
| `cg_int` | $rose(intr_o) | Interrupt fired |
| `cg_back2back` | valid_i && ready_i && valid_o && ready_o | Full pipeline throughput |
| `cg_fifo` | fifo_overflow | FIFO overflow (error path) |

---

## 12. DFT Requirements

### 12.1 Scan Chain Specification

| Scan Chain | Clock Domain | Flop Count | Chain Length | IO Pins |
|------------|-------------|------------|-------------|---------|
| chain_0 | clk_core | `<N>` | `<N+1>` | `scan_in0 / scan_out0` |
| chain_1 | clk_core | `<M>` | `<M+1>` | `scan_in1 / scan_out1` |
| chain_bus | clk_bus | `<K>` | `<K+1>` | `scan_in2 / scan_out2` |

### 12.2 Test Mode Behavior

| Signal | Function Mode | Test Mode | Description |
|--------|--------------|-----------|-------------|
| `test_mode_i` | 0 | 1 | 全局测试模式使能 |
| `scan_enable_i` | 0 | 1 | 扫描移位使能 |
| `scan_in_i` | — | data_in | 扫描链输入 |
| `scan_out_o` | — | data_out | 扫描链输出 |

### 12.3 Test Mode Rules

- **TMR1**: 所有 FFs 必须是可扫描替换的 (scan flip-flop)
- **TMR2**: 时钟在测试模式下由 `test_clk_i` 控制
- **TMR3**: 异步复位在测试模式下必须被屏蔽 (`test_mode_i → rst_n mux`)
- **TMR4**: 所有双向 I/O 在测试模式下必须配置为固定方向
- **TMR5**: 内部 PLL 在扫描测试时被旁路

### 12.4 MBIST (if applicable)

| Memory Instance | BIST Controller | Test Algorithm | Redundancy |
|----------------|----------------|----------------|------------|
| `<fifo_instance>` | `mbist_ctrl_0` | March C- | None |
| `<sram_instance>` | `mbist_ctrl_1` | March C+ | 1 row spare |

### 12.5 JTAG / Boundary Scan

| Feature | Support | Description |
|---------|---------|-------------|
| IEEE 1149.1 | Yes | Standard JTAG TAP |
| IEEE 1500 | Optional | Core wrapper for embedded cores |
| BYPASS instruction | Required | Bypass register for board-level test |
| IDCODE | Required | 32-bit device identification |

---

## 13. Delivery Checklist

### 13.1 Deliverable Files

| # | File | Description | Status | Reviewer |
|---|------|-------------|--------|----------|
| 1 | `<module_name>.sv` | 主 RTL 源代码 | ☐ Not started / ☐ Review / ☐ Done | |
| 2 | `<module_name>.sdc` | 时序约束文件 | ☐ Not started / ☐ Review / ☐ Done | |
| 3 | `<module_name>_tb.sv` | 自检测试台 | ☐ Not started / ☐ Review / ☐ Done | |
| 4 | `<module_name>_top.ys` | Yosys 综合脚本 | ☐ Not started / ☐ Review / ☐ Done | |
| 5 | `<module_name>_lint.rpt` | Lint 检查报告 | ☐ Not started / ☐ Review / ☐ Done | |
| 6 | `<module_name>_area.rpt` | 面积报告 | ☐ Not started / ☐ Review / ☐ Done | |
| 7 | `<module_name>_timing.rpt` | 时序报告 | ☐ Not started / ☐ Review / ☐ Done | |
| 8 | `<module_name>.vcd` | 仿真波形 (关键场景) | ☐ Not started / ☐ Review / ☐ Done | |

### 13.2 Quality Gates

| Gate | Criteria | Entry | Exit |
|------|----------|-------|------|
| **G1: Lint Clean** | 0 errors, 0 warnings | RTL ready | Lint report |
| **G2: Simulation Pass** | All directed tests pass | Testbench ready | Test report |
| **G3: Synthesis Clean** | 0 DRC violations, no latch inferred | SDC + RTL ready | Area/timing report |
| **G4: DFT Ready** | Scan chain insertion verified | Synthesis done | DFT report |
| **G5: Timing Clean** | WNS ≥ 0 at target frequency | Physical data | STA report |

### 13.3 Format Requirements

| Deliverable | Format | Header Required | Reviewed By |
|-------------|--------|----------------|-------------|
| RTL source | SystemVerilog (.sv) | Yes (copyright + module header) | Design lead |
| SDC | Synopsys SDC (.sdc) | Yes (version + generation info) | PD engineer |
| Testbench | SystemVerilog (.sv) | Yes | Verification lead |
| Report | Plain text (.rpt) | Yes (date + tool version) | Tech lead |

---

## 14. Revision History

| Version | Date | Author | Change Description | Reviewer |
|---------|------|--------|-------------------|----------|
| V0.1 | | | 初稿 — 微架构规格书创建 | |
| V0.2 | | | 修订 — | |
| V0.3 | | | 设计评审 — | |
| V1.0 | | | 正式发布 — LLD Freeze | |

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| CDC | Clock Domain Crossing |
| CSR | Control and Status Register |
| DFT | Design for Testability |
| FSM | Finite State Machine |
| LLD | Low-Level Design (微架构) |
| MBIST | Memory Built-In Self-Test |
| PVT | Process-Voltage-Temperature |
| SDC | Synopsys Design Constraints |
| STA | Static Timing Analysis |
| SVA | SystemVerilog Assertions |
| W1C | Write-1-to-Clear (register attribute) |
| WNS | Worst Negative Slack |

## Appendix B: Reference Documents

| Document | Version | Source | Description |
|----------|---------|--------|-------------|
| `<Protocol Spec>` | `<rev>` | `<link>` | 接口协议标准 |
| `<SoC Arch Spec>` | `<rev>` | `<link>` | SoC 级架构规格书 |
| `<Block HLD>` | `<rev>` | `<link>` | 模块架构 HLD (03_block_arch.HLD.md) |
| `<DFT Guide>` | `<rev>` | `<link>` | DFT 实现指导 |
| `<Synthesis Guide>` | `<rev>` | `<link>` | 综合流程指导 |

---

*本文档由 Chip Design Agent 生成 — AI-Executable LLD Template V2.0*
