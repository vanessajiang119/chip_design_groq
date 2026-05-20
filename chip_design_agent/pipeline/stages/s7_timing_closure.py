"""pipeline/stages/s7_timing_closure.py — 时序收敛"""

from pipeline.stages.base import BaseStage, StageInput, StageResult


class Stage(BaseStage):
    stage_id = "s7_timing_closure"
    stage_name = "时序收敛"
    tools_required = ["pt_shell"]

    def run(self, inputs: StageInput) -> StageResult:
        pt_script = self._generate_pt_script()
        script_path = self.write_script("pt_signoff.tcl", pt_script)

        result = self.run_synopsys_tool("pt_shell", script_path)

        report_data = {
            "timestamp": self._now(),
            "status": "completed" if result.success else "failed",
            "summary": "PT signoff 时序分析完成" if result.success else f"PT 失败 (exit={result.returncode})",
            "metrics": {"pt_exit_code": result.returncode},
        }
        report_path = self.write_report("timing_closure", report_data)

        return StageResult.ok(
            summary=report_data["summary"],
            metrics=report_data["metrics"],
            files={"timing_signoff_report": report_path},
        )

    def _generate_pt_script(self) -> str:
        return (
            "# PT Signoff 时序脚本 (自动生成)\n"
            "set top_module top\n\n"
            "read_verilog artifacts/s6_physical_design/outputs/design/top_routed.v.gz\n"
            "current_design $top_module\n"
            "link\n\n"
            "# 约束\n"
            "read_sdc artifacts/s6_physical_design/outputs/sdc/top_layout.sdc\n\n"
            "# 时序分析\n"
            "report_timing -setup -max_paths 100 > outputs/timing_reports/setup_timing.rpt\n"
            "report_timing -hold -max_paths 100 > outputs/timing_reports/hold_timing.rpt\n"
            "report_timing -signoff > outputs/timing_reports/signoff_timing.rpt\n\n"
            'echo "Timing signoff complete"\n'
        )

    def _now(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()
