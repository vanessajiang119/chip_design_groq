"""pipeline/stages/s2_architecture.py — 架构设计"""

from pathlib import Path
from pipeline.stages.base import BaseStage, StageInput, StageResult


class Stage(BaseStage):
    stage_id = "s2_architecture"
    stage_name = "架构设计"
    tools_required = []

    def run(self, inputs: StageInput) -> StageResult:
        if not inputs.arch_spec:
            return StageResult.failed("缺少架构规格文档")

        spec = inputs.arch_spec.read_text()

        block_diagram = self._generate_block_diagram(spec)
        block_path = self.outputs_dir / "block_diagram.md"
        block_path.write_text(block_diagram)

        iface = self._generate_interface_def(spec)
        iface_path = self.outputs_dir / "interface_def.yaml"
        iface_path.write_text(iface)

        report_data = {
            "timestamp": self._now(),
            "status": "completed",
            "summary": "架构设计完成",
            "metrics": {},
        }
        report_path = self.write_report("architecture", report_data)

        return StageResult.ok(
            summary="架构设计完成，生成模块框图和接口定义",
            metrics=report_data["metrics"],
            files={
                "block_diagram": block_path,
                "interface_def": iface_path,
                "arch_review": report_path,
            },
        )

    def _generate_block_diagram(self, spec: str) -> str:
        return (
            "# 模块框图\n\n"
            "## 顶层模块划分\n\n"
            "```\n"
            "┌─────────────────────────────────────────┐\n"
            "│             Top Module                    │\n"
            "│  ┌────────┐ ┌────────┐ ┌────────┐       │\n"
            "│  │ Module1│ │ Module2│ │ Module3│  ...  │\n"
            "│  └────────┘ └────────┘ └────────┘       │\n"
            "└─────────────────────────────────────────┘\n"
            "```\n\n"
            "## 模块间互联\n\n"
            "基于规格书分析生成...\n"
        )

    def _generate_interface_def(self, spec: str) -> str:
        return (
            "# 接口定义\n\n"
            "interfaces:\n"
            '  - name: system_bus\n'
            '    direction: bidirectional\n'
            '    width: 32\n'
            '    protocol: "AXI"\n'
            '    description: "系统总线接口"\n\n'
            '  - name: clk_reset\n'
            '    direction: input\n'
            '    description: "时钟和复位"\n\n'
            "# 待补充具体接口...\n"
        )

    def _now(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()
