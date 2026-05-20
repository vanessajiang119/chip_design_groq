# Chip Design Agent 用户指导

> **从规格书到 GDS 签核的全流程自动化流水线**

---

## 1. 概述

Chip Design Agent 是一个芯片研发管理自动化系统，覆盖从 **规格书分析** 到 **GDS 签核** 的完整芯片设计流程。它由两部分组成：

| 组件 | 说明 |
|------|------|
| `chip-pipeline` CLI | Python 命令行工具，管理流水线拓扑、状态、检查点和产物注册表 |
| Chip Design Agent | Claude Code Agent，作为交互层编排流水线、解读报告、处理异常 |

### 设计理念

- **Pipeline Engine + Per-Stage Agents** 模式
- 每阶段独立执行，通过产物注册表传递中间结果
- 自动检查点机制，支持断点续跑和回滚
- 标准化 Synopsys EDA 工具调用接口

---

## 2. 快速开始

### 2.1 环境要求

| 依赖 | 说明 |
|------|------|
| Python >= 3.9 | 运行时环境 |
| PyYAML >= 6.0 | 配置文件解析 |
| Claude Code | Agent 交互层 |
| Synopsys EDA 工具 | VCS / DC / ICC2 / PT / ICV (按需) |

### 2.2 安装

```bash
# 从 chip_design_agent 目录安装
cd chip_design_agent
pip install -e .

# 验证安装
chip-pipeline --help
```

### 2.3 启动 Agent

```bash
# 在 chip_design_agent 目录启动 Claude Code
claude

# 在 Claude Code 中使用
/chip-design init my_project --top my_core --tech 7nm
```

---

## 3. 工作流程

### 3.1 标准流程

```
用户提供规格书
      │
      ▼
┌─────────────────┐
│ 1. 规格书分析    │  解析设计参数，生成架构规格文档
└────────┬────────┘
         ▼
┌─────────────────┐
│ 2. 架构设计      │  模块划分，接口定义，架构决策
└────────┬────────┘
         ▼
┌─────────────────┐
│ 3. RTL 编码      │  Verilog/SystemVerilog 实现
└────────┬────────┘
         ▼
┌─────────────────┐
│ 4. 验证          │  VCS 仿真，UVM 验证
└────────┬────────┘
         ▼
┌─────────────────┐
│ 5. 综合与DFT     │  DC 综合，扫描链插入
└────────┬────────┘
         ▼
┌─────────────────┐
│ 6. 物理设计      │  ICC2 布局布线
└────────┬────────┘
         ▼
┌─────────────────┐
│ 7. 时序收敛      │  PT Signoff STA
└────────┬────────┘
         ▼
┌─────────────────┐
│ 8. GDS 签核      │  DRC/LVS 验证，流片交付
└─────────────────┘
```

### 3.2 推荐使用方式

| 场景 | 命令 |
|------|------|
| 首次全流程运行 | `chip-pipeline run` |
| 从某阶段开始 | `chip-pipeline run --from s3_rtl_design` |
| 只跑到某阶段 | `chip-pipeline run --to s5_synthesis` |
| 跳过某阶段 | `chip-pipeline run --skip s4_verification` |
| 重跑单个阶段 | `chip-pipeline stage s5_synthesis --force` |
| 只看执行计划 | `chip-pipeline run --dry-run` |

---

## 4. CLI 命令参考

### 4.1 `init` — 初始化项目

```bash
chip-pipeline init [--force]
```

在当前目录下创建流水线配置文件 `pipeline.yaml` 和目录结构：

```
project/
├── pipeline.yaml          # 流水线配置
├── pipeline.state.json    # 运行状态
├── artifacts/
│   ├── s1_spec_analysis/  # 各阶段的输入/输出/日志
│   ├── s2_architecture/
│   └── ...
├── .checkpoints/          # 自动检查点
└── spec/                  # 规格书存放目录
```

### 4.2 `run` — 运行流水线

```bash
chip-pipeline run                    # 全自动运行
chip-pipeline run --from s3_rtl_design  # 从 RTL 阶段开始
chip-pipeline run --to s5_synthesis     # 跑到综合阶段
chip-pipeline run --skip s4_verification  # 跳过验证阶段
chip-pipeline run --dry-run              # 预览执行计划
```

### 4.3 `stage` — 运行单个阶段

