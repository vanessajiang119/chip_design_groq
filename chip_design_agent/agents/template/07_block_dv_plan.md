# 模块验证规划 — Block Verification Plan

> **模块名称:**
> **层次路径:** <!-- top.chip.subsystem.module -->
> **版本:** V1.0
> **日期:**
> **状态:** Draft / Review / Final
> **驱动文档:** `03_block_arch.HLD.md` (模块架构)、`04_block_micro.LLD.md` (微架构)
> **上级文档:** `06_soc_dv_plan.md` (SoC 验证规划)
> **输出文档:** `09_block_dv_report.md` (模块验证报告)

---

## 1. 模块概述与验证范围

### 1.1 模块标识

| 属性 | 值 |
|------|-----|
| 模块全名 | `<ModuleName>` |
| 层次路径 | `<top.chip.subsystem.module>` |
| 功能分类 | `<数据通路 / 控制 / 存储 / 接口桥接>` |
| 目标频率 | `<MHz>` |
| 接口协议 | `<AXI4 / APB / AHB / 自定义>` |
| 架构文档 | `03_block_arch.HLD.md` (模块架构) |
| 微架构文档 | `04_block_micro.LLD.md` (微架构 LLD) |

### 1.2 验证范围

#### 1.2.1 在验证范围内 (In-Scope)

| 验证域 | 具体内容 | 来源文档 § | 优先级 |
|--------|---------|-----------|--------|
| 接口协议合规性 | 总线协议时序符合规范 | `03_block_arch.HLD.md §2` | P0 |
| 模块功能正确性 | 核心数据处理/运算功能 | `03_block_arch.HLD.md §1.3` | P0 |
| CSR 寄存器读写 | 所有寄存器/位域的 RW/RO/W1C 属性 | `04_block_micro.LLD.md §7` | P0 |
| FSM 状态迁移 | 所有状态的进入/退出/非法跳转 | `04_block_micro.LLD.md §4` | P0 |
| 数据通路完整性 | 输入输出数据一致、字节序正确 | `04_block_micro.LLD.md §6` | P0 |
| 流水线行为 | 各级流水线的 stall/hold/bubble/flush | `04_block_micro.LLD.md §5` | P0 |
| 背压与流控 | FIFO 满/空、反压传播 | `03_block_arch.HLD.md §4.3` | P0 |
| 中断生成 | 每个中断源的触发与清除 | `03_block_arch.HLD.md §2.4` | P0 |
| 时钟门控 / 低功耗 | 模块级时钟门控功能 | `03_block_arch.HLD.md §6` | P1 |
| 错误处理 | 每种错误的检测与恢复 | `04_block_micro.LLD.md §4.2` | P0 |
| 配置参数覆盖 | 所有可配置参数组合 | `03_block_arch.HLD.md §5.2` | P1 |
| 操作模式覆盖 | 所有操作模式 (Normal/Continuous/等) | `03_block_arch.HLD.md §5.4` | P0 |

#### 1.2.2 不在验证范围内 (Out-of-Scope)

| 排除项 | 原因 | 由谁覆盖 |
|--------|------|---------|
| SoC 级互联/系统场景 | SoC 级验证范畴 | `06_soc_dv_plan.md` |
| 跨模块交互 (除本模块接口外) | SoC 集成验证 | `06_soc_dv_plan.md` |
| DFT 扫描链/测试模式 | DFT 团队 | DFT 验证计划 |
| 软件驱动/固件 | SW 团队 | SW 测试 |
| 工艺角时序检查 | STA (static timing) | `s7_timing_closure` |

### 1.3 功能优先级 (P0/P1/P2)

| 优先级 | 定义 | 验证要求 |
|--------|------|---------|
| **P0** | 功能不正确则模块无法集成 | 100% 用例通过, 覆盖率达目标 |
| **P1** | 核心功能, 有变通方案可让步 | 主要场景覆盖, 覆盖率目标建议 |
| **P2** | 次要功能 | 抽测, 不设覆盖率目标 |

---

## 2. 验证方法学

### 2.1 方法学选择

