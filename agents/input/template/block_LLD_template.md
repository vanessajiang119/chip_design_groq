# 模块级设计规格书

> **模块名称:**
> **所属芯片:**
> **版本:** V1.0
> **日期:**
> **状态:** Draft

---

## 1. 模块概述

### 1.1 模块功能
<!-- 用 2-3 句话描述该模块的核心功能 -->

### 1.2 关键特性
- <!-- 特性 1 -->
- <!-- 特性 2 -->
- <!-- 特性 3 -->

### 1.3 应用场景
<!-- 该模块在芯片中的具体应用场景 -->

### 1.4 设计约定
| 约定项 | 说明 |
|--------|------|
| 时钟域 | |
| 复位方式 | 异步复位/同步复位 |
| 字节序 | Little-endian / Big-endian |
| 数据格式 | 补码/原码/IEEE754 |
| 接口协议 | AXI/AHB/APB/自定义 |

### 1.5 相关模块
| 模块名 | 关系 | 交互接口 |
|--------|------|---------|
| | 上游模块 | |
| | 下游模块 | |

---

## 2. 接口信号

### 2.1 顶层接口

| 信号名 | 方向 | 位宽 | 类型 | 描述 | 时钟域 |
|--------|------|------|------|------|--------|
| clk | input | 1 | clock | 模块主时钟 | - |
| rst_n | input | 1 | reset | 异步复位，低有效 | clk |
| | | | | | |

### 2.2 总线接口信号

**从机接口 (Slave)**

| 信号名 | 方向 | 位宽 | 描述 |
|--------|------|------|------|
| s_axi_awvalid | input | 1 | 写地址通道 valid |
| s_axi_awaddr | input | 32 | 写地址 |
| s_axi_awready | output | 1 | 写地址通道 ready |
| s_axi_wvalid | input | 1 | 写数据通道 valid |
| s_axi_wdata | input | 32 | 写数据 |
| s_axi_wstrb | input | 4 | 写字节选通 |
| s_axi_wready | output | 1 | 写数据通道 ready |
| s_axi_bvalid | output | 1 | 写响应通道 valid |
| s_axi_bready | input | 1 | 写响应通道 ready |
| s_axi_arvalid | input | 1 | 读地址通道 valid |
| s_axi_araddr | input | 32 | 读地址 |
| s_axi_arready | output | 1 | 读地址通道 ready |
| s_axi_rvalid | output | 1 | 读数据通道 valid |
| s_axi_rdata | output | 32 | 读数据 |
| s_axi_rready | input | 1 | 读数据通道 ready |

**主机接口 (Master)**

| 信号名 | 方向 | 位宽 | 描述 |
|--------|------|------|------|
| m_axi_awvalid | output | 1 | |
| m_axi_awaddr | output | 32 | |
| m_axi_awready | input | 1 | |
| ... | | | |

### 2.3 握手协议时序

**valid-ready 握手规则:**
- valid 表示发送方数据有效
- ready 表示接收方可以接收
- 当 valid 和 ready 同时为高时，传输完成

**时序图示例:**
```
clk      ▄▄▁▁▄▄▁▁▄▄▁▁▄▄▁▁▄▄▁▁▄▄▁▁
valid    ______▄▄▄▄▄▄▄▄▄▄▄▄________
ready    ______▄▄▄▄______▄▄▄▄▄▄____
data     ______XXXX_D0____XXXX_D1____
```

### 2.4 中断接口

| 信号名 | 方向 | 描述 | 触发条件 |
|--------|------|------|---------|
| irq | output | 中断请求 | 电平触发 / 边沿触发 |
| | | | |

---

## 3. 微架构设计

### 3.1 模块内部结构

```
┌─────────────────────────────────────────────────────┐
│                     Module_Top                        │
│                                                       │
│  ┌──────────────┐   ┌──────────────┐                │
│  │    Ctrl FSM   │◄─►│  Data Path   │                │
│  └──────┬───────┘   └──────┬───────┘                │
│         │                  │                          │
│         ▼                  ▼                          │
│  ┌──────────────┐   ┌──────────────┐                │
│  │  Reg File    │   │  FIFO/Buffer │                │
│  └──────────────┘   └──────────────┘                │
│                                                       │
│  ┌──────────────┐   ┌──────────────┐                │
│  │  Arbiter     │   │  Datapath    │                │
│  └──────────────┘   └──────────────┘                │
└─────────────────────────────────────────────────────┘
```

### 3.2 控制状态机

