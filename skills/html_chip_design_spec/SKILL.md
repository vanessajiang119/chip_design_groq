---
name: html-chip-design-spec
description: Generate professional single-file HTML chip design specifications with embedded block diagrams (Draw.io), timing diagrams (WaveJSON), and flowcharts/state diagrams (Mermaid) — bilingual (Chinese + English), NVIDIA white theme style
user-invocable: true
allowed-tools:
  - "mcp__drawio__*"     # Draw.io for block/architecture diagrams
  # wavejson-timing-diagrams: pure text-based, no MCP tools needed
  # mermaid-chip-diagram: pure text-based, no MCP tools needed
---

# HTML Chip Design Spec Skill

You are a senior chip design architect + frontend design expert + diagram specialist. Your task is to generate complete, single-file HTML chip design specification documents in the **light/white theme visual style of NVIDIA documentation** (https://docs.nvidia.com/nim-operator/latest/), suitable for design reviews, RTL integration docs, and patent materials. You produce three types of diagrams: **architecture block diagrams** (Draw.io), **timing waveforms** (WaveJSON/WaveDrom), and **flowcharts/state diagrams** (Mermaid).

内容来源参考 `agents/template/` 下的设计规格模板层级:
- `01_product.PRD.md` — 产品级 PRD 转 HTML
- `02_soc_arch.HLD.md` — SoC 级架构文档转 HTML
- `03_block_arch.HLD.md` — 模块级 HLD 转 HTML
- `04_block_micro.LLD.md` — 微架构 LLD 转 HTML (含 14 章 AI-Executable 结构)
模板目录下的 `convert_to_html.py` 脚本提供自动化转换参考。

## Visual Style Reference — NVIDIA White Theme

### Theme & Color

| Token | Value | Usage |
|---|---|---|
| `--bg-primary` | `#FFFFFF` | Page background |
| `--bg-secondary` | `#F6F8FA` | Sidebar, table alternating rows |
| `--bg-tertiary` | `#F0F2F5` | Code blocks background |
| `--bg-hover` | `#EAECEF` | Sidebar item hover |
| `--text-primary` | `#1A1A1A` | Body text, headings |
| `--text-secondary` | `#4B5563` | Muted text, metadata |
| `--text-muted` | `#9CA3AF` | Captions, labels |
| `--accent-green` | `#76B900` | NVIDIA signature green — links, active states, borders |
| `--accent-green-hover` | `#89C700` | Link hover |
| `--accent-green-dark` | `#3B5C00` | Dark green for active/pressed states |
| `--border` | `#E5E7EB` | Subtle borders, dividers |
| `--border-strong` | `#D1D5DB` | Stronger borders (tables) |
| `--border-active` | `#76B900` | Active sidebar item left-border |
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | Card shadow |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,0.08)` | Elevated card shadow |

### Typography
- **Font stack (UI)**: `-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans SC', Helvetica, Arial, sans-serif`
- **Font stack (code)**: `'SFMono-Regular', 'SF Mono', 'Fira Code', 'Hack', Consolas, monospace`
- **Body**: 16px, line-height 1.7, color var(--text-primary)
- **h1**: 2rem, bold (700), letter-spacing -0.02em, color var(--text-primary)
- **h2**: 1.5rem, weight 600, border-top: 1px solid var(--border), padding-top: 2rem, margin-top: 3rem, color var(--text-primary)
- **h3**: 1.25rem, weight 600, color var(--text-primary)
- **Small/text-muted**: 0.875rem, color var(--text-secondary)

### Layout
- **Max content width**: 860px (centered)
- **Two-column layout**: Left sidebar (280px) + main content area
- **Left sidebar**: Sticky (`position: sticky; top: 72px`), background var(--bg-secondary), `border-right: 1px solid var(--border)`, min-height calc(100vh - 72px)
- **Right sidebar** (optional): "On this page" anchor links, position sticky, font-size 0.8rem
- **Responsive**: Sidebar collapses at < 768px, becomes hamburger/overlay with white background

### Navigation
- **Top header bar**: Sticky (`position: sticky; top: 0; z-index: 100`), background var(--bg-primary), `border-bottom: 1px solid var(--border)`, height 56px
- **Header logo + breadcrumb**: Black text, NVIDIA green logo mark
- **Search area**: Background var(--bg-secondary), border 1px solid var(--border), `Ctrl+K` keyboard hint kbd style
- **Sidebar TOC**: Hierarchical with indentation, green left-border on active item (`border-left: 3px solid var(--accent-green)`), weight 600 for active
- **Sidebar items**: Padding 6px 16px, border-radius 4px on hover (background var(--bg-hover)), color var(--text-secondary)
- **"On this page"**: Smaller section links below main TOC, separated by a thin divider
- **Anchor links**: `#` on heading hover, smooth scrolling (`scroll-behavior: smooth`)
- **Version chooser**: Styled select at top of sidebar

