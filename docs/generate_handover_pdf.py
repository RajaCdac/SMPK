"""
Generate SMPK First Pension handover PDF from Markdown sources.

Output: docs/FIRST_PENSION_CODE_HANDOVER.pdf

Requires: pip install markdown fpdf2
Optional: Microsoft Edge for HTML→PDF (preferred quality)
Fallback: fpdf2 text PDF
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent
QUICK_START = DOCS / "FIRST_PENSION_QUICK_START.md"
FULL_DOC = DOCS / "FIRST_PENSION_CODE_HANDOVER.md"
HTML_OUT = DOCS / "FIRST_PENSION_CODE_HANDOVER.html"
PDF_OUT = DOCS / "FIRST_PENSION_CODE_HANDOVER.pdf"

PRINT_CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }
body {
  font-family: "Segoe UI", Calibri, Arial, sans-serif;
  font-size: 10.5pt;
  line-height: 1.45;
  color: #1a1a1a;
  max-width: 100%;
}
.cover {
  page-break-after: always;
  text-align: center;
  padding-top: 80px;
}
.cover h1 { font-size: 26pt; color: #0d3b66; margin-bottom: 8px; }
.cover .subtitle { font-size: 13pt; color: #555; margin-bottom: 40px; }
.cover .meta { font-size: 11pt; color: #666; line-height: 1.8; }
h1 { color: #0d3b66; font-size: 18pt; border-bottom: 2px solid #0d3b66; padding-bottom: 4px; margin-top: 28px; page-break-after: avoid; }
h2 { color: #145da0; font-size: 14pt; margin-top: 22px; page-break-after: avoid; }
h3 { color: #333; font-size: 12pt; margin-top: 16px; }
h4 { color: #444; font-size: 11pt; }
a { color: #145da0; text-decoration: none; }
code, pre { font-family: Consolas, "Courier New", monospace; font-size: 9pt; background: #f4f6f8; }
pre { padding: 10px; border-radius: 4px; overflow-x: auto; white-space: pre-wrap; page-break-inside: avoid; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 9.5pt; page-break-inside: avoid; }
th, td { border: 1px solid #ccc; padding: 6px 8px; text-align: left; vertical-align: top; }
th { background: #e8eef4; font-weight: 600; }
tr:nth-child(even) td { background: #fafbfc; }
ul, ol { margin: 8px 0; padding-left: 22px; }
li { margin: 3px 0; }
.checklist li { list-style: none; margin-left: -18px; }
.checklist li:before { content: "☐ "; font-size: 12pt; }
blockquote { border-left: 4px solid #145da0; margin: 12px 0; padding: 8px 14px; background: #f0f6fc; color: #333; }
.toc { page-break-after: always; }
.toc ul { list-style: none; padding-left: 0; }
.toc li { margin: 6px 0; border-bottom: 1px dotted #ccc; padding-bottom: 4px; }
.toc a { display: flex; justify-content: space-between; }
.section-quick { page-break-before: always; }
hr { border: none; border-top: 1px solid #ddd; margin: 20px 0; }
@media print {
  h1, h2, h3 { page-break-after: avoid; }
  table, pre, blockquote { page-break-inside: avoid; }
}
"""


def load_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def md_to_html(md: str) -> str:
    import markdown

    return markdown.markdown(
        md,
        extensions=["tables", "fenced_code", "toc", "nl2br"],
        extension_configs={"toc": {"permalink": False, "toc_depth": 3}},
    )


def build_html(quick_md: str, full_md: str) -> str:
    quick_html = md_to_html(quick_md)
    full_html = md_to_html(full_md)

    # Promote checklist items styling
    quick_html = quick_html.replace("<ul>", '<ul class="checklist">', 1)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>SMPK First Pension — Code Handover</title>
  <style>{PRINT_CSS}</style>
</head>
<body>

<div class="cover">
  <h1>SMPK First Pension</h1>
  <div class="subtitle">Code Handover &amp; Quick Start Guide</div>
  <div class="meta">
    <p><strong>Audience:</strong> Junior developer / maintenance team</p>
    <p><strong>Module:</strong> Django backend + React frontend</p>
    <p><strong>API prefix:</strong> <code>first-pension/</code></p>
    <p><strong>Generated from:</strong> docs/FIRST_PENSION_*.md</p>
  </div>
</div>

<div class="toc section-quick">
  <h1 id="quick-start-index">Document index</h1>
  <ul>
    <li><a href="#quick-start"><span>Part A — Quick Start Checklist</span></span></a></li>
    <li><a href="#full-handover"><span>Part B — Full Code Handover</span></span></a></li>
    <li><a href="#section-1"><span>1. What this system does</span></a></li>
    <li><a href="#section-2"><span>2. End-to-end workflow</span></a></li>
    <li><a href="#section-3"><span>3. Architecture</span></a></li>
    <li><a href="#section-4"><span>4. Normal RT vs VR</span></a></li>
    <li><a href="#section-5"><span>5. Oracle Forms mapping</span></a></li>
    <li><a href="#section-6"><span>6. Database models</span></a></li>
    <li><a href="#section-7"><span>7. Backend functions</span></a></li>
    <li><a href="#section-8"><span>8. Frontend functions</span></a></li>
    <li><a href="#section-9"><span>9. API endpoint index</span></a></li>
    <li><a href="#section-10"><span>10. Run &amp; test locally</span></a></li>
    <li><a href="#section-11"><span>11. Known gaps</span></a></li>
  </ul>
