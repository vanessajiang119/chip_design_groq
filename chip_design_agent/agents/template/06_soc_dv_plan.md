# SoC 验证规划 — SoC Verification Plan

> **芯片名称:**
> **版本:** V1.0
> **日期:**
> **状态:** Draft / Review / Final
> **驱动文档:** `01_product.PRD.md` (产品需求)、`02_soc_arch.HLD.md` (系统架构)
> **输出文档:** `08_soc_dv_report.md` (验证报告)

---

## 1. 文档概述

### 1.1 目的与范围

本文档定义 SoC 级验证的完整规划，回答以下问题：
- **验证什么** — SoC 级验证的范围与边界
- **怎么验证** — 采用哪些方法学、各方法学的覆盖范围
- **怎么衡量** — 覆盖率目标、质量门限
- **谁来做、何时完成** — 资源计划、时间节点

本文档的输入来源于 `01_product.PRD.md` (产品需求规格书) 和 `02_soc_arch.HLD.md` (SoC 架构设计)。芯片级功能需求 → SoC 验证场景，系统架构 → 集成验证策略。

### 1.2 适用范围

| 角色 | 关注内容 |
|------|---------|
| 验证主管 | 验证策略、资源规划、时间节点 |
| 设计主管 | 设计交付物要求、接口定义 |
| DV 工程师 | 验证环境架构、测试用例规划 |
| 项目经理 | 进度管理、milestone 对齐 |

### 1.3 参考文档

| 文档 | 版本 | 说明 |
|------|------|------|
| `01_product.PRD.md` | V1.0 | 芯片产品规格、PPA 目标、应用场景 |
| `02_soc_arch.HLD.md` | V1.0 | SoC 顶层架构、子系统定义、互联 |
| `03_block_arch.HLD.md` (各模块) | V1.0 | 模块级架构、接口协议 |
| `04_block_micro.LLD.md` (各模块) | V1.0 | 微架构细节、时序、CSR 定义 |
| `07_block_dv_plan.md` (各模块) | V1.0 | 模块级验证计划 (本 SoC plan 引用) |

---

## 2. 验证范围

### 2.1 在验证范围内 (In-Scope)

| 验证域 | 具体内容 | 来源文档 | 优先级 |
|--------|---------|---------|--------|
| 系统启动流程 | BootROM → DDR Init → Bootloader → OS 加载 | `02_soc_arch.HLD.md §2.3` | P0 |
| 地址映射正确性 | 每个地址区域访问对齐、属性检查 | `02_soc_arch.HLD.md §4.3` | P0 |
| 互联/总线 | SoC 级 NoC/总线仲裁、QoS、带宽 | `02_soc_arch.HLD.md §5` | P0 |
| 电源管理 | 所有功耗状态切换、唤醒源 | `02_soc_arch.HLD.md §8` | P0 |
| 时钟/复位 | 各时钟域频率、门控、复位同步 | `02_soc_arch.HLD.md §7` | P0 |
| 安全 | 安全启动、TrustZone 隔离、密钥管理 | `02_soc_arch.HLD.md §9` | P0 |
| 中断系统 | SoC 级中断控制器、中断路由 | `02_soc_arch.HLD.md §2, §10` | P0 |
| 外设集成验证 | 各高速/低速外设的系统级集成 | `02_soc_arch.HLD.md §6` | P0 |
| 系统性能 | 吞吐、延迟、带宽是否达标 | `01_product.PRD.md §5.1` | P1 |
| 系统功耗 | 各场景功耗是否达标 | `01_product.PRD.md §5.2` | P1 |
| Debug 调试 | JTAG/SWD、断点、trace | `02_soc_arch.HLD.md §10` | P1 |
| 多主并发 | CPU/NPU/DMA 同时访问内存 | `02_soc_arch.HLD.md §5.3` | P1 |
| IO MUX | Pin Muxing 配置组合 | `02_soc_arch.HLD.md §6.3` | P2 |

### 2.2 不在验证范围内 (Out-of-Scope)

| 排除项 | 原因 | 由谁覆盖 |
|--------|------|---------|
| 单个模块内部功能 | 属于模块级验证范畴 | `07_block_dv_plan.md` (模块级) |
| 单个模块内部 FSM/数据通路 | 模块微架构验证 | `07_block_dv_plan.md` |
| DFT 测试模式功能 | DFT ATPG/MBIST | DFT 团队 |
| 软件开发/应用兼容性 | 软件测试 | SW 团队 |
| 板级信号完整性 | PCB/系统级 | SI/PI 团队 |

