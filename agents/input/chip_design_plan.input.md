# agent定义

将以下需求，转换为一个专业做写芯片设计的专业agent，chip_design_arch
agent保存所在路径在./agents/commands/
# 需求

## 总体工作流

chip_design_arch 包括：

```
Phase 1: 调研 → design-research 对输入文档
Phase 3: 模块规格生成 + 迭代循环 (最多 3 轮)
Phase 4: 流水线执行 (蜂巢模式) — 每个模块独立运行 chip-pipeline s1~s4
Phase 5: (可选) 顶层集成 — 子模块全部完成后，整合为顶层设计
```

### Phase 1: 规划

根据用户需求，分析工艺节点、设计类型、接口协议，识别模块边界（Ctrl FSM, Data Path, FIFO, Arbiter, 配置接口等）。生成:
- `1.planning/planning.yml` — modules 列表、max_iterations=3
- `1.planning/search_strategy.md` — 搜索策略

### Phase 2: 调研

委托 `design-research` (现有 agent) 进行多轮网络调研。研究结果写入 `2.research/round-N-<topic>.md`。

### Phase 3: 模块规格生成 + 迭代循环

1. 读取 `2.research/` 中的研究结果，识别模块边界，生成 `3.working/module_decomposition.md`
2. **蜂巢模式**: 委托 `chip_spec_gen` (Mode B) 进行模块规格生成：模块分解 → 蜂巢模式并行 `chip_spec_gen.module_spec` → 迭代检查 `chip_spec_gen.iteration_check` → 迭代决策。输出到 `4.result/<ModuleName>_spec_v<N>_YYYYMMDD-HHMM.md`

### Phase 4: 流水线执行 (蜂巢模式)

1. 为每个模块委托一个 `chip_design_arch.pipeline_exec` 实例 (蜂巢模式，`run_in_background`)
2. 每个实例执行:
   - 复制 `chip_design_agent/` → `work_dir.<ModuleName>/`
   - `chip-pipeline init`
   - 配置模块规格书为 s1 输入
   - `chip-pipeline run --from s1_spec_analysis --to s4_verification`
3. 验证覆盖率按工具实际结果报告，目标尽量高
4. 等待所有完成后汇总每个模块的流水线报告

### Phase 5: (可选) 顶层集成

子模块全部完成设计验证后，如果需要顶层集成:
- 在 `work_dir.TopModule/` 下创建顶层设计
- 引用各子模块的规格书作为输入
- 执行 `chip-pipeline run --from s1_spec_analysis --to s4_verification`
- 当前 Phase 4 默认不执行此步骤

## 目录结构约定

所有文件遵循以下目录结构:
```
1.planning/       — 规划文件 (planning.yml, search_strategy.md)
2.research/       — 调研结果 (round-N-<topic>.md)
3.working/        — 工作文件 (模块分解、迭代完整度报告)
4.result/         — 输出结果 (模块规格书)
work_dir.<ModuleName>/  — 每个模块的流水线工作目录
```

## 子 Agent 列表

| 子 Agent | 类型 | 职责 | 输出目录 |
|----------|------|------|---------|
| `chip_design_arch.planning` | 独立 agent | 需求分析、模块分解、生成 planning.yml | 1.planning/ |
| `design-research` | 现有 agent | 多轮网络调研 | 2.research/ |
| `chip_spec_gen (Mode B)` | 编排器 agent | Phase 3 委托: 模块分解 → 蜂巢模式生成 → 迭代检查 → 决策 | 3.working/ + 4.result/ |
| `chip_design_arch.pipeline_exec` | 蜂巢 agent | 复制 pipeline、配置输入、运行 s1~s4 | work_dir.<ModuleName>/ |

## 规则

1. **模板层级**: 设计规格遵循 `agents/template/` 下的 4 级模板层级。各流水线阶段引用对应模板:
   - **s1_spec_analysis** → `01_product.PRD.md` (产品规格: 9 章)
   - **s2_architecture** → `02_soc_arch.HLD.md` (SoC 架构: 14 章+4 附录) + `03_block_arch.HLD.md` (模块架构: 11 章)
   - **s3_rtl_design** → `04_block_micro.LLD.md` (微架构: 14 章)
   填充顺序: **01 → 02 → 03 → 04**，下层继承并细化上层定义的接口和边界
2. **迭代**: Phase 3 最多 3 轮，完整度 >= 80% 即可进入 Phase 4
3. **蜂巢模式**: 并行任务使用 Agent 工具 + `run_in_background`
4. **缺失标记**: 规格书中无法确定的内容标记为 **待补充**
5. **验证覆盖率**: 按工具实际结果报告，目标尽量高；不强制要求 100%
6. **时间戳格式**: `YYYYMMDD-HHMM`
7. **命名规范**: 文件名使用英文，内容中英双语（中文描述 + 专业英文术语/缩写）