**状态转换图:**
```
         ┌─────────┐
         │  IDLE   │◄────────────┐
         └────┬────┘             │
              │ start            │
              ▼                  │
         ┌─────────┐   done      │
    ┌───►│  BUSY   │─────────────┤
    │    └────┬────┘             │
    │         │ error            │
    │         ▼                  │
    │    ┌─────────┐             │
    └────│  ERROR  │─────────────┘
         └─────────┘   clear
```

**状态编码:**
| 状态 | 编码 | 描述 |
|------|------|------|
| IDLE | 3'b001 | 空闲，等待触发 |
| BUSY | 3'b010 | 正在处理 |
| ERROR | 3'b100 | 错误状态 |
| DONE | 3'b000 | 完成 (伪状态，组合输出) |

**状态转移条件:**
| 当前状态 | 下一状态 | 跳转条件 |
|---------|---------|---------|
| IDLE | BUSY | start_i == 1 |
| BUSY | IDLE | done == 1 && err == 0 |
| BUSY | ERROR | err == 1 |
| ERROR | IDLE | clear_i == 1 |

### 3.3 数据通路

**数据流:**
```
input_data[31:0]
      │
      ▼
┌─────────────┐
│  Stage 1:   │  ← ctrl_sel
│  MUX/ALIGN  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Stage 2:   │
│  PROCESS    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Stage 3:   │
│  FORMAT     │
└──────┬──────┘
       │
       ▼
output_data[31:0]
```

**流水线级数:** 3 级

| 级数 | 功能 | 延迟 | 寄存器 |
|------|------|------|--------|
| Stage 1 | 输入对齐/选择 | 1 cycle | align_reg[31:0] |
| Stage 2 | 核心处理 | 1 cycle | proc_reg[31:0] |
| Stage 3 | 输出格式化 | 1 cycle | format_reg[31:0] |

### 3.4 FIFO 规格

| 参数 | 值 | 说明 |
|------|-----|------|
| 深度 | | 必须为 2 的幂 |
| 数据位宽 | | |
| 空标志 | almost_empty / empty | |
| 满标志 | almost_full / full | |
| 计数 | | 当前存储条目数 |
| 实现方式 | register-based / SRAM-based | |
| 读写指针 | binary / gray code | |

### 3.5 仲裁与调度

- **仲裁算法**: round-robin / fixed-priority / weighted
- **调度策略**:
- **QoS 支持**:

---

## 4. 流水线行为

### 4.1 基本操作流程

```
Cycle:   0    1    2    3    4    5    6    7
        ┌────┬────┬────┬────┬────┬────┬────┬────┐
clk     │    │    │    │    │    │    │    │    │
        └────┴────┴────┴────┴────┴────┴────┴────┘

start   ________▄▄▄▄________________________

s1_val  ________▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄____________
s1_data ________XXXX_D0__D1__D2____________

s2_val  ________________▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄____
s2_data ________________XXXX_P0__P1__P2____

s3_val  ________________________▄▄▄▄▄▄▄▄▄▄▄▄
s3_data ________________________XXXX_O0__O1__

done    ________________________▄▄▄▄________
```

### 4.2 背靠背传输
<!-- 描述连续传输时的行为 -->

### 4.3 停顿与反压
<!-- 描述 FIFO 满时的反压机制 -->

### 4.4 异常处理
| 异常类型 | 处理方式 | 恢复机制 |
|---------|---------|---------|
| 超时 | | |
| 数据错误 | | |
| 协议错误 | | |
| FIFO 溢出 | | |

---

## 5. 配置寄存器

### 5.1 寄存器地址映射

基地址: `BASE_ADDR + offset`

| 偏移 | 名称 | 位宽 | 访问类型 | 默认值 | 描述 |
|------|------|------|---------|-------|------|
| 0x00 | CTRL | 32 | RW | 0x0000_0000 | 控制寄存器 |
| 0x04 | STATUS | 32 | RO | 0x0000_0000 | 状态寄存器 |
| 0x08 | CONFIG | 32 | RW | 0x0000_0000 | 配置寄存器 |
| 0x0C | DATA_IN | 32 | WO | 0x0000_0000 | 输入数据 |
| 0x10 | DATA_OUT | 32 | RO | 0x0000_0000 | 输出数据 |
| 0x14 | INT_EN | 32 | RW | 0x0000_0000 | 中断使能 |
| 0x18 | INT_STATUS | 32 | RW1C | 0x0000_0000 | 中断状态 |
| 0x1C | TIMEOUT | 32 | RW | 0x0000_1000 | 超时配置 |
| 0x20 | VERSION | 32 | RO | 0x0000_0100 | 版本号 |

### 5.2 寄存器位域描述

