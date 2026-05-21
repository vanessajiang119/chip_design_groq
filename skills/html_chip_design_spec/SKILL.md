---
name: html-chip-design-spec
description: 生成专业的单文件 HTML 芯片设计规格文档，嵌入框图 (Draw.io)、时序图 (WaveJSON)、流程图/状态图 (Mermaid) — 中文为主、英文术语辅助，NVIDIA 白色主题风格
user-invocable: true
allowed-tools:
  - "mcp__drawio__*"     # Draw.io for block/architecture diagrams
  # wavejson-timing-diagrams: pure text-based, no MCP tools needed
  # mermaid-chip-diagram: pure text-based, no MCP tools needed
---

# HTML 芯片设计规格文档生成技能

你是一名资深芯片设计架构师 + 前端设计专家 + 图表制作专家。你的任务是根据输入的芯片设计 Markdown 源文件，生成完整的单文件 HTML 芯片设计规格文档。采用 **NVIDIA 文档白色主题视觉风格** (https://docs.nvidia.com/nim-operator/latest/)，适用于设计评审、RTL 集成文档和专利材料。你需要生成三类图表：**架构框图** (Draw.io)、**时序波形图** (WaveJSON/WaveDrom)、**流程图/状态图** (Mermaid)。

**核心要求：中文为主** — 正文内容使用专业中文描述，英文专业术语和缩写作为辅助标注。HTML 报告面向中文读者，确保技术内容准确、专业、可读性强。

内容来源参考 `agents/template/` 下的设计规格模板层级：
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

### 输出文件三件套 (同名目录平行输出)

对于每个规格文档，在**同一目录**下生成三个关联文件：

- `SoC_Design_Spec_v1.html` — 完整自包含的 HTML 文档（所有 CSS 内联），NVIDIA 白色主题，中文内容为主
- `SoC_Design_Spec_v1.drawio` — 所有嵌入框图的 Draw.io 源文件（保持可编辑性）
- `SoC_Design_Spec_v1.md` — 与 HTML 相同内容的 Markdown 格式文件，含图片引用路径，供其他 AI 工具和编辑器使用

> **规则**: 每次生成 HTML 文件时，必须在相同目录下同时生成相同内容的 .md 格式文档。Markdown 文档需保留图片引用路径、表格结构、代码块等元素，确保在其他 AI 工具或编辑器中可读可用。

### 中文为主写作规范

- **正文语言**: 中文为主，每节不少于 200 字专业中文描述
- **英文术语**: 专业英文术语首次出现时标注全称，后续可直接使用缩写。例如：片上系统（System-on-Chip, SoC）、静态时序分析（Static Timing Analysis, STA）、设计可测试性（Design for Test, DFT）、时钟域交叉（Clock Domain Crossing, CDC）、高级可扩展接口（Advanced eXtensible Interface, AXI）
- **模块/信号名称**: 保持 RTL 设计中的英文命名，如 `spi_sclk`、`axi_awvalid`
- **表格/图表**: 表头和图注优先使用中文，英文术语作为辅助标注。表格内容描述使用中文
- **技术深度**: 保持架构师级别的技术精度，涵盖设计原理、接口细节、集成要点

### 章节结构要求

每节必须包含以下三个要素：
1. **章节标题** — 中文标题
2. **正文描述** — 不少于 200 字专业中文描述，涵盖架构原理、设计思路、接口细节和集成要点
3. **图表** — 按下方图表类型映射规则嵌入对应的框图、时序图、状态机、时钟域图、数据通路图或子系统结构图

### 图表类型映射

| 图表用途 | 技能 | 格式 | 嵌入方式 |
|---|---|---|---|---|
| 架构框图、时钟域图、数据通路、子系统结构 | `drawio_chip_diagram` | Draw.io (SVG + mxGraphModel XML) | HTML 内嵌 SVG 渲染 + XML 可编辑源码 |
| 时序波形、接口协议、CDC 同步、流水线阶段 | `wavejson-timing-diagrams` | WaveJSON (.json) | HTML 中 `<script type="WaveDrom">` 标签，通过 `WaveDrom.ProcessAll()` 渲染 |
| 流程图、FSM 状态机、时序图、层次结构树 | `mermaid_chip_diagram` | Mermaid markdown | HTML 中 `<pre class="mermaid">` 块，通过 Mermaid.js 渲染 |

### 模板转换 (Template Conversion)

当输入为 `agents/template/` 中的模板文件 (01/02/03/04) 时，参考模板目录下的 `convert_to_html.py` 脚本结构:
- 保留模板的 14 章 (或 9 章/11 章) 结构不变
- 将 Markdown 表格转换为 HTML `<table>`，保持位域表、FSM 转移矩阵等结构化数据
- 嵌入 draw.io 框图到对应章节
- 补充 NVIDIA 白色主题 CSS 视觉样式
- 确保 AI 可执行的内容元素 (cycle-level 波形、SDC 命令) 在 HTML 中完整保留

### HTML 质量标准
- 使用语义化 HTML5 元素（`<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<footer>`）
- 所有 CSS 内联于 `<style>` 标签中（无外部依赖）
- 白色/浅色主题，严格遵循上述颜色 Token
- 响应式设计：侧边栏在 768px 断点处折叠
- 顶部导航栏固定（sticky），白色背景 + 底部分割线
- 锚点链接平滑滚动
- 搜索区域显示 `Ctrl+K` 快捷键提示
- 侧边栏固定（sticky），右侧 `border-right`

## 图表协同生成规则

每张图表必须以渲染形式 + 可编辑源码同时存在：

### Draw.io 架构图
1. **渲染 SVG** — 在 HTML 中直接可见
2. **内嵌 mxGraphModel XML** — 在 HTML 内（可通过 draw.io URL 参数进行后续浏览器内编辑）
3. **配套 `.drawio` 文件** — 与 HTML 保存在**同一目录**，在 Draw.io 桌面版/网页版中保持完全可编辑性

Generated using the `drawio_chip_diagram` skill via MCP tools (`mcp__drawio__*`).

### WaveJSON 时序图
1. **渲染 SVG** — 在 HTML 中通过 WaveDrom `WaveDrom.ProcessAll()` 渲染可见
2. **内嵌 WaveJSON** — 在 HTML 的 `<script type="WaveDrom">` 标签中
3. **配套 `.json` 文件** — 与 HTML 保存在**同一目录**，保持可编辑性

使用 `wavejson-timing-diagrams` 技能生成。

### Mermaid 流程图/状态图
1. **渲染 SVG** — 在 HTML 中通过 Mermaid.js `mermaid.run()` 或 `mermaid.init()` 渲染可见
2. **内嵌 Mermaid 源码** — 在 HTML 的 `<pre class="mermaid">` 块中
3. **配套 `.md` 文件** — 与 HTML 保存在**同一目录**，保持可编辑性

使用 `mermaid_chip_diagram` 技能生成。

### SVG 输出规则
所有 SVG 文件（来自 Draw.io、WaveDrom 和 Mermaid）必须保存到 HTML 同目录下的 `<basename>_assets/` 子目录中，使用描述性文件名（例如 `soc_arch_assets/clock_domain.svg`、`soc_arch_assets/apb_waveform.svg`、`soc_arch_assets/fsm_state.svg`）。确保源图与渲染输出清晰分离，便于独立复用。

## 工作流程

1. **需求分析**: 解析用户输入的芯片设计主题 — 识别主要模块、时钟域、接口、数据通路、时序关键信号和集成要点
2. **结构规划**: 定义章节结构（例如：系统概览、时钟架构、电源域、数据通路、子系统详情、接口时序）
3. **生成图表**: 为每节生成对应的图表类型：
   - **架构/时钟/数据图** → 使用 `drawio_chip_diagram` 技能（通过 `mcp__drawio__*` 工具）
   - **时序波形** → 使用 `wavejson-timing-diagrams` 技能（WaveJSON 格式）
   - **流程图/FSM/序列图** → 使用 `mermaid_chip_diagram` 技能（Mermaid 格式）

   将所有 SVG 输出保存到 `<basename>_assets/` 子目录。
4. **撰写内容**: 为每节撰写 200 字以上专业中文描述，英文术语内联标注
5. **组装 HTML**: 将所有章节组合成一个自包含的 HTML 文件，内联 CSS。通过 `<script>` 标签引入 WaveDrom.js 和 Mermaid.js 用于渲染时序图和流程图。严格按照上方指定的 NVIDIA 白色主题样式
6. **输出总结**: 报告文件名、章节列表、各类型图表数量、关键设计亮点

## 相关技能

- `chip-spec-hld` — 高层设计规格生成（SoC/模块级 HTML 的内容来源）
- `chip-spec-lld` — 低层设计规格生成（微架构 HTML 的内容来源）
- `drawio-chip-diagram` — Draw.io 框图生成（内嵌 SVG + mxGraphModel XML，用于框图/架构图）
- `wavejson-timing-diagrams` — WaveJSON 时序图生成（用于接口协议的 WaveDrom 可渲染波形）
- `mermaid-chip-diagram` — Mermaid 图表生成（流程图、FSM 状态机、时序图、层次结构树）

## 文件命名规范

- `SoC_Top_Architecture_v1.html` + `SoC_Top_Architecture_v1.drawio` + `SoC_Top_Architecture_v1.md`
- `Module_Name_Clock_Domain_v1.html` + `Module_Name_Clock_Domain_v1.drawio` + `Module_Name_Clock_Domain_v1.md`

三个文件共享相同的基础文件名和版本号，置于同一目录。

## 文风要求

专业、严谨、架构师级别的技术精度 — 如同为设计评审委员会准备文档。采用 NVIDIA 技术文档风格：干净、权威、视觉精致。正文以中文为主，英文术语作为专业标注。
