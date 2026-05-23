# 项目需求跟踪矩阵 — Project Requirements Traceability Matrix (RTM)

> **项目代号:**
> **芯片型号:**
> **版本:** V1.0
> **日期:**
> **状态:** Draft / Review / Final
> **关联模板:** `00`→`01`→`02`→`03`→`04`→`06/07`→`08/09`

---

## 1. 文档概述

### 1.1 目的

本文档是项目的**需求跟踪矩阵 (RTM)**，建立从市场需求到验证签核的端到端双向追溯链。它回答以下问题：

- **正向追溯**：每个市场需求（MRD）是否被产品规格（PRD）覆盖？每个产品规格是否被架构设计（HLD）实现？每个设计特性是否被验证计划（DV Plan）覆盖并验证通过（DV Report）？
- **逆向追溯**：每条验证用例验证的是哪个设计特性？每个设计特性对应哪条产品需求？每条产品需求源自哪个市场洞察？
- **覆盖分析**：哪些需求尚未被设计覆盖？哪些设计特性尚未被验证覆盖？

### 1.2 适用范围

| 角色 | 关注内容 |
|------|---------|
| 项目经理 | 全链需求覆盖状态、风险项 |
| 产品经理 | 市场/产品需求是否被完整实现 |
| 架构师 | 架构决策与需求的对齐关系 |
| 设计主管 | 模块级需求分解与分配 |
| 验证主管 | 验证计划的完整性与需求覆盖 |
| 质量/审计 | 合规性与可追溯性证据 |

### 1.3 阅读路径

```
正向追溯路径:
  00_market.MRD.md  ──►  01_product.PRD.md  ──►  02_soc_arch.HLD.md  ──►  03_block_arch.HLD.md
     市场需求              产品规格               系统架构                   模块架构
       │                       │                      │                        │
       │                       │                      │                  ┌─────┘
       │                       │                      │                  ▼
       │                       │                      │          04_block_micro.LLD.md
       │                       │                      │              微架构设计
       ▼                       ▼                      ▼
  06_soc_dv_plan.md ◄─────────────────────────────── 08_soc_dv_report.md
  (SoC 验证计划)                                          (SoC 验证报告)

  07_block_dv_plan.md ──► 09_block_dv_report.md
  (模块验证计划)               (模块验证报告)
```

### 1.4 RTM 编号规则

每条需求使用分层编号体系：

```
RTM-{CAT}-{NNN}

CAT = 分类缩写:
  MKT  — 市场与商业 (Market & Business)
  PRD  — 产品规格 (Product Specification)
  SYS  — 系统架构 (System Architecture)
  PWR  — 电源管理 (Power Management)
  CLK  — 时钟/复位 (Clock/Reset)
  SEC  — 安全 (Security)
  MOD  — 模块功能 (Module Function)
  CSR  — 配置寄存器 (CSR)
  IF   — 接口/协议 (Interface/Protocol)
  PERF — 性能 (Performance)
  VER  — 验证 (Verification)
  QAL  — 质量与签核 (Quality & Sign-off)

NNN = 三位序号 (001, 002, ..., 999)
```

---

## 2. RTM 填写说明

### 2.1 各列定义

| 列 | 定义 | 填写要求 |
|----|------|---------|
| **RTM ID** | 需求唯一标识 | 按编号规则生成，全局唯一 |
| **需求描述** | 需求的简要描述 | 使用"主语 + 谓语 + 指标（如适用）"的格式 |
| **优先级** | P0/P1/P2/P3 | P0=流片必须满足, P1=强烈推荐, P2=条件允许, P3=未来版本 |
| **MRD §** | 对应 MRD 章节 | `00_market.MRD.md §X.X` |
| **PRD §** | 对应 PRD 章节 | `01_product.PRD.md §X.X` |
| **HLD §** | 对应 HLD 章节 | `02_soc_arch.HLD.md §X.X` 或 `03_block_arch.HLD.md §X.X` |
| **LLD §** | 对应 LLD 章节 | `04_block_micro.LLD.md §X` |
| **DV Plan §** | 对应 DV 计划章节/用例 ID | `06_soc_dv_plan.md §X` 或 `07_block_dv_plan.md §X` |
| **DV Report §** | 对应 DV 报告章节/结果 | `08_soc_dv_report.md §X` 或 `09_block_dv_report.md §X` |
| **状态** | 覆盖/验证状态 | **Covered** / **In Design** / **In Verification** / **Pass** / **Fail** / **Waived** / **Not Covered** |
| **风险** | H/M/L | 基于技术难度、进度压力和依赖关系综合评估 |
| **备注** | 补充说明 | 例外处理、假设条件、待定决策 |