### 2.3 功能分级 (Feature Tiering)

| 优先级 | 定义 | 对应验证活动 |
|--------|------|-------------|
| **P0 (流片必须)** | 功能不正确则流片不可接受 | 100% 用例通过, 覆盖率目标强制 |
| **P1 (强烈建议)** | 功能应正常工作, 有变通方案可让步 | 主要场景覆盖, 覆盖率目标建议 |
| **P2 (最好有)** | 验证资源允许时覆盖 | 抽测, 不设覆盖率目标 |

---

## 3. 验证方法学矩阵

### 3.1 方法学总览

| 方法学 | 适用阶段 | 验证对象 | 优势 | 局限 |
|--------|---------|---------|------|------|
| **UVM 仿真** | RTL → Tape-out | 功能验证、集成验证 | 场景丰富、可配置、成熟度高 | 速度慢、覆盖率不 guarantee |
| **Formal 验证** | RTL 早期 → Gate level | 控制逻辑、协议合规、安全属性 | 穷尽覆盖、早期发现边界 case | 有限复杂度、数据通路弱 |
| **FPGA 原型验证** | Netlist → 样片 | 系统级场景、OS 启动、性能评估 | 运行速度快、真实场景 | 可见性差、调试困难 |
| **Emulation** | RTL → Gate level | 全芯片级、软件栈验证、功耗评估 | 速度快 (MHz)、Debug 能力强 | 成本高、许可证有限 |
| **C/Co-Simulation** | 架构探索 → RTL | 算法验证、性能模型 | 开发快、架构验证 | 精度不足 |

### 3.2 方法学覆盖矩阵

| 验证域 | UVM 仿真 | Formal | FPGA | Emulation | C/Co-Sim | 首选方法 |
|--------|----------|--------|------|-----------|----------|---------|
| 系统启动流程 | ✓ (系统级) | — | ✓ (主要) | ✓ (主要) | — | FPGA + Emulation |
| 地址映射 | ✓ (系统级) | ✓ (Formal) | ✓ | ✓ | — | Formal + UVM |
| 互联/总线 QoS | ✓ | — | ✓ | ✓ | — | UVM + Emulation |
| 电源管理序列 | ✓ | ✓ (电源域) | — | ✓ | — | UVM + Formal |
| 时钟门控/复位 | ✓ | ✓ (CDC) | — | ✓ | — | Formal CDC + UVM |
| 安全启动 | ✓ | ✓ (签名验证) | ✓ | ✓ | — | Formal + Emulation |
| TrustZone 隔离 | — | ✓ (穷尽) | ✓ | ✓ | — | Formal (穷尽) |
| 外设集成 | ✓ (系统级测试) | — | ✓ (驱动) | ✓ | — | UVM |
| 中断系统 | ✓ | ✓ (中断树) | ✓ | ✓ | — | Formal + UVM |
| 性能/带宽 | ✓ (性能 monitor) | — | ✓ | ✓ | ✓ (架构模型) | Emulation |
| 功耗估算 | — | — | — | ✓ (功耗评估) | ✓ (Power model) | Emulation |
| Debug 接口 | ✓ | ✓ (JTAG TAP) | ✓ | ✓ | — | UVM |
| 多主并发 | ✓ (traffic gen) | — | ✓ | ✓ | — | UVM + Emulation |

### 3.3 UVM 验证

UVM 是 SoC 级验证的**主力方法学**，覆盖绝大多数功能场景。

| 组件 | 用途 | 复用于模块级 |
|------|------|-------------|
| UVM System Testbench | SoC 级 testbench 顶层 | — |
| System-level Virtual Sequencer | 协调多个 VIP 的激励序列 | — |
| AXI/AHB/APB VIP | 总线协议驱动与监测 | ✓ (部分可复用) |
| DDR VIP | DDR 协议合规检查 | — |
| PCIe/USB/Ethernet VIP | 高速外设协议 | — |
| Power Sequence VIP | 电源序列控制 | — |
| Scoreboard | SoC 级数据完整性检查 | ✓ (扩展) |
| Functional Coverage Collector | SoC 级覆盖率收集 | ✓ (扩展) |

### 3.4 Formal 验证

Formal 用于**穷尽验证**关键控制逻辑和安全属性，弥补 UVM 无法覆盖的边界 case。

