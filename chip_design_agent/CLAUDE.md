# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a **Claude Code configuration and extension workspace** for **AI hardware research and chip design**. It is not a standalone software project — it contains agent definitions, skills, commands, hook automation, and rules that activate when Claude Code runs from this directory.

There are no build, test, or lint tools. The project "runs" by launching `claude` from this directory — all configurations activate automatically.

## Architecture

The entire codebase lives under `.claude/` with six subsystems:

### 1. Settings (`.claude/settings.json`)
Single entry point for Claude Code configuration. Key settings:
- Broad permissions (`allow`) for all editor/writer/read tools; `ask` for destructive commands (`rm`, `npm`, `pip`, `docker`)
- All 27 lifecycle hooks wired to `hooks.py`
- Plans directory at `./reports`
- Custom spinner verbs and tips
- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80`

### 2. Hook System (`.claude/hooks/scripts/hooks.py`)
A 481-line Python script that plays sound effects on all Claude Code lifecycle events. Key design:
- Maps events (e.g., `PreToolUse` → `pretooluse` sound folder)
- Platform detection: `afplay` (macOS), `paplay`/`aplay`/`ffplay`/`mpg123` (Linux), `winsound` (Windows)
- Special sound for `git commit` commands
- Supports agent-specific sounds via `--agent=<name>` flag
- Config-driven hook disable via `hooks-config.json` (local override at `hooks-config.local.json`, gitignored)
- Always exits 0 — never interrupts Claude Code

**Toggle hooks off**: Set `"disableAllHooks": true` in `.claude/settings.local.json` (gitignored).

### 3. Agent Definitions (`.claude/agents/`)
YAML + Markdown agent definitions for multi-agent workflows:

| Agent | Model | Purpose |
|---|---|---|
| `weather-agent` | Sonnet | Fetches Dubai weather via skill, restricted toolset |
| `time-agent` | Haiku | Displays PKT time |
| `presentation-vibe-coding` | Sonnet | Edits vibe-coding presentation, self-evolving |
| `presentation-claude-code` | Sonnet | Edits canonical Claude Code best-practice deck (49+ slides, level-badge system) |
| `presentation-claude-gemini` | Sonnet | Edits GDG Kolachi event deck (6-level journey bar) |
| `development-workflows-research-agent` | Sonnet | Researches GitHub repos (stars, counts via API), 30 max turns |

### 4. Commands & Workflows (`.claude/commands/`)
- **Slash commands**: `weather-orchestrator` (multi-step weather fetch → SVG), `time-command` (PKT time)
- **README workflow docs** (`.claude/commands/workflows/`): `development-workflows`, `agent-collections`, `skill-collections` — each defines parallel-agent research pipelines that update README tables. Pattern: Phase 0 (read state) → Phase 1 (parallel research agents) → Phase 2 (compare & report) → Phase 3 (execute on approval)

### 5. Skills (`.claude/skills/`)
Eight skills across domains:
- **Weather**: `weather-fetcher` (Open-Meteo API), `weather-svg-creator` (SVG card)
- **Time**: `time-skill` (PKT via `TZ='Asia/Karachi' date`)
- **Browser**: `agent-browser` (full browser automation CLI)
- **Presentation**: `presentation-structure`, `presentation-styling`, `vibe-to-agentic-framework`

### 6. Rules (`.claude/rules/`)
- `markdown-docs.md` — applies to `**/*.md`: keep files focused, use relative links, tables for comparisons, hierarchical headings
- `presentation.md` — applies to `presentation/**`: **never edit presentation HTML directly**; delegate to per-presentation agents (`presentation-vibe-coding`, `presentation-claude-gemini`, `presentation-claude-code`)

## Key Workflow Patterns

### Multi-Agent Research Pipeline
Used by AI2groq projects: `1.planning/` → `2.research/` → `3.working/` → `4.result/`. Each phase produces markdown + HTML output with research organized in rounds.

### Parallel Agent Dispatch
For README table updates, launch independent research agents concurrently, then aggregate results. Example: researching 11 workflow repos via 2 parallel agents.

### Presentation Delegation
All presentation edits MUST go through per-presentation agents. Never edit HTML files directly. Each presentation has unique structure (slide count, level system, audience).

## Common Tasks

| Task | How |
|---|---|
| Disable hook sounds | Set `"disableAllHooks": true` in `.claude/settings.local.json` |
| Test hook system | Run `echo '{"hook_event_name":"SessionStart"}' \| python3 .claude/hooks/scripts/hooks.py` from repo root |
| Add a new skill | Create `.claude/skills/<name>/SKILL.md` with YAML frontmatter |
| Add a new agent | Create `.claude/agents/<name>.md` with YAML frontmatter (model, tools, instructions, hooks) |
| Add a new slash command | Create `.claude/commands/<name>.md` |
| Modify presentation | Use Agent tool with the appropriate presentation agent — never edit HTML directly |

## Response Language

Tech content uses bilingual format: Chinese descriptions + professional English terminology/acronyms.