```bash
chip-pipeline stage s1_spec_analysis       # 运行规格书分析
chip-pipeline stage s5_synthesis --force   # 强制重跑综合
```

`--force` 会忽略该阶段已完成的状态，重新执行。

### 4.4 `status` — 查看流水线状态

```bash
chip-pipeline status          # 表格形式
chip-pipeline status --json   # JSON 格式输出
```

状态图标说明：

| 状态 | 图标 | 含义 |
|------|------|------|
| pending | ` ` | 等待执行 |
| running | `>` | 正在运行 |
| completed | `v` | 已完成 |
| failed | `x` | 执行失败 |
| skipped | `-` | 已跳过 |

### 4.5 `checkpoint` — 检查点管理

```bash
chip-pipeline checkpoint list                  # 列出所有检查点
chip-pipeline checkpoint list --stage s3_rtl_design  # 筛选某阶段
chip-pipeline checkpoint restore <cp_id>       # 恢复到指定检查点
chip-pipeline checkpoint clean --keep 5        # 清理旧检查点
```

检查点自动在每阶段成功后创建，包含：
- 阶段结果元数据
- 输出文件快照
- 流水线状态快照

### 4.6 `report` — 生成报告

```bash
chip-pipeline report                    # Markdown 格式
chip-pipeline report --format json      # JSON 格式
chip-pipeline report --format html -o report.html  # HTML 格式
```

### 4.7 `artifacts` — 产物管理

```bash
chip-pipeline artifacts list           # 列出所有注册产物
```

产物注册表位于 `artifacts/registry.json`，记录每个产物的：
- 来源阶段
- 文件路径
- MD5 校验和
- 下游消费者列表

### 4.8 `tool` — EDA 工具检查

```bash
chip-pipeline tool check               # 检查所有 EDA 工具路径
```

---

## 5. 流水线阶段详解

### 阶段 1: 规格书分析 (`s1_spec_analysis`)

| 项目 | 说明 |
|------|------|
| 工具 | 无 |
| 输入 | `spec_doc` (规格书文档) |
| 输出 | `arch_spec`, `parameter_list`, `spec_analysis_report` |
| 超时 | 1 小时 |

**功能:**
- 解析规格书，提取频率、电压、功耗、面积、工艺等设计参数
- 生成架构规格文档 (`arch_spec.md`)
- 生成参数列表 (`parameter_list.yaml`)

### 阶段 2: 架构设计 (`s2_architecture`)

| 项目 | 说明 |
|------|------|
| 工具 | 无 |
| 输入 | `arch_spec` |
| 输出 | `block_diagram`, `interface_def`, `arch_review` |
| 超时 | 2 小时 |

**功能:**
- 基于架构规格生成模块框图
- 定义模块间接口和互连协议

### 阶段 3: RTL 编码 (`s3_rtl_design`)

| 项目 | 说明 |
|------|------|
| 工具 | 无 |
| 输入 | `arch_spec`, `block_diagram`, `interface_def` |
| 输出 | `rtl_files`, `constraints`, `testbench`, `rtl_file_list` |
| 超时 | 4 小时 |

**功能:**
- 生成顶层 Verilog 模块框架
- 生成 testbench 框架
- 生成 Synopsys Design Constraints (SDC)

### 阶段 4: 验证 (`s4_verification`)

| 项目 | 说明 |
|------|------|
| 工具 | VCS |
| 输入 | `rtl_files` |
| 输出 | `verification_report` |
| 超时 | 8 小时 |

**功能:**
- 调用 VCS 编译并运行仿真
- 生成验证报告

### 阶段 5: 综合与 DFT (`s5_synthesis`)

| 项目 | 说明 |
|------|------|
| 工具 | Synopsys DC (dc_shell) |
| 输入 | `rtl_files`, `constraints` |
| 输出 | `netlist` (.v.gz / .ddc), `synthesis_report` |
| 超时 | 8 小时 |

**功能:**
- Design Compiler 逻辑综合
- 生成时序/面积/功耗报告

### 阶段 6: 物理设计 (`s6_physical_design`)

| 项目 | 说明 |
|------|------|
| 工具 | Synopsys ICC2 (icc2_shell) |
| 输入 | `netlist`, `constraints` |
| 输出 | `placed_netlist`, `routed_netlist`, `physical_report` |
| 超时 | 24 小时 |

**功能:**
- 布图规划 (Floorplan)
- 标准单元放置 (Placement)
- 时钟树综合 (CTS)
- 绕线 (Routing)

