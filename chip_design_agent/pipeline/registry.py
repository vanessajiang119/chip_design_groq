"""Artifact registry — tracks stage outputs and inter-stage dependencies."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional, Any


# ---------------------------------------------------------------------------
# artifact record
# ---------------------------------------------------------------------------
class ArtifactRecord:
    """Single artifact entry in the registry."""

    def __init__(
        self,
        name: str,
        stage: str,
        path: str,
        art_type: str,
        md5: str,
        consumers: list[str] | None = None,
    ) -> None:
        self.name = name
        self.stage = stage
        self.path = path
        self.art_type = art_type
        self.md5 = md5
        self.consumers = consumers or []

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "stage": self.stage,
            "path": self.path,
            "art_type": self.art_type,
            "md5": self.md5,
            "consumers": self.consumers,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ArtifactRecord":
        return cls(
            name=data["name"],
            stage=data["stage"],
            path=data["path"],
            art_type=data["art_type"],
            md5=data["md5"],
            consumers=data.get("consumers", []),
        )


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------
class ArtifactRegistry:
    """Persistent artifact registry backed by ``project_dir / artifacts/registry.json``."""

    REGISTRY_FILE = "registry.json"

    def __init__(self, project_dir: str | Path) -> None:
        self._project_dir = Path(project_dir)
        self._registry_dir: Path = self._project_dir / "artifacts"
        self._registry_file: Path = self._registry_dir / self.REGISTRY_FILE
        self._artifacts: dict[str, ArtifactRecord] = {}
        self._load()

    # -- public API ----------------------------------------------------
    def register(
        self,
        name: str,
        stage: str,
        path: str | Path,
        art_type: str,
        consumers: list[str] | None = None,
    ) -> ArtifactRecord:
        """Register (or update) an artifact, computing its md5 hash."""
        p = Path(path)

        md5_hash = self._compute_md5(p) if p.is_file() else ""

        record = ArtifactRecord(
            name=name,
            stage=stage,
            path=str(p),
            art_type=art_type,
            md5=md5_hash,
            consumers=consumers or [],
        )
        self._artifacts[name] = record
        self._save()
        return record

    def resolve(self, name: str) -> Optional[Path]:
        """Resolve an artifact name to its filesystem ``Path`` (or ``None``)."""
        record = self._artifacts.get(name)
        if record is None:
            return None
        p = Path(record.path)
        return p if p.exists() else None

    def get_stage_outputs(self, stage: str) -> dict[str, Any]:
        """Return a dict of artifact names → paths for a given stage."""
        outputs = {}
        for name, rec in self._artifacts.items():
            if rec.stage == stage:
                outputs[name] = rec.path
        return outputs

    def list_artifacts(self) -> list[dict]:
        """Return a list of all registered artifact records as plain dicts."""
        return [rec.to_dict() for rec in self._artifacts.values()]

    # -- persistence ---------------------------------------------------
    def _save(self) -> None:
        self._registry_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "artifacts": {name: rec.to_dict() for name, rec in self._artifacts.items()}
        }
        with open(self._registry_file, "w") as fh:
            json.dump(data, fh, indent=2)

    def _load(self) -> None:
        if not self._registry_file.exists():
            self._artifacts = {}
            return
        with open(self._registry_file) as fh:
            data = json.load(fh)
        self._artifacts = {
            name: ArtifactRecord.from_dict(rec)
            for name, rec in data.get("artifacts", {}).items()
        }

    # -- helpers -------------------------------------------------------
    @staticmethod
    def _compute_md5(path: Path) -> str:
        """Compute the MD5 checksum of a file."""
        h = hashlib.md5()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