### 2.2 状态迁移规则

| 当前状态 | 迁移条件 | 下一状态 |
|---------|---------|---------|
| Not Covered | HLD 章节已定义设计实现 | In Design |
| In Design | LLD 章节已细化且 RTL 冻结 | Covered |
| Covered | DV Plan 已分配测试用例且开始执行 | In Verification |
| In Verification | DV Report 确认测试通过且覆盖率达标 | Pass |
| 任何状态 | 经变更评审确认不适用 | Waived |
| In Verification | DV Report 确认测试失败且无法修复 | Fail |

### 2.3 与变更管理 (CR) 的集成

当设计规格发生变更时：
1. 发起 **Change Request (CR)**，明确变更范围和影响
2. 在 RTM 中标记受影响的需求行，状态设为 **CR-Pending**
3. CR 批准后更新对应的 HLD/LLD/DV Plan 章节引用
4. CR 执行完成后更新 RTM 状态并关闭 CR

> **变更触发条件**：PRD 指标修改、架构方案调整、模块功能增删、工艺/封装变更。

---

## 3. 需求跟踪矩阵

### 3.A 市场与商业需求 — Market & Business (MKT)

<!-- 本节源自 00_market.MRD.md Part 1~2，需逐条确认是否转化为 PRD 产品规格 -->

| RTM ID | 需求描述 | Pri | MRD § | PRD § | HLD § | LLD § | DV Plan § | DV Report § | 状态 | 风险 | 备注 |
|--------|---------|:---:|:-----:|:-----:|:-----:|:-----:|:---------:|:-----------:|:----:|:----:|------|
| RTM-MKT-001 | 目标市场定义（TAM/SAM/SOM）| P0 | §1.2.1 | §2.2 | — | — | — | — | Not Covered | L | 市场定义不涉及设计实现 |
| RTM-MKT-002 | 目标应用场景与关键要求 | P0 | §2 | §2.6 | §1.2 | — | §5 (场景分解) | §6 | Not Covered | M | 场景定义驱动 SoC 验证用例 |
| RTM-MKT-003 | 用户画像与使用模式定义 | P1 | §3 | §2.6 | — | — | — | — | Not Covered | L | 间接影响功耗场景定义 |
| RTM-MKT-004 | 盈利模式与收入模型 Y1~Y5 | P0 | §5.1 | §2.3 (SKU) | — | — | — | — | Not Covered | L | 商业层需求，不直接进入设计 |
| RTM-MKT-005 | 目标售价与 BOM 成本约束 | P0 | §5.2 | §2.4 (§4) | §1.3 (面积/成本) | — | — | — | Not Covered | M | 约束芯片面积和封装选型 |
| RTM-MKT-006 | 竞品关键指标对标 | P1 | §4 | §2.4 | §1.4 (KPI) | — | — | — | Not Covered | M | 竞品指标转化为设计目标 |
| RTM-MKT-007 | 产品型号与 SKU 分级 | P0 | §14 | §2.3 | — | — | — | — | Not Covered | L | 决定 feature 优先级 |

### 3.B 产品规格需求 — Product Specification (PRD)

<!-- 本节源自 01_product.PRD.md §2~§5，是设计输入的核心 -->

