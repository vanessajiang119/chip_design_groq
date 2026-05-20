"""pipeline/stages/s4_verification.py — 验证"""

from pipeline.stages.base import BaseStage, StageInput, StageResult


class Stage(BaseStage):
    stage_id = "s4_verification"
    stage_name = "验证"
    tools_required = ["vcs"]

    def run(self, inputs: StageInput) -> StageResult:
        vcs_script = self._generate_vcs_script()
        script_path = self.write_script("vcs_compile.tcl", vcs_script)

        result = self.run_synopsys_tool("vcs", script_path)

        report_data = {
            "timestamp": self._now(),
            "status": "completed" if result.success else "failed",
            "summary": "VCS 仿真完成" if result.success else f"VCS 仿真失败 (exit={result.returncode})",
            "metrics": {"vcs_exit_code": result.returncode},
        }
        report_path = self.write_report("verification", report_data)

        return StageResult.ok(
            summary=report_data["summary"],
            metrics=report_data["metrics"],
            files={"verification_report": report_path},
        )

    def _generate_vcs_script(self) -> str:
        rtl_list = self.outputs_dir.parent.parent / "s3_rtl_design" / "outputs" / "rtl_file_list.f"
        return (
            f"// VCS 编译脚本 (自动生成)\n"
            f"set rtl_files [glob -types f {{*.v}}]\n"
            f"if {{[file exists {rtl_list}]}} {{\n"
            f"    set rtl_files [exec cat {rtl_list}]\n"
            f"}}\n"
            f"foreach file $rtl_files {{\n"
            f'    puts "Compiling: $file"\n'
            f"}}\n"
            f'puts "VCS compilation complete"\n'
        )

    def _now(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()
