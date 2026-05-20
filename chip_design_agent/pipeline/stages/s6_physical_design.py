"""pipeline/stages/s6_physical_design.py — 物理设计"""

from pipeline.stages.base import BaseStage, StageInput, StageResult


class Stage(BaseStage):
    stage_id = "s6_physical_design"
    stage_name = "物理设计"
    tools_required = ["icc2_shell"]

    def run(self, inputs: StageInput) -> StageResult:
        fp_script = self._generate_floorplan_script()
        self.write_script("icc2_floorplan.tcl", fp_script)

        result = self.run_synopsys_tool("icc2_shell",
                   self.scripts_dir / "icc2_floorplan.tcl")

        report_data = {
            "timestamp": self._now(),
            "status": "completed" if result.success else "failed",
            "summary": "物理设计完成" if result.success else f"ICC2 失败 (exit={result.returncode})",
            "metrics": {"icc2_exit_code": result.returncode},
        }
        report_path = self.write_report("physical_design", report_data)

        return StageResult.ok(
            summary=report_data["summary"],
            metrics=report_data["metrics"],
            files={"physical_design_report": report_path},
        )

    def _generate_floorplan_script(self) -> str:
        return (
            "# ICC2 Floorplan 脚本 (自动生成)\n"
            "set top_module top\n\n"
            "# 读入门网表\n"
            "read_netlist artifacts/s5_synthesis/outputs/netlist/top_syn.v.gz\n\n"
            "# Floorplan\n"
            "create_floorplan -core_utilization 0.7 \\\n"
            "    -core_aspect_ratio 1.0 \\\n"
            "    -core_orientation horizontal\n\n"
            "# 标准单元放置\n"
            "place_standard_cells\n\n"
            "# CTS\n"
            "clock_opt\n\n"
            "# 绕线\n"
            "route_auto\n\n"
            "# 报告\n"
            "report_design > outputs/physical_report.rpt\n\n"
            'echo "Physical design complete"\n'
        )

    def _now(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()
