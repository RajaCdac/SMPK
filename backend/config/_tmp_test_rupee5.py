from io import BytesIO
from pathlib import Path
import base64

from PIL import Image, ImageDraw, ImageFont
from xhtml2pdf import pisa
from pypdf import PdfReader

# Render ₹ glyph with Arial into a small PNG
font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 28)
# measure
tmp = Image.new("RGBA", (64, 64), (255, 255, 255, 0))
d = ImageDraw.Draw(tmp)
bbox = d.textbbox((0, 0), "₹", font=font)
w, h = bbox[2] - bbox[0] + 2, bbox[3] - bbox[1] + 2
img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
ImageDraw.Draw(img).text((-bbox[0], -bbox[1]), "₹", font=font, fill=(0, 0, 0, 255))
buf = BytesIO()
img.save(buf, format="PNG")
b64 = base64.b64encode(buf.getvalue()).decode("ascii")
data_uri = f"data:image/png;base64,{b64}"

html = f"""
<html><head><meta charset="utf-8"/>
<style>
body {{ font-family: Helvetica; font-size: 12px; }}
img.rupee {{ height: 11px; width: auto; vertical-align: middle; }}
</style></head>
<body>
<p>Amount (<img class="rupee" src="{data_uri}" />) =
<img class="rupee" src="{data_uri}" /> 12,345.50</p>
</body></html>
"""
out = Path(r"d:\SMPK\SMPK\backend\config\_tmp_rupee5.pdf")
with open(out, "wb") as fh:
    st = pisa.CreatePDF(html, dest=fh, encoding="utf-8")
print("err", st.err, "size", out.stat().st_size)
# Just confirm PDF created; image won't be in extract_text
print("ok")
