#!/usr/bin/env python3
"""Convert template markdown files to NVIDIA white theme HTML."""

import markdown
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

MD_FILES = [
    "01_product.PRD.md",
    "02_soc_arch.HLD.md",
    "03_block_arch.HLD.md",
    "04_block_micro.LLD.md",
    "doc_userguide.md",
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root {{
    --bg-primary: #FFFFFF;
    --bg-secondary: #F6F8FA;
    --bg-tertiary: #F0F2F5;
    --bg-hover: #EAECEF;
    --text-primary: #1A1A1A;
    --text-secondary: #4B5563;
    --text-muted: #9CA3AF;
    --accent-green: #76B900;
    --accent-green-hover: #89C700;
    --accent-green-dark: #3B5C00;
    --border: #E5E7EB;
    --border-strong: #D1D5DB;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans SC', Helvetica, Arial, sans-serif;
    font-size: 16px;
    line-height: 1.7;
    color: var(--text-primary);
    background: var(--bg-primary);
  }}

  /* Header */
  header {{
    position: sticky; top: 0; z-index: 100;
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border);
    height: 56px;
    display: flex; align-items: center; padding: 0 24px;
  }}
  header .logo {{ display: flex; align-items: center; gap: 8px; }}
  header .logo-mark {{
    width: 24px; height: 24px; background: var(--accent-green); border-radius: 4px;
    display: inline-flex; align-items: center; justify-content: center;
    color: white; font-weight: bold; font-size: 14px;
  }}
  header .logo-text {{ font-weight: 600; font-size: 14px; color: var(--text-primary); }}
  header .breadcrumb {{ margin-left: 16px; font-size: 13px; color: var(--text-secondary); }}
  header .breadcrumb span {{ color: var(--text-muted); margin: 0 4px; }}

  /* Layout */
  .layout {{ display: flex; max-width: 1200px; margin: 0 auto; }}

  /* Sidebar */
  nav.sidebar {{
    width: 280px; min-width: 280px;
    position: sticky; top: 56px;
    background: var(--bg-secondary);
    border-right: 1px solid var(--border);
    height: calc(100vh - 56px);
    overflow-y: auto;
    padding: 1.5rem 0;
  }}
  nav.sidebar .sidebar-section {{
    padding: 0 16px; margin-bottom: 1rem;
  }}
  nav.sidebar .sidebar-label {{
    font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: 8px;
  }}
  nav.sidebar a {{
    display: block; padding: 6px 16px; border-radius: 4px;
    color: var(--text-secondary); text-decoration: none; font-size: 0.875rem;
    border-left: 3px solid transparent; transition: all 0.15s;
  }}
  nav.sidebar a:hover {{ background: var(--bg-hover); color: var(--text-primary); }}
  nav.sidebar a.active {{
    border-left-color: var(--accent-green); color: var(--text-primary); font-weight: 600;
  }}
  nav.sidebar a.h2 {{ padding-left: 32px; font-size: 0.8rem; }}
  nav.sidebar a.h3 {{ padding-left: 48px; font-size: 0.78rem; }}
  nav.sidebar .divider {{ border-top: 1px solid var(--border); margin: 1rem 16px; }}

  /* Main content */
  main {{
    flex: 1; min-width: 0;
    padding: 2rem 3rem;
    max-width: 860px;
  }}

  /* Typography */
  h1 {{ font-size: 2rem; font-weight: 700; letter-spacing: -0.02em; color: var(--text-primary); margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--border); }}
  h2 {{ font-size: 1.5rem; font-weight: 600; color: var(--text-primary); border-top: 1px solid var(--border); padding-top: 2rem; margin-top: 3rem; margin-bottom: 1rem; }}
  h3 {{ font-size: 1.25rem; font-weight: 600; color: var(--text-primary); margin-top: 2rem; margin-bottom: 0.75rem; }}
  h4 {{ font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin-top: 1.5rem; margin-bottom: 0.5rem; }}
  p {{ margin-bottom: 1.25rem; color: var(--text-primary); }}
  a {{ color: var(--accent-green); text-decoration: underline; }}
  a:hover {{ color: var(--accent-green-hover); }}
  strong {{ font-weight: 600; }}
  blockquote {{
    border-left: 4px solid var(--accent-green); padding: 0.75rem 1rem; margin: 1.25rem 0;
    background: var(--bg-secondary); border-radius: 4px; color: var(--text-secondary);
  }}
  blockquote p {{ margin-bottom: 0; color: var(--text-secondary); }}

  /* Tables */
  table {{
    width: 100%; border-collapse: collapse; margin: 1.25rem 0; font-size: 0.9rem;
  }}
  thead th {{
    border-bottom: 2px solid var(--border-strong);
    padding: 10px 14px; font-size: 0.75rem; font-weight: 600;
    color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.03em;
    text-align: left;
  }}
  tbody td {{
    padding: 10px 14px; border-bottom: 1px solid var(--border);
    vertical-align: top;
  }}
  tbody tr:nth-child(even) {{ background: var(--bg-secondary); }}
  table code {{ font-size: 0.82rem; }}

  /* Code */
  code {{
    font-family: 'SFMono-Regular', 'SF Mono', 'Fira Code', 'Hack', Consolas, monospace;
    font-size: 0.85rem; background: var(--bg-tertiary); padding: 2px 6px; border-radius: 4px;
  }}
  pre {{
    background: var(--bg-tertiary); border: 1px solid var(--border); border-radius: 6px;
    padding: 1rem; overflow-x: auto; margin: 1.25rem 0; position: relative;
  }}
  pre code {{ background: none; padding: 0; font-size: 0.85rem; }}

  /* Lists */
  ul, ol {{ margin: 1rem 0; padding-left: 2rem; }}
  li {{ margin-bottom: 0.5rem; }}
  ul ul, ol ul, ul ol, ol ol {{ margin: 0.25rem 0; }}

  /* Horizontal rule */
  hr {{ border: none; border-top: 1px solid var(--border); margin: 2rem 0; }}

  /* Responsive */
  @media (max-width: 768px) {{
    nav.sidebar {{ display: none; }}
    main {{ padding: 1.5rem 1rem; }}
  }}

  /* Print */
  @media print {{
    header, nav.sidebar {{ display: none; }}
    body {{ font-size: 12px; }}
    main {{ max-width: 100%; padding: 0; }}
    h2 {{ border-top: none; padding-top: 1rem; margin-top: 1.5rem; }}
    table {{
      page-break-inside: avoid;
    }}
  }}