| Formal 验证项 | 应用范围 | 属性数量 | 穷尽/ bounded |
|--------------|---------|---------|-------------|
| 地址解码互斥 | SoC 地址映射 | <!-- N --> | 穷尽 |
| TrustZone 隔离 | 安全/非安全访问检查 | <!-- N --> | 穷尽 |
| 中断树完整性 | 中断路由逻辑 | <!-- N --> | 穷尽 |
| FSM 安全状态 | 子系统级 FSM 非法状态检查 | <!-- N --> | 穷尽 |
| CDC 检查 | 跨时钟域同步器正确性 | — | 穷尽 |
| X-Propagation | X 态传播检查 | — | 穷尽 |

### 3.5 FPGA 原型验证

FPGA 原型用于**高速系统级验证**，特别是软件/固件协同验证。

| 验证场景 | 运行频率 | 覆盖窗口 | 优势 |
|---------|---------|---------|------|
| OS 启动 (Linux/RTOS) | <!-- 10~50 MHz --> | 每次启动 | 真实 BootROM + Bootloader |
| 驱动验证 | <!-- 10~50 MHz --> | 驱动开发阶段 | 真实外设访问 |
| 应用场景验证 | <!-- 10~50 MHz --> | 系统测试 | 端到端应用场景 |
| 性能评估 | <!-- 10~50 MHz --> | 性能调优阶段 | 接近真实性能 |

> **FPGA 实现约束**: 通常只能实现芯片 30~50% 的逻辑 (ASIC-to-FPGA 比率), 需做层次化分区和接口适配。

### 3.6 Emulation

Emulation 用于**全芯片级深度验证**，同时具备高速运行和良好的 Debug 能力。

| 验证场景 | 速度 | Debug 能力 | 功耗评估 |
|---------|------|-----------|---------|
| 全芯片系统级测试 | <!-- 1~5 MHz --> | 全信号可视 | ✓ |
| 软件栈验证 | <!-- 1~5 MHz --> | 受限 | — |
| 功耗分析 (PowerPro) | — | — | ✓ (波形驱动) |
| Regression (夜间/周末) | — | — | — |

---

## 4. 验证环境架构

### 4.1 SoC 级验证顶层框图

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SoC Verification Environment                      │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │                   UVM Test Layer                          │       │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────────┐  │       │
│  │  │Boot  │ │Power │ │Perf  │ │Secu- │ │Integration   │  │       │
│  │  │Test  │ │Seq   │ │Test  │ │rity  │ │Test (multi-  │  │       │
│  │  │      │ │      │ │      │ │Test  │ │master/stress)│  │       │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────────────┘  │       │
│  └──────────────────────┬───────────────────────────────────┘       │
│                          │                                           │
│  ┌──────────────────────▼───────────────────────────────────┐       │
│  │              Virtual Sequencer / Test Controller           │       │
│  └──────────────────────┬───────────────────────────────────┘       │
│                          │                                           │
│  ┌──────────────────────▼───────────────────────────────────┐       │
│  │                    SoC DUT (Top-level)                     │       │
│  │                                                           │       │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌────────┐ ┌──────────┐    │       │
│  │  │CPU   │ │NPU   │ │Mem   │ │Periph  │ │Interrupt │    │       │
│  │  │Complex│ │Accel │ │Subsys│ │Subsys  │ │Controller│    │       │
│  │  └──────┘ └──────┘ └──────┘ └────────┘ └──────────┘    │       │
│  │  ┌──────────────────────────────────────────────────┐   │       │
│  │  │          Interconnect / NoC / Bus Fabric          │   │       │
│  │  └──────────────────────────────────────────────────┘   │       │
│  └──────────────────────┬───────────────────────────────────┘       │
│                          │                                           │
│  ┌──────────────────────▼───────────────────────────────────┐       │
│  │              VIP / Monitor / Scoreboard Layer             │       │
│  │                                                           │       │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌────┐   │       │
│  │  │AXI   │ │AHB   │ │DDR   │ │PCIe  │ │USB   │ │... │   │       │
│  │  │VIP   │ │VIP   │ │VIP   │ │VIP   │ │VIP   │ │    │   │       │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └────┘   │       │
│  │  ┌──────────────────────────────────────────────────┐   │       │
│  │  │         SoC Scoreboard + 覆盖率 Collector          │   │       │
│  │  └──────────────────────────────────────────────────┘   │       │
│  └──────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 验证环境组件

