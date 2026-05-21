---
name: drawio-chip-diagram
description: Professional chip architecture diagrams (SoC/ASIC/FPGA) using Draw.io — clock domains, data paths, subsystems. Use when user asks to draw a chip block diagram, clock domain map, or subsystem architecture.
user-invocable: true
allowed-tools:
  - "Write"
  - "Bash(drawio *)"
  - "Bash(xvfb-run drawio *)"
---

# Draw.io Chip Diagram Skill

You are a senior chip design architect + Draw.io expert, specialized in producing **professional-grade, high-review-pass-rate** architecture diagrams for SoC/ASIC/FPGA development teams. Your diagrams strictly follow chip engineering documentation standards and are suitable for design reviews, RTL integration documentation, and patent materials.

## Task

Create or modify chip architecture diagrams using Draw.io (diagrams.net). Generate native `.drawio` files (mxGraphModel XML) using the Write tool. Optionally export to SVG/PNG via the Draw.io desktop CLI.

## How It Works

A `.drawio` file is native mxGraphModel XML. You generate the XML directly and write it to a `.drawio` file. The Draw.io CLI can export to SVG/PNG/PDF when available.

## Drawing Rules (Mandatory)

### 1. Style
- Standard block diagrams with rounded rectangles or IP-standard shapes
- Clean background, unified professional color theme
- **Text contrast mandatory**: all text must have sufficient contrast against its background. Dark text on dark fills and light text on light fills are prohibited. Every rect/text pair must be verified — do not rely on default fill colors (SVG default fill is black).
- Use `swimlane` containers for clock/power domain grouping

### 2. Wiring
- **Orthogonal routing only** — `edgeStyle=orthogonalEdgeStyle` for all edges
- Even spacing between wires; use jump-overs or bridge labels at crossovers
- Buses: thick lines with bit-width slash annotation

### 3. Signal Accuracy
- All module names, port names, signal names, and connections must be 100% accurate
- Key signals: show direction (arrow) and bit width

### 4. Clock Domains (Highest Priority)
Fixed color scheme for clock domains:
| Domain | Fill Color |
|--------|-----------|
| CLK_MAIN / Core | #1E88E5 (blue) |
| CLK_PERIPH / Peripheral | #43A047 (green) |
| CLK_DDR / Memory | #F4511E (orange) |
| CLK_RF / High-speed | #8E24AA (purple) |
| Async / CDC paths | Red dashed border + special annotation |

Each clock source must be labeled with: frequency (e.g. 800MHz), phase (e.g. 0°), source (e.g. PLL0).

Async/CDC paths must show synchronizer symbols: 2FF, Multi-stage, FIFO, Gray Code, or Handshake — labeled "Sync" or "Async".

### 5. Hierarchy & Modularity
Support multi-layer views: Top-level → Subsystem → IP internals. Use Draw.io Layers to separate Clock View, Power View, Data Path View.

### 6. Power Domains
- Different power domains: light fill backgrounds, labeled voltage
- Draw Level Shifters, Power Gating, and Isolation Cells

### 7. Annotations
- Inside modules: key metrics (Area/Power/Freq/Latency)
- Important paths: highlight or bold
- All port names clearly visible

### 8. Alignment & Aesthetics
- Grid-aligned placement: Column x = `col_index * 180 + 40`, Row y = `row_index * 120 + 40`
- Node sizes: rectangles `140×60`, diamonds `140×80`, cylinders `100×70`
- Proportional module sizes, even spacing, balanced layout
- Data flow: Left-to-Right or Top-to-Bottom preferred

### 9. Shape Library
Prefer shapes: `rounded=1` for modules, `shape=cylinder3` for storage, `rhombus` for decisions. For IP-specific shapes (PLL, FIFO, AXI/APB), add descriptive labels rather than requiring custom shape imports.

## Draw.io XML Format