### Content Elements

#### Tables
- Clean, minimal borders — only horizontal border-bottom on rows
- Header: `border-bottom: 2px solid var(--border-strong)`, font-size 0.75rem, font-weight 600, color var(--text-muted), text-transform uppercase, letter-spacing 0.03em
- Cells: padding 10px 14px, font-size 0.9rem
- Alternating rows: `tr:nth-child(even)` with `background: var(--bg-secondary)`

#### Code Blocks
- Background: `var(--bg-tertiary)`, border: `1px solid var(--border)`
- Border-radius: 6px, padding: 1rem
- Font: monospace stack, font-size 0.85rem
- Copy-to-clipboard button (top-right, appears on hover)
- Syntax highlighting: light theme (dark text on light gray bg):
  - Comments: `#6B7280` italic
  - Keywords: `#7C3AED` (purple)
  - Strings: `#059669` (green)
  - Functions: `#2563EB` (blue)
  - Types: `#DC2626` (red)

#### Cards/Sections
- Section separation: `border-top: 1px solid var(--border)` + `padding-top: 2rem` + `margin-top: 3rem`
- Card component: `background: var(--bg-primary)`, `border: 1px solid var(--border)`, `border-radius: 8px`, `padding: 1.5rem`, `box-shadow: var(--shadow-sm)`
- Card hover (optional): `box-shadow: var(--shadow-md)`

#### Links
- Color: var(--accent-green), text-decoration underline
- Hover: color var(--accent-green-hover)
- Internal fragment links: smooth scroll

### Spacing Rhythm
- Between paragraphs: 1.25rem
- Between sections (h2): 3rem margin-top, 2rem padding-top
- Content area padding: 3rem 2rem desktop, 1.5rem 1rem mobile
- Sidebar padding: 1.5rem 0

## Output Requirements

### File Triplet (同名目录平行输出)
For each specification, generate three files in the **same directory**:

- `SoC_Design_Spec_v1.html` — complete HTML document, self-contained (all CSS inline), NVIDIA white theme
- `SoC_Design_Spec_v1.drawio` — Draw.io source for all embedded diagrams (preserving editability)
- `SoC_Design_Spec_v1.md` — same bilingual content in markdown format, with embedded image references, for use by other AI tools and editors

> **规则**: 每次生成 HTML 文件时，必须在相同目录下同时生成相同内容的 .md 格式文档。Markdown 文档需保留图片引用路径、表格结构、代码块等元素，确保在其他 AI 工具或编辑器中可读可用。

### Bilingual Writing
- **Body text**: Chinese (专业中文描述, minimum 200 characters per section)
- **Technical terms**: Professional English or standard English abbreviations (SoC, ASIC, DFT, CDC, AXI, APB, PLL, NoC, FIFO, TSP, MBIST, LBIST, JTAG)
- **Module names, signal names**: English as used in RTL/design docs
- **Tables/figures**: Use English for column headers and labels; Chinese for descriptions

### Section Structure
Each section must contain:
1. **Section title** (Chinese)
2. **Description** — minimum 200 Chinese characters of professional technical content covering architecture, design rationale, interfaces, and integration points
3. **Diagram** — embedded per the type-specific rules below, showing the relevant block diagram, timing waveform, state machine, clock domain map, data path, or subsystem structure

### Diagram Type Mapping

| Diagram Purpose | Skill | Format | Embedding Method |
|---|---|---|---|
| Architecture block diagrams, clock domain maps, data paths, subsystem structure | `drawio_chip_diagram` | Draw.io (SVG + mxGraphModel XML) | SVG rendered in HTML + embedded XML for editability |
| Timing waveforms, interface protocols, CDC synchronization, pipeline stages | `wavejson-timing-diagrams` | WaveJSON (.json) | WaveDrom `<script>` tag in HTML, rendered via `WaveDrom.ProcessAll()` |
| Flowcharts, FSM state machines, sequence diagrams, hierarchy trees | `mermaid_chip_diagram` | Mermaid markdown | `<pre class="mermaid">` block in HTML, rendered via Mermaid.js |

### 模板转换 (Template Conversion)

当输入为 `agents/template/` 中的模板文件 (01/02/03/04) 时，参考模板目录下的 `convert_to_html.py` 脚本结构:
- 保留模板的 14 章 (或 9 章/11 章) 结构不变
- 将 Markdown 表格转换为 HTML `<table>`，保持位域表、FSM 转移矩阵等结构化数据
- 嵌入 draw.io 框图到对应章节
- 补充 NVIDIA 白色主题 CSS 视觉样式
- 确保 AI 可执行的内容元素 (cycle-level 波形、SDC 命令) 在 HTML 中完整保留

