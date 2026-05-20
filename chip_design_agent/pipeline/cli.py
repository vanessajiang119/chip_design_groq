#!/usr/bin/env python3
"""CLI entry point for the Chip Design Pipeline (``chip-pipeline``)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import NoReturn

from pipeline.config import PipelineConfig, StageDef
from pipeline.engine import PipelineEngine


# ======================================================================
# default pipeline config
# ======================================================================
DEFAULT_STAGES = [
    StageDef(id="s1_spec_analysis",    name="规格书分析",       enabled=True,
             input=["spec_doc"],        output=["arch_spec", "parameter_list"],
             timeout=3600),
    StageDef(id="s2_architecture",     name="架构设计",         enabled=True,
             input=["arch_spec"],      output=["block_diagram", "interface_def"],
             timeout=7200),
    StageDef(id="s3_rtl_design",       name="RTL 编码",        enabled=True,
             input=["arch_spec", "block_diagram", "interface_def"],
             output=["rtl_files", "constraints", "rtl_file_list"],
             timeout=14400),
    StageDef(id="s4_verification",     name="验证",             enabled=True, tool="vcs",
             input=["rtl_files"],      output=["verification_report"],
             timeout=28800),
    StageDef(id="s5_synthesis",        name="综合与DFT",        enabled=True, tool="dc_shell",
             input=["rtl_files", "constraints"],
             output=["netlist", "synthesis_report"],
             timeout=28800),
    StageDef(id="s6_physical_design",  name="物理设计",         enabled=True, tool="icc2_shell",
             input=["netlist", "constraints"],
             output=["placed_netlist", "routed_netlist", "physical_report"],
             timeout=86400),
    StageDef(id="s7_timing_closure",   name="时序收敛",         enabled=True, tool="pt_shell",
             input=["routed_netlist", "constraints"],
             output=["timing_report"],
             timeout=43200),
    StageDef(id="s8_gds_signoff",      name="GDS签核",          enabled=True, tool="icv",
             input=["routed_netlist"], output=["gds", "signoff_report"],
             timeout=43200),
]


DEFAULT_CONFIG = PipelineConfig(
    name="chip-pipeline",
    version="1.0.0",
    project_name="unnamed",
    tech_node="28nm",
    top_module="top",
    stages=DEFAULT_STAGES,
)


# ======================================================================
# helpers
# ======================================================================
def _load_config(config_path: str | Path) -> PipelineConfig:
    path = Path(config_path)
    if not path.exists():
        print(f"Error: config file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return PipelineConfig.load(path)


def _get_engine(config: str | Path, project_dir: str | Path) -> PipelineEngine:
    return PipelineEngine(config_path=config, project_dir=project_dir)


def _print_json(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


# ======================================================================
# subcommand handlers
# ======================================================================
def cmd_init(args: argparse.Namespace) -> None:
    """Initialize a new pipeline project."""
    project_dir = Path(args.project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)

    # directories
    for sub in ("stages", "templates", "reports", "artifacts", ".checkpoints"):
        (project_dir / sub).mkdir(parents=True, exist_ok=True)

    # default config
    config_path: Path = project_dir / "pipeline.yaml"
    if config_path.exists() and not args.force:
        print(f"Config already exists: {config_path} (use --force to overwrite)")
    else:
        cfg = DEFAULT_CONFIG
        cfg.project_name = project_dir.name
        cfg.save(config_path)
        print(f"Created config: {config_path}")

    # default state file
    state_file = project_dir / "pipeline.state.json"
    if not state_file.exists():
        with open(state_file, "w") as fh:
            json.dump({"stages": {}}, fh, indent=2)
        print(f"Created state: {state_file}")

    print(f"Initialized pipeline project at: {project_dir.resolve()}")


def cmd_run(args: argparse.Namespace) -> None:
    """Run the full pipeline or a range of stages."""
    engine = _get_engine(args.config, args.project_dir)
    skip_list = args.skip.split(",") if args.skip else None

    for result in engine.run(
        from_stage=args.from_stage,
        to_stage=args.to_stage,
        skip=skip_list,
        dry_run=args.dry_run,
    ):
        status = "OK" if result.success else "FAIL"
        print(f"  [{status}] {result.stage_id}: {result.summary}")
        if not result.success:
            sys.exit(1)


def cmd_stage(args: argparse.Namespace) -> None:
    """Run a single pipeline stage."""
    engine = _get_engine(args.config, args.project_dir)
    result = engine.run_stage(args.stage_id, force=args.force)
    status = "OK" if result.success else "FAIL"
    print(f"  [{status}] {result.stage_id}: {result.summary}")
    if not result.success:
        sys.exit(1)


def cmd_status(args: argparse.Namespace) -> None:
    """Show current pipeline status."""
    engine = _get_engine(args.config, args.project_dir)
    stages_info = []
    for sd in engine.config.stages:
        st = engine.state.get_stage(sd.id)
        stages_info.append(
            {
                "id": sd.id,
                "name": sd.name,
                "enabled": sd.enabled,
                "status": st.status if st else "pending",
                "started_at": st.started_at if st else None,
                "completed_at": st.completed_at if st else None,
                "exit_code": st.exit_code if st else None,
                "error": st.error if st else None,
            }
        )

    if args.json:
        _print_json(
            {
                "project_dir": str(engine.project_dir.resolve()),
                "config": args.config,
                "overall": engine.state._overall_status(),
                "stages": stages_info,
            }
        )
    else:
        print(f"\nPipeline: {engine.config.name}  ({engine.config.project_name})")
        print(f"Overall status: {engine.state._overall_status()}")
        print(f"{'='*60}")
        for s in stages_info:
            icon = {"pending": " ", "running": ">", "completed": "v", "failed": "x", "skipped": "-"}
            mark = icon.get(s["status"], "?")
            print(f"  [{mark}] {s['id']:25s} {s['status']:12s} {s['name']}")
        print()


def cmd_checkpoint(args: argparse.Namespace) -> None:
    """Manage pipeline checkpoints."""
    engine = _get_engine(args.config, args.project_dir)

    if args.action == "list":
        cps = engine.checkpointer.list_checkpoints(stage=args.stage)
        if not cps:
            print("No checkpoints found.")
            return
        for cp in cps:
            ts = cp.get("timestamp", "?")[:19]
            print(f"  {cp['id']}  {ts}  stage={cp['stage_id']}")
        return

    if args.action == "restore":
        try:
            result = engine.checkpointer.restore(args.checkpoint_id)
            print(f"Restored checkpoint: {args.checkpoint_id}")
            print(f"  Stage: {result['metadata']['stage_id']}")
            print(f"  Outputs restored: {len(result.get('outputs', {}))}")
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        return

    if args.action == "clean":
        removed = engine.checkpointer.clean(keep=args.keep)
        print(f"Removed {removed} old checkpoint(s). (keeping {args.keep})")
        return

    print(f"Unknown checkpoint action: {args.action}", file=sys.stderr)
    sys.exit(1)


def cmd_report(args: argparse.Namespace) -> None:
    """Generate a pipeline report."""
    engine = _get_engine(args.config, args.project_dir)

    report_lines = []
    report_lines.append(f"# Pipeline Report: {engine.config.name}")
    report_lines.append(f"")
    report_lines.append(f"- **Project**: {engine.config.project_name}")
    report_lines.append(f"- **Tech node**: {engine.config.tech_node}")
    report_lines.append(f"- **Top module**: {engine.config.top_module}")
    report_lines.append(f"- **Overall status**: {engine.state._overall_status()}")
    report_lines.append(f"")

    for sd in engine.config.stages:
        st = engine.state.get_stage(sd.id)
        status = st.status if st else "pending"
        report_lines.append(f"## {sd.id}: {sd.name}")
        report_lines.append(f"")
        report_lines.append(f"- **Status**: {status}")
        report_lines.append(f"- **Tool**: {sd.tool or 'N/A'}")
        if st and st.started_at:
            report_lines.append(f"- **Started**: {st.started_at}")
        if st and st.completed_at:
            report_lines.append(f"- **Completed**: {st.completed_at}")
        if st and st.error:
            report_lines.append(f"- **Error**: {st.error}")
        report_lines.append(f"")

    artifacts = engine.registry.list_artifacts()
    if artifacts:
        report_lines.append(f"## Artifacts")
        report_lines.append(f"")
        for a in artifacts:
            report_lines.append(f"- `{a['name']}` ({a['art_type']}, stage: {a['stage']})")

    report_text = "\n".join(report_lines)

    if args.format == "markdown":
        print(report_text)
    elif args.format == "json":
        _print_json(
            {
                "name": engine.config.name,
                "project_name": engine.config.project_name,
                "tech_node": engine.config.tech_node,
                "top_module": engine.config.top_module,
                "overall_status": engine.state._overall_status(),
                "stages": [
                    {
                        "id": sd.id,
                        "name": sd.name,
                        "status": (engine.state.get_stage(sd.id).status
                                   if engine.state.get_stage(sd.id) else "pending"),
                    }
                    for sd in engine.config.stages
                ],
                "artifacts": artifacts,
            }
        )
    elif args.format == "html":
        _render_html_report(args.output, report_text, engine)
    else:
        print(f"Unknown format: {args.format}", file=sys.stderr)
        sys.exit(1)


def _render_html_report(output: str, report_text: str, engine) -> None:
    """Render a minimal HTML report."""
    html_parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        f"<title>Pipeline Report - {engine.config.name}</title>",
        "<style>body{font-family:sans-serif;max-width:960px;margin:2em auto;padding:0 1em}"
        "h1{border-bottom:2px solid #333}table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #ccc;padding:8px;text-align:left}"
        "</style></head><body>",
        "<pre>",
        report_text,
        "</pre></body></html>",
    ]
    html = "\n".join(html_parts)

    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html)
        print(f"Report written to: {out_path}")
    else:
        print(html)


def cmd_artifacts(args: argparse.Namespace) -> None:
    """List artifacts in the registry."""
    engine = _get_engine(args.config, args.project_dir)
    artifacts = engine.registry.list_artifacts()

    if args.json:
        _print_json(artifacts)
        return

    if not artifacts:
        print("No artifacts registered.")
        return

    print(f"\nArtifacts ({len(artifacts)} total):")
    print(f"{'='*60}")
    for a in artifacts:
        print(f"  {a['name']:30s} {a['art_type']:15s} stage={a['stage']}")
    print()


def cmd_tool(args: argparse.Namespace) -> None:
    """Check EDA tool availability."""
    engine = _get_engine(args.config, args.project_dir)

    all_ok = True
    for sd in engine.config.stages:
        if not sd.tool:
            continue
        available = shutil.which(sd.tool) is not None
        status = "available" if available else "NOT FOUND"
        if not available:
            all_ok = False
        print(f"  {sd.tool:20s} {status:12s} ({sd.id}: {sd.name})")

    if not all_ok:
        print("\nSome tools are missing. Install them or update pipeline.yaml.")
        sys.exit(1)


# ======================================================================
# argument parser
# ======================================================================
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chip-pipeline",
        description="Chip Design Pipeline: 8-stage flow from spec to GDS.",
    )
    p.add_argument(
        "--config",
        default="pipeline.yaml",
        help="Path to pipeline config YAML (default: pipeline.yaml)",
    )
    p.add_argument(
        "--project-dir",
        default=".",
        help="Project root directory (default: current dir)",
    )

    sub = p.add_subparsers(dest="command", required=True)

    # -- init ----------------------------------------------------------
    init_p = sub.add_parser("init", help="Initialize a new pipeline project")
    init_p.add_argument("--force", action="store_true", help="Overwrite existing files")

    # -- run -----------------------------------------------------------
    run_p = sub.add_parser("run", help="Run the full pipeline or a range")
    run_p.add_argument("--from", dest="from_stage", help="Stage id to start from")
    run_p.add_argument("--to", dest="to_stage", help="Stage id to stop at (inclusive)")
    run_p.add_argument("--skip", help="Comma-separated list of stage ids to skip")
    run_p.add_argument("--dry-run", action="store_true", help="Print what would run")

    # -- stage ---------------------------------------------------------
    stage_p = sub.add_parser("stage", help="Run a single pipeline stage")
    stage_p.add_argument("stage_id", help="Stage id to execute")
    stage_p.add_argument("--force", action="store_true", help="Re-run even if completed")

    # -- status --------------------------------------------------------
    status_p = sub.add_parser("status", help="Show pipeline status")
    status_p.add_argument("--json", action="store_true", help="Output as JSON")

    # -- checkpoint ----------------------------------------------------
    cp_p = sub.add_parser("checkpoint", help="Manage checkpoints")
    cp_sub = cp_p.add_subparsers(dest="action", required=True)

    cp_list = cp_sub.add_parser("list", help="List checkpoints")
    cp_list.add_argument("--stage", help="Filter by stage id")

    cp_restore = cp_sub.add_parser("restore", help="Restore a checkpoint")
    cp_restore.add_argument("checkpoint_id", help="Checkpoint id to restore")

    cp_clean = cp_sub.add_parser("clean", help="Remove old checkpoints")
    cp_clean.add_argument("--keep", type=int, default=5, help="Number to keep (default: 5)")

    # -- report --------------------------------------------------------
    report_p = sub.add_parser("report", help="Generate a pipeline report")
    report_p.add_argument(
        "--format",
        choices=["markdown", "json", "html"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    report_p.add_argument("--output", help="Write HTML report to file")

    # -- artifacts -----------------------------------------------------
    art_p = sub.add_parser("artifacts", help="Manage artifacts")
    art_sub = art_p.add_subparsers(dest="action", required=True)

    art_list = art_sub.add_parser("list", help="List registered artifacts")
    art_list.add_argument("--json", action="store_true", help="Output as JSON")

    # -- tool ----------------------------------------------------------
    tool_p = sub.add_parser("tool", help="Check EDA tool availability")
    tool_sub = tool_p.add_subparsers(dest="action", required=True)
    tool_check = tool_sub.add_parser("check", help="Check EDA tools availability")

    return p


# ======================================================================
# entry point
# ======================================================================
def main(argv: list[str] | None = None) -> NoReturn:
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "init": cmd_init,
        "run": cmd_run,
        "stage": cmd_stage,
        "status": cmd_status,
        "checkpoint": cmd_checkpoint,
        "report": cmd_report,
        "artifacts": cmd_artifacts,
        "tool": cmd_tool,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()

    sys.exit(0)


if __name__ == "__main__":
    main()
