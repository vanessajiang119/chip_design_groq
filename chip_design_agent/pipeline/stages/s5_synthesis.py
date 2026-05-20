"""pipeline/stages/s5_synthesis.py — 综合与 DFT"""

from pipeline.stages.base import BaseStage, StageInput, StageResult


class Stage(BaseStage):
    stage_id = "s5_synthesis"
    stage_name = "综合与DFT"
    tools_required = ["dc_shell"]

    def run(self, inputs: StageInput) -> StageResult:
        dc_script = self._generate_dc_script(inputs)
        script_path = self.write_script("dc_synthesis.tcl", dc_script)

        result = self.run_synopsys_tool("dc_shell", script_path)

        report_data = {
            "timestamp": self._now(),
            "status": "completed" if result.success else "failed",
            "summary": "DC 综合完成" if result.success else f"DC 综合失败 (exit={result.returncode})",
            "metrics": {"dc_exit_code": result.returncode},
        }
        report_path = self.write_report("synthesis", report_data)

        return StageResult.ok(
            summary=report_data["summary"],
            metrics=report_data["metrics"],
            files={"synthesis_report": report_path},
        )

    def _generate_dc_script(self, inputs: StageInput) -> str:
        return (
            "# DC 综合脚本 (自动生成)\n"
            "set top_module top\n"
            "set rtl_files [glob -types f artifacts/s3_rtl_design/outputs/rtl/*.v]\n\n"
            "analyze -format verilog $rtl_files\n"
            "elaborate $top_module\n"
            "current_design $top_module\n"
            "link\n\n"
            "# 约束\n"
            "set PERIOD 10.0\n"
            "create_clock -period $PERIOD [get_ports clk]\n\n"
            "compile_ultra\n\n"
            "# 报告\n"
            "report_timing > reports/timing_report.rpt\n"
            "report_area > reports/area_report.rpt\n"
            "report_power > reports/power_report.rpt\n\n"
            "# 输出\n"
            "write -format verilog -output outputs/netlist/top_syn.v.gz\n"
            "write -format ddc -output outputs/netlist/top.ddc\n\n"
            'echo "DC synthesis complete"\n'
        )

    def _now(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()
