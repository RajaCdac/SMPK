from pathlib import Path

from xhtml2pdf import pisa
from pypdf import PdfReader

font_dir = Path(r"d:\SMPK\SMPK\backend\config\methodology2\fonts")
regular = (font_dir / "arial.ttf").as_posix()
bold = (font_dir / "arialbd.ttf").as_posix()

html = f"""
<html><head><meta charset="utf-8"/>
<style>
@font-face {{
  font-family: M2PdfFont;
  src: url("{regular}");
}}
@font-face {{
  font-family: M2PdfFont;
  src: url("{bold}");
  font-weight: bold;
}}
body {{ font-family: M2PdfFont; font-size: 14px; }}
</style></head>
<body><p>Amount (₹) = ₹ 12,345.50</p></body></html>
"""
out = Path(r"d:\SMPK\SMPK\backend\config\_tmp_rupee3.pdf")
with open(out, "wb") as fh:
    st = pisa.CreatePDF(html, dest=fh, encoding="utf-8")
print("err", st.err)
t = PdfReader(str(out)).pages[0].extract_text() or ""
print("rupee", "₹" in t)
print(t.encode("unicode_escape").decode())