| 组件 | 类型 | 描述 | 复用来源 |
|------|------|------|---------|
| `soc_test_top` | SV module | 测试顶层, DUT 实例化 | 新建 |
| `soc_tb_env` | UVM env | SoC 级 env, 包含所有 VIP | 新建 |
| `soc_vseq` | UVM virtual sequencer | SoC 级虚拟序列器 | 新建 |
| `axi_vip` | UVM agent | AXI4-Full/Lite VIP | VIP 库 |
| `ahb_vip` | UVM agent | AHB-Lite VIP | VIP 库 |
| `ddr_vip` | UVM agent | DDR4/LPDDR4 VIP | VIP 库 |
| `pcie_vip` | UVM agent | PCIe Gen3/4 VIP | VIP 库 |
| `usb_vip` | UVM agent | USB 3.2 VIP | VIP 库 |
| `eth_vip` | UVM agent | Ethernet VIP | VIP 库 |
| `i2c_spi_vip` | UVM agent | I2C/SPI VIP | VIP 库 |
| `soc_scoreboard` | UVM scoreboard | SoC 级数据比对 | 新建 (可复用模块级) |
| `soc_cov_collector` | UVM coverage | SoC 级覆盖率收集 | 新建 |
| `soc_power_seq` | UVM sequence | 电源序列控制 | 新建 |
| `soc_perf_monitor` | UVM monitor | 性能计数器 monitor | 新建 |

### 4.3 SoC 级 Scoreboard

| 检查项 | 实现方式 | 比对数据源 |
|--------|---------|-----------|
| 数据传输完整性 | Data mirror + compare | AXI VIP monitor + DDR VIP monitor |
| 中断正确性 | Interrupt monitor | 中断控制器状态 + 期望值 |
| 寄存器读写 | Reg model predict | UVM reg model + CSR 预测值 |
| DMA 传输 | Data compare | 源数据 vs 目标数据 |

---

## 5. SoC 级测试场景

### 5.1 系统启动与初始化

| 测试 ID | 场景描述 | 输入 | 期望行为 | 优先级 | 方法学 |
|--------|---------|------|---------|--------|--------|
| SOC_BOOT_001 | 正常启动: POR → BootROM → DDR Init → Bootloader | POR 复位 | 各阶段正确跳转, DDR 初始化成功 | P0 | UVM + FPGA |
| SOC_BOOT_002 | 从所有启动介质引导 | 各启动介质选择 | 正确加载 FSBL | P0 | UVM + FPGA |
| SOC_BOOT_003 | Secure Boot: 签名验证成功 | 正确签名的镜像 | 正常启动 | P0 | UVM + Formal |
| SOC_BOOT_004 | Secure Boot: 签名验证失败 | 篡改镜像 | 启动拒绝 | P0 | UVM + Formal |
| SOC_BOOT_005 | BootROM 校验和失败 | 破损 BootROM | 进入错误处理 | P1 | UVM |
| SOC_BOOT_006 | DDR 初始化失败 / 训练失败 | 模拟 DDR 失败 | 错误上报, 重试或停机 | P1 | UVM |

### 5.2 地址映射与访问

| 测试 ID | 场景描述 | 输入 | 期望行为 | 优先级 | 方法学 |
|--------|---------|------|---------|--------|--------|
| SOC_MAP_001 | 所有地址区域 32/64/128bit 读写 | 各区域 R/W 测试 | 数据正确, 属性匹配 (RO/RW/WO) | P0 | UVM + Formal |
| SOC_MAP_002 | 非法地址访问 | 访问未映射地址 | slave 返回 error / 缺页异常 | P0 | UVM |
| SOC_MAP_003 | 外设寄存器地址边界检查 | 访问寄存器边界 +1/−1 | 正确解码或返回 error | P0 | Formal |
| SOC_MAP_004 | TrustZone 安全/非安全隔离 | NS=0/1 交叉访问 | 非安全无法访问安全区域 | P0 | Formal |
| SOC_MAP_005 | AXI 保护单元 (PBHA) 检查 | 各保护属性组合 | 访存权限正确 | P1 | Formal |

### 5.3 互联与总线

