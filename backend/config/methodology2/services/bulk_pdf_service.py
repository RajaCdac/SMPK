"""Render consolidation snapshot to HTML / PDF matching one-by-one print layout."""

from __future__ import annotations

import base64
import os
import re
from datetime import date, datetime
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


def _windows_font_path(*names: str) -> Path | None:
    fonts_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for name in names:
        path = fonts_dir / name
        if path.is_file():
            return path
    return None


@lru_cache(maxsize=1)
def _rupee_data_uri() -> str:
    """
    xhtml2pdf cannot draw U+20B9 (₹) as text (shows a black box).
    Render the glyph once with Arial/Segoe into a tiny PNG and embed it.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return ""

    font_path = _windows_font_path("arial.ttf", "segoeui.ttf", "calibri.ttf")
    if not font_path:
        return ""

    font = ImageFont.truetype(str(font_path), 36)
    probe = Image.new("RGBA", (8, 8), (255, 255, 255, 0))
    draw = ImageDraw.Draw(probe)
    bbox = draw.textbbox((0, 0), "₹", font=font)
    width = max(1, bbox[2] - bbox[0] + 2)
    height = max(1, bbox[3] - bbox[1] + 2)
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    ImageDraw.Draw(img).text(
        (-bbox[0], -bbox[1]), "₹", font=font, fill=(0, 0, 0, 255)
    )
    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _rupee_img_html() -> str:
    uri = _rupee_data_uri()
    if uri:
        return f'<img class="rupee" src="{uri}" alt="Rs" />'
    return "Rs."


def _format_card_value(value) -> str:
    """Match frontend formatCardValue (en-IN grouping, up to 2 decimals)."""
    if value is None or value == "":
        return "—"
    try:
        n = float(value)
    except (TypeError, ValueError):
        return str(value)

    negative = n < 0
    n = abs(n)
    if abs(n - round(n)) < 1e-9:
        int_part = str(int(round(n)))
        frac = ""
    else:
        whole, dec = f"{n:.2f}".split(".")
        int_part = whole
        frac = f".{dec.rstrip('0')}".rstrip(".")

    if len(int_part) <= 3:
        grouped = int_part
    else:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        chunks = []
        while rest:
            chunks.append(rest[-2:])
            rest = rest[:-2]
        grouped = ",".join(reversed(chunks)) + "," + last3

    return ("-" if negative else "") + grouped + frac


def _money(value):
    if value is None or value == "":
        return "—"
    return mark_safe(f"{_rupee_img_html()} {_format_card_value(value)}")


def _last_pay_with_stagnation(last_pay, stagnation_amount):
    base = _money(last_pay)
    if base == "—":
        return base
    try:
        if stagnation_amount is None or stagnation_amount == "":
            return base
        stag = float(stagnation_amount)
        if stag == 0:
            return base
    except (TypeError, ValueError):
        return base
    return mark_safe(
        f"{base} (Stagnation amount {_format_card_value(stag)})"
    )


def _format_date_en_in(raw) -> str:
    if not raw:
        return "—"
    if isinstance(raw, datetime):
        d = raw.date()
    elif isinstance(raw, date):
        d = raw
    else:
        text = str(raw).strip()
        if not text:
            return "—"
        try:
            if "T" in text:
                d = datetime.fromisoformat(text.replace("Z", "+00:00")).date()
            else:
                d = date.fromisoformat(text[:10])
        except ValueError:
            return text
    return f"{d.day}/{d.month}/{d.year}"


def _tqs_display(snapshot: dict) -> str:
    tqs = (snapshot or {}).get("tqs")
    if tqs:
        return str(tqs)
    yr = snapshot.get("tqs_yr")
    mo = snapshot.get("tqs_month")
    days = snapshot.get("tqs_days")
    if yr is None and mo is None and days is None:
        return "—"
    return f"{yr or 0} Y / {mo or 0} M / {days or 0} D"


def _build_print_context(snapshot: dict) -> dict:
    s = snapshot or {}
    comparison = s.get("pension_comparison") or {}
    columns = comparison.get("columns") or []
    is_employee_pension = bool(s.get("is_employee_pension"))
    has_death_split = bool(
        comparison.get("has_death_split")
        or s.get("date_of_death")
        or comparison.get("double_fpension_upto")
        or comparison.get("rate_cutover")
    )
    pension_section_title = comparison.get("section_title") or (
        "EMPLOYEE PENSION" if is_employee_pension else "FAMILY PENSION"
    )

    # Legacy 2-column fallback when older snapshots have no comparison JSON.
    if not columns:
        if is_employee_pension:
            m2_277_raw = s.get("m2_pension_277")
            m2_359_raw = s.get("m2_pension_359")
        else:
            m2_277_raw = s.get("m2_family_pension_277")
            m2_359_raw = s.get("m2_family_pension_359")
        m1_277_raw = s.get("m1_family_pension_277")
        m1_359_raw = s.get("m1_family_pension_359")

        def _diff(a, b):
            if a is None or b is None:
                return None
            try:
                return float(a) - float(b)
            except (TypeError, ValueError):
                return None

        columns = [
            {
                "key": "277",
                "cpi": 277,
                "header_lines": ["In 2017 (277 CPI)"],
                "m2_display": _money(m2_277_raw),
                "m1_display": _money(m1_277_raw),
                "diff_display": _money(_diff(m2_277_raw, m1_277_raw)),
            },
            {
                "key": "359",
                "cpi": 359,
                "header_lines": ["In 2022 (359 CPI)"],
                "m2_display": _money(m2_359_raw),
                "m1_display": _money(m1_359_raw),
                "diff_display": _money(_diff(m2_359_raw, m1_359_raw)),
            },
        ]
    else:
        enriched = []
        for col in columns:
            enriched.append(
                {
                    **col,
                    "m2_display": _money(col.get("m2")),
                    "m1_display": _money(col.get("m1")),
                    "diff_display": _money(col.get("diff")),
                }
            )
        columns = enriched

    avg = s.get("last_pay")
    if avg is None:
        avg = s.get("average_pay")
    stag = (
        s.get("stagnation_amount")
        if s.get("stagnation_amount") is not None
        else comparison.get("stagnation_amount")
    )
    last_pay_display = _last_pay_with_stagnation(avg, stag)

    blocks = []
    for block in s.get("revision_blocks") or []:
        if not isinstance(block, dict):
            continue
        rows = []
        for row in block.get("rows") or []:
            if not isinstance(row, dict):
                continue
            rows.append(
                {
                    "code": row.get("code") or "",
                    "description": row.get("description") or row.get("label") or "",
                    "amount_display": _format_card_value(row.get("value")),
                }
            )
        rev_key = str(block.get("revision_key") or "")
        title = block.get("title") or rev_key or ""
        is_277 = bool(
            re.search(r"277", rev_key, re.I)
            or re.search(r"CPI\s*277|277\s*CPI", str(title), re.I)
        )
        blocks.append(
            {
                "revision_key": rev_key,
                "title": title,
                "rows": rows,
                "page_break_after": is_277,
            }
        )

    family_name = (
        comparison.get("family_pensioner_name")
        or s.get("pensioner_name")
        or ""
    )
    dod_display = comparison.get("date_of_death_display") or _format_date_en_in(
        s.get("date_of_death")
    )
    double_upto_display = comparison.get(
        "double_fpension_upto_display"
    ) or _format_date_en_in(comparison.get("double_fpension_upto"))
    show_family_name = has_death_split or (not is_employee_pension and bool(family_name))
    show_dod = bool(
        dod_display
        and (s.get("date_of_death") or comparison.get("date_of_death"))
    )
    show_double_upto = bool(
        double_upto_display and comparison.get("double_fpension_upto")
    )

    return {
        "s": s,
        "rupee_img": mark_safe(_rupee_img_html()),
        "generated_on": _format_date_en_in(date.today()),
        "retirement_date": _format_date_en_in(s.get("retirement_date")),
        "retirement_type": s.get("retirement_type") or "—",
        "tqs": _tqs_display(s),
        "average_pay": _money(avg),
        "last_pay": last_pay_display,
        "is_employee_pension": is_employee_pension,
        "has_death_split": has_death_split,
        "show_family_name": show_family_name,
        "family_pensioner_name": family_name or "—",
        "date_of_death_display": dod_display if show_dod else "",
        "double_fpension_upto_display": (
            double_upto_display if show_double_upto else ""
        ),
        "pension_section_title": pension_section_title,
        "comparison_columns": columns,
        "blocks": blocks,
    }


def render_consolidation_html(snapshot: dict) -> str:
    return render_to_string(
        "methodology2/bulk_consolidation.html",
        _build_print_context(snapshot),
    )


def safe_case_filename(case_no: str, emp_cd: str, ext: str = "pdf") -> str:
    """Filesystem-safe name from case_no (e.g. C/02140 → C-02140.pdf)."""
    name = str(case_no or "").strip() or str(emp_cd or "unknown").strip()
    name = re.sub(r'[<>:"/\\|?*]+', "-", name)
    name = re.sub(r"\s+", "_", name).strip(" ._")
    if not name:
        name = str(emp_cd or "unknown").strip() or "unknown"
    return f"{name}.{ext.lstrip('.')}"


def write_consolidation_files(
    snapshot: dict, out_dir: Path, emp_cd: str, case_no: str = ""
) -> dict:
    """