| 方法学 | 是否采用 | 覆盖范围 | 说明 |
|--------|---------|---------|------|
| UVM 约束随机 | ✓ 主要 | 功能验证、数据通路、CSR | 主力验证方法 |
| Directed Test | ✓ 辅助 | 边界 case、错误注入 | 定向测试补漏 |
| Formal | ✓ 根据复杂度 | FSM 安全、协议合规、CSR 互斥 | 穷尽验证控制逻辑 |
| SVA 断言 | ✓ 内嵌 | 接口协议、FSM 跳转、数据完整性 | RTL 内嵌检查 |
| C-Model Co-Sim | ⚠ 按需 | 算法验证 | 有 C reference 时使用 |

### 2.2 方法学覆盖矩阵

| 验证域 | UVM | Directed | Formal | SVA | 说明 |
|--------|-----|----------|--------|-----|------|
| 接口协议 | ✓ (VIP) | — | ✓ | ✓ | VIP 协议检查 + Formal |
| CSR 读写 | ✓ (reg model) | ✓ (边界) | ✓ (互斥) | — | Reg model bulk + Formal |
| FSM 状态机 | ✓ (随机激励) | ✓ (状态强制) | ✓ (穷尽) | ✓ (SVA) | Formal 保证非法状态 |
| 数据通路 | ✓ (scoreboard) | ✓ (DMAC) | — | ✓ (数据断言) | Scoreboard data compare |
| 流水线 | ✓ (随机) | ✓ (背压注入) | — | ✓ (流水线断言) | 所有 stall 条件 |
| 中断 | ✓ | ✓ | ✓ | — | Formal 保证中断行为 |
| 错误恢复 | ✓ (注入) | ✓ | — | — | 随机 + 定向注入 |

---

## 3. 验证环境架构

### 3.1 UVM Testbench 框图

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Block-Level UVM Testbench                           │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────┐        │
│  │                       Test Layer                          │        │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │        │
│  │  │reg_access│ │ func_test │ │err_inject│ │perf_test   │  │        │
│  │  │_test     │ │_base      │ │_test     │ │_base       │  │        │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │        │
│  └──────────────────────┬───────────────────────────────────┘        │
│                          │                                            │
│  ┌──────────────────────▼───────────────────────────────────┐        │
│  │              Virtual Sequencer / Sequence Library          │        │
│  └──────────────────────┬───────────────────────────────────┘        │
│                          │                                            │
│  ┌──────────────────────▼───────────────────────────────────┐        │
│  │              env (uvm_env)                                │        │
│  │                                                           │        │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │        │
│  │  │ Bus VIP  │  │  Driver  │  │  Monitor │  │  Agent   │ │        │
│  │  │ (master) │  │ (custom) │  │ (custom) │  │ (slave)  │ │        │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │        │
│  │       │             │             │             │       │        │
│  │       └─────────────┼─────────────┼─────────────┘       │        │
│  │                     ▼             ▼                      │        │
│  │              ┌──────────────────────────┐                │        │
│  │              │      DUT: Module_Name    │                │        │
│  │              │  (RTL / Gate-level)      │                │        │
│  │              └──────────────────────────┘                │        │
│  │                     │             │                       │        │
│  │  ┌──────────────────┴─────────────┴──────────────────┐   │        │
│  │  │              Scoreboard                            │   │        │
│  │  │  ┌──────────┐  ┌──────────┐  ┌─────────────────┐  │   │        │
│  │  │  │Prediction│  │ Compare  │  │ Error Counting  │  │   │        │
│  │  │  │FIFO      │  │ Engine   │  │ & Logging       │  │   │        │
│  │  │  └──────────┘  └──────────┘  └─────────────────┘  │   │        │
│  │  └────────────────────────────────────────────────────┘   │        │
│  │                                                           │        │
│  │  ┌──────────────────────────────────────────────────────┐ │        │
│  │  │              Coverage Collector                      │ │        │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │ │        │
│  │  │  │cg_csr    │ │cg_fsm    │ │cg_data   │ │cg_prot │ │ │        │
│  │  │  │          │ │          │ │path      │ │ocol    │ │ │        │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └────────┘ │ │        │
│  │  └──────────────────────────────────────────────────────┘ │        │
│  └──────────────────────────────────────────────────────────┘        │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────┐        │
│  │        Config DB / Reg Model (uvm_reg_block)              │        │
│  └──────────────────────────────────────────────────────────┘        │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 Testbench 组件

