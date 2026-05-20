"""Checkpoint save / restore / clean for pipeline stages."""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any


class CheckpointManager:
    """Manages stage-level checkpoints inside ``<project_dir>/.checkpoints/``."""

    CHECKPOINT_DIR = ".checkpoints"
    META_FILE = "checkpoint.json"

    def __init__(self, project_dir: str | Path) -> None:
        self._project_dir = Path(project_dir)
        self._cp_root: Path = self._project_dir / self.CHECKPOINT_DIR

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def save(
        self,
        stage_id: str,
        result: Any,
        outputs: dict[str, str] | None = None,
        state_snapshot: dict | None = None,
    ) -> str:
        """Create a checkpoint for *stage_id* and return its unique id.

        The checkpoint directory structure::

            .checkpoints/
              <cp_id>/
                checkpoint.json   # metadata
                outputs/          # copied output files
                state.json        # pipeline state snapshot
        """
        cp_id = _new_id()
        cp_dir = self._cp_root / cp_id
        cp_dir.mkdir(parents=True, exist_ok=True)
        outputs_dir = cp_dir / "outputs"
        outputs_dir.mkdir(exist_ok=True)

        # -- copy output files -----------------------------------------
        copied = {}
        if outputs:
            for logical_name, src_path_str in outputs.items():
                src = Path(src_path_str)
                if src.exists():
                    dst = outputs_dir / logical_name
                    shutil.copy2(src, dst)
                    copied[logical_name] = str(dst)

        # -- metadata --------------------------------------------------
        meta: dict[str, Any] = {
            "id": cp_id,
            "stage_id": stage_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "result": result.to_dict() if hasattr(result, "to_dict") else result,
            "outputs": copied,
        }
        with open(cp_dir / self.META_FILE, "w") as fh:
            json.dump(meta, fh, indent=2)

        # -- optional state snapshot -----------------------------------
        if state_snapshot:
            with open(cp_dir / "state.json", "w") as fh:
                json.dump(state_snapshot, fh, indent=2)

        return cp_id

    def list_checkpoints(self, stage: str | None = None) -> list[dict]:
        """Return a list of checkpoint metadata dicts, newest first.

        If *stage* is given, only checkpoints for that stage are returned.
        """
        if not self._cp_root.exists():
            return []

        entries: list[dict] = []
        for cp_dir in sorted(self._cp_root.iterdir()):
            if not cp_dir.is_dir():
                continue
            meta_file = cp_dir / self.META_FILE
            if not meta_file.exists():
                continue
            with open(meta_file) as fh:
                meta = json.load(fh)
            if stage is None or meta.get("stage_id") == stage:
                entries.append(meta)

        # newest first
        entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return entries

    def restore(self, cp_id: str) -> dict:
        """Restore a checkpoint: return its metadata and state snapshot.

        Returns::

            {
                "metadata": {...},
                "state": {...} | None,
                "outputs": {...},
            }
        """
        cp_dir = self._cp_root / cp_id
        if not cp_dir.exists():
            raise FileNotFoundError(f"Checkpoint '{cp_id}' not found at {cp_dir}")

        with open(cp_dir / self.META_FILE) as fh:
            meta = json.load(fh)

        state = None
        state_file = cp_dir / "state.json"
        if state_file.exists():
            with open(state_file) as fh:
                state = json.load(fh)

        # copy output files back to their original locations
        outputs_dir = cp_dir / "outputs"
        restored = {}
        if outputs_dir.exists():
            for logical_name, orig_path_str in meta.get("outputs", {}).items():
                src = outputs_dir / logical_name
                if src.exists():
                    dst = Path(orig_path_str)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    restored[logical_name] = str(dst)

        return {
            "metadata": meta,
            "state": state,
            "outputs": restored,
        }

    def clean(self, keep: int = 5) -> int:
        """Keep the *keep* most recent checkpoints and remove the rest.

        Returns the number of checkpoints removed.
        """
        all_cps = self.list_checkpoints()
        if len(all_cps) <= keep:
            return 0

        remove = all_cps[keep:]
        for meta in remove:
            cp_dir = self._cp_root / meta["id"]
            if cp_dir.exists():
                shutil.rmtree(cp_dir)
        return len(remove)


def _new_id() -> str:
    """Generate a short unique checkpoint id."""
    return uuid.uuid4().hex[:12]
