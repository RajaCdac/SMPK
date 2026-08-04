from io import BytesIO
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf import pisa
from pypdf import PdfReader

pdfmetrics.registerFont(TTFont("M2PdfFont", r"C:\Windows\Fonts\arial.ttf"))
pdfmetrics.registerFont(TTFont("M2PdfFont-Bold", r"C:\Windows\Fonts\arialbd.ttf"))
registerFontFamily("M2PdfFont", normal="M2PdfFont", bold="M2PdfFont-Bold")

html = (
    "<html><head><meta charset='utf-8'/>"
    "<style>body{font-family:M2PdfFont;font-size:14px}</style></head>"
    "<body><p>Amount (&#8377;) = &#8377; 12,345.50</p>"
    "<p>Amount (₹) = ₹ 12,345.50</p></body></html>"
)
out = Path(r"d:\SMPK\SMPK\backend\config\_tmp_rupee.pdf")
with open(out, "wb") as fh:
    st = pisa.CreatePDF(html, dest=fh, encoding="utf-8")
print("err", st.err)
t = PdfReader(str(out)).pages[0].extract_text() or ""
print("rupee", "₹" in t)
print([hex(ord(c)) for c in t if ord(c) > 127][:20])
print(t.encode("unicode_escape").decode())
