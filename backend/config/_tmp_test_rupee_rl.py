from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from pypdf import PdfReader

pdfmetrics.registerFont(TTFont("M2PdfFont", r"C:\Windows\Fonts\arial.ttf"))
pdfmetrics.registerFont(TTFont("M2PdfFont-Bold", r"C:\Windows\Fonts\arialbd.ttf"))
registerFontFamily("M2PdfFont", normal="M2PdfFont", bold="M2PdfFont-Bold")

out = Path(r"d:\SMPK\SMPK\backend\config\_tmp_rupee_rl.pdf")
doc = SimpleDocTemplate(str(out))
styles = getSampleStyleSheet()
style = styles["Normal"]
style.fontName = "M2PdfFont"
style.fontSize = 14
doc.build([Paragraph("Amount (₹) = ₹ 12,345.50", style)])
t = PdfReader(str(out)).pages[0].extract_text() or ""
print("rupee", "₹" in t)
print(t.encode("unicode_escape").decode())