| 测试 ID | 场景描述 | 输入 | 期望行为 | 优先级 | 方法学 |
|--------|---------|------|---------|--------|--------|
| SOC_BUS_001 | 单 master 连续传输 | CPU 连续对 DDR 读写 | 数据完整, 无丢失 | P0 | UVM |
| SOC_BUS_002 | 多 master 并发 (CPU+NPU+DMA) | 三个 master 同时访问 | 仲裁正确, 无死锁 | P0 | UVM |
| SOC_BUS_003 | QoS 优先级验证 | 高/低优先级流量混合 | 高优先级始终优先 | P1 | UVM |
| SOC_BUS_004 | 总线反压 + 超时 | 从设备延迟响应 | 反压传播正确, 超时处理 | P1 | UVM |
| SOC_BUS_005 | Out-of-Order 传输 | 多笔 outstanding 事务 | 数据乱序返回, tag 匹配 | P1 | UVM |
| SOC_BUS_006 | 总线带宽压力 | 100% 带宽持续 1M cycles | 达到预期带宽 | P1 | UVM |

### 5.4 电源管理

| 测试 ID | 场景描述 | 输入 | 期望行为 | 优先级 | 方法学 |
|--------|---------|------|---------|--------|--------|
| SOC_PWR_001 | 所有电源状态切换 | 遍历所有电源状态 | 各状态进入/退出正确 | P0 | UVM + Emulation |
| SOC_PWR_002 | CPU sleep → 中断唤醒 | CPU 执行 WFI, 发送中断 | CPU 恢复执行 | P0 | UVM |
| SOC_PWR_003 | Deep Sleep → 唤醒源 | 所有唤醒源逐一测试 | 唤醒序列正确 | P0 | UVM |
| SOC_PWR_004 | 电源域关断/上电序列 | 关断 PD_CPU/PD_NPU | 序列合规, 隔离正确 | P0 | UVM + Formal |
| SOC_PWR_005 | 唤醒后状态保持 | 睡眠后检查 retention reg | 关键状态未丢失 | P1 | UVM |
| SOC_PWR_006 | DVFS 电压/频率切换 | 各 V/F 对 | 切换过程中功能正确 | P1 | Emulation |

### 5.5 时钟与复位

| 测试 ID | 场景描述 | 输入 | 期望行为 | 优先级 | 方法学 |
|--------|---------|------|---------|--------|--------|
| SOC_CLK_001 | 各时钟域频率正确 | 测量各 clk divider 输出 | 频率符合预期 | P0 | UVM + Formal |
| SOC_CLK_002 | 时钟门控功能 | 使能/关闭各域门控 | 门控生效, 唤醒正确 | P0 | UVM |
| SOC_CLK_003 | 异步复位同步释放 | 复位释放时序 | 各域复位同步释放 | P0 | Formal (CDC) |
| SOC_CLK_004 | CDC 路径验证 | 所有跨时钟域路径 | 无 CDC 违例 | P0 | Formal CDC checker |

### 5.6 中断系统

| 测试 ID | 场景描述 | 输入 | 期望行为 | 优先级 | 方法学 |
|--------|---------|------|---------|--------|--------|
| SOC_INT_001 | 单中断源触发 | 触发一个外设中断 | CPU 正确响应中断 | P0 | UVM |
| SOC_INT_002 | 多中断并发 | 同时触发多个中断 | 优先级仲裁正确 | P0 | UVM |
| SOC_INT_003 | 中断嵌套 | 高优先级中断打断低优先级 | 嵌套处理正确 | P1 | UVM |
| SOC_INT_004 | SPI/PPI/SGI 中断 | 所有中断类型 | 中断路由正确 | P0 | Formal + UVM |
| SOC_INT_005 | 虚假中断 (Spurious) | 无中断源的中断号 | 正确处理 | P2 | UVM |

### 5.7 安全

| 测试 ID | 场景描述 | 输入 | 期望行为 | 优先级 | 方法学 |
|--------|---------|------|---------|--------|--------|
| SOC_SEC_001 | Secure Boot 完整流程 | 签名验证链 | 逐级验证成功 | P0 | UVM + Formal |
| SOC_SEC_002 | TrustZone 隔离穷尽 | 所有安全区域 NS 访问 | 100% 拒绝 | P0 | Formal |
| SOC_SEC_003 | 加密引擎功能 | 各种加密模式 (AES/RSA/SM4) | 加密/解密正确 | P0 | UVM |
| SOC_SEC_004 | TRNG 随机性 | 长时间运行 | 符合 SP800-22 | P1 | UVM (后处理) |
| SOC_SEC_005 | OTP/eFuse 读写 | 编程和读取 | 编程后不可更改 | P0 | UVM |
| SOC_SEC_006 | 安全 JTAG 认证 | 带密码/签名的 JTAG 访问 | 仅认证后可访问 | P1 | Formal + UVM |