### 阶段 7: 时序收敛 (`s7_timing_closure`)

| 项目 | 说明 |
|------|------|
| 工具 | Synopsys PT (pt_shell) |
| 输入 | `routed_netlist`, `constraints` |
| 输出 | `timing_report` |
| 超时 | 12 小时 |

**功能:**
- PrimeTime Signoff STA
- Setup/Hold 时序分析
- 生成签核时序报告

### 阶段 8: GDS 签核 (`s8_gds_signoff`)

| 项目 | 说明 |
|------|------|
| 工具 | Synopsys ICV |
| 输入 | `routed_netlist` |
| 输出 | `gds`, `signoff_report`, `signoff_checklist`, `tapeout_manifest` |
| 超时 | 12 小时 |

**功能:**
- GDS 文件生成
- 签核检查清单生成 (DRC/LVS/STA)
- 流片清单生成

---

## 6. 异常处理

### 6.1 常见错误类型

| 错误类型 | 现象 | 处理方法 |
|---------|------|---------|
| 工具未找到 | `tool check` 显示 NOT FOUND | 安装 EDA 工具或更新 PATH |
| 脚本错误 | EDA 工具返回非零退出码 | 查看 `artifacts/<stage>/logs/<tool>.log` |
| 设计错误 | 综合/时序违例 | 修改 RTL 或约束后重跑 |
| 超时 | 阶段运行超过 timeout | 调整 `pipeline.yaml` 中的 timeout 参数 |
| 环境问题 | 磁盘空间不足 / 许可不足 | 清理磁盘 / 检查 license |

### 6.2 故障恢复流程

```
阶段失败
    │
    ▼
chip-pipeline status          ← 确认哪个阶段失败
    │
    ▼
查看 artifacts/<stage_id>/logs/
    │
    ├── EDA 工具日志 (*.log)
    └── 阶段报告 (*_report.md)
    │
    ▼
判断错误类型:
    ├── 环境问题 → 修复环境后 chip-pipeline stage <id> --force
    ├── 脚本问题 → 修改脚本后 chip-pipeline stage <id> --force
    └── 设计问题 → 修改设计后 chip-pipeline stage <id> --force
```

### 6.3 检查点回滚

```bash
# 查看可用的检查点
chip-pipeline checkpoint list

# 恢复到某阶段完成时的状态
chip-pipeline checkpoint restore cp_s3_rtl_design_20260519_120000

# 确认恢复后的状态
chip-pipeline status
```

---

## 7. 配置参考

### 7.1 pipeline.yaml

```yaml
# 核心配置字段说明
name: "chip-design-flow"        # 流水线名称
version: "1.0"                   # 配置版本

project:
  name: "my_chip"                # 项目名称
  tech_node: "28nm"              # 工艺节点
  top_module: "top"              # 顶层模块名

stages:
  - id: s1_spec_analysis         # 阶段 ID (必须唯一)
    name: "规格书分析"            # 阶段显示名称
    enabled: true                 # 是否启用
    input: ["spec_doc"]           # 输入产物列表 (来自注册表)
    output: ["arch_spec"]         # 输出产物列表 (注册到注册表)
    tool: null                    # EDA 工具名 (null = 不需要工具)
    timeout: 3600                 # 超时时间 (秒)
```

### 7.2 阶段间数据流

```
产物注册表 (artifacts/registry.json) 是阶段间传递数据的唯一通道：

s1_spec_analysis  ─── arch_spec ───► s2_architecture
s1_spec_analysis  ─── parameter_list ──► s2_architecture
s2_architecture   ─── block_diagram ──► s3_rtl_design
s2_architecture   ─── interface_def ──► s3_rtl_design
s3_rtl_design     ─── rtl_files ─────► s4_verification
s3_rtl_design     ─── constraints ───► s4_verification, s5_synthesis
```

---

## 8. 项目目录结构

