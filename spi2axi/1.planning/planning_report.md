# SPI2AXI Bridge 文档生成规划报告

## Phase 1: 源材料分析 (Source Analysis) — 完成

### 1.1 项目概述 (Project Overview)

- **项目名称**: SPI2AXI Bridge IP 文档生成
- **源材料**: 7 页 PDF 规格说明 (SPI2AXI SPEC)
- **检测模式**: **Mode A** (通用文档生成模式 — General Document Generation)
- **IP 类型**: Block-level IP — SPI Slave to AXI4-Lite Master Bridge

### 1.2 源文档分析结果 (Source Analysis Results)

源文档 `source_raw.md` 共包含 7 页内容，涵盖以下关键信息：

| 页码 | 主要内容 |
|---|---|
| Page 1 | IP 概述、主要特性 (SPI 接口、AXI Lite 接口、CDC) |
| Page 2 | SPI 接口信号定义、AXI 接口定义、写操作序列 |
| Page 3 | 读操作序列、可配置参数表、应用场景 |
| Page 4 | 操作描述、FSM 说明、帧格式 (Opcode + Address + Data) |
| Page 5 | SPI 命令操作码、SPI 侧寄存器设定 |
| Page 6 | QSPI 读写时序、Wrap 操作支持 |
| Page 7 | Wrap 地址环绕示例 |

### 1.3 关键信息提取 (Key Information Extraction)

**接口方面**:
- SPI 接口: 标准 SPI / QSPI 双模，时钟 50 MHz，低有效片选
- AXI 接口: AXI4-Lite Master，5 通道 (AW/AR/W/R/B)，仅支持 single transfer
- 跨时钟域: 独立 SPI 时钟域 + AXI 时钟域，通过 dual-clock FIFO 实现 CDC

**协议方面**:
- SPI 帧结构: 8-bit Opcode + 32-bit Address (optional) + Dummy Cycles + 32-bit Data
- 数据格式: MSB first
- 读操作需要可编程的 dummy cycles (DUMMY_CYCLES + 1)
- 寄存器地址由 Opcode 编码，内存访问需要 32-bit 地址

**可配置参数 (4 个)**:
- `AXI_ADDR_WIDTH` (默认 32)
- `AXI_DATA_WIDTH` (默认 32)
- `AXI_ID_WIDTH` (默认 3)
- `DUMMY_CYCLES` (默认 32)

**特殊功能**:
- Address Wrap: 可配置的地址回绕，模拟 burst 访问
- QSPI: 四线 SPI 模式，4x 吞吐率

### 1.4 信息完整性评估 (Information Completeness Assessment)

| 章节 | 完整性 | 缺失内容 |
|---|---|---|
| 模块概述 (Module Overview) | 中 (Medium) | 缺少详细的框图、性能指标、面积/功耗目标 |
| 接口定义 (Interface Definition) | 中 (Medium) | SPI 信号完整，AXI 信号缺少详细信号级描述 |
| 子模块划分 (Sub-Module Partition) | 低 (Low) | 未提及内部子模块划分 |
| 有限状态机 (FSM) | 低 (Low) | 提到 FSM 但无具体状态定义和转换表 |
| 流水线 (Pipeline) | 低 (Low) | 无流水线深度和阶段信息 |
| 数据通路 (Datapath) | 低 (Low) | 无 datapath 宽度和结构描述 |
| 配置寄存器 (CSR) | 低 (Low) | 提到 SPI 侧寄存器但无具体 CSR 定义 |
| 时钟与复位 (Clock & Reset) | 中 (Medium) | 提到双时钟域，但无复位策略 |
| SDC 约束 (SDC) | 低 (Low) | 无时序约束信息 |
| 实现要点 (Implementation) | 低 (Low) | 无 RTL coding 指南和设计决策 |
| 验证方案 (Verification) | 低 (Low) | 无验证策略和测试计划 |
| DFT 设计 (DFT) | 低 (Low) | 无 DFT 相关信息 |
| 交付物 (Delivery) | 低 (Low) | 无交付物清单 |
| 修订记录 (Revision) | 低 (Low) | 无修订记录 |

**总评**: 源文档提供了 IP 的核心功能定义和接口规范，但缺少微架构级细节 (micro-architecture details)。后续文档生成阶段需要基于标准 SPI2AXI bridge 设计实践进行合理的补充 (reasonable supplementation)。

### 1.5 设计研究决策 (Design Research Decision)

- **外部研究 (External Research)**: 已禁用 (`enabled: false`)
- **理由**: 源文档已定义清晰的功能规范和接口标准。SPI2AXI Bridge 是标准 IP 类型，设计模式成熟，无需额外的外部研究即可基于设计经验完成文档填充。

---

## Phase 2: 切片计划 (Slicing Plan)

### 2.1 文档切片策略 (Document Slicing Strategy)

将 14 章内容按照生成工具能力进行切片，每个切片对应一个独立的工作单元：