| RTM ID | 需求描述 | Pri | MRD § | PRD § | HLD § | LLD § | DV Plan § | DV Report § | 状态 | 风险 | 备注 |
|--------|---------|:---:|:-----:|:-----:|:-----:|:-----:|:---------:|:-----------:|:----:|:----:|------|
| RTM-PRD-001 | 工艺节点选择 | P0 | §10.1 | §3.1 | §1.3 | — | — | — | Not Covered | M | 影响 STA sign-off 条件 |
| RTM-PRD-002 | 封装类型与管脚数 | P0 | §10.2 | §3.2 | §2.2 | — | — | — | Not Covered | M | 决定顶层 I/O 布局 |
| RTM-PRD-003 | 芯片总性能目标 (DMIPS/TOPS) | P0 | §12.1 | §4.1 | §1.4 | — | §5 (场景) | §6 | Not Covered | H | 核心 PPA 指标 |
| RTM-PRD-004 | 芯片总功耗预算 (Typ/Max/Standby) | P0 | §12.2 | §4.2 | §1.3, §8 | — | §5 (PM) | §6 | Not Covered | H | 核心 PPA 指标 |
| RTM-PRD-005 | 芯片总面积预算 | P1 | §12.3 | §4.3 | §1.3 | — | — | — | Not Covered | M | 核心 PPA 指标 |
| RTM-PRD-006 | 顶层 I/O 类型与数量 | P0 | §10.3 | §3.3 | §2.2, §6 | — | — | — | Not Covered | M | 影响封装和 PCB |
| RTM-PRD-007 | 电源轨定义 (电压/电流) | P0 | §12.4 | §3.4 | §8.2 | — | — | — | Not Covered | H | 影响电源网络设计 |
| RTM-PRD-008 | 工作温度范围 | P0 | §10.4 | §3.5 | §1.3 | — | — | — | Not Covered | M | 影响工艺角选择 |
| RTM-PRD-009 | 目标应用场景功耗分布 | P1 | §2 | §4.2 | §8.3 | — | §5 (PM) | §6 | Not Covered | M | 驱动 DV 功耗验证场景 |

### 3.C 系统架构需求 — System Architecture (SYS)

<!-- 本节源自 02_soc_arch.HLD.md，将产品规格分解为架构方案 -->

| RTM ID | 需求描述 | Pri | MRD § | PRD § | HLD § | LLD § | DV Plan § | DV Report § | 状态 | 风险 | 备注 |
|--------|---------|:---:|:-----:|:-----:|:-----:|:-----:|:---------:|:-----------:|:----:|:----:|------|
| RTM-SYS-001 | CPU 子系统核心数/微架构/频率 | P0 | — | §2.5 | §3.1 | §3 (子模块) | §5 (Boot) | §4 | Not Covered | H | |
| RTM-SYS-002 | 缓存层次结构 (L1/L2/L3 容量) | P0 | — | §2.5 | §3.2 | §3 | §5 (Perf) | §6 | Not Covered | H | |
| RTM-SYS-003 | 片上存储 (SRAM/ROM 容量与分布) | P0 | — | §2.5 | §3.3 | §3 | §5 (Mem) | §4 | Not Covered | M | |
| RTM-SYS-004 | 外部存储器接口 (DDR/HBM 规格) | P0 | — | §2.5 | §3.3 | §3 | §5 (Mem) | §4 | Not Covered | H | |
| RTM-SYS-005 | 互联架构 (总线/NoC 拓扑与带宽) | P0 | — | — | §5 | §5 (Pipeline) | §5 (Bus) | §4 | Not Covered | H | |
| RTM-SYS-006 | 地址映射 (Memory Map) | P0 | — | — | §4 | — | §5 (Addr) | §4 | Not Covered | M | |
| RTM-SYS-007 | 中断控制器架构与中断路由 | P0 | — | — | §2, §10 | §7 (CSR) | §5 (Int) | §4 | Not Covered | M | |
| RTM-SYS-008 | DMA 引擎配置与通道数 | P1 | — | — | §6 | §3 | §5 (Perf) | §4 | Not Covered | M | |
| RTM-SYS-009 | 调试与追踪架构 (JTAG/SWD/ETM) | P1 | — | — | §10 | — | §2 | — | Not Covered | L | 调试架构，非功能验证 |

### 3.D 时钟/复位/电源管理需求 — Clock/Reset/Power (CLK)