```
my_chip/
├── pipeline.yaml                    # 流水线配置
├── pipeline.state.json              # 运行状态 (自动管理，勿手动修改)
├── spec/
│   └── spec.md                      # 规格书 (用户提供)
├── artifacts/
│   ├── registry.json                # 产物注册表 (自动管理)
│   ├── s1_spec_analysis/
│   │   ├── inputs/                  # 输入文件 (自动链接)
│   │   ├── outputs/                 # 输出文件
│   │   │   ├── arch_spec.md
│   │   │   ├── parameter_list.yaml
│   │   │   └── spec_analysis_report.md
│   │   ├── scripts/                 # 生成的脚本
│   │   └── logs/                    # 运行日志
│   ├── s2_architecture/
│   ├── s3_rtl_design/
│   │   ├── outputs/
│   │   │   ├── rtl/                 # RTL 代码
│   │   │   ├── tb/                  # Testbench
│   │   │   ├── cons/                # 时序约束
│   │   │   └── rtl_file_list.f
│   ├── s4_verification/
│   ├── s5_synthesis/
│   ├── s6_physical_design/
│   ├── s7_timing_closure/
│   └── s8_gds_signoff/
│       └── outputs/
│           ├── gds/                 # GDS 文件
│           ├── signoff/             # 签核检查清单
│           └── tapeout/             # 流片清单
├── .checkpoints/                    # 自动检查点
│   ├── cp_s1_spec_analysis_xxx/
│   ├── cp_s2_architecture_xxx/
│   └── ...
└── reports/                         # 报告输出
```

---

## 9. 最佳实践

### 9.1 项目启动

1. **先写规格书**: 使用 `01_product.PRD.md` 模板编写详细的顶层规格书
2. **初始化项目**: `chip-pipeline init` 创建目录结构
3. **注册规格书**: 将规格书放入 `spec/` 目录
4. **预览计划**: `chip-pipeline run --dry-run` 确认执行顺序

### 9.2 迭代开发

- 非 EDA 阶段 (s1-s3) 可快速迭代 — 适合频繁修改
- EDA 阶段 (s4-s8) 运行时间长 — 建议用 `--from` 和 `--to` 分段执行
- 每阶段完成后 `chip-pipeline checkpoint list` 确认检查点已创建

### 9.3 EDA 工具

- 首次使用前运行 `chip-pipeline tool check`
- 工具脚本在 `artifacts/<stage>/scripts/` 中生成
- 可在运行前手动修改脚本文件
- 日志文件在 `artifacts/<stage>/logs/` 中

### 9.4 多人协作

- `pipeline.yaml` 和 `pipeline.state.json` 应纳入版本控制
- `artifacts/` 目录产物按需纳入版本控制
- `.checkpoints/` 通常是本地缓存，不需要版本控制

---

## 10. 设计规格书模板

Chip Design Agent 配套提供四份设计规格模板，按自然层级组织：

| 模板 | 文件 | 适用场景 |
|------|------|---------|
| 产品需求规格书 (PRD) | `01_product.PRD.md` | 芯片级产品定义 — 市场定位、工艺封装、PPA 目标 |
| SoC 架构蓝图 (HLD) | `02_soc_arch.HLD.md` | SoC 顶层架构 — 系统集成视图、子系统划分 |
| 模块架构蓝图 (HLD) | `03_block_arch.HLD.md` | IP/模块架构 — 外部接口、数据流、配置寄存器 |
| 模块微架构规格书 (LLD) | `04_block_micro.LLD.md` | 模块内部实现 — 子模块划分、流水线、时序 |

使用方式：

```bash
# 将模板复制到项目 spec 目录
cp agents/template/01_product.PRD.md my_project/spec/spec.md
# 编辑填写具体参数后启动流水线
chip-pipeline stage s1_spec_analysis
```

---

## 附录 A: 产物注册表

产物注册表 (`artifacts/registry.json`) 记录所有阶段产物的元数据：

```json
{
  "artifacts": {
    "arch_spec": {
      "stage": "s1_spec_analysis",
      "path": "artifacts/s1_spec_analysis/outputs/arch_spec.md",
      "type": "md",
      "consumers": ["s2_architecture", "s3_rtl_design"],
      "hash": "a1b2c3d4"
    }
  }
}
```

## 附录 B: 状态文件

流水线状态 (`pipeline.state.json`) 记录每阶段的执行状态：

```json
{
  "status": "completed",
  "stages": {
    "s1_spec_analysis": {
      "status": "completed",
      "started_at": "2026-05-19T12:00:00",
      "completed_at": "2026-05-19T12:01:30",
      "exit_code": 0
    }
  }
}
```

> **注意**: `pipeline.state.json` 和 `registry.json` 由系统自动管理，**不要手动编辑**。

---

*文档版本: V1.0 | 更新日期: 2026-05-19*