| 切片编号 | 章节 (Chapter) | 依赖关系 | 工作量估计 |
|---|---|---|---|
| S01 | 模块概述 (Module Overview) | 无 | 低 |
| S02 | 接口定义 (Interface Definition) | S01 | 中 |
| S03 | 子模块划分 (Sub-Module Partition) | S01, S02 | 高 |
| S04 | 有限状态机 (FSM) | S03 | 高 |
| S05 | 流水线 (Pipeline) | S03 | 中 |
| S06 | 数据通路 (Datapath) | S03 | 中 |
| S07 | 配置寄存器 (CSR) | S02, S03 | 高 |
| S08 | 时钟与复位 (Clock & Reset) | S01, S03 | 中 |
| S09 | SDC 约束 (SDC) | S02, S08 | 中 |
| S10 | 实现要点 (Implementation) | S03-S09 | 中 |
| S11 | 验证方案 (Verification) | S03-S07 | 高 |
| S12 | DFT 设计 (DFT) | S02, S08 | 低 |
| S13 | 交付物 (Delivery) | S01-S12 | 低 |
| S14 | 修订记录 (Revision) | 无 | 低 |

### 2.2 切片执行顺序 (Execution Order)

```
S01 → S02 → S03 → (S04, S05, S06, S07, S08) → (S09, S10, S11, S12) → S13 → S14
```

- S04-S08 可部分并行生成
- S09-S12 在 S04-S08 基础上进行

---

## Phase 3: 文档生成计划 (Generation Plan)

### 3.1 输出格式 (Output Formats)

| 格式 (Format) | 用途 (Purpose) | 工具 (Tool) |
|---|---|---|
| **Markdown** | 源文档和结构化内容 (Source + structured content) | 直接编写 (Direct write) |
| **HTML** | 格式化设计规格书 (Formatted design spec) | html_chip_design_spec skill |
| **DrawIO** | 框图、FSM 图、架构图 (Block diagram, FSM, architecture) | drawio_chip_diagram skill |

### 3.2 模板使用 (Template Usage)

| 模板 (Template) | 用途 (Purpose) |
|---|---|
| `agents/template/03_block_arch.HLD.md` | 生成 Block-level 架构设计文档 (HLD) |
| `agents/template/04_block_micro.LLD.md` | 生成 Block-level 微架构设计文档 (LLD, 14 章) |

### 3.3 生成策略 (Generation Strategy)

1. 先基于 `source_spec.md` 和 `03_block_arch.HLD.md` 模板生成 **HLD (High-Level Design)**，聚焦于架构框图、接口信号、功能描述
2. 再基于 `source_spec.md` 和 `04_block_micro.LLD.md` 模板生成 **LLD (Low-Level Design / Micro-Architecture)**，覆盖全部 14 个章节
3. 对于源文档中缺失的微架构细节，依据 SPI2AXI Bridge 的标准设计实践进行补充（如 FSM 状态定义、FIFO 深度、CSR 寄存器布局等）
4. 使用 DrawIO 生成架构图和 FSM 图
5. 最终生成 HTML 格式的设计规格书

### 3.4 迭代策略 (Iteration Strategy)

- 最大迭代次数: **5**
- 每次迭代由 `iteration_check` 子代理进行 14 章完整性检查
- 检查标准: 每章内容覆盖度、技术准确性、格式合规性
- 缺失的关键数据（如 state encoding、CSR 地址偏移等）标注为 **待补充 (To Be Completed)**

---

## Phase 4: 交付计划 (Delivery Plan)

### 4.1 交付物清单 (Deliverables)

| 交付物 (Deliverable) | 路径 (Path) | 说明 (Description) |
|---|---|---|
| 规划报告 | `spi2axi/1.planning/planning_report.md` | 本文件 |
| 规划配置 | `spi2axi/1.planning/planning.yml` | 流程控制配置 |
| 源材料规格分析 | `spi2axi/1.planning/source_spec.md` | 结构化源材料分析 |
| 架构设计 HLD | `spi2axi/3.working/spi2axi_bridge_arch.HLD.md` | 高 Level 架构设计 |
| 微架构设计 LLD | `spi2axi/3.working/spi2axi_bridge_micro.LLD.md` | 低 Level 微架构设计 |
| HTML 文档 | `spi2axi/4.result/` | 格式化的设计规格书 |

### 4.2 部署结构 (Directory Structure)

```
spi2axi/
├── 0.start/              # 启动文件
│   └── idea.md           # 用户需求
├── 1.planning/           # 规划阶段 (已完成)
│   ├── planning.yml      # 规划配置
│   ├── source_raw.md     # 原始源文档
│   ├── source_spec.md    # 结构化规格分析
│   └── planning_report.md # 规划报告 (本文件)
├── 2.slice/              # 切片阶段 (待完成)
├── 3.working/            # 工作阶段 (待完成)
│   ├── spi2axi_bridge_arch.HLD.md      # HLD 文档
│   └── spi2axi_bridge_micro.LLD.md     # LLD 文档
└── 4.result/             # 结果阶段 (待完成)
    └── SPI2AXI_*.html     # HTML 设计规格书
```

---

*报告生成日期: 2026-05-21*
*规划模式: Mode A (通用文档生成模式)*
