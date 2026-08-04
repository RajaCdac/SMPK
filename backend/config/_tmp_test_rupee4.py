from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf import pisa
from pypdf import PdfReader

# Register directly from Windows path (no @font-face temp copy)
pdfmetrics.registerFont(TTFont("M2PdfFont", r"C:\Windows\Fonts\arial.ttf"))
pdfmetrics.registerFont(TTFont("M2PdfFont-Bold", r"C:\Windows\Fonts\arialbd.ttf"))
registerFontFamily("M2PdfFont", normal="M2PdfFont", bold="M2PdfFont-Bold")

# Also register under names xhtml2pdf may look up
pdfmetrics.registerFont(TTFont("Arial", r"C:\Windows\Fonts\arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\Windows\Fonts\arialbd.ttf"))
registerFontFamily("Arial", normal="Arial", bold="Arial-Bold")

html = """
<html><head><meta charset="utf-8"/>
<style>
body { font-family: Arial; font-size: 14px; }
.r { font-family: M2PdfFont; }
</style></head>
<body>
<p class="r">M2: Amount (₹) = ₹ 12,345.50</p>
<p>Arial: Amount (₹) = ₹ 12,345.50</p>
<p>Entity: Amount (&#8377;) = &#8377; 12,345.50</p>
<p>Rs fallback: Amount (Rs.) = Rs. 12,345.50</p>
</body></html>
"""
out = Path(r"d:\SMPK\SMPK\backend\config\_tmp_rupee4.pdf")
with open(out, "wb") as fh:
    st = pisa.CreatePDF(html, dest=fh, encoding="utf-8")
print("err", st.err)
t = PdfReader(str(out)).pages[0].extract_text() or ""
print(t.encode("unicode_escape").decode())