</div>

<div class="section-quick" id="quick-start">
  <h1>Part A — Quick Start Checklist</h1>
  {quick_html}
</div>

<div id="full-handover">
  <h1>Part B — Full Code Handover</h1>
  {full_html}
</div>

</body>
</html>
"""


def add_section_ids(html: str) -> str:
    """Add anchor ids to numbered sections for TOC links."""
    for i in range(1, 12):
        html = re.sub(
            rf'<h2 id="[^"]*">\s*{i}\.\s',
            f'<h2 id="section-{i}">{i}. ',
            html,
            count=1,
        )
        html = re.sub(
            rf'<h2>\s*{i}\.\s',
            f'<h2 id="section-{i}">{i}. ',
            html,
            count=1,
        )
    return html


def pdf_via_edge(html_path: Path, pdf_path: Path) -> bool:
    edge_paths = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ]
    edge = next((p for p in edge_paths if p.exists()), None)
    if not edge:
        return False

    html_uri = html_path.resolve().as_uri()
    cmd = [
        str(edge),
        "--headless=new",
        "--disable-gpu",
        f"--print-to-pdf={pdf_path.resolve()}",
        "--no-pdf-header-footer",
        html_uri,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return result.returncode == 0 and pdf_path.exists()


def pdf_via_fpdf(quick_md: str, full_md: str, pdf_path: Path) -> None:
    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            if self.page_no() > 1:
                self.set_font("Helvetica", "I", 8)
                self.set_text_color(100, 100, 100)
                self.cell(0, 8, "SMPK First Pension - Code Handover", align="C")
                self.ln(10)

        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 8, f"Page {self.page_no()}/{{nb}}", align="C")

        def chapter_title(self, title: str):
            self.add_page()
            self.set_font("Helvetica", "B", 16)
            self.set_text_color(13, 59, 102)
            self.multi_cell(0, 10, title)
            self.ln(4)

        def section_title(self, title: str):
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(20, 93, 160)
            self.multi_cell(0, 8, title)
            self.ln(2)

        def body_text(self, text: str):
            self.set_font("Helvetica", "", 10)
            self.set_text_color(26, 26, 26)
            self.multi_cell(0, 5, text)
            self.ln(2)

    def strip_md(md: str) -> str:
        text = re.sub(r"```[\s\S]*?```", "", md)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"^#+\s*", "", text, flags=re.M)
        text = re.sub(r"^\|.*\|$", "", text, flags=re.M)
        text = re.sub(r"^[-=]{3,}$", "", text, flags=re.M)
        text = re.sub(r"^\s*[-*]\s*\[ \]", "[ ]", text, flags=re.M)
        return text.strip()

    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(13, 59, 102)
    pdf.ln(40)
    pdf.cell(0, 12, "SMPK First Pension", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, "Code Handover & Quick Start Guide", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, "See HTML version for tables and full formatting.\nThis PDF is a text fallback.", align="C")

    pdf.chapter_title("Part A - Quick Start Checklist")
    for block in strip_md(quick_md).split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("[ ]") or block.startswith("-"):
            pdf.body_text(block.replace("[ ]", "[ ] "))
        elif len(block) < 80 and block.isupper() is False and block.endswith(":") is False:
            if block.startswith("Day ") or block.startswith("Key ") or "checklist" in block.lower():
                pdf.section_title(block)
            else:
                pdf.body_text(block)
        else:
            pdf.body_text(block)

    pdf.chapter_title("Part B - Full Code Handover (summary)")
    summary = strip_md(full_md)
    if len(summary) > 50000:
        summary = summary[:50000] + "\n\n... [Truncated - open .md or .html for full content] ..."
    for para in summary.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if re.match(r"^\d+\.", para):
            pdf.section_title(para[:120])
        else:
            pdf.body_text(para[:2000])

    pdf.output(str(pdf_path))


def main() -> int:
    if not QUICK_START.exists() or not FULL_DOC.exists():
        print("Missing markdown source files in docs/", file=sys.stderr)
        return 1

    quick_md = load_markdown(QUICK_START)
    full_md = load_markdown(FULL_DOC)
    html = build_html(quick_md, full_md)
    html = add_section_ids(html)
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {HTML_OUT}")

    if pdf_via_edge(HTML_OUT, PDF_OUT):
        print(f"Wrote {PDF_OUT} (via Microsoft Edge)")
        return 0

    print("Edge PDF export unavailable; using fpdf2 fallback...")
    pdf_via_fpdf(quick_md, full_md, PDF_OUT)
    print(f"Wrote {PDF_OUT} (text fallback - also open .html in browser and Print to PDF)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
