"""pipeline/stages/s1_spec_analysis.py — 规格书分析"""

from pathlib import Path
from pipeline.stages.base import BaseStage, StageInput, StageResult


class Stage(BaseStage):
    stage_id = "s1_spec_analysis"
    stage_name = "规格书分析"
    tools_required = []

    def run(self, inputs: StageInput) -> StageResult:
        spec_path = inputs.spec_doc
        if not spec_path or not spec_path.exists():
            return StageResult.failed("规格书文件不存在")

        spec_content = spec_path.read_text()
        params = self._parse_spec(spec_content)

        arch_spec = self._generate_arch_spec(spec_content, params)
        arch_spec_path = self.outputs_dir / "arch_spec.md"
        arch_spec_path.write_text(arch_spec)

        param_list = self._generate_params(params)
        param_path = self.outputs_dir / "parameter_list.yaml"
        param_path.write_text(param_list)

        report_data = {
            "timestamp": self._now(),
            "status": "completed",
            "summary": f"已分析规格书，提取 {len(params)} 个设计参数",
            "metrics": {"parameters": len(params), "sections": self._count_sections(spec_content)},
        }
        report_path = self.write_report("spec_analysis", report_data)

        return StageResult.ok(
            summary=f"规格书分析完成，生成架构规格文档",
            metrics=report_data["metrics"],
            files={
                "arch_spec": arch_spec_path,
                "parameter_list": param_path,
                "spec_analysis_report": report_path,
            },
        )

    def _parse_spec(self, content: str) -> dict:
        params = {}
        for line in content.split("\n"):
            line = line.strip()
            for prefix in ["频率", "电压", "功耗", "面积", "温度", "工艺", "接口", "数据位宽"]:
                if line.startswith(prefix):
                    parts = line.split(":", 1) if ":" in line else line.split("：", 1)
                    if len(parts) == 2:
                        params[prefix] = parts[1].strip()
        return params

    def _generate_arch_spec(self, content: str, params: dict) -> str:
        lines = [
            "# 架构规格书",
            "",
            "## 1. 设计概述",
            "",
            "基于规格书分析生成的架构设计规格。",
            "",
            "## 2. 设计参数",
            "",
            "| 参数 | 值 |",
            "|------|-----|",
        ]
        for k, v in params.items():
            lines.append(f"| {k} | {v} |")
        body = content[:2000] if len(content) > 2000 else content
        lines.extend([
            "",
            "## 3. 功能描述",
            "",
            body,
            "",
            "## 4. 接口定义",
            "",
            "待架构设计阶段补充...",
            "",
        ])
        return "\n".join(lines)

    def _generate_params(self, params: dict) -> str:
        return "# 设计参数列表\n\n" + "\n".join(f"{k}: {v}" for k, v in params.items()) + "\n"

    def _now(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()

    def _count_sections(self, content: str) -> int:
        return sum(1 for line in content.split("\n") if line.startswith("#"))
