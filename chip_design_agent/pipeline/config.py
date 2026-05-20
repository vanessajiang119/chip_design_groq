"""Pipeline configuration: YAML-based stage definitions and project settings."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None  # fallback: manual reader below


# ---------------------------------------------------------------------------
# dataclasses
# ---------------------------------------------------------------------------

@dataclass
class StageDef:
    """Definition of a single pipeline stage."""

    id: str
    name: str
    enabled: bool = True
    input: list[str] = field(default_factory=list)
    output: list[str] = field(default_factory=list)
    tool: Optional[str] = None
    timeout: int = 3600
    tool_setup: list[str] = field(default_factory=list)


@dataclass
class PipelineConfig:
    """Top-level pipeline configuration."""

    name: str = "chip-pipeline"
    version: str = "1.0.0"
    project_name: str = "unnamed"
    tech_node: str = "28nm"
    top_module: str = "top"
    stages: list[StageDef] = field(default_factory=list)

    # ------------------------------------------------------------------
    # YAML I/O
    # ------------------------------------------------------------------
    @classmethod
    def load(cls, path: str | Path) -> "PipelineConfig":
        """Load pipeline configuration from a YAML file."""
        path = Path(path)
        raw = _read_yaml(path)

        name = raw.get("name", "chip-pipeline")
        version = raw.get("version", "1.0.0")
        project_name = raw.get("project_name", "unnamed")
        tech_node = raw.get("tech_node", "28nm")
        top_module = raw.get("top_module", "top")

        stages = []
        for s in raw.get("stages", []):
            stages.append(
                StageDef(
                    id=s.get("id", ""),
                    name=s.get("name", ""),
                    enabled=s.get("enabled", True),
                    input=s.get("input", []),
                    output=s.get("output", []),
                    tool=s.get("tool"),
                    timeout=s.get("timeout", 3600),
                    tool_setup=s.get("tool_setup", []),
                )
            )

        return cls(
            name=name,
            version=version,
            project_name=project_name,
            tech_node=tech_node,
            top_module=top_module,
            stages=stages,
        )

    def save(self, path: str | Path) -> None:
        """Save the current configuration to a YAML file."""
        path = Path(path)
        data = {
            "name": self.name,
            "version": self.version,
            "project_name": self.project_name,
            "tech_node": self.tech_node,
            "top_module": self.top_module,
            "stages": [asdict(s) for s in self.stages],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        if yaml:
            with open(path, "w") as fh:
                yaml.safe_dump(data, fh, default_flow_style=False, sort_keys=False)
        else:
            _write_json_fallback(path, data)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def stage(self, stage_id: str) -> Optional[StageDef]:
        """Look up a stage definition by id."""
        for s in self.stages:
            if s.id == stage_id:
                return s
        return None


# ---------------------------------------------------------------------------
# low-level YAML helpers (optional PyYAML, fallback JSON)
# ---------------------------------------------------------------------------

def _read_yaml(path: Path) -> dict:
    if yaml:
        with open(path) as fh:
            return yaml.safe_load(fh) or {}
    # fallback: try JSON
    with open(path) as fh:
        return json.load(fh)


def _write_json_fallback(path: Path, data: dict) -> None:
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)