| 组件 | 类型 | 描述 | 新建/复用 |
|------|------|------|----------|
| `block_env` | `uvm_env` | 验证环境顶层 | 新建 |
| `block_agent` | `uvm_agent` | 驱动/监测 DUT 接口 | 新建 (含 driver/monitor/sequencer) |
| `bus_vip` | `uvm_agent` | 总线协议 VIP (AXI/APB/AHB 等) | 复用 (VIP 库) |
| `block_driver` | `uvm_driver` | 自定义激励驱动器 | 新建 |
| `block_monitor` | `uvm_monitor` | 自定义信号监测器 | 新建 |
| `block_sequencer` | `uvm_sequencer` | 序列器 | 新建 |
| `virtual_sequencer` | `uvm_sequencer` | 虚拟序列器 (协调多个 agent) | 新建 |
| `block_scoreboard` | `uvm_scoreboard` | 数据比对、预测 | 新建 |
| `block_cov_collector` | `uvm_component` | 功能覆盖率收集 | 新建 |
| `reg_model` | `uvm_reg_block` | CSR 寄存器模型 | 新建 (来自 LLD §7) |
| `block_pkg` | package | UVM 包 (所有组件声明) | 新建 |

### 3.3 Scoreboard 设计

| 检查项 | 实现方式 | 数据流 | 错误上报 |
|--------|---------|--------|---------|
| 数据输入 vs 输出 | 预测 FIFO + compare | monitor A → predict FIFO → compare → monitor B | `uvm_error` + 计数 |
| CSR 读写 | reg model predict | reg write → predict → read check | `uvm_error` |
| 中断行为 | interrupt monitor | 中断事件→ expected vs actual | `uvm_error` |
| 协议合规 | VIP checker | VIP 内置 protocol checker | VIP `uvm_error` |

---

## 4. 测试用例

### 4.1 测试用例总览

| 类别 | 用例数 | 验证方法 | 优先级 |
|------|--------|---------|--------|
| CSR 寄存器测试 | <!-- N --> | UVM reg model | P0 |
| 基本功能测试 | <!-- N --> | Directed + UVM | P0 |
| 接口协议测试 | <!-- N --> | VIP + Formal | P0 |
| FSM 状态机测试 | <!-- N --> | UVM + Formal | P0 |
| 数据通路测试 | <!-- N --> | UVM scoreboard | P0 |
| 流水线/性能测试 | <!-- N --> | UVM 随机 | P1 |
| 错误注入测试 | <!-- N --> | UVM error injection | P0 |
| 边界/压力测试 | <!-- N --> | UVM 多 seed | P1 |
| 中断测试 | <!-- N --> | UVM | P0 |
| 配置参数组合 | <!-- N --> | UVM 参数化 | P1 |

### 4.2 CSR 寄存器测试

| 测试 ID | 测试名称 | 场景描述 | 验证方法 | 覆盖率目标 | 优先级 |
|--------|---------|---------|---------|-----------|--------|
| CSR_001 | 所有 RW 寄存器写回读 | 遍历所有 RW 位域, 写 0xAAAA/0x5555 | Reg model frontdoor | 100% 寄存器 | P0 |
| CSR_002 | 寄存器复位值检查 | 复位后读所有寄存器 | Reg model reset check | 100% 寄存器 | P0 |
| CSR_003 | RO 寄存器写保护 | 对 RO 位域执行写操作 | Reg model backdoor | 100% RO 位域 | P0 |
| CSR_004 | W1C 位域清除 | 置位后写 1 清除 | Reg model | 100% W1C 位域 | P0 |
| CSR_005 | 非法地址访问 | 访问保留地址 | Reg model | 100% 非法地址 | P0 |
| CSR_006 | HW set/clear 条件 | 验证 HW set/clear 条件是否按 spec 工作 | UVM sequence | 100% HW 条件 | P0 |

### 4.3 基本功能测试

| 测试 ID | 测试名称 | 场景描述 | 激励 | 期望行为 | 优先级 |
|--------|---------|---------|------|---------|--------|
| FUNC_001 | 模块使能/禁用 | 配置 CTRL.enable | enable=1 → 操作 → enable=0 | 使能后模块开始工作, 禁用后停止 | P0 |
| FUNC_002 | 单次传输 (Normal 模式) | 配置 → 启动 → 等待完成 | 单笔数据传输 | STATUS.done=1, 中断触发 | P0 |
| FUNC_003 | 连续传输 (Auto 模式) | 自动连续处理 N 笔数据 | N 笔数据连续输入 | 全部处理完成, 数据正确 | P0 |
| FUNC_004 | Bypass 模式 | 配置 bypass 模式 | 输入数据 | 输出与输入一致 (直通) | P1 |
| FUNC_005 | 软复位 | 操作中执行软复位 | 操作进行中 → soft_rst=1 | FSM → IDLE, FIFO 清空, 寄存器复位 | P0 |