**CTRL (0x00) — 控制寄存器**
| 位域 | 名称 | 访问 | 默认值 | 描述 |
|------|------|------|-------|------|
| [31:4] | reserved | RO | 0 | 保留位 |
| [3] | soft_rst | WO | 0 | 写 1 软复位 |
| [2] | irq_en | RW | 0 | 中断使能 |
| [1] | mode | RW | 0 | 操作模式: 0=模式A, 1=模式B |
| [0] | start | RW | 0 | 写 1 启动操作, 硬件自动清零 |

**STATUS (0x04) — 状态寄存器**
| 位域 | 名称 | 访问 | 默认值 | 描述 |
|------|------|------|-------|------|
| [31:4] | reserved | RO | 0 | 保留位 |
| [3] | timeout_err | RO | 0 | 超时错误 |
| [2] | data_err | RO | 0 | 数据错误 |
| [1] | busy | RO | 0 | 忙标志 |
| [0] | ready | RO | 1 | 就绪标志 |

**INT_STATUS (0x18) — 中断状态寄存器**
| 位域 | 名称 | 访问 | 默认值 | 描述 |
|------|------|------|-------|------|
| [31:2] | reserved | RO | 0 | 保留位 |
| [1] | done_int | RW1C | 0 | 操作完成中断 |
| [0] | err_int | RW1C | 0 | 错误中断, 写 1 清零 |

### 5.3 寄存器访问时序

**读时序:**
```
clk      ▄▄▁▁▄▄▁▁▄▄▁▁▄▄▁▁
araddr   ______XXXX_ADDR__
arvalid  ______▄▄▄▄______
arready  ______▄▄▄▄______
rdata    ____________XXXX_DATA
rvalid   ____________▄▄▄▄
rready   ____________▄▄▄▄
```

**写时序:**
```
clk      ▄▄▁▁▄▄▁▁▄▄▁▁▄▄▁▁
awaddr   ______XXXX_ADDR__
awvalid  ______▄▄▄▄______
awready  ______▄▄▄▄______
wdata    ______XXXX_DATA__
wvalid   ______▄▄▄▄______
wready   ______▄▄▄▄______
bvalid   ____________▄▄▄▄
bready   ____________▄▄▄▄
```

---

## 6. 时钟与复位

### 6.1 时钟域
| 时钟名 | 频率 | 来源 | 扇出模块 |
|--------|------|------|---------|
| clk | | 顶层输入 | 所有时序逻辑 |

### 6.2 跨时钟域 (CDC)
| 信号名 | 源时钟域 | 目标时钟域 | 同步方案 |
|--------|---------|---------|---------|
| | | | 2-DFF / handshake / async FIFO / DMUX |

### 6.3 复位树
- **复位类型**: 异步复位 / 同步复位
- **复位释放**: 异步释放
- **所有触发器是否使用统一复位**: 是/否
- **寄存器的复位值是否全部可配置**: 是/否

### 6.4 门控时钟
- **门控时钟使能**: 有/无
- **门控粒度**: 模块级 / 单元级
- **门控类型**: 集成门控单元 / AND 门

---

## 7. 时序约束

### 7.1 时钟约束
```tcl
# 主时钟
create_clock -name clk -period 10.000 [get_ports clk]
set_clock_uncertainty -setup 0.200 [get_clocks clk]
set_clock_uncertainty -hold  0.050 [get_clocks clk]
set_clock_transition -rise 0.100 [get_clocks clk]
set_clock_transition -fall 0.100 [get_clocks clk]

# 生成时钟
create_generated_clock -name clk_div2 \
    -source [get_ports clk] \
    -divide_by 2 \
    [get_pins u_divider/clk_out]
```

### 7.2 I/O 约束
```tcl
# 输入延迟
set_input_delay -clock clk -max 2.000 [get_ports data_in*]
set_input_delay -clock clk -min 0.500 [get_ports data_in*]

# 输出延迟
set_output_delay -clock clk -max 2.500 [get_ports data_out*]
set_output_delay -clock clk -min 0.500 [get_ports data_out*]

# 输入转换
set_input_transition -max 0.300 [get_ports data_in*]
```

### 7.3 时序例外
```tcl
# 伪路径
set_false_path -from [get_clocks clk_a] -to [get_clocks clk_b]

# 多周期路径
set_multicycle_path -setup 2 -from [get_pins u_src/q] -to [get_pins u_dst/d]
set_multicycle_path -hold 1  -from [get_pins u_src/q] -to [get_pins u_dst/d]
```

---

## 8. 面积与功耗

### 8.1 面积估计

