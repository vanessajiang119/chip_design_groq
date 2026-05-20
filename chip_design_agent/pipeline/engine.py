"""Pipeline Engine — orchestrates the 8-stage chip design flow."""

from __future__ import annotations

import importlib
import importlib.util
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Generator, Optional

from pipeline.config import PipelineConfig, StageDef
from pipeline.state import PipelineState
from pipeline.registry import ArtifactRegistry
from pipeline.checkpoint import CheckpointManager


# ===================================================================
# StageResult
# ===================================================================
@dataclass
class StageResult:
    """The result returned after executing a pipeline stage."""

    stage_id: str
    success: bool
    summary: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    files: dict[str, str] = field(default_factory=dict)

    # -- factory methods ----------------------------------------------
    @classmethod
    def ok(
        cls,
        stage_id: str = "",
        summary: str = "",
        metrics: dict[str, Any] | None = None,
        files: dict[str, str] | None = None,
    ) -> "StageResult":
        return cls(
            stage_id=stage_id,
            success=True,
            summary=summary,
            metrics=metrics or {},
            files=files or {},
        )

    @classmethod
    def failed(
        cls,
        stage_id: str = "",
        summary: str = "",
        metrics: dict[str, Any] | None = None,
        files: dict[str, str] | None = None,
    ) -> "StageResult":
        return cls(
            stage_id=stage_id,
            success=False,
            summary=summary,
            metrics=metrics or {},
            files=files or {},
        )

    # -- serialisation ------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "stage_id": self.stage_id,
            "success": self.success,
            "summary": self.summary,
            "metrics": self.metrics,
            "files": {k: str(v) for k, v in self.files.items()},
        }


# ===================================================================
# PipelineEngine
# ===================================================================
class PipelineEngine:
    """Core pipeline engine.

    Parameters
    ----------
    config_path : str | Path
        Path to the YAML pipeline configuration file.
    project_dir : str | Path
        Root directory of the project (state, registry, checkpoints are
        stored here).
    """

    def __init__(self, config_path: str | Path, project_dir: str | Path) -> None:
        self._config_path = Path(config_path)
        self._project_dir = Path(project_dir)
        self._config: Optional[PipelineConfig] = None
        self._state: Optional[PipelineState] = None
        self._registry: Optional[ArtifactRegistry] = None
        self._checkpointer: Optional[CheckpointManager] = None

    # -- properties ---------------------------------------------------
    @property
    def config(self) -> PipelineConfig:
        if self._config is None:
            self._config = PipelineConfig.load(self._config_path)
        return self._config

    @property
    def project_dir(self) -> Path:
        return self._project_dir

    @property
    def state(self) -> PipelineState:
        if self._state is None:
            self._state = PipelineState(self._project_dir)
        return self._state

    @property
    def registry(self) -> ArtifactRegistry:
        if self._registry is None:
            self._registry = ArtifactRegistry(self._project_dir)
        return self._registry

    @property
    def checkpointer(self) -> CheckpointManager:
        if self._checkpointer is None:
            self._checkpointer = CheckpointManager(self._project_dir)
        return self._checkpointer

    # -- public API ---------------------------------------------------
    def run(
        self,
        from_stage: str | None = None,
        to_stage: str | None = None,
        skip: list[str] | None = None,
        dry_run: bool = False,
    ) -> Generator[StageResult, None, None]:
        """Run the pipeline (or a subset of stages).

        Parameters
        ----------
        from_stage : str, optional
            Stage id to start from.
        to_stage : str, optional
            Stage id to stop at (inclusive).
        skip : list[str], optional
            Stage ids to skip.
        dry_run : bool
            If True, print what would be executed without actually running.

        Yields
        ------
        StageResult
            Result for each executed stage.
        """
        skip = skip or []
        started = from_stage is None
        all_stages = self.config.stages

        for stage_def in all_stages:
            if not stage_def.enabled:
                continue

            # -- range filtering ---------------------------------------
            if from_stage and stage_def.id == from_stage:
                started = True
            if not started:
                continue
            if to_stage and stage_def.id == to_stage:
                yield self._execute_stage(stage_def, dry_run=dry_run)
                break

            # -- skip / already-completed ------------------------------
            if stage_def.id in skip:
                self.state.mark_skipped(stage_def.id)
                yield StageResult(
                    stage_id=stage_def.id,
                    success=True,
                    summary=f"Skipped ({stage_def.id})",
                )
                continue

            if self.state.is_completed(stage_def.id):
                yield StageResult(
                    stage_id=stage_def.id,
                    success=True,
                    summary=f"Already completed ({stage_def.id})",
                )
                continue

            yield self._execute_stage(stage_def, dry_run=dry_run)

    def run_stage(self, stage_id: str, force: bool = False) -> StageResult:
        """Run a single stage by its id.

        Parameters
        ----------
        stage_id : str
            The stage to run.
        force : bool
            If True, re-run even if the stage is already completed.

        Returns
        -------
        StageResult
        """
        stage_def = self.config.stage(stage_id)
        if stage_def is None:
            return StageResult.failed(
                stage_id=stage_id,
                summary=f"Unknown stage: {stage_id}",
            )

        if not force and self.state.is_completed(stage_id):
            return StageResult(
                stage_id=stage_id,
                success=True,
                summary=f"Already completed ({stage_id})",
            )

        return self._execute_stage(stage_def)

    # -- internal -----------------------------------------------------
    def _execute_stage(self, stage_def: StageDef, dry_run: bool = False) -> StageResult:
        """Import and execute a stage module.

        The stage module is expected at ``pipeline.stages.{stage_def.id}``
        and must expose a ``Stage`` class with an ``execute(engine, stage_def)``
        method.
        """
        if dry_run:
            print(f"[DRY-RUN] Would execute stage: {stage_def.id} ({stage_def.name})")
            return StageResult.ok(stage_def.id, summary=f"Dry-run ({stage_def.id})")

        self.state.mark_running(stage_def.id)
        start = time.time()

        try:
            mod = importlib.import_module(f"pipeline.stages.{stage_def.id}")
            stage_cls = getattr(mod, "Stage", None)
            if stage_cls is None:
                raise AttributeError(
                    f"Module pipeline.stages.{stage_def.id} has no 'Stage' class"
                )

            instance = stage_cls()
            result: StageResult = instance.execute(self, stage_def)

            elapsed = time.time() - start
            result.metrics["elapsed_seconds"] = round(elapsed, 2)

            if result.success:
                self.state.mark_completed(stage_def.id)
            else:
                self.state.mark_failed(stage_def.id, error=result.summary)

            # checkpoint automatically on success
            if result.success:
                outputs = self.registry.get_stage_outputs(stage_def.id)
                self.checkpointer.save(
                    stage_id=stage_def.id,
                    result=result,
                    outputs=outputs,
                )

            return result

        except Exception as exc:
            elapsed = time.time() - start
            self.state.mark_failed(stage_def.id, error=str(exc))
            return StageResult.failed(
                stage_id=stage_def.id,
                summary=str(exc),
                metrics={"elapsed_seconds": round(elapsed, 2)},
            )