| RTM ID | 需求描述 | Pri | MRD § | PRD § | HLD § | LLD § | DV Plan § | DV Report § | 状态 | 风险 | 备注 |
|--------|---------|:---:|:-----:|:-----:|:-----:|:-----:|:---------:|:-----------:|:----:|:----:|------|
| RTM-CLK-001 | 时钟源与 PLL 配置 | P0 | — | — | §7.1 | §11 (Clk) | §5 (Clk) | §4 | Not Covered | H | |
| RTM-CLK-002 | 时钟域划分与跨时钟域 (CDC) | P0 | — | — | §7.2 | §11 (Clk) | §5 (Clk) | §3 (Formal) | Not Covered | H | CDC 需形式化验证 |
| RTM-CLK-003 | 时钟门控策略 | P1 | — | §4.2 | §7.3 | §11 (Clk) | §5 (PM) | §6 | Not Covered | M | |
| RTM-CLK-004 | 复位架构 (同步/异步/复位域) | P0 | — | — | §7.4 | §11 (Rst) | §5 (Clk) | §4 | Not Covered | M | |
| RTM-CLK-005 | 上电/掉电序列 | P0 | — | — | §8.1 | — | §5 (PM) | §4 | Not Covered | H | |
| RTM-CLK-006 | 低功耗模式定义 (Active/Sleep/DeepSleep) | P0 | — | §4.2 | §8.3 | §11 (Pwr) | §5 (PM) | §6 | Not Covered | H | |
| RTM-CLK-007 | 电源域划分与隔离策略 | P0 | — | — | §8.2 | — | §5 (PM) | §4 | Not Covered | H | |
| RTM-CLK-008 | 唤醒源与唤醒时间约束 | P0 | §2 (场景) | §4.2 | §8.4 | §4 (FSM) | §5 (PM) | §6 | Not Covered | H | |

### 3.E 安全需求 — Security (SEC)

| RTM ID | 需求描述 | Pri | MRD § | PRD § | HLD § | LLD § | DV Plan § | DV Report § | 状态 | 风险 | 备注 |
|--------|---------|:---:|:-----:|:-----:|:-----:|:-----:|:---------:|:-----------:|:----:|:----:|------|
| RTM-SEC-001 | 安全启动 (Secure Boot) | P0 | §16.1 | §2.5 | §9.1 | — | §5 (Sec) | §4 | Not Covered | H | |
| RTM-SEC-002 | 硬件信任根/密钥存储 | P0 | §16.2 | — | §9.2 | §7 (CSR) | §5 (Sec) | §4 | Not Covered | H | |
| RTM-SEC-003 | 内存隔离/保护机制 (TrustZone/PMP) | P0 | — | — | §9.3 | — | §5 (Sec) | §4 | Not Covered | H | |
| RTM-SEC-004 | 安全调试与访问控制 | P1 | — | — | §9.4 | — | §5 (Sec) | §4 | Not Covered | M | |
| RTM-SEC-005 | 加密加速引擎 (AES/RSA/HMAC) | P1 | — | — | §9.5 | §3 | §5 (Sec) | §4 | Not Covered | M | |
| RTM-SEC-006 | 物理安全 (电压/频率/温度检测) | P2 | — | — | §9.6 | — | — | — | Not Covered | L | 车规/金融场景 |
| RTM-SEC-007 | 安全生命周期管理 | P1 | — | — | §9.7 | — | — | — | Not Covered | M | |

### 3.F 模块功能需求 — Module Function (MOD)

<!-- 本节源自 03_block_arch.HLD.md 和 04_block_micro.LLD.md，每个模块一份 -->

| RTM ID | 需求描述 | Pri | MRD § | PRD § | HLD § | LLD § | DV Plan § | DV Report § | 状态 | 风险 | 备注 |
|--------|---------|:---:|:-----:|:-----:|:-----:|:-----:|:---------:|:-----------:|:----:|:----:|------|
| RTM-MOD-001 | 模块功能描述与操作模式 | P0 | — | — | §1.3 | §1 | §1.2 (范围) | §6 (Feature Matrix) | Not Covered | — | 每模块创建独立 RTM-MOD-xxx 条目 |
| RTM-MOD-002 | 模块接口时序合规性 | P0 | — | — | §2 | §2 | §4 (IF) | §4 | Not Covered | — | |
| RTM-MOD-003 | 模块 FSM 状态定义与迁移 | P0 | — | — | §4.2 | §4 | §4 (FSM) | §4 | Not Covered | — | |
| RTM-MOD-004 | 模块数据通路宽度与处理能力 | P0 | — | — | §4.1 | §6 | §4 (Datapath) | §4 | Not Covered | — | |
| RTM-MOD-005 | 模块流水线级数与控制逻辑 | P0 | — | — | — | §5 | §4 (Pipeline) | §4 | Not Covered | — | |
| RTM-MOD-006 | 模块错误处理与异常恢复 | P0 | — | — | §4.4 | §4.2 | §4 (Error) | §4 | Not Covered | — | |
| RTM-MOD-007 | 模块背压与流控机制 | P0 | — | — | §4.3 | §6 | §4 (IF) | §4 | Not Covered | — | |
| RTM-MOD-008 | 模块中断源与触发条件 | P0 | — | — | §2.4 | §4 | §4 (Int) | §4 | Not Covered | — | |