### 4.4 接口协议测试

| 测试 ID | 测试名称 | 场景描述 | 激励 | 期望行为 | 优先级 |
|--------|---------|---------|------|---------|--------|
| PROT_001 | 总线写时序 | APB/AXI4 write burst | 标准写序列 | pready 响应正确, 数据写入 | P0 |
| PROT_002 | 总线读时序 | APB/AXI4 read burst | 标准读序列 | prdata 正确, pready 响应 | P0 |
| PROT_003 | 总线等待状态 | 带 wait state 的传输 | 插入 wait state | 传输在 wait 后完成 | P0 |
| PROT_004 | valid/ready 握手 | valid/ready 全组合 | 所有 valid/ready 相位组合 | 数据在握手时正确传输 | P0 |
| PROT_005 | 背压 (backpressure) | 输出 FIFO 满 | 持续发送数据但不读输出 | 上游反压传播 | P0 |
| PROT_006 | 非对齐访问 (如支持) | 非对齐地址读写 | 非对齐地址 | NV error / 正确操作 (取决于 spec) | P1 |

### 4.5 FSM 状态机测试

| 测试 ID | 测试名称 | 场景描述 | 激励 | 期望行为 | 优先级 |
|--------|---------|---------|------|---------|--------|
| FSM_001 | 正常状态序列 | IDLE → SETUP → BUSY → DONE → IDLE | 标准操作序列 | 状态按预期跳转 | P0 |
| FSM_002 | 所有合法状态转换 | 遍历转换矩阵 | 触发每个转换条件 | 状态正确跳转 | P0 |
| FSM_003 | 错误状态进入与恢复 | BUSY → ERROR → IDLE | 注入错误条件 | error 标志设, 软复位恢复 | P0 |
| FSM_004 | 非法状态恢复 | 强制 FSM 进入 110/111 | 同步注入非法编码 | 自动回到 IDLE/ERROR | P0 |
| FSM_005 | 长时间运行验证 | 10,000 次操作循环 | 循环触发 | 无状态锁死 | P1 |

### 4.6 数据通路测试

| 测试 ID | 测试名称 | 场景描述 | 激励 | 期望行为 | 优先级 |
|--------|---------|---------|------|---------|--------|
| DPATH_001 | 单笔数据传输完整性 | 单笔数据输入 → 处理 → 输出 | 随机数据值 | 输出 = predict(输入) | P0 |
| DPATH_002 | 多笔连续传输 | back-to-back 100 笔 | 递增/随机数据 | 无数据丢失或错位 | P0 |
| DPATH_003 | 字节序检查 | LE/BE 模式切换 | 已知模式数据 | 字节序转换正确 | P1 |
| DPATH_004 | 所有 ALU/运算单元 | 遍历 opcode 表 | 随机操作数 | 运算结果正确 | P0 |
| DPATH_005 | 数据 mux 选择 | 遍历 mux 选择编码 | 各输入源 | mux 输出正确 | P1 |

### 4.7 错误与异常测试

| 测试 ID | 测试名称 | 场景描述 | 激励 | 期望行为 | 优先级 |
|--------|---------|---------|------|---------|--------|
| ERR_001 | 非法配置模式 | 写入 reserved 模式编码 | 配置 10/11 | 配置忽略, error flag | P0 |
| ERR_002 | FIFO 溢出 | FIFO 满时继续写入 | FIFO 满后再写 | error flag, 数据丢弃 | P0 |
| ERR_003 | FIFO 空读 | FIFO 空时读取 | 空 FIFO 读请求 | error flag / 返回 0 | P0 |
| ERR_004 | 配置超时 | SETUP 状态超时等待 | CFG_LOAD 状态下 timeout | FSM → ERROR | P0 |
| ERR_005 | 错误码验证 | 注入不同类型错误 | 各类错误条件 | 错误码区分正确 | P1 |

### 4.8 中断测试

