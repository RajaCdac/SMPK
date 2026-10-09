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


def _last_pay_with_npa(display, npa_amount):
    if display == "—":
        return display
    try:
        if npa_amount is None or npa_amount == "":
            return display
        npa = float(npa_amount)
        if npa == 0:
            return display
    except (TypeError, ValueError):
        return display
    return mark_safe(f"{display} (npa {_format_card_value(npa)})")


def _macp_track_scale(scale) -> str:
    """'MACP 16400-40500' → '16400-40500'. Empty when not a MACP case."""
    match = re.match(r"^MACP\s+(.+)$", str(scale or "").strip(), re.I)
    return match.group(1).strip() if match else ""


def _with_macp_before_scale(title: str) -> str:
    text = str(title or "")
    if re.search(r"MACP\s+Scale", text, re.I):
        return text
    return re.sub(
        r"\((\d[\d\s,]*-\s*\d[\d\s,]*)\)",
        r"(MACP Scale \1)",
        text,
        count=1,
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
    columns = list(comparison.get("columns") or [])
    is_employee_pension = bool(s.get("is_employee_pension"))
    cat = str(s.get("category") or "").strip()
    class12_omit_359 = cat in ("1", "2") or bool(
        comparison.get("class12_omit_359")
        or comparison.get("class12_continuous_277")
    )
    has_death_split = bool(
        comparison.get("has_death_split")
        or s.get("date_of_death")
        or comparison.get("double_fpension_upto")
        or comparison.get("rate_cutover")
    )
    pension_section_title = comparison.get("section_title") or (
        "EMPLOYEE PENSION" if is_employee_pension else "FAMILY PENSION"
    )

    def _is_359_col(col: dict) -> bool:
        if not isinstance(col, dict):
            return False
        try:
            if int(col.get("cpi")) == 359:
                return True
        except (TypeError, ValueError):
            pass
        key = str(col.get("key") or "")
        if key.startswith("359"):
            return True
        hdr = " ".join(
            str(x) for x in (col.get("header_lines") or [])
        ) + " " + str(col.get("header") or "")
        return bool(re.search(r"359\s*CPI|In\s+2022", hdr, re.I)) and not re.search(
            r"277", hdr
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
                "m2": m2_277_raw,
                "m2_display": _money(m2_277_raw),
                "m1_display": _money(m1_277_raw),
                "diff_display": _money(_diff(m2_277_raw, m1_277_raw)),
            },
        ]
        # Class 1/2 last CPI is 277 — never invent a blank 359 column.
        if not class12_omit_359:
            columns.append(
                {
                    "key": "359",
                    "cpi": 359,
                    "header_lines": ["In 2022 (359 CPI)"],
                    "m2_display": _money(m2_359_raw),
                    "m1_display": _money(m1_359_raw),
                    "diff_display": _money(_diff(m2_359_raw, m1_359_raw)),
                }
            )
    else:
        enriched = []
        for col in columns:
            if class12_omit_359 and _is_359_col(col):
                continue
            m2_base = (
                col.get("m2_base")
                if col.get("m2_base") is not None
                else col.get("m2")
            )
            m1_val = col.get("m1")
            base_diff = col.get("diff")
            if base_diff is None and m2_base is not None and m1_val is not None:
                try:
                    base_diff = float(m2_base) - float(m1_val)
                except (TypeError, ValueError):
                    base_diff = None
            enriched.append(
                {
                    **col,
                    "m2_display": _money(m2_base),
                    "m1_display": _money(m1_val),
                    "diff_display": _money(base_diff),
                    "oa_m2_display": _money(col.get("oa_benefit_m2") or 0),
                    "oa_m1_display": _money(col.get("oa_benefit_m1") or 0),
                    "oa_diff_display": _money(col.get("oa_diff") or 0),
                    "payable_display": _money(col.get("payable_basic")),
                    "oa_benefit_display": _money(col.get("oa_benefit") or 0),
                    "revised_display": _money(col.get("revised_total_basic")),
                }
            )
        columns = enriched

    m1_particulars = "Pension fixed as per Methodology-1"
    if class12_omit_359 and is_employee_pension:
        from methodology2.services.lic_bunching import fetch_class12_m1_bunching

        bunch = s.get("m1_bunching") or fetch_class12_m1_bunching(
            s.get("emp_cd"), category=cat
        )
        basic = bunch.get("basic_pension") if isinstance(bunch, dict) else None
        extra = bunch.get("bunch_basic") if isinstance(bunch, dict) else None
        total = bunch.get("m1_bunched") if isinstance(bunch, dict) else None
        if basic is not None and extra not in (None, 0) and total is not None:
            m1_particulars = (
                "Pension fixed as per Methodology-1 with bunching"
            )
            bunched_m1 = mark_safe(
                f"{_rupee_img_html()} {_format_card_value(total)} "
                f"({_format_card_value(basic)} + {_format_card_value(extra)})"
            )

            def _is_employee_277(col: dict) -> bool:
                kind = str(col.get("kind") or "employee").strip().lower()
                if kind not in ("", "employee"):
                    return False
                try:
                    if int(col.get("cpi") or 277) == 359:
                        return False
                except (TypeError, ValueError):
                    pass
                return not str(col.get("key") or "").startswith("359")

            for col in columns:
                if not _is_employee_277(col):
                    continue
                m2_raw = (
                    col.get("m2_base")
                    if col.get("m2_base") is not None
                    else col.get("m2")
                )
                col["m1_display"] = bunched_m1
                try:
                    col["diff_display"] = _money(float(m2_raw) - float(total))
                except (TypeError, ValueError):
                    col["diff_display"] = "—"

    show_oldage_calc = bool(
        comparison.get("has_oldage_calc_table")
        or comparison.get("has_oldage_split")
        or any(float(c.get("oldage_percent") or 0) > 0 for c in columns)
    )

    avg = s.get("last_pay")
    if avg is None:
        avg = s.get("average_pay")
    stag = (
        s.get("stagnation_amount")
        if s.get("stagnation_amount") is not None
        else comparison.get("stagnation_amount")
    )
    last_pay_display = _last_pay_with_stagnation(avg, stag)
    npa = (
        s.get("npa_amount")
        if s.get("npa_amount") is not None
        else comparison.get("npa_amount")
    )
    last_pay_display = _last_pay_with_npa(last_pay_display, npa)
    macp_track = _macp_track_scale(s.get("scale"))
    if macp_track and last_pay_display != "—":
        last_pay_display = mark_safe(
            f"{last_pay_display} (MACP Scale {macp_track})"
        )

    # Wage-revision order suffix on block titles (same as screen print).
    try:
        from methodology2.services.consolidation_service import (
            _append_class12_wage_revision_order,
            _append_wage_revision_order,
            _class12_notionalize_last_description,
            _class12_round_note,
            ensure_class12_opening_basic,
        )
    except Exception:
        _append_wage_revision_order = None
        _append_class12_wage_revision_order = None
        _class12_notionalize_last_description = None
        _class12_round_note = None
        ensure_class12_opening_basic = None

    source_blocks = s.get("revision_blocks") or []
    if class12_omit_359 and ensure_class12_opening_basic:
        source_blocks = ensure_class12_opening_basic(source_blocks)

    blocks = []
    for block_idx, block in enumerate(source_blocks):
        if not isinstance(block, dict):
            continue
        rows = []
        block_rows = [r for r in (block.get("rows") or []) if isinstance(r, dict)]
        last_idx = len(block_rows) - 1
        for idx, row in enumerate(block_rows):
            code = str(row.get("code") or "").strip()
            if not code:
                # Backfill A/B/C for older class 1/2 snapshots saved without codes.
                code = chr(ord("A") + idx) if idx < 26 else str(idx + 1)
            desc = row.get("description") or row.get("label") or ""
            if (
                class12_omit_359
                and _class12_notionalize_last_description
                and idx == last_idx
            ):
                desc = _class12_notionalize_last_description(desc)
            if class12_omit_359 and _class12_round_note:
                desc = _class12_round_note(desc)
            rows.append(
                {
                    "code": code,
                    "description": desc,
                    "amount_display": _money(row.get("value")),
                }
            )
        rev_key = str(block.get("revision_key") or "")
        title = block.get("title") or rev_key or ""
        if class12_omit_359 and _append_class12_wage_revision_order:
            # Class 1/2: Pay Revision wording; 2017 is last (no As per 2022).
            title = _append_class12_wage_revision_order(title, rev_key or title)
        elif _append_wage_revision_order:
            title = _append_wage_revision_order(title, rev_key or title)
        if macp_track and block_idx > 0:
            title = _with_macp_before_scale(title)
        blocks.append(
            {
                "revision_key": rev_key,
                "title": title,
                "rows": rows,
                # Keep bulk PDF on one page (no forced break after 277).
                "page_break_after": False,
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
    family_pensioner_dob_display = comparison.get(
        "family_pensioner_dob_display"
    ) or _format_date_en_in(
        comparison.get("family_pensioner_dob")
        or s.get("family_pensioner_dob")
    )
    double_upto_display = comparison.get(
        "double_fpension_upto_display"
    ) or _format_date_en_in(comparison.get("double_fpension_upto"))
    show_family_name = has_death_split or (not is_employee_pension and bool(family_name))
    show_dod = bool(dod_display and dod_display != "—")
    show_family_pensioner_dob = bool(
        family_pensioner_dob_display
        and family_pensioner_dob_display != "—"
        and (not is_employee_pension or show_family_name)
    )
    show_double_upto = bool(
        double_upto_display and comparison.get("double_fpension_upto")
    )
    date_of_birth_display = _format_date_en_in(
        s.get("date_of_birth") or comparison.get("date_of_birth")
    )

    family_extra_cells = []
    if show_dod:
        family_extra_cells.append(
            {
                "label": "Date of Death (D.O.D.)",
                "value": dod_display,
            }
        )
    if show_family_pensioner_dob:
        family_extra_cells.append(
            {
                "label": "DOB of Family Pensioner",
                "value": family_pensioner_dob_display,
            }
        )
    if show_double_upto:
        family_extra_cells.append(
            {
                "label": "Enhanced FP upto",
                "value": double_upto_display,
            }
        )
    n_extra = len(family_extra_cells)
    for idx, cell in enumerate(family_extra_cells):
        remaining = n_extra - idx
        cell["colspan"] = (4 - n_extra) if remaining == 1 else 1

    return {
        "s": s,
        "rupee_img": mark_safe(_rupee_img_html()),
        "generated_on": _format_date_en_in(date.today()),
        "retirement_date": _format_date_en_in(s.get("retirement_date")),
        "retirement_type": s.get("retirement_type") or "—",
        "date_of_birth_display": date_of_birth_display,
        "tqs": _tqs_display(s),
        "average_pay": _money(avg),
        "last_pay": last_pay_display,
        "is_employee_pension": is_employee_pension,
        "has_death_split": has_death_split,
        "show_family_name": show_family_name,
        "family_pensioner_name": family_name or "—",
        "family_extra_cells": family_extra_cells,
        "pension_section_title": pension_section_title,
        "comparison_columns": columns,
        "m1_particulars": m1_particulars,
        "show_oldage_calc": show_oldage_calc,
        "blocks": blocks,
        "print_title": (
            "Consolidation of Pension as per Methodology-2 and comparison "
            "between M-1 & M-2 for 2017"
            if class12_omit_359
            else (
                "Consolidation of Pension as per Methodology-2 and comparison "
                "between M-1 & M-2 for 2017 & 2022"
            )
        ),
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