> **说明**：条目 RTM-MOD-001~008 为模块级需求的通用模板。实际项目中，每个 IP/模块（如 UART、SPI、DMA、NPU、GPU 等）应复制一份独立条目，填充具体模块名称和参数。

### 3.G 配置寄存器需求 — CSR (CSR)

| RTM ID | 需求描述 | Pri | MRD § | PRD § | HLD § | LLD § | DV Plan § | DV Report § | 状态 | 风险 | 备注 |
|--------|---------|:---:|:-----:|:-----:|:-----:|:-----:|:---------:|:-----------:|:----:|:----:|------|
| RTM-CSR-001 | CSR 地址分配不重叠 | P0 | — | — | §5.3 | §7 | §4 (CSR) | §4 | Not Covered | M | 地址冲突检测 |
| RTM-CSR-002 | CSR 位域 R/W/R0/W1C 属性正确 | P0 | — | — | — | §7 | §4 (CSR) | §4 | Not Covered | M | 需遍历所有位域 |
| RTM-CSR-003 | CSR 复位值符合规格 | P0 | — | — | — | §7 | §4 (CSR) | §4 | Not Covered | M | |
| RTM-CSR-004 | 保留位域读回 0 / 写忽略 | P0 | — | — | — | §7 | §4 (CSR) | §4 | Not Covered | L | |
| RTM-CSR-005 | HW set/clear 条件与行为正确 | P0 | — | — | — | §7 | §4 (CSR) | §4 | Not Covered | M | |
| RTM-CSR-006 | 非法地址访问返回错误响应 | P0 | — | — | §4 (地址映射) | §7 | §4 (CSR) | §4 | Not Covered | M | |

### 3.H 接口与协议需求 — Interface/Protocol (IF)

| RTM ID | 需求描述 | Pri | MRD § | PRD § | HLD § | LLD § | DV Plan § | DV Report § | 状态 | 风险 | 备注 |
|--------|---------|:---:|:-----:|:-----:|:-----:|:-----:|:---------:|:-----------:|:----:|:----:|------|
| RTM-IF-001 | AXI/AHB/APB 协议时序合规 | P0 | — | — | §5 | §2 | §4 (IF) | §4 | Not Covered | H | 使用 Protocol VIP |
| RTM-IF-002 | PCIe 链路宽度/速率/协商 | P0 | — | — | §6 | §2 | §5 (Periph) | §4 | Not Covered | H | |
| RTM-IF-003 | MIPI CSI/DSI 协议合规 | P0 | — | — | §6 | §2 | §5 (Periph) | §4 | Not Covered | H | |
| RTM-IF-004 | I2C/SPI/UART 主从模式 | P0 | — | — | §6 | §2 | §4 (IF) | §4 | Not Covered | M | |
| RTM-IF-005 | GPIO 功能/中断/复用 | P0 | — | §3.3 | §6 | §2 | §5 (IO Mux) | §4 | Not Covered | M | |
| RTM-IF-006 | 片间同步接口时序 | P1 | — | — | §6 | §2 | §4 (IF) | §4 | Not Covered | M | |

### 3.I 性能需求 — Performance (PERF)