| 测试 ID | 测试名称 | 场景描述 | 激励 | 期望行为 | 优先级 |
|--------|---------|---------|------|---------|--------|
| INT_001 | 使能中断触发 | 使能中断, 触发事件 | 使能 INT_EN → 触发事件 | intr_o 拉高, INT_STAT 置位 | P0 |
| INT_002 | 禁用中断不触发 | 禁用中断, 触发事件 | 禁用 INT_EN → 触发事件 | intr_o 保持低 | P0 |
| INT_003 | W1C 清除中断 | 中断后 W1C 清除 | intr_o 高 → W1C INT_STAT | intr_o 恢复低 | P0 |
| INT_004 | 多中断源并发 | 同时触发多个中断 | 事件 A+B 同时发生 | 所有 INT_STAT 位正确 | P1 |
| INT_005 | 中断恢复后再次触发 | 清除后续又触发 | 中断 → 清除 → 再次触发 | 第二次中断正常 | P1 |

### 4.9 性能测试

| 测试 ID | 测试名称 | 场景描述 | 激励 | 期望行为 | 优先级 |
|--------|---------|---------|------|---------|--------|
| PERF_001 | 峰值吞吐 | 最大速率连续传输 | back-to-back 输入 | 达到目标吞吐 | P1 |
| PERF_002 | 端到端延迟 | 测量输入到输出延迟 | 单笔传输 | 延迟 < 目标值 | P1 |
| PERF_003 | 流水线 flush 延迟 | flush 到恢复的时间 | 流水线满时 flush | flush 延迟 < 目标 | P2 |
| PERF_004 | 多通道仲裁公平性 | 多通道并发, 测量各通道带宽 | 各通道 100% 负载 | 各通道带宽均等 | P2 |

---

## 5. 覆盖率计划

### 5.1 代码覆盖率

| 类型 | 目标 | 说明 |
|------|------|------|
| Line / Block | 95% | 非冗余代码 |
| Toggle | 90% | 关注接口信号和控制信号 |
| FSM (state/transition) | 100% | 所有状态 + 所有合法跳转 |
| Branch | 90% | |
| Condition | 85% | |

### 5.2 功能覆盖率

#### 5.2.1 Covergroup 定义

| Covergroup | 覆盖点 | Cross | 目标 |
|-----------|--------|-------|------|
| `cg_csr` | 所有 RW 寄存器写入值 | — | 100% coverage bins |
| `cg_fsm` | state_q, transition (cur→nxt) | state × error_cond | 100% 状态 × 跳转 |
| `cg_data` | data_i values, data_o values, data_width | — | 边界值: min/max/zero |
| `cg_protocol` | valid/ready 所有相位组合 | valid × ready phases | 100% 握手场景 |
| `cg_backpressure` | fifo_level, stall_active | fifo_level × stall | 所有 FIFO 水位 |
| `cg_error` | error_code, fsm_state_on_error | error_code × state | 100% 错误码 × 状态 |
| `cg_channel` | channel_id, arb_type | channel × arb | 所有通道 × 仲裁模式 |

#### 5.2.2 覆盖率 Bin 设计示例

```systemverilog
// FSM 状态覆盖率
covergroup cg_fsm @(posedge clk_i);
    state_cp       : coverpoint state_q {
        bins legal  = {ST_IDLE, ST_SETUP, ST_BUSY, ST_WAIT, ST_DONE, ST_ERROR};
        bins illegal = default;  // 检查是否进入非法状态
    }
    transition_cp  : coverpoint state_q {
        bins idle_to_setup = (ST_IDLE => ST_SETUP);
        bins busy_to_done  = (ST_BUSY => ST_DONE);
        bins busy_to_err   = (ST_BUSY => ST_ERROR);
        bins busy_to_wait  = (ST_BUSY => ST_WAIT);
        bins wait_to_busy  = (ST_WAIT => ST_BUSY);
        bins done_to_idle  = (ST_DONE => ST_IDLE);
        bins err_to_idle   = (ST_ERROR => ST_IDLE);
    }
    csr_x_fsm      : cross state_cp, csr_ctrl_val;
endgroup
```

### 5.3 断言覆盖率

| 断言 | 类型 | 覆盖内容 | Formal/SVA |
|------|------|---------|-----------|
| `assert_fsm_safe` | 安全 | FSM 不进入非法状态 | Formal (穷尽) |
| `assume_valid_ready_protocol` | 协议 | valid/ready 时序合规 | SVA |
| `assert_data_integrity` | 数据 | 数据路径完整 | SVA |
| `cover_intr_triggered` | 覆盖 | 每个中断源至少触发一次 | SVA cover |
| `assert_csr_write_protect` | 安全 | RO 位域不受写影响 | Formal |
| `cover_fifo_full` | 覆盖 | FIFO 满条件被触发 | SVA cover |