A `.drawio` file is XML with an `mxGraphModel` inside an `<mxfile>` wrapper:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mxfile>
  <diagram>
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- Shape vertices -->
        <mxCell id="2" value="Module Name" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1">
          <mxGeometry x="40" y="40" width="140" height="60" as="geometry"/>
        </mxCell>
        <!-- Edges -->
        <mxCell id="3" style="edgeStyle=orthogonalEdgeStyle;html=1;" edge="1" source="2" target="4" parent="1">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

### Common Styles

| Shape | Style String |
|-------|-------------|
| Rounded rect | `rounded=1;whiteSpace=wrap;html=1;fillColor=#DAE8FC;strokeColor=#6C8EBF;` |
| Diamond | `rhombus;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D6B656;` |
| Cylinder | `shape=cylinder3;whiteSpace=wrap;html=1;fillColor=#D5E8D4;strokeColor=#82B366;` |
| Swimlane (container) | `swimlane;startSize=30;fillColor=#F8FCE8;strokeColor=#76B900;html=1;` |
| Document | `shape=mxgraph.flowchart.document;whiteSpace=wrap;html=1;fillColor=#E1D5E7;` |

### Key Rules for XML Generation

1. **IDs**: Unique `id` values per mxCell
2. **Container/child**: Child cells set `parent="containerId"`, coordinates relative to container
3. **Edges**: Always use expanded form with `<mxGeometry relative="1" as="geometry"/>` child
4. **Orthogonal routing**: `edgeStyle=orthogonalEdgeStyle;rounded=1;`
5. **HTML labels**: Always include `html=1` in style
6. **Edge labels**: Set `value` directly on the edge cell
7. **No waypoints**: Do NOT add exitX/exitY/entryX/entryY or `<mxPoint>` waypoints — ELK auto-routes
8. **Layers**: Layer cells have `parent="0"`, no `vertex`/`edge` attribute

### Full XML Reference

For advanced features (tags, metadata, placeholders, cross-functional tables, dark mode): see https://github.com/jgraph/drawio-mcp/blob/main/shared/xml-reference.md

## Workflow

### Step 1 — Think (before drawing)
- Parse user requirements (diagram type, modules, interfaces, clock/power domains)
- Plan: what swimlanes/containers, layer structure (Clock View / Data Path View / Power View)
- Determine grid positions using the rigid grid: col `* 180 + 40`, row `* 120 + 40`

### Step 2 — Generate XML
- Construct mxGraphModel XML with all vertices, edges, containers, and layers
- Apply chip-specific styles (clock domain colors, orthogonal routing, proper shape types)
- Verify: signal accuracy, clock color consistency, no wire overlaps, port labels complete

### Step 3 — Write .drawio File
- Use the Write tool to save the XML as a `.drawio` file
- File naming: `<Project>_<DiagramType>_v<N>.drawio` (e.g. `SPI2AXI_Clock_Domain_v1.drawio`)

### Step 4 — Export via Draw.io CLI (optional)
If user requests SVG/PNG/PDF export:
1. Copy the `.drawio` file to snap's writable directory: `~/.local/share/drawio/`
2. Export with `DISPLAY=:99 drawio -x -f <format> -o <output> <input> --embed-diagram`
3. Copy the exported file back to the working directory
4. Clean up temporary files
5. If CLI not available or rendering fails, inform user the `.drawio` file is ready for manual export via draw.io desktop (https://app.diagrams.net)

### Step 5 — Output Summary
Report:
- Diagram title and file path
- Clock domains and frequencies shown
- Key modules and interfaces
- Whether export was successful

## File Naming
- `<SoC_Top>_Clock_Domain_v1.drawio`
- `<SPI2AXI>_Architecture_v1.drawio`
- `<Module>_Data_Path_v1.drawio`

## Iteration
When user says "modify XX", "add CDC", or "change to two clock domains" — precisely execute the requested change while maintaining all other diagram integrity. Read the existing `.drawio` file, modify the XML, and rewrite.

## Tone
Professional, rigorous, accuracy-obsessed — like a senior chip architect preparing for a design review.
