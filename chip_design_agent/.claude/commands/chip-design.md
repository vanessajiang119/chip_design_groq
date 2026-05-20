---
name: chip-design
description: 启动芯片研发管理 Agent，从规格书到 GDS 全流程
---

## 用法

```
/chip-design [command]
```

启动 Chip Design Agent，进入芯片设计流水线模式。

### 子命令
- `init <project> --top <module>` — 初始化新项目
  - 支持 `--template 01|02|03|04` 选择设计规格模板层级起点
- `run [--from <stage>]` — 运行流水线
- `status` — 查看状态
- `report --format html` — 生成报告

## 模板使用流程 (Template Usage Flow)

设计规格遵循 `agents/template/` 下的 4 级模板层级，按自顶向下顺序填充:

| 层级 | 模板 | 对应流水线阶段 |
|------|------|--------------|
| 01 PRD | `01_product.PRD.md` (9章) | s1_spec_analysis |
| 02 SoC HLD | `02_soc_arch.HLD.md` (14章+4附录) | s2_architecture |
| 03 Block HLD | `03_block_arch.HLD.md` (11章) | s2_architecture |
| 04 Block LLD | `04_block_micro.LLD.md` (14章) | s3_rtl_design |

填充顺序: **01 → 02 → 03 → 04**，下层继承并细化上层定义的接口和边界。

### 示例
```
/chip-design init my_chip --top usb_ctrl --tech 28nm --spec doc/spec.md
/chip-design run
/chip-design status
/chip-design report --format html
```