### 5.4 覆盖 Waive 流程

| 步骤 | 内容 | 责任人 |
|------|------|--------|
| 1. 识别 | 无法覆盖的代码/功能点 | DV 工程师 |
| 2. 理由 | 填写 waive 理由 | DV 工程师 |
| 3. 评审 | 验证主管 + 设计主管 | 验证主管 |
| 4. 归档 | 纳入 `09_block_dv_report.md` | DV 工程师 |

---

## 6. 验证环境配置

### 6.1 验证参数化

| 参数 | 默认值 | 描述 | 影响 |
|------|--------|------|------|
| `DATA_WIDTH` | 32 | 数据总线位宽 | 需测试所有支持值 |
| `FIFO_DEPTH` | 16 | FIFO 深度 | 测试满/空/almost_full |
| `NUM_CHANNELS` | 1 | 通道数 | 测试单通道+多通道 |
| `EN_PIPELINE` | 1 | 流水线使能 | 测试使能/禁用 |
| `EN_ECC` | 0 | ECC 使能 | 测试 ECC 功能 |

### 6.2 随机约束

| 随机变量 | 约束范围 | 分布倾向 | 说明 |
|---------|---------|---------|------|
| 数据值 | [0, 2^DATA_WIDTH-1] | 均匀分布 | 边界值 weighted |
| 传输长度 | [1, MAX_BURST_LEN] | 短长度 60%, 长长度 40% | — |
| valid/ready 延迟 | [0, 10] cycles | 0~2 cycles 70% | 偶发高延迟 |
| 背压插入频率 | — | 10% cycles | 注入背压 |
| 错误注入 | — | 1% of operations | 低概率注入 |

### 6.3 Regression 计划

| 回归类型 | 种子数 | 运行时间 | 频率 | 通过标准 |
|---------|--------|---------|------|---------|
| Smoke | 1 × N tests | < 10 min | 每次提交 | 100% pass |
| Full | 10 × N tests | < 2 hrs | Daily | 100% P0 pass, > 90% P1 |
| Stress | 50 × N tests | < 8 hrs | Weekly | 无锁死/数据错误 |
| Formal | — | < 4 hrs | Daily | 0 违例 |

---

## 7. 验证时间节点

### 7.1 模块级验证里程碑

| 里程碑 | 目标日期 | 交付物 | 退出标准 |
|--------|---------|--------|---------|
| **M_B0: DV Plan Freeze** | <!-- YYYY-MM --> | `07_block_dv_plan.md` (本文档) | Plan 评审通过 |
| **M_B1: TB Build** | <!-- YYYY-MM --> | Testbench smoke pass | TB 编译, 基础 sequence 跑通 |
| **M_B2: P0 Tests** | <!-- YYYY-MM --> | 所有 P0 用例通过 | 0 P0 blocker bug |
| **M_B3: Coverage** | <!-- YYYY-MM --> | 覆盖率达标 | Code cov > 90%, Func cov > 90% |
| **M_B4: Formal** | <!-- YYYY-MM --> | Formal 通过 | 0 违例 |
| **M_B5: Sign-off** | <!-- YYYY-MM --> | `09_block_dv_report.md` | Sign-off 评审通过, 可交付集成 |

### 7.2 与 SoC DV 对齐

| SoC DV 里程碑 | 模块 DV 需完成 | 交付物 |
|--------------|--------------|--------|
| M_DV1: TB Ready | M_B1 | 模块 TB smoke pass 报告 |
| M_DV2: P0 Tests Pass | M_B2 | 模块 P0 测试完成确认 |
| M_DV3: Coverage Freeze | M_B3 | 模块覆盖率报告 |
| M_DV5: Full Regression | M_B5 | 模块 sign-off 报告 |

---

## 8. Formal 验证计划 (按需)

### 8.1 Formal 适用范围

| Formal 项 | 复杂度评估 | 预计属性数 | 工具 |
|----------|-----------|-----------|------|
| FSM 安全属性 | 低 (N states) | <!-- 5~10 --> | <!-- JasperGold --> |
| CSR 互斥检查 | 中 (N registers) | <!-- 10~20 --> | <!-- JasperGold --> |
| 接口协议合规 | 中 | <!-- 10~15 --> | <!-- VC Formal --> |
| 数据完整性 | 高 (大位宽数据通路) | — | 不适用 Formal |