### 5.8 系统性能

| 测试 ID | 场景描述 | 输入 | 期望行为 | 优先级 | 方法学 |
|--------|---------|------|---------|--------|--------|
| SOC_PERF_001 | DDR 带宽测试 | STREAM benchmark | 达到目标带宽 | P1 | Emulation |
| SOC_PERF_002 | NPU 推理延迟 | 典型模型 (MobileNet v2) | 延迟 < 目标值 | P1 | Emulation |
| SOC_PERF_003 | 中断响应延迟 | 中断到 ISR 入口 | 延迟 < 1 us | P1 | Emulation |
| SOC_PERF_004 | 系统唤醒延迟 | Deep Sleep → Active | 唤醒时间 < 目标值 | P1 | Emulation |
| SOC_PERF_005 | DMA 传输吞吐 | 连续 DMA | 达到峰值吞吐 | P1 | UVM |

---

## 6. 覆盖率策略

### 6.1 覆盖率目标

| 覆盖率类型 | 目标 | 强制/建议 | 说明 |
|-----------|------|----------|------|
| **代码覆盖率** | | | |
| Line / Block | 95% | 强制 | 不可覆盖的代码需 waive |
| Toggle | 90% | 建议 | 关注关键控制信号 |
| FSM (状态/跳转) | 100% | 强制 | 所有状态和跳转 |
| Branch / Condition | 90% | 强制 | |
| **功能覆盖率** | | | |
| SoC 级 covergroup | 100% | 强制 | 所有 defined bin 被击中 |
| 协议覆盖率 (AXI/DDR) | 95% | 强制 | VIP 内置 coverage |
| 场景覆盖率 | 100% | 强制 | 所有测试场景至少运行一次 |
| **断言覆盖率** | | | |
| Formal asserted properties | 100% | 强制 | Formal 证明全部通过 |
| SVA cover properties | 100% | 建议 | 每个关键时序被触发 |

### 6.2 覆盖率合并策略

| 源 | 合并方法 | 频率 |
|----|---------|------|
| UVM 仿真 (多 seed) | 按 test + seed 渐进合并 | 每次 regression 后 |
| Formal 属性覆盖 | 独立报告, 不合并 | Formal 运行后 |
| FPGA/Emulation 覆盖 | 通过追踪上板场景, 不自动合并 | 按需 |
| **最终合并** | 所有 UVM tests + Formal = 最终覆盖率报告 | Tape-out 前 freeze |

### 6.3 覆盖率 Waive 流程

| 步骤 | 内容 | 责任人 |
|------|------|--------|
| 1. 识别 | 识别无法覆盖的代码/功能点 | DV 工程师 |
| 2. 理由说明 | 填写 waive 理由 (e.g. 冗余代码/DFT only/debug only) | DV 工程师 |
| 3. 评审 | 验证主管 + 设计主管评审 | 验证主管 |
| 4. 归档 | waive 列表纳入 `08_soc_dv_report.md` | DV 工程师 |

---

## 7. 验证基础设施

### 7.1 Regression 策略

| 回归类型 | 触发条件 | 覆盖范围 | 运行时间 | 通过标准 |
|---------|---------|---------|---------|---------|
| **Smoke Test** | 每次代码提交 | 10 个核心 P0 用例 | < 30 min | 100% pass |
| **Full Regression** | 每日 (nightly) | 所有 P0/P1 用例 | < 8 hrs | 100% pass |
| **Weekend Regression** | 每周五 | 所有用例 + 多 seed (×10) | < 48 hrs | 所有 P0 pass, P1 > 90% |
| **Tape-out Regression** | Tape-out 前 | 所有用例 × 最大 seed × 所有 corner | < 1 week | 100% pass, 覆盖率达标 |

### 7.2 验证数据库

| 组件 | 工具/格式 | 用途 |
|------|---------|------|
| 测试用例管理 | <!-- Jira / TestRail / Excel --> | 用例登记、执行跟踪 |
| Bug 跟踪 | <!-- Jira / Bugzilla --> | Bug 提交、分配、状态跟踪 |
| 覆盖率数据库 | <!-- vcd / urg / unified coverage db --> | 覆盖率合并、分析 |
| Regression 报告 | <!-- HTML / JSON --> | 运行结果汇总 |
| 波形数据库 | <!-- fsdb / vcd --> | Debug 用波形存储 |

