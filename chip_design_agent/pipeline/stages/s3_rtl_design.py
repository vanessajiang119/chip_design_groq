"""pipeline/stages/s3_rtl_design.py — RTL 编码"""

from pathlib import Path
from pipeline.stages.base import BaseStage, StageInput, StageResult


class Stage(BaseStage):
    stage_id = "s3_rtl_design"
    stage_name = "RTL 编码"
    tools_required = []

    def run(self, inputs: StageInput) -> StageResult:
        rtl_dir = self.outputs_dir / "rtl"
        tb_dir = self.outputs_dir / "tb"
        cons_dir = self.outputs_dir / "cons"
        rtl_dir.mkdir(exist_ok=True)
        tb_dir.mkdir(exist_ok=True)
        cons_dir.mkdir(exist_ok=True)

        # Read top_module from pipeline config
        top = "top"
        if self._engine is not None and self._engine.config is not None:
            top = self._engine.config.top_module

        # Check if a pre-written RTL file exists (from spec-based generation)
        prebuilt_rtl = rtl_dir / f"{top}.v"
        if prebuilt_rtl.exists():
            # Reuse existing RTL, only regenerate testbench and constraints
            rtl_files = sorted(rtl_dir.rglob("*.v"))
        else:
            top_rtl = self._generate_top_module(top, inputs)
            top_path = rtl_dir / f"{top}.v"
            top_path.write_text(top_rtl)
            rtl_files = [top_path]

        tb = self._generate_testbench(top)
        tb_path = tb_dir / f"tb_{top}.v"
        tb_path.write_text(tb)

        sdc = self._generate_constraints(top)
        sdc_path = cons_dir / "sync_constraints.sdc"
        sdc_path.write_text(sdc)

        flist_lines = [str(p) for p in sorted(rtl_dir.rglob("*.v"))]
        flist = "\n".join(flist_lines)
        flist_path = self.outputs_dir / "rtl_file_list.f"
        flist_path.write_text(flist)

        return StageResult.ok(
            summary=f"生成 RTL 代码: {len(flist_lines)} 个模块 (module={top})",
            metrics={"modules": len(flist_lines), "top_module": top},
            files={
                "rtl_top": str(rtl_dir / f"{top}.v"),
                "testbench": str(tb_path),
                "constraints": str(sdc_path),
                "rtl_file_list": str(flist_path),
            },
        )

    def _generate_top_module(self, top: str, inputs: StageInput) -> str:
        return (
            f"// {top}.v — 顶层模块 (由芯片设计流水线自动生成)\n"
            f"// 基于规格书分析生成的架构规格\n\n"
            f"module {top} (\n"
            f"    input  wire        clk,\n"
            f"    input  wire        rst_n,\n"
            f"    // TODO: 根据架构规格添加接口信号\n"
            f"    input  wire [31:0] data_in,\n"
            f"    output wire [31:0] data_out\n"
            f");\n\n"
            f"    // TODO: 模块实例化\n\n"
            f"endmodule\n"
        )

    def _generate_testbench(self, top: str) -> str:
        return (
            f"// tb_{top}.v — Testbench (自动生成)\n"
            f"`timescale 1ns/1ps\n\n"
            f"module tb_{top}();\n\n"
            f"    reg        clk;\n"
            f"    reg        rst_n;\n"
            f"    reg  [31:0] data_in;\n"
            f"    wire [31:0] data_out;\n\n"
            f"    {top} u_{top} (\n"
            f"        .clk    (clk),\n"
            f"        .rst_n  (rst_n),\n"
            f"        .data_in (data_in),\n"
            f"        .data_out(data_out)\n"
            f"    );\n\n"
            f"    initial begin\n"
            f"        clk = 0;\n"
            f"        forever #5 clk = ~clk;\n"
            f"    end\n\n"
            f"    initial begin\n"
            f"        rst_n = 0;\n"
            f"        #20 rst_n = 1;\n"
            f"        // TODO: 添加测试向量\n"
            f"        #100 $finish;\n"
            f"    end\n\n"
            f"endmodule\n"
        )

    def _generate_constraints(self, top: str) -> str:
        return (
            f"# {top} 时序约束 (自动生成)\n"
            f"create_clock -period 10.000 [get_ports clk]\n"
            f"set_clock_uncertainty -setup 0.200 [get_clocks clk]\n"
            f"set_clock_uncertainty -hold 0.050 [get_clocks clk]\n"
            f"set_input_delay -clock clk 2.000 [get_ports data_in]\n"
            f"set_output_delay -clock clk 2.000 [get_ports data_out]\n"
        )