</style>
</head>
<body>
  <header>
    <div class="logo">
      <span class="logo-mark">C</span>
      <span class="logo-text">Chip Design Agent</span>
    </div>
    <div class="breadcrumb"><span>/</span> {title}</div>
  </header>
  <div class="layout">
    <nav class="sidebar" id="sidebar">
      <div class="sidebar-section">
        <div class="sidebar-label">On this page</div>
        {toc}
      </div>
    </nav>
    <main>
{content}
    </main>
  </div>
</body>
</html>"""


def extract_headings(md_text):
    """Extract headings for TOC generation."""
    headings = []
    for line in md_text.split('\n'):
        m = re.match(r'^(#{1,3})\s+(.+?)(\s+\{#[^}]+\})?\s*$', line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            # Remove HTML comments from heading text
            text = re.sub(r'<!--.*?-->', '', text).strip()
            # Also remove markdown code formatting for TOC display
            text_clean = re.sub(r'[`*]', '', text)
            anchor = text.lower()
            anchor = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '-', anchor).strip('-')
            anchor = re.sub(r'-+', '-', anchor)
            headings.append((level, text_clean, anchor))
    return headings


def generate_toc(headings):
    """Generate sidebar TOC HTML."""
    items = []
    for level, text, anchor in headings:
        cls = 'h2' if level == 2 else ('h3' if level >= 3 else '')
        items.append(f'<a href="#{anchor}" class="{cls}">{text}</a>')
    return '\n'.join(items)


def convert_md_to_html(md_path):
    """Convert a markdown file to NVIDIA-themed HTML."""
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    # Extract title from first h1
    title_match = re.search(r'^#\s+(.+)$', md_text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else os.path.basename(md_path)

    # Extract headings for TOC
    headings = extract_headings(md_text)
    toc = generate_toc([h for h in headings if h[0] <= 3])

    # Add anchor IDs to headings in markdown
    # We need to do this before converting to HTML
    def add_anchor(m):
        level = len(m.group(1))
        text = m.group(2).strip()
        text_clean = re.sub(r'[`*]', '', text)
        anchor = text_clean.lower()
        anchor = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '-', anchor).strip('-')
        anchor = re.sub(r'-+', '-', anchor)
        return f'<a id="{anchor}"></a>\n{"#" * level} {text}'

    # Only add anchors to h2 and h3 for the TOC
    md_with_anchors = re.sub(
        r'^(#{2,3})\s+(.+?)$',
        add_anchor,
        md_text,
        flags=re.MULTILINE
    )

    # Convert markdown to HTML
    html_body = markdown.markdown(
        md_with_anchors,
        extensions=['fenced_code', 'tables', 'codehilite', 'nl2br'],
        extension_configs={
            'codehilite': {
                'css_class': 'highlight',
            }
        }
    )

    # Make table classes
    html_body = html_body.replace('<table>', '<table class="doc-table">')

    # Wrap in template
    full_html = HTML_TEMPLATE.format(
        title=title.replace('"', '&quot;'),
        toc=toc,
        content=html_body
    )

    return full_html, title


def main():
    for md_file in MD_FILES:
        md_path = os.path.join(SCRIPT_DIR, md_file)
        if not os.path.exists(md_path):
            print(f"  SKIP (not found): {md_file}")
            continue

        base = os.path.splitext(md_file)[0]
        html_path = os.path.join(SCRIPT_DIR, f"{base}.html")

        html_content, title = convert_md_to_html(md_path)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"  OK: {md_file} → {base}.html  ({title[:40]})")


if __name__ == '__main__':
    print("Converting template markdown files to HTML...")
    main()
    print("\nDone! All files converted.")