### 8.2 Formal 验证环境

```
┌─────────────────────────────────────────────────┐
│              Formal Verification Env             │
│                                                  │
│  ┌─────────────────┐  ┌──────────────────────┐  │
│  │  assume (约束)   │  │  assert (待证明属性)   │  │
│  │  - 时钟/复位     │  │  - FSM safety        │  │
│  │  - 接口协议      │  │  - CSR 互斥          │  │
│  │  - 输入范围      │  │  - 协议合规          │  │
│  └─────────────────┘  └──────────────────────┘  │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │              DUT (Bound)                  │   │
│  │  (Formal 引擎自动展开时间帧)              │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌─────────────────┐  ┌──────────────────────┐  │
│  │  cover (覆盖)    │  │  Regression 脚本     │  │
│  └─────────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────┘
```

---

## 附录 A: 测试用例清单总表

<!-- 本文档中定义的所有测试用例汇总 -->

| 测试 ID | 名称 | 方法 | 优先级 | 种子数 | 预期运行时间 | 状态 |
|--------|------|------|--------|--------|------------|------|
| CSR_001 | RW 写回读 | UVM | P0 | 1 | <!-- min --> | ☐ Plan / ☐ Pass / ☐ Fail |
| CSR_002 | 复位值检查 | UVM | P0 | 1 | <!-- min --> | ☐ Plan / ☐ Pass / ☐ Fail |
| ... | | | | | | |
| FUNC_001 | 模块使能/禁用 | UVM | P0 | 10 | <!-- min --> | ☐ Plan / ☐ Pass / ☐ Fail |
| FUNC_002 | 单次传输 | UVM | P0 | 10 | <!-- min --> | ☐ Plan / ☐ Pass / ☐ Fail |
| ... | | | | | | |
| ERR_001 | 非法配置 | UVM | P0 | 10 | <!-- min --> | ☐ Plan / ☐ Pass / ☐ Fail |
| INT_001 | 中断触发 | UVM | P0 | 5 | <!-- min --> | ☐ Plan / ☐ Pass / ☐ Fail |
| PERF_001 | 峰值吞吐 | UVM | P1 | 5 | <!-- min --> | ☐ Plan / ☐ Pass / ☐ Fail |

## 附录 B: 与 LLD 的章节映射

| LLD 章节 | 对应验证活动 | 测试用例 |
|----------|------------|---------|
| LLD §4 FSM | FSM 状态机验证 | FSM_001~005 |
| LLD §5 流水线 | 流水线行为验证 | PROT_004~006, PERF_001~004 |
| LLD §6 Datapath | 数据通路验证 | DPATH_001~005 |
| LLD §7 CSR | CSR 寄存器验证 | CSR_001~006 |
| LLD §9 SDC | 时序约束 (不验证) | — |
| LLD §11 验证指引 | 直接测试场景 | 对应 FUNC/ERR/INT 测试 |

## 附录 C: 术语表

| 术语 | 含义 |
|------|------|
| DUT | Device Under Test |
| DV | Design Verification |
| Formal | 形式化验证 (数学证明) |
| Reg model | UVM Register Model |
| Scoreboard | 数据比对器 |
| SVA | SystemVerilog Assertions |
| UVM | Universal Verification Methodology |
| VIP | Verification IP (商用协议检查器) |
| Waive | 豁免 (覆盖率无法达到的合理理由) |

## 附录 D: 参考文档

| 文档 | 版本 | 来源 | 说明 |
|------|------|------|------|
| `03_block_arch.HLD.md` | V1.0 | 内部 | 模块架构设计 |
| `04_block_micro.LLD.md` | V1.0 | 内部 | 模块微架构 LLD |
| `06_soc_dv_plan.md` | V1.0 | 内部 | SoC 级验证规划 (上级文档) |
| UVM 参考手册 | IEEE 1800.2 | IEEE | UVM 标准 |
| 接口协议规范 | — | 供应商/标准 | 总线/接口协议标准 |

---

*本文档由 Chip Design Agent 生成 — Block DV Plan Template V1.0*

*完成验证后，请填写 `09_block_dv_report.md` (模块验证报告)。*