| RTM ID | 需求描述 | Pri | MRD § | PRD § | HLD § | LLD § | DV Plan § | DV Report § | 状态 | 风险 | 备注 |
|--------|---------|:---:|:-----:|:-----:|:-----:|:-----:|:---------:|:-----------:|:----:|:----:|------|
| RTM-PERF-001 | 系统总吞吐/带宽目标 | P0 | §12.1 | §4.1 | §1.4, §5 | — | §5 (Perf) | §6 | Not Covered | H | |
| RTM-PERF-002 | 关键路径延迟约束 | P0 | — | §4.1 | §1.4 | §9 (SDC) | — | — | Not Covered | H | STA 覆盖 |
| RTM-PERF-003 | 总线利用率与 QoS | P1 | — | — | §5.2 | — | §5 (Perf) | §6 | Not Covered | M | |
| RTM-PERF-004 | 内存带宽与延迟 | P0 | — | §4.1 | §3.3, §5 | — | §5 (Perf) | §6 | Not Covered | H | |
| RTM-PERF-005 | 低功耗模式唤醒时间 | P0 | §2 (场景) | §4.2 | §8.4 | §4 (FSM) | §5 (PM) | §6 | Not Covered | H | |
| RTM-PERF-006 | 芯片启动时间 | P1 | — | §4.1 | §1.4 | — | §5 (Boot) | §6 | Not Covered | M | |

### 3.J 验证需求 — Verification (VER)

<!-- 本节源自 06_soc_dv_plan.md 和 07_block_dv_plan.md -->

| RTM ID | 需求描述 | Pri | MRD § | PRD § | HLD § | LLD § | DV Plan § | DV Report § | 状态 | 风险 | 备注 |
|--------|---------|:---:|:-----:|:-----:|:-----:|:-----:|:---------:|:-----------:|:----:|:----:|------|
| RTM-VER-001 | UVM 验证环境搭建 | P0 | — | — | — | — | §4 (UVM) | §2 | Not Covered | M | |
| RTM-VER-002 | 代码行覆盖率 ≥ 95% | P0 | — | — | — | — | §6 (Cov) | §3 | Not Covered | M | |
| RTM-VER-003 | FSM 状态/转移覆盖率 100% | P0 | — | — | — | §4 | §5 (Cov Plan) | §3 | Not Covered | M | |
| RTM-VER-004 | 功能覆盖率 (Covergroup) 100% | P0 | — | — | — | — | §6 (Cov) | §3 | Not Covered | H | |
| RTM-VER-005 | Assertion 覆盖率 100% | P0 | — | — | — | — | §6 (Cov) | §3 | Not Covered | M | |
| RTM-VER-006 | Formal 验证完成 (FSM/CDC/CSR) | P1 | — | — | — | — | §8 (Formal) | §3 | Not Covered | M | |
| RTM-VER-007 | P0 测试通过率 100% | P0 | — | — | — | — | §5 (Test) | §4 | Not Covered | H | |
| RTM-VER-008 | Bug 零 P0 未修复 (sign-off) | P0 | — | — | — | — | — | §5, §7 | Not Covered | H | |
| RTM-VER-009 | 全回归通过率 ≥ 99% | P0 | — | — | — | — | §7 (Regression) | §2 | Not Covered | M | |
| RTM-VER-010 | DV 里程碑 M_DV0~M_DV6 达成 | P0 | — | — | — | — | §8 (Schedule) | §2 | Not Covered | H | |

### 3.K 质量与签核需求 — Quality & Sign-off (QAL)

| RTM ID | 需求描述 | Pri | MRD § | PRD § | HLD § | LLD § | DV Plan § | DV Report § | 状态 | 风险 | 备注 |
|--------|---------|:---:|:-----:|:-----:|:-----:|:-----:|:---------:|:-----------:|:----:|:----:|------|
| RTM-QAL-001 | Sign-off 检查清单 14 项全部完成 | P0 | — | — | — | — | — | §7.1 | Not Covered | H | |
| RTM-QAL-002 | 无未修复的 DRC/LVS 违例 | P0 | — | — | — | — | — | — | Not Covered | H | GDS sign-off |
| RTM-QAL-003 | STA 无 setup/hold 违例 | P0 | — | — | — | §9 (SDC) | — | — | Not Covered | H | 综合后检查 |
| RTM-QAL-004 | DFT 覆盖率达标 | P0 | — | — | — | §12 (DFT) | — | — | Not Covered | M | DFT 团队覆盖 |
| RTM-QAL-005 | 流片前变更审计 (CR 全部关闭) | P0 | — | §6 (Milestone) | — | — | — | §7 | Not Covered | H | |
| RTM-QAL-006 | 设计/验证文档版本对齐 | P1 | — | — | — | — | — | §7 | Not Covered | M | |