### 7.3 CI/CD 集成

| 流水线阶段 | 工具 | 触发 | 产出 |
|-----------|------|------|------|
| 代码检查 | <!-- Lint (Spyglass / Ascent) --> | Pre-commit | Lint 报告 |
| 编译检查 | <!-- VCS / Xcelium --> | Pre-commit | 编译通过/失败 |
| Smoke Test | <!-- VCS + UVM --> | Post-commit | Smoke 报告 |
| Full Regression | <!-- LSF / Grid --> | Nightly | Regression 报告 |
| Formal | <!-- VC Formal / JasperGold --> | Nightly | Formal 证明报告 |
| Coverage Merge | <!-- urg / imc --> | Weekly | 覆盖率报告 |

### 7.4 Seed 管理

| 参数 | 策略 |
|------|------|
| 每个 test 最小 seed 数 | <!-- 10 --> |
| Regression 总 seed 数 | <!-- 每个 test × seed count --> |
| Failed seed 保留 | 保留 fail log + waveform |
| Seed 复现 | 通过 +UVM_TEST_SEED 复现 |

---

## 8. 验证时间节点

### 8.1 关键里程碑

| 里程碑 | 目标日期 | 交付物 | 退出标准 |
|--------|---------|--------|---------|
| **M_DV0: DV Plan Freeze** | <!-- YYYY-MM --> | `06_soc_dv_plan.md` (本文档) | 验证计划评审通过 |
| **M_DV1: Testbench Ready** | <!-- YYYY-MM --> | SoC TB 环境跑通 smoke test | TB 编译通过, smoke pass |
| **M_DV2: P0 Tests Pass** | <!-- YYYY-MM --> | 所有 P0 用例通过 | 无 P0 失败, 无 P0 blocker bug |
| **M_DV3: Coverage Freeze** | <!-- YYYY-MM --> | 覆盖率达到目标 | Code cov > 90%, Func cov > 95% |
| **M_DV4: Formal Complete** | <!-- YYYY-MM --> | Formal 证明全部通过 | 0 违例 |
| **M_DV5: Full Regression** | <!-- YYYY-MM --> | Tape-out regression 通过 | 所有用例 100%, 覆盖率达目标 |
| **M_DV6: DV Sign-off** | <!-- YYYY-MM --> | `08_soc_dv_report.md` | Sign-off checklist 全部完成 |

### 8.2 验证活动时间线

```
活动                    Y1                         Y2
               Q1    Q2    Q3    Q4    Q1    Q2    Q3    Q4
            ──┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────►
DV Plan      ████████
TB Build            ████████████
P0 Tests                    ████████████
P1 Tests                          ████████████████
Formal DV       ████████████████████████████████████
Coverage                              ████████████
FPGA DV                     ████████████████████████
Emulation DV                         ████████████████
Regression                                    ████████
Sign-off                                           ██
```

### 8.3 资源需求

| 角色 | 人数 | 时间 | 职责 |
|------|------|------|------|
| 验证主管 | <!-- X --> | 全程 | DV plan, 策略, 资源管理 |
| SoC DV 工程师 | <!-- X --> | Y1 Q2 → Y2 Q4 | SoC TB, 系统级用例 |
| Formal 工程师 | <!-- X --> | Y1 Q1 → Y2 Q4 | Formal 属性开发与证明 |
| FPGA 验证工程师 | <!-- X --> | Y2 Q1 → Y2 Q4 | FPGA 原型移植与测试 |
| Emulation 工程师 | <!-- X --> | Y2 Q2 → Y2 Q4 | Emulation 环境与运行 |

---

## 9. 工具与许可

### 9.1 EDA 工具

| 工具 | 版本 | 用途 | License 需求 |
|------|------|------|-------------|
| <!-- Synopsys VCS / Cadence Xcelium --> | <!-- ver --> | 仿真器 | <!-- N seat --> |
| <!-- Synopsys VC Formal / Cadence JasperGold --> | <!-- ver --> | Formal 验证 | <!-- N seat --> |
| <!-- Synopsys Verdi / Cadence SimVision --> | <!-- ver --> | Debug / 波形查看 | <!-- N seat --> |
| <!-- Synopsys VCS Power / Cadence Xcelium Power --> | <!-- ver --> | 功耗仿真 | <!-- N seat --> |
| <!-- Siemens Questa / Cadence Palladium --> | <!-- ver --> | Emulation | <!-- system --> |

