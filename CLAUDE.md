# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Personal knowledge vault + Claude Code development workspace focused on **semiconductor chip design** (DFT, architecture, project management) and **AI hardware research**. The repo is simultaneously an Obsidian vault and a Claude Code project.

## Active Directories

| Directory | Purpose |
|---|---|
| `AI2groq/` | AI hardware research projects (Groq LPU architecture: TSP microarchitecture, dataflow streaming, compiler design, memory hierarchy). Each project follows: planning/ → research/ → working/ → result/ |
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

**Hook system**: Single `hooks.py` script handles all 30+ Claude Code lifecycle events, playing platform-appropriate sound effects (afplay on macOS, paplay/aplay on Linux, winsound on Windows). Hook config supports disabling individual hooks and logging via `hooks/config/hooks-config.json`.

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
