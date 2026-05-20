"""Abstract base class for all pipeline stages.

Each concrete stage (s1_spec_analysis, s2_architecture, etc.) inherits from
:class:`BaseStage` and implements the abstract :meth:`run` method.

The :meth:`execute` method is a **template method** that coordinates the
standard execution workflow:

    check_tools -> resolve_inputs -> run() -> register_outputs
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from pipeline.config import PipelineConfig, StageDef
from pipeline.engine import StageResult
from pipeline.registry import ArtifactRegistry


# ===================================================================
# Data classes
# ===================================================================


@dataclass
class StageInput:
    """Resolved inputs for a pipeline stage.

    Each field corresponds to a known artifact category that upstream
    stages may produce.  Unknown / extra artifacts are placed in
    ``extra``.
    """

    spec_doc: Optional[Path] = None
    arch_spec: Optional[Path] = None
    block_diagram: Optional[Path] = None
    interface_def: Optional[Path] = None
    rtl_dir: Optional[Path] = None
    netlist_dir: Optional[Path] = None
    constraints: Optional[Path] = None
    design_db: Optional[Path] = None
    extra: dict[str, Path] = field(default_factory=dict)


@dataclass
class ToolResult:
    """Result of running an external EDA tool (e.g. Synopsys DC, PT)."""

    success: bool
    log_path: Path
    returncode: int = 0
    stdout: str = ""


# ===================================================================
# BaseStage
# ===================================================================


class BaseStage(ABC):
    """Abstract base class for chip design pipeline stages.

    Class-level attributes (``stage_id``, ``stage_name``,
    ``tools_required``) are overridden by concrete subclasses.

    Parameters
    ----------
    stage_def : StageDef
        The stage definition from the pipeline YAML configuration.
    project_dir : str
        Root directory of the project (used to derive artifact paths).
    """

    # -- class-level metadata (overridden by subclasses) --------------
    stage_id: str = ""
    stage_name: str = ""
    tools_required: list[str] = []

    def __init__(self) -> None:
        self._stage_def: Optional[StageDef] = None
        self._project_dir: Optional[Path] = None
        self._registry: Optional[ArtifactRegistry] = None
        self._engine: Any = None
        self.inputs_dir: Optional[Path] = None
        self.outputs_dir: Optional[Path] = None
        self.logs_dir: Optional[Path] = None
        self.scripts_dir: Optional[Path] = None

    def _init_dirs(self, stage_def: StageDef, project_dir: Path) -> None:
        """Set up stage directories (called from execute())."""
        self._stage_def = stage_def
        self._project_dir = project_dir
        artifacts_root = project_dir / "artifacts" / stage_def.id
        self.inputs_dir = artifacts_root / "inputs"
        self.outputs_dir = artifacts_root / "outputs"
        self.logs_dir = artifacts_root / "logs"
        self.scripts_dir = artifacts_root / "scripts"
        for d in (self.inputs_dir, self.outputs_dir, self.logs_dir, self.scripts_dir):
            d.mkdir(parents=True, exist_ok=True)

    # -- public template method ---------------------------------------

    def execute(
        self,
        engine: Any = None,
        stage_def: Optional[StageDef] = None,
    ) -> StageResult:
        """Template method — coordinates the standard execution workflow.

        The engine calls ``instance.execute(self, stage_def)`` where
        *self* is the :class:`PipelineEngine` instance.

        Workflow
        --------
        1. :meth:`_check_tools` — verify every tool in ``tools_required``
           is on ``$PATH``.
        2. :meth:`_resolve_inputs` — look up artifact names in the
           registry and symlink them into ``inputs_dir``.
        3. :meth:`run` (abstract) — stage-specific logic.
        4. :meth:`_register_outputs` — register produced files in the
           artifact registry.
        """
        if stage_def is None:
            return StageResult.failed(
                stage_id=self.stage_id,
                summary="No stage definition provided",
            )

        # Hang on to the engine for registry / config access
        if engine is not None:
            self._engine = engine
            if hasattr(engine, "registry"):
                self._registry = engine.registry

        # Initialize directories from stage_def + engine project_dir
        project_dir = Path(engine.project_dir) if engine is not None else Path.cwd()
        self._init_dirs(stage_def, project_dir)

        # -- phase 1: check tools -------------------------------------
        missing = self._check_tools()
        if missing:
            return StageResult.failed(
                stage_id=stage_def.id,
                summary=f"Missing required tools: {', '.join(missing)}. "
                f"Ensure they are installed and on PATH.",
            )

        # -- phase 2: resolve inputs ----------------------------------
        inputs = self._resolve_inputs()

        # -- phase 3: stage-specific logic ----------------------------
        result = self.run(inputs)

        # Fill in stage_id if the subclass did not set it
        if result.stage_id == "":
            result.stage_id = stage_def.id

        # -- phase 4: register outputs --------------------------------
        if result.success and self._registry is not None:
            self._register_outputs(result)

        return result

    # -- tool checking -------------------------------------------------

    def _check_tools(self) -> list[str]:
        """Return a list of tool names that are **not** on ``$PATH``.

        Returns an empty list when every required tool is available.
        """
        missing: list[str] = []
        for tool in self.tools_required:
            if shutil.which(tool) is None:
                missing.append(tool)
        return missing

    # -- input resolution ----------------------------------------------

    def _resolve_inputs(self) -> StageInput:
        """Resolve the artifact names declared in ``stage_def.input``.

        ``stage_def.input`` is a list of artifact names (strings).
        Each is resolved through the :class:`ArtifactRegistry`, symlinked
        into ``inputs_dir``, and mapped to the matching :class:`StageInput`
        field name by convention.
        """
        inputs = StageInput()

        if self._registry is None or self._stage_def is None:
            return inputs

        # Mapping from registry names -> StageInput field names
        field_map = {
            "spec_doc": "spec_doc",
            "arch_spec": "arch_spec",
            "block_diagram": "block_diagram",
            "interface_def": "interface_def",
            "rtl_files": "rtl_dir",
            "netlist": "netlist_dir",
            "constraints": "constraints",
            "design_db": "design_db",
            "routed_netlist": "netlist_dir",
            "placed_netlist": "netlist_dir",
        }

        for artifact_name in self._stage_def.input:
            resolved = self._registry.resolve(artifact_name)
            if resolved is None:
                continue

            # Symlink into inputs_dir
            link_path = self.inputs_dir / resolved.name
            if not link_path.exists():
                try:
                    link_path.symlink_to(resolved)
                except (OSError, NotImplementedError):
                    shutil.copy2(resolved, link_path)

            # Map to StageInput field
            field_name = field_map.get(artifact_name)
            if field_name and hasattr(inputs, field_name):
                setattr(inputs, field_name, resolved)
            else:
                inputs.extra[artifact_name] = resolved

        return inputs

    # -- output registration -------------------------------------------

    def _register_outputs(self, result: StageResult) -> None:
        """Register every file in ``result.files`` with the artifact registry.

        ``result.files`` is a dict mapping ``{name: path}``.
        Artifact type is inferred from the file extension.
        Downstream consumers are discovered via :meth:`_find_consumers`.
        """
        if self._registry is None or self._stage_def is None:
            return

        for name, file_path_str in result.files.items():
            fp = Path(file_path_str)
            art_type = fp.suffix.lstrip(".") or "unknown"
            consumers = self._find_consumers(name)

            self._registry.register(
                name=name,
                stage=self._stage_def.id,
                path=str(fp),
                art_type=art_type,
                consumers=consumers,
            )

    # -- downstream-stage discovery ------------------------------------

    def _find_consumers(self, artifact_name: str) -> list[str]:
        """Return a list of downstream stage ids that declare this
        artifact in their ``input`` list."""
        consumers: list[str] = []
        try:
            downstream = self._get_downstream_stages()
            for ds in downstream:
                if artifact_name in ds.input:
                    consumers.append(ds.id)
        except Exception:
            pass
        return consumers

    def _get_downstream_stages(self) -> list[StageDef]:
        """Load the pipeline YAML and return all stages that appear after
        the current stage in declaration order."""
        try:
            config_path = self._project_dir / "pipeline.yaml"
            if not config_path.exists():
                return []

            config = PipelineConfig.load(config_path)
            my_idx: Optional[int] = None
            for i, s in enumerate(config.stages):
                if s.id == self._stage_def.id:
                    my_idx = i
                    break

            if my_idx is None:
                return []

            return config.stages[my_idx + 1 :]

        except Exception:
            return []

    # -- abstract method -----------------------------------------------

    @abstractmethod
    def run(self, inputs: StageInput) -> StageResult:
        """Execute the stage-specific logic.

        This is the **only** method concrete subclasses are required to
        implement.  It receives a fully resolved :class:`StageInput` and
        must return a :class:`StageResult`.
        """
        ...

    # -- Synopsys tool runner ------------------------------------------

    def run_synopsys_tool(
        self,
        tool: str,
        script_path: str | Path,
        timeout: int = 3600,
    ) -> ToolResult:
        """Run a Synopsys EDA tool (DC, PT, ICV, Formality, etc.).

        The tool is invoked as::

            <tool> -f <script_path>

        Output is **teed** — written to both ``stdout`` and a log file
        under ``self.logs_dir``.

        Parameters
        ----------
        tool : str
            Executable name (e.g. ``"dc_shell"``, ``"pt_shell"``).
        script_path : str | Path
            Path to the tool script (e.g. ``run.tcl``).
        timeout : int
            Maximum wall-clock time in seconds (default 3600).

        Returns
        -------
        ToolResult
        """
        script_path = Path(script_path)
        log_file = self.logs_dir / f"{tool}.log"

        cmd = [tool, "-f", str(script_path)]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            stdout_lines: list[str] = []
            with open(log_file, "w") as lf:
                for line in proc.stdout:  # type: ignore[union-attr]
                    print(line, end="", file=sys.stdout)
                    lf.write(line)
                    stdout_lines.append(line)

            proc.wait(timeout=timeout)
            stdout = "".join(stdout_lines)

            return ToolResult(
                success=proc.returncode == 0,
                log_path=log_file,
                returncode=proc.returncode,
                stdout=stdout,
            )

        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            return ToolResult(
                success=False,
                log_path=log_file,
                returncode=-1,
                stdout="",
            )

    # -- script writing ------------------------------------------------

    def write_script(self, filename: str, content: str) -> Path:
        """Write an executable script to ``self.scripts_dir``.

        Parameters
        ----------
        filename : str
            Script file name (e.g. ``"run.tcl"``, ``"synthesize.sh"``).
        content : str
            Script content.  Leading indentation common to all lines is
            stripped (via :func:`textwrap.dedent`).

        Returns
        -------
        Path
            Absolute path to the written script.
        """
        script_path = self.scripts_dir / filename
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(textwrap.dedent(content))
        script_path.chmod(0o755)
        return script_path

    # -- report writing ------------------------------------------------

    def write_report(self, template_name: str, data: dict) -> Path:
        """Generate a Markdown report with a metrics table.

        The report is written to ``self.outputs_dir / <template_name>.md``.

        Parameters
        ----------
        template_name : str
            Stem of the output filename (e.g. ``"synthesis_summary"``).
        data : dict
            Data to populate the report.  If *data* contains a ``metrics``
            key whose value is a ``dict``, a metrics table is rendered.
            All other keys are rendered as top-level sections::

                ## <Key Title>
                <value>

        Returns
        -------
        Path
            Absolute path to the generated report.
        """
        report_path = self.outputs_dir / f"{template_name}.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = [
            f"# {template_name.replace('_', ' ').title()}",
            "",
            f"**Stage:** {self._stage_def.name} (`{self._stage_def.id}`)",
            "",
        ]

        # Metrics table
        metrics = data.get("metrics", {})
        if metrics and isinstance(metrics, dict):
            lines.append("## Metrics")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            for key, value in metrics.items():
                lines.append(f"| {key} | {value} |")
            lines.append("")

        # Extra sections (everything except "metrics")
        for key, value in data.items():
            if key == "metrics":
                continue
            heading = key.replace("_", " ").title()
            lines.append(f"## {heading}")
            lines.append("")
            lines.append(str(value))
            lines.append("")

        report_path.write_text("\n".join(lines) + "\n")
        return report_path