Write PDF only (HTML is built in-memory for xhtml2pdf; not saved to disk).

Layout matches Methodology2ConsolidationPrint (one-by-one print).
Returns {"html": "", "pdf": path|None, "pdf_error": str|None, "filename": stem}
"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    emp = str(emp_cd).strip()
    case = str(case_no or (snapshot or {}).get("case_no") or "").strip()

    html = render_consolidation_html(snapshot)

    pdf_name = safe_case_filename(case, emp, "pdf")
    pdf_path = out_dir / pdf_name
    pdf_error = None
    try:
        from xhtml2pdf import pisa

        with open(pdf_path, "wb") as fh:
            status = pisa.CreatePDF(html, dest=fh, encoding="utf-8")
        if status.err:
            pdf_error = f"xhtml2pdf reported {status.err} error(s)"
            if pdf_path.exists():
                pdf_path.unlink(missing_ok=True)
            pdf_path = None
    except Exception as exc:
        pdf_error = str(exc)
        pdf_path = None
        maybe = out_dir / pdf_name
        if maybe.exists():
            maybe.unlink(missing_ok=True)

    return {
        "html": "",
        "pdf": str(pdf_path) if pdf_path else None,
        "pdf_error": pdf_error,
        "filename": Path(pdf_name).stem,
    }