| 子模块 | 面积 (um²) | 门数 (等效NAND2) | 比例 |
|--------|-----------|-----------------|------|
| Control FSM | | | |
| Data Path | | | |
| Register File | | | |
| FIFO | | | |
| Arbiter | | | |
| **总计** | | | **100%** |

### 8.2 功耗估计

| 子模块 | 动态功耗 (mW) | 静态功耗 (mW) | 总计 (mW) |
|--------|-------------|-------------|----------|
| Control FSM | | | |
| Data Path | | | |
| Register File | | | |
| FIFO | | | |
| Arbiter | | | |
| **总计** | | | |

### 8.3 低功耗设计技术
- [ ] 时钟门控
- [ ] 电源门控
- [ ] 多阈值电压 (HVT/RVT/LVT)
- [ ] 操作数隔离
- [ ] 动态电压频率缩放 (DVFS)
- [ ] 体偏置

---

## 9. 验证计划

### 9.1 验证范围

| 验证项 | 方法 | 覆盖要求 |
|--------|------|---------|
| 功能正确性 | 定向测试 | 所有功能点 |
| 接口协议 | UVM VIP | 协议完整性 |
| 异常处理 | 异常注入 | 所有异常路径 |
| 性能 | 性能测试 | 满足吞吐量指标 |
| 随机验证 | 约束随机 | 覆盖率驱动 |
| Formal | 属性检查 | 关键断言 |

### 9.2 测试用例

| 编号 | 测试名称 | 描述 | 优先级 | 验证方法 |
|------|---------|------|--------|---------|
| TC-01 | basic_rw | 基本读写测试 | P0 | Simulation |
| TC-02 | burst_test | 连续传输测试 | P0 | Simulation |
| TC-03 | fifo_full | FIFO 满条件测试 | P1 | Simulation |
| TC-04 | error_inject | 错误注入测试 | P1 | Simulation |
| TC-05 | perf_max | 最大吞吐量测试 | P2 | Performance |
| TC-06 | formal_assert | Formal 属性验证 | P0 | Formal |

### 9.3 断言清单

```systemverilog
// 基本协议断言
assert_ready_after_valid: assert property(
    @(posedge clk) disable iff (!rst_n)
    valid |-> ##[0:$] ready
);

// FIFO 溢出保护
assert_no_fifo_overflow: assert property(
    @(posedge clk) disable iff (!rst_n)
    !(fifo_full && fifo_write)
);

// 状态机独占性
assert_onehot_state: assert property(
    @(posedge clk) disable iff (!rst_n)
    $onehot(state)
);
```

### 9.4 覆盖率目标

| 覆盖率类型 | 目标 |
|-----------|------|
| Line Coverage | 100% |
| Toggle Coverage | 95% |
| FSM Coverage | 100% (state/transition) |
| Branch Coverage | 95% |
| Assertion Coverage | 100% |
| Functional Coverage | 90% |

---

## 10. DFT 要求

### 10.1 扫描测试
- **扫描模式**: 内部扫描
- **扫描链数量**:
- **扫描使能引脚**:
- **ATPG 覆盖率目标**: > 98%

### 10.2 MBIST
- **测试频率**:
- **算法**: March C-
- **BIST 接口**: JTAG 访问

### 10.3 测试模式

| 模式 | 使能条件 | 行为说明 |
|------|---------|---------|
| Normal | test_mode=0 | 正常运行 |
| Scan | test_mode=1 | 扫描移位模式 |
| BIST | test_mode=1, bist_en=1 | Memory BIST |

---

## 11. 交付检查清单

### 11.1 RTL 交付
- [ ] RTL 代码通过 lint 检查
- [ ] 所有阻塞赋值仅用于组合逻辑
- [ ] 无锁存器推断
- [ ] 跨时钟域信号已做同步处理
- [ ] 所有状态机有默认状态 / 完备性编码
- [ ] 无仿真-综合不匹配问题

### 11.2 验证交付
- [ ] 所有 P0/P1 测试用例通过
- [ ] 覆盖率目标达成
- [ ] Formal 验证通过
- [ ] 无未修复的功能 bug

### 11.3 综合交付
- [ ] 时序收敛 (无 setup/hold 违例)
- [ ] 面积满足预算
- [ ] 功耗满足预算
- [ ] DFT 覆盖率满足目标

---

## 12. 修订历史

| 版本 | 日期 | 作者 | 修订说明 |
|------|------|------|---------|
| V0.1 | | | 初稿 |
| V1.0 | | | 正式发布 |

---

*本文档由 Chip Design Agent 自动生成*