### 9.2 VIP 清单

| VIP | 供应商 | License 类型 | 关键特性 |
|-----|--------|-------------|---------|
| AXI4 VIP | <!-- 厂商 --> | 年度 | out-of-order, QoS |
| AHB VIP | <!-- 厂商 --> | 年度 | — |
| DDR4/LPDDR4 VIP | <!-- 厂商 --> | 年度 | DFI 接口, power mgmt |
| PCIe VIP | <!-- 厂商 --> | 年度 | Gen3/4, multi-lane |
| USB VIP | <!-- 厂商 --> | 年度 | USB 3.2 + 2.0 |
| Ethernet VIP | <!-- 厂商 --> | 年度 | 10/100/1000 |
| Power Sequence VIP | <!-- 厂商/自研 --> | 年度/自研 | 多电源域控制 |

---

## 附录 A: 功能到验证的追溯矩阵

<!-- 从 01_PRD 和 02_SoC HLD 提取功能需求，映射到 SoC 验证场景 -->

| 功能 ID | 来源文档 | 功能描述 | 优先级 | 对应测试 ID | 验证方法 | 覆盖率目标 |
|---------|---------|---------|--------|------------|---------|-----------|
| F001 | PRD §2.5 | 4TOPS NPU 推理 | P0 | SOC_PERF_002 | Emulation | 延迟达标 |
| F002 | HLD §2.3 | 系统启动 | P0 | SOC_BOOT_001~006 | UVM + FPGA | 100% 启动场景 |
| F003 | HLD §4.3 | 地址映射 | P0 | SOC_MAP_001~005 | Formal + UVM | 100% 地址区域 |
| F004 | HLD §5.3 | QoS 带宽保障 | P0 | SOC_BUS_003 | UVM | QoS 配置全覆盖 |
| F005 | HLD §8.3 | 功耗状态切换 | P0 | SOC_PWR_001~006 | UVM | 100% 状态转换 |
| F006 | PRD §6.1 | 安全启动 | P0 | SOC_SEC_001 | Formal + UVM | 所有签名场景 |
| F007 | HLD §9.2 | TrustZone 隔离 | P0 | SOC_SEC_002 | Formal | 100% 隔离规则 |
| F008 | HLD §7.2 | 时钟频率门控 | P0 | SOC_CLK_001~004 | Formal + UVM | 所有时钟域 |
| F009 | HLD §6.3 | Pin Muxing | P1 | SOC_MAP_005 | Formal | 100% 配置组合 |
| F010 | HLD §8.4 | 上电/掉电序列 | P0 | SOC_PWR_004 | UVM + Formal | 100% 序列要求 |
| <!-- ... --> | | | | | | |

## 附录 B: 术语表

| 术语 | 含义 |
|------|------|
| CDC | Clock Domain Crossing |
| DV | Design Verification |
| DUT | Device Under Test |
| Emulation | 硬件仿真加速 (如 Palladium/Zebu) |
| Formal | 形式化验证 (数学证明) |
| MCDC | Modified Condition/Decision Coverage |
| Regression | 回归测试 |
| Seed | 随机种子 (约束随机验证) |
| UVM | Universal Verification Methodology |
| VIP | Verification IP |
| Waive | 豁免 (覆盖率无法达到的合理理由) |

## 附录 C: 参考文档

| 文档 | 版本 | 来源 | 说明 |
|------|------|------|------|
| `01_product.PRD.md` | V1.0 | 内部 | 产品需求规格书 |
| `02_soc_arch.HLD.md` | V1.0 | 内部 | SoC 顶层架构设计 |
| `07_block_dv_plan.md` (各模块) | V1.0 | 内部 | 模块级验证计划 |
| UVM 参考手册 | IEEE 1800.2 | IEEE | UVM 标准 |
| EDA 工具用户指南 | — | 供应商 | 仿真/Formal/Emulation 工具手册 |

---

*本文档由 Chip Design Agent 生成 — SoC DV Plan Template V1.0*

*完成本文档后，模块级验证请参考 `07_block_dv_plan.md`，验证报告请参考 `08_soc_dv_report.md`。*
