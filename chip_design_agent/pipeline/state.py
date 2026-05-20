"""Pipeline running state management (JSON-based)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# allowed status values
# ---------------------------------------------------------------------------
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

_VALID_STATUSES = frozenset(
    {STATUS_PENDING, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED, STATUS_SKIPPED}
)


# ---------------------------------------------------------------------------
# single stage state
# ---------------------------------------------------------------------------
@dataclass
class StageState:
    """Runtime state of one pipeline stage."""

    stage_id: str
    status: str = STATUS_PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None

    # -- serialization ------------------------------------------------
    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> "StageState":
        return cls(
            stage_id=data.get("stage_id", ""),
            status=data.get("status", STATUS_PENDING),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            exit_code=data.get("exit_code"),
            error=data.get("error"),
        )


# ---------------------------------------------------------------------------
# timestamp helper
# ---------------------------------------------------------------------------
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# full pipeline state
# ---------------------------------------------------------------------------
class PipelineState:
    """Manages a JSON state file at ``project_dir / pipeline.state.json``."""

    STATE_FILE = "pipeline.state.json"

    def __init__(self, project_dir: str | Path) -> None:
        self._project_dir = Path(project_dir)
        self._state_file: Path = self._project_dir / self.STATE_FILE
        self._stages: dict[str, StageState] = {}
        self._load()

    # -- public helpers ------------------------------------------------
    def get_stage(self, stage_id: str) -> Optional[StageState]:
        return self._stages.get(stage_id)

    def mark_running(self, stage_id: str) -> None:
        st = self._stages.setdefault(
            stage_id, StageState(stage_id=stage_id)
        )
        st.status = STATUS_RUNNING
        st.started_at = _now()
        st.error = None
        self.save()

    def mark_completed(self, stage_id: str, exit_code: int = 0) -> None:
        st = self._stages.setdefault(
            stage_id, StageState(stage_id=stage_id)
        )
        st.status = STATUS_COMPLETED
        st.completed_at = _now()
        st.exit_code = exit_code
        self.save()

    def mark_failed(self, stage_id: str, error: str, exit_code: int = 1) -> None:
        st = self._stages.setdefault(
            stage_id, StageState(stage_id=stage_id)
        )
        st.status = STATUS_FAILED
        st.completed_at = _now()
        st.exit_code = exit_code
        st.error = error
        self.save()

    def mark_skipped(self, stage_id: str) -> None:
        st = self._stages.setdefault(
            stage_id, StageState(stage_id=stage_id)
        )
        st.status = STATUS_SKIPPED
        st.completed_at = _now()
        self.save()

    def is_completed(self, stage_id: str) -> bool:
        st = self._stages.get(stage_id)
        return st is not None and st.status == STATUS_COMPLETED

    def is_failed(self, stage_id: str) -> bool:
        st = self._stages.get(stage_id)
        return st is not None and st.status == STATUS_FAILED

    # -- serialisation ------------------------------------------------
    def save(self) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "stages": {sid: st.to_dict() for sid, st in self._stages.items()},
        }
        with open(self._state_file, "w") as fh:
            json.dump(data, fh, indent=2)

    def _load(self) -> None:
        if not self._state_file.exists():
            self._stages = {}
            return
        with open(self._state_file) as fh:
            data = json.load(fh)
        self._stages = {
            sid: StageState.from_dict(sd)
            for sid, sd in data.get("stages", {}).items()
        }

    # -- helper -------------------------------------------------------
    def _overall_status(self) -> str:
        """Return the overall pipeline status based on all stage states."""
        if not self._stages:
            return STATUS_PENDING
        statuses = {st.status for st in self._stages.values()}
        if STATUS_FAILED in statuses:
            return STATUS_FAILED
        if STATUS_RUNNING in statuses:
            return STATUS_RUNNING
        if all(s == STATUS_COMPLETED for s in statuses):
            return STATUS_COMPLETED
        if all(s in (STATUS_COMPLETED, STATUS_SKIPPED) for s in statuses):
            return STATUS_COMPLETED
        if STATUS_PENDING in statuses:
            return STATUS_PENDING
        return STATUS_PENDING