---

## 4. 覆盖率统计分析

### 4.1 需求覆盖汇总

| 分类 | 总条数 | Covered | In Design | In Verification | Pass | Fail | Waived | Not Covered | 覆盖率 |
|:----:|:-----:|:-------:|:---------:|:--------------:|:----:|:----:|:------:|:-----------:|:------:|
| MKT | 7 | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- | <!-- | <!-- | <!-- % --> |
| PRD | 9 | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- | <!-- | <!-- | <!-- % --> |
| SYS | 9 | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- | <!-- | <!-- | <!-- % --> |
| CLK | 8 | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- | <!-- | <!-- | <!-- % --> |
| SEC | 7 | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- | <!-- | <!-- | <!-- % --> |
| MOD | 8 | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- | <!-- | <!-- | <!-- % --> |
| CSR | 6 | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- | <!-- | <!-- | <!-- % --> |
| IF | 6 | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- | <!-- | <!-- | <!-- % --> |
| PERF | 6 | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- | <!-- | <!-- | <!-- % --> |
| VER | 10 | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- | <!-- | <!-- | <!-- % --> |
| QAL | 6 | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- | <!-- | <!-- | <!-- % --> |
| **合计** | **82** | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- | <!-- | <!-- | <!-- % --> |

### 4.2 优先级分布

| 优先级 | 总条数 | Pass | Fail | Waived | Not Covered | Pass 率 |
|:------:|:-----:|:----:|:----:|:------:|:-----------:|:-------:|
| P0 | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- % --> |
| P1 | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- % --> |
| P2 | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- % --> |

### 4.3 风险分布

| 风险级别 | 条数 | 占比 | 重点关注 |
|:--------:|:----:|:----:|:--------:|
| H (高风险) | <!-- --> | <!-- % --> | 需每周追踪，制定 mitigation 计划 |
| M (中风险) | <!-- --> | <!-- % --> | 需定期 review |
| L (低风险) | <!-- --> | <!-- % --> | 常规管理 |

---

## 5. 附录

### 附录 A: 术语表

| 缩写 | 全称 | 说明 |
|------|------|------|
| CR | Change Request | 变更请求 |
| CSR | Control/Status Register | 控制/状态寄存器 |
| DV | Design Verification | 设计验证 |
| FSM | Finite State Machine | 有限状态机 |
| HLD | High-Level Design | 高层设计 / 架构设计 |
| LLD | Low-Level Design | 低层设计 / 微架构设计 |
| MRD | Market Requirements Document | 市场需求文档 |
| PPA | Performance, Power, Area | 性能、功耗、面积 |
| PRD | Product Requirements Document | 产品需求规格书 |
| RTM | Requirements Traceability Matrix | 需求跟踪矩阵 |
| STA | Static Timing Analysis | 静态时序分析 |
| UVM | Universal Verification Methodology | 通用验证方法学 |

### 附录 B: 需求变更记录

| CR ID | 变更描述 | 影响 RTM ID | 提出人 | 日期 | 状态 (Open/Approved/Closed) |
|-------|---------|------------|--------|------|---------------------------|
| <!-- CR-001 --> | <!-- 变更描述 --> | <!-- RTM-xxx --> | <!-- 姓名 --> | <!-- 日期 --> | Open |

### 附录 C: 参考文档清单

