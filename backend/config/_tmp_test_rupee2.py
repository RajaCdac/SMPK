from pathlib import Path
from urllib.parse import urlparse, unquote

from xhtml2pdf import pisa
from pypdf import PdfReader


def link_callback(uri, rel):
    if uri.startswith("file:"):
        parsed = urlparse(uri)
        path = unquote(parsed.path)
        # Windows: /C:/Windows/Fonts/arial.ttf
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        return path
    return uri


html = f"""
<html><head><meta charset="utf-8"/>
<style>
@font-face {{
  font-family: M2PdfFont;
  src: url("file:///C:/Windows/Fonts/arial.ttf");
}}
@font-face {{
  font-family: M2PdfFont;
  src: url("file:///C:/Windows/Fonts/arialbd.ttf");
  font-weight: bold;
}}
body {{ font-family: M2PdfFont; font-size: 14px; }}
</style></head>
<body><p>Amount (₹) = ₹ 12,345.50</p></body></html>
"""
out = Path(r"d:\SMPK\SMPK\backend\config\_tmp_rupee2.pdf")
with open(out, "wb") as fh:
    st = pisa.CreatePDF(html, dest=fh, encoding="utf-8", link_callback=link_callback)
print("err", st.err)
t = PdfReader(str(out)).pages[0].extract_text() or ""
print("rupee", "₹" in t)
print(t.encode("unicode_escape").decode())
