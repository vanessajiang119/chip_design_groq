# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Personal knowledge vault + Claude Code development workspace focused on **semiconductor chip design** (DFT, architecture, project management) and **AI hardware research**. The repo is simultaneously an Obsidian vault and a Claude Code project.

## Active Directories

| Directory | Purpose |
|---|---|
| `AI2groq/` | AI hardware research projects (Groq LPU architecture: TSP microarchitecture, dataflow streaming, compiler design, memory hierarchy). Each project follows: planning/ → research/ → working/ → result/ |
| `chip_design_agent/` | Python-based **chip design automation pipeline** — 8-stage flow from spec analysis to GDS signoff. Installed via `pip install -e chip_design_agent/`, entry point `chip-pipeline`. |
| `skills/` | Claude Code skills — 9 skills (drawio chip diagram, chip spec HLD/LLD, HTML design spec, presentation, weather, web search, browser, time) |
| `agents/config/` | Agent definitions for multi-agent workflows: chip spec generation, design research, drawio/mermaid/html diagram generation |
| `commands/` | Custom slash command docs + 3 workflow docs (development-workflows, skill-collections, agent-collections) that update README tables via parallel research agents |
| `hooks/` | Python-based lifecycle hook system — plays event sounds for all 30+ Claude Code hooks. Configurable via `hooks/config/hooks-config.json` |
| `rules/` | Claude Code rules: presentation delegation (route to per-presentation agents, never edit HTML directly) + markdown docs standards |
| `.claude/` | Local settings overrides (permissions allowlist) |
| `agent-memory/` | Weather agent memory storage |

## Architecture

**Multi-agent research workflow** (used by AI2groq projects):
`1.planning/` → `2.research/` → `3.working/` → `4.result/`
Each phase produces markdown + HTML output. Research is organized in rounds within each phase.

**README table management**: Three workflow docs (`commands/workflows/`) define parallel-agent research pipelines that update star counts, skill/agent/command counts, and workflow pipelines in the README tables. Agents report structured data; orchestrator presents diff, then executes on approval.

**Chip Design Pipeline** (`chip_design_agent/`): 8-stage automated flow from spec to GDS. Installed as `chip-pipeline` CLI. See section below.

**Hook system**: Single `hooks.py` script handles all 30+ Claude Code lifecycle events, playing platform-appropriate sound effects (afplay on macOS, paplay/aplay on Linux, winsound on Windows). Hook config supports disabling individual hooks and logging via `hooks/config/hooks-config.json`.

## Chip Design Pipeline (`chip_design_agent/`)

An 8-stage **chip design automation pipeline** written in Python. Installed as a package (`pip install -e chip_design_agent/`) with the `chip-pipeline` CLI entry point.

### Architecture

The pipeline uses a **template method pattern** — `BaseStage.execute()` in `pipeline/stages/base.py` defines the execution skeleton: `check_tools → resolve_inputs → run() → register_outputs`. Concrete stages implement only the `run()` method.

Key modules:
| Module | Purpose |
|---|---|
| `pipeline/config.py` | YAML-based `PipelineConfig` + `StageDef` dataclasses |
| `pipeline/engine.py` | `PipelineEngine` orchestrator — imports stages dynamically, manages state transitions, auto-checkpoints on success |
| `pipeline/stages/base.py` | `BaseStage` ABC with template method, Synopsys tool runner (`run_synopsys_tool`), artifact I/O, report writer |
| `pipeline/stages/s1..s8_*.py` | 8 concrete stage implementations |
| `pipeline/state.py` | JSON-backed `PipelineState` — tracks pending/running/completed/failed/skipped per stage |
| `pipeline/registry.py` | `ArtifactRegistry` — persistent JSON registry tracking inter-stage artifact dependencies with MD5 checksums |
| `pipeline/checkpoint.py` | `CheckpointManager` — save/restore/clean stage checkpoints under `.checkpoints/` |

### 8 Pipeline Stages

| Stage | ID | Tool | Purpose |
|---|---|---|---|
| 规格书分析 | s1_spec_analysis | — | Parse spec doc → arch spec + parameter list |
| 架构设计 | s2_architecture | — | Block diagram + interface definition |
| RTL 编码 | s3_rtl_design | — | RTL code generation |
| 验证 | s4_verification | vcs | Verification with Synopsys VCS |
| 综合与DFT | s5_synthesis | dc_shell | Synthesis + DFT insertion |
| 物理设计 | s6_physical_design | icc2_shell | Place & route |
| 时序收敛 | s7_timing_closure | pt_shell | STA with PrimeTime |
| GDS签核 | s8_gds_signoff | icv | DRC/LVS signoff |

### Common Commands

```bash
# Install the pipeline package
pip install -e chip_design_agent/

# Initialize a new project (creates pipeline.yaml + directory structure)
chip-pipeline init [--project-dir <dir>]

# Run full pipeline
chip-pipeline run [--from s1_spec_analysis] [--to s8_gds_signoff] [--skip stage_id]

# Run a single stage
chip-pipeline stage <stage_id> [--force]

# Check status
chip-pipeline status [--json]

# Manage checkpoints
chip-pipeline checkpoint list [--stage <id>]
chip-pipeline checkpoint restore <checkpoint_id>
chip-pipeline checkpoint clean [--keep 5]

# Generate reports
chip-pipeline report [--format markdown|json|html] [--output file.html]

# Check EDA tool availability
chip-pipeline tool check

# List registered artifacts
chip-pipeline artifacts list [--json]
```

## Skills

| Skill | Purpose |
|---|---|
| `drawio_chip_diagram` | Chip architecture diagrams via draw.io |
| `chip_spec_hld` / `chip_spec_lld` | High-level / low-level chip design spec generation |
| `html_chip_design_spec` | Structured HTML spec documents |
| `presentation/` | Presentation generation (3 sub-skills: structure, styling, vibe-to-agentic framework) |
| `weather-fetcher` / `weather-svg-creator` | Weather data + SVG visualization |
| `web_search_Tavily` | Web search via Tavily API |
| `agent-browser` | Browser-based agent |
| `time-skill` | Time-related queries |

## Key Config

- `settings.json` — Main config: permissions (broad allow + specific deny/ask), hooks wiring (all events → `hooks.py`), env vars, attribution, spinner customization
- `.claude/settings.local.json` — Local permission overrides (git, npm, python3, codex, drawio, web search)

## Response Language

Tech content uses bilingual format: Chinese descriptions + professional English terminology/acronyms.