| 文档 | 版本 | 日期 | 存放路径 |
|------|:----:|:----:|---------|
| `00_market.MRD.md` | <!-- V1.0 --> | <!-- --> | `agents/template/00_market.MRD.md` |
| `01_product.PRD.md` | <!-- V1.0 --> | <!-- --> | `agents/template/01_product.PRD.md` |
| `02_soc_arch.HLD.md` | <!-- V1.0 --> | <!-- --> | `agents/template/02_soc_arch.HLD.md` |
| `03_block_arch.HLD.md` (<Module>) | <!-- V1.0 --> | <!-- --> | `agents/template/03_block_arch.HLD.md` |
| `04_block_micro.LLD.md` (<Module>) | <!-- V1.0 --> | <!-- --> | `agents/template/04_block_micro.LLD.md` |
| `04_block_micro.LLD.md` (<Module>) | <!-- V1.0 --> | <!-- --> | `<!-- 各模块独立文件 -->` |
| `06_soc_dv_plan.md` | <!-- V1.0 --> | <!-- --> | `agents/template/06_soc_dv_plan.md` |
| `07_block_dv_plan.md` (<Module>) | <!-- V1.0 --> | <!-- --> | `agents/template/07_block_dv_plan.md` |
| `08_soc_dv_report.md` | <!-- V1.0 --> | <!-- --> | `agents/template/08_soc_dv_report.md` |
| `09_block_dv_report.md` (<Module>) | <!-- V1.0 --> | <!-- --> | `agents/template/09_block_dv_report.md` |

---

### 附录 D: 模板章节引用速查

| 模板 | 核心章节速查 |
|------|-------------|
| `00_market.MRD.md` | Part1:市场(Ch1~5), Part2:商业(Ch6~9), Part3:可行性(Ch10~15), Part4:IP(Ch16~17), Part5:供应链(Ch18~19) |
| `01_product.PRD.md` | 定位(§2), 工艺/封装(§3), PPA目标(§4), I/O/电源(§3.3~3.4), 里程碑(§6) |
| `02_soc_arch.HLD.md` | 架构框图(§2), CPU子系统(§3), 存储(§3.3), 互联(§5), 地址映射(§4), 时钟/复位(§7), 电源(§8), 安全(§9) |
| `03_block_arch.HLD.md` | 模块I/O(§2), 框图(§3), 数据流(§4), CSR(§5), 配置参数(§5.2) |
| `04_block_micro.LLD.md` | 接口时序(§2), 子模块(§3), FSM(§4), Pipeline(§5), Datapath(§6), CSR(§7), Clk/Rst(§11), SDC(§9) |
| `06_soc_dv_plan.md` | 验证范围(§2), 方法学(§3), 环境架构(§4), 场景(§5), 覆盖率(§6), 回归(§7), 里程碑(§8) |
| `07_block_dv_plan.md` | 验证范围(§1), UVM环境(§3), 测试用例(§4), 覆盖率(§5), Formal(§8) |
| `08_soc_dv_report.md` | 执行总结(§2), 覆盖率(§3), 测试结果(§4), Bug分析(§5), 性能验证(§6), Sign-off(§7) |
| `09_block_dv_report.md` | 验证结果(§2), 覆盖率(§3), Bug分析(§5), Feature矩阵(§6), 质量评估(§7) |

---

### 附录 E: 模块扩展记录

<!--
实际项目中，每个 IP/模块需要扩展 §3.F (MOD) 的 RTM 条目。
下表示例了多模块场景下的 RTM ID 分配方式。
-->

| 模块名 | 层次路径 | RTM ID 前缀 | 条目数 | 所属 DV Plan | 所属 DV Report |
|--------|---------|------------|:------:|-------------|---------------|
| <!-- CPU_Cluster --> | <!-- top.cpu_cluster --> | RTM-MOD-CPU-* | 8 | `07_block_dv_plan-cpu.md` | `09_block_dv_report-cpu.md` |
| <!-- NPU --> | <!-- top.npu --> | RTM-MOD-NPU-* | 8 | `07_block_dv_plan-npu.md` | `09_block_dv_report-npu.md` |
| <!-- DMA --> | <!-- top.periph.dma --> | RTM-MOD-DMA-* | 8 | `07_block_dv_plan-dma.md` | `09_block_dv_report-dma.md` |
| <!-- SPI_Master --> | <!-- top.periph.spi --> | RTM-MOD-SPI-* | 8 | `07_block_dv_plan-spi.md` | `09_block_dv_report-spi.md` |

---

*由 Chip Design Agent 编写 — 项目需求跟踪矩阵模板*

*本模板与 `00_market.MRD.md`~`09_block_dv_report.md` 配套使用，构成完整的芯片设计规格与验证文档体系。*