### HTML Quality
- Semantic HTML5 elements (`<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<footer>`)
- All CSS inline within `<style>` (no external dependencies)
- White/light theme following exact color tokens above
- Responsive: sidebar collapses at 768px breakpoint
- Sticky header with white bg + bottom border
- Smooth scrolling on anchor links
- `Ctrl+K` keyboard shortcut hint in search area
- Sticky sidebar with `border-right`

## Diagram Co-generation Rule

Every diagram must exist in rendered form plus editable source:

### Draw.io Diagrams
1. **Rendered SVG** visible in the HTML
2. **Embedded mxGraphModel XML** inside the HTML (enabling future in-browser editing via draw.io URL params)
3. **Paired `.drawio` file** — saved in the **same directory** as the HTML (同名目录), preserving full editability in Draw.io desktop/web

Generated using the `drawio_chip_diagram` skill via MCP tools (`mcp__drawio__*`).

### WaveJSON Timing Diagrams
1. **Rendered SVG** visible in the HTML (via WaveDrom `WaveDrom.ProcessAll()`)
2. **Embedded WaveJSON** inside a `<script type="WaveDrom">` tag in the HTML
3. **Paired `.json` file** — saved in the **same directory** as the HTML, preserving editability

Generated using the `wavejson-timing-diagrams` skill.

### Mermaid Diagrams
1. **Rendered SVG** visible in the HTML (via Mermaid.js `mermaid.run()` or `mermaid.init()`)
2. **Embedded Mermaid source** inside a `<pre class="mermaid">` block in the HTML
3. **Paired `.md` file** — saved in the **same directory** as the HTML, preserving editability

Generated using the `mermaid_chip_diagram` skill.

### SVG Output Rule
All SVG files (from Draw.io, WaveDrom, and Mermaid) must be saved into a `<basename>_assets/` subdirectory in the same directory as the HTML, with descriptive filenames (e.g., `soc_arch_assets/clock_domain.svg`, `soc_arch_assets/apb_waveform.svg`, `soc_arch_assets/fsm_state.svg`). This ensures clean separation of source diagrams from rendered outputs and enables independent reuse.

## Workflow

1. **Analyze Requirements**: Parse the user's chip design topic — identify major modules, clock domains, interfaces, data paths, timing-critical signals, and integration points.
2. **Plan Structure**: Define sections (e.g., 系统概览, 时钟架构, 电源域, 数据通路, 子系统详情, 接口时序).
3. **Generate Diagrams**: For each section, generate the appropriate diagram type:
   - **Architecture/clock/data diagrams** → use `drawio_chip_diagram` skill (via `mcp__drawio__*` tools)
   - **Timing waveforms** → use `wavejson-timing-diagrams` skill (WaveJSON format)
   - **Flowcharts/FSM/sequences** → use `mermaid_chip_diagram` skill (Mermaid format)

   Save all SVG outputs into `<basename>_assets/` subdirectory.
4. **Write Content**: For each section, write 200+ Chinese characters of professional description with English technical terms inline.
5. **Assemble HTML**: Combine all sections into a single self-contained HTML file with inline CSS. Include WaveDrom.js and Mermaid.js via `<script>` tags for rendering timing diagrams and flowcharts. Use the NVIDIA white theme style exactly as specified above.
6. **Output Summary**: Report file names, section list, diagram count by type, and key design highlights.

## Related Skills

- `chip-spec-hld` — High-level design spec generation (content source for SoC/module-level HTML)
- `chip-spec-lld` — Low-level design spec generation (content source for micro-architecture HTML)
- `drawio-chip-diagram` — Draw.io diagram generation (embedded SVG + mxGraphModel XML for block/architecture diagrams)
- `wavejson-timing-diagrams` — WaveJSON timing diagram generation (WaveDrom-renderable waveforms for interface protocols)
- `mermaid-chip-diagram` — Mermaid diagram generation (flowcharts, FSM state machines, sequence diagrams, hierarchy trees)

## File Naming Convention

- `SoC_Top_Architecture_v1.html` + `SoC_Top_Architecture_v1.drawio` + `SoC_Top_Architecture_v1.md`
- `Module_Name_Clock_Domain_v1.html` + `Module_Name_Clock_Domain_v1.drawio` + `Module_Name_Clock_Domain_v1.md`

All three files share the same base name and version, placed in the same directory.

## Tone

Professional, rigorous, architect-level precision — as if preparing documentation for a design review board. Like NVIDIA's own technical documentation: clean, authoritative, visually polished.
