"""
Family Pension Bill generation (First = N, Monthly = M).

Oracle: FI_PN_First_Family_Pension_Bill.fmb / FPROC_BILL_GENERATE
  radio TXT_BILL_TYPE N (First Bill) / M (Monthly Bill).

Web: generate PFN for unbilled TH rows of one claim
     (or all rows of that emp+claim when regenerate=True).
     Monthly type M uses standing monthly rates (relief 208 + pension 209
     + arrear 214 when present), not a copy of First FP.
"""

from __future__ import annotations

import calendar
import math
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import connection, transaction

from .first_fpension_service import (
    FirstFamilyPensionError,
    _allocate_fpen_id,
    _insert_td_line,
)


class FirstFpBillError(Exception):
    pass


def _clip(value, max_len=None, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    if max_len is not None:
        return text[:max_len]
    return text


def _emp_key(emp_cd):
    text = _clip(emp_cd, 5)
    if text.isdigit() and len(text) < 5:
        return text.zfill(5)
    return text


def _num(value):
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _money(value) -> float:
    return float(
        Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def _fetchone(sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params or [])
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0].lower() for d in cur.description]
        return dict(zip(cols, row))


def _fetchall(sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params or [])
        cols = [d[0].lower() for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _bill_period_closed(bill_type: str, month: int, year: int) -> bool:
    row = _fetchone(
        """
        SELECT BILL_CLOSE_FLG
        FROM fi_pn_mh_pmthsetup
        WHERE BILL_TYPE = %s AND BILL_MTH = %s AND BILL_YR = %s
        LIMIT 1
        """,
        [_clip(bill_type, 3) or "N", int(month), int(year)],
    )
    if not row:
        return False
    return int(row.get("bill_close_flg") or 0) == 1


def _mark_pmthsetup_processed(cur, bill_type: str, month: int, year: int):
    """Light month bookkeeping (skip auto-close of previous month for single-claim bill)."""
    bt = _clip(bill_type, 3) or "N"
    cur.execute(
        """
        SELECT 1 FROM fi_pn_mh_pmthsetup
        WHERE BILL_TYPE = %s AND BILL_MTH = %s AND BILL_YR = %s
        LIMIT 1
        """,
        [bt, int(month), int(year)],
    )
    if cur.fetchone():
        cur.execute(
            """
            UPDATE fi_pn_mh_pmthsetup
            SET BILL_PROCESS_FLG = 1
            WHERE BILL_TYPE = %s AND BILL_MTH = %s AND BILL_YR = %s
            """,
            [bt, int(month), int(year)],
        )
    else:
        # Optional insert if table requires a row — skip if structure unknown
        try:
            cur.execute(
                """
                INSERT INTO fi_pn_mh_pmthsetup (
                    BILL_TYPE, BILL_MTH, BILL_YR,
                    BILL_CLOSE_FLG, BILL_PROCESS_FLG
                ) VALUES (%s, %s, %s, 0, 1)
                """,
                [bt, int(month), int(year)],
            )
        except Exception:
            pass


def _allocate_pfn_bill_no(cur, month: int, year: int) -> str:
    """
    Next PFN bill no: PFN/MM/YYYY/n from DOC_ABV='PFN' fin control
    (same as FPROC_BILL_GENERATE).
    """
    bill_dt = date(int(year), int(month), 1)
    cur.execute(
        """
        SELECT det.L_TRN_NO, mas.FIN_YR
        FROM fi_xx_xx_m_d_fin_ctrl det
        JOIN fi_xx_xx_m_h_fin_ctrl mas ON det.FIN_YR = mas.FIN_YR
        WHERE det.DOC_ABV = 'PFN'
          AND mas.FIN_STAT = 0
          AND %s BETWEEN DATE(mas.YR_ST_DT) AND DATE(mas.YR_END_DT)
        ORDER BY mas.FIN_YR DESC
        LIMIT 1
        FOR UPDATE
        """,
        [bill_dt],
    )
    row = cur.fetchone()
    if not row:
        cur.execute(
            """
            SELECT det.L_TRN_NO, mas.FIN_YR
            FROM fi_xx_xx_m_d_fin_ctrl det
            JOIN fi_xx_xx_m_h_fin_ctrl mas ON det.FIN_YR = mas.FIN_YR
            WHERE det.DOC_ABV = 'PFN' AND mas.FIN_STAT = 0
            ORDER BY mas.FIN_YR DESC
            LIMIT 1
            FOR UPDATE
            """
        )
        row = cur.fetchone()
    if not row:
        raise FirstFpBillError(
            "No PFN document control (fi_xx_xx_m_d_fin_ctrl DOC_ABV=PFN)"
        )

    last_no = int(row[0] or 0)
    fin_yr = int(row[1])
    next_no = last_no + 1
    cur.execute(
        """
        UPDATE fi_xx_xx_m_d_fin_ctrl
        SET L_TRN_NO = %s
        WHERE DOC_ABV = 'PFN' AND FIN_YR = %s
        """,
        [next_no, fin_yr],
    )
    return f"PFN/{int(month):02d}/{int(year)}/{next_no}"


# Common earn/dedn labels used on the First Family Pension Bill print
_EARN_FALLBACKS = {
    "208": "RELIEF",
    "209": "PENSION(FAMILY)",
    "106": "PENSION(FAMILY)",
    "110": "RELIEF",
}


_ONES = (
    "",
    "ONE",
    "TWO",
    "THREE",
    "FOUR",
    "FIVE",
    "SIX",
    "SEVEN",
    "EIGHT",
    "NINE",
    "TEN",
    "ELEVEN",
    "TWELVE",
    "THIRTEEN",
    "FOURTEEN",
    "FIFTEEN",
    "SIXTEEN",
    "SEVENTEEN",
    "EIGHTEEN",
    "NINETEEN",
)
_TENS = (
    "",
    "",
    "TWENTY",
    "THIRTY",
    "FORTY",
    "FIFTY",
    "SIXTY",
    "SEVENTY",
    "EIGHTY",
    "NINETY",
)
_MONTH_FULL = (
    "",
    "JANUARY",
    "FEBRUARY",
    "MARCH",
    "APRIL",
    "MAY",
    "JUNE",
    "JULY",
    "AUGUST",
    "SEPTEMBER",
    "OCTOBER",
    "NOVEMBER",
    "DECEMBER",
)
_MONTH_SHORT = (
    "",
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
)


def _two_digit_words(n: int) -> str:
    n = int(n)
    if n < 20:
        return _ONES[n]
    return f"{_TENS[n // 10]}{_ONES[n % 10]}".strip()


def _amount_in_words(value) -> str:
    """Indian style (RUPEES … ONLY) for whole rupees."""
    try:
        n = int(Decimal(str(value or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except Exception:
        n = 0
    if n == 0:
        return "(RUPEES ZERO ONLY)"
    if n < 0:
        return f"(RUPEES MINUS {_amount_in_words(abs(n))[8:-1].strip()} ONLY)"

    parts = []
    crore = n // 10000000
    n %= 10000000
    lakh = n // 100000
    n %= 100000
    thousand = n // 1000
    n %= 1000
    hundred = n // 100
    n %= 100

    if crore:
        parts.append(f"{_two_digit_words(crore)} CRORE")
    if lakh:
        parts.append(f"{_two_digit_words(lakh)} LAKH")
    if thousand:
        parts.append(f"{_two_digit_words(thousand)} THOUSAND")
    if hundred:
        parts.append(f"{_ONES[hundred]} HUNDRED")
    if n:
        parts.append(_two_digit_words(n))
    # Match Oracle samples: no spaces between compound words like FORTYSEVEN
    joined = " ".join(p for p in parts if p)
    return f"(RUPEES {joined} ONLY)"


def _fmt_amt(value, commas=False) -> str:
    n = _money(value)
    if commas:
        return f"{n:,.2f}"
    return f"{n:.2f}"


def _fmt_bill_date(d: date | None = None) -> str:
    dt = d or date.today()
    return dt.strftime("%d-%b-%y").upper()


def _fmt_dd_mm_yyyy(value) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.date().strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    text = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date().strftime("%d/%m/%Y")
        except ValueError:
            continue
    return text


def _last_day_of_month(month: int, year: int) -> date:
    last = calendar.monthrange(int(year), int(month))[1]
    return date(int(year), int(month), last)


def _earn_desc(code: str | None) -> str:
    cd = _clip(code, 10)
    if not cd:
        return "EARNING"
    if cd in _EARN_FALLBACKS:
        return _EARN_FALLBACKS[cd]
    for sql in (
        "SELECT EARNDEDN_DESC AS d FROM fi_pr_mh_earndedn WHERE EARNDEDN_CD = %s LIMIT 1",
        "SELECT EARNDEDN_DESC AS d FROM fi_pn_mh_earndedn WHERE EARNDEDN_CD = %s LIMIT 1",
        "SELECT EARNDEDN_SNAME AS d FROM fi_pr_mh_earndedn WHERE EARNDEDN_CD = %s LIMIT 1",
        "SELECT EARNDEDN_SNAME AS d FROM fi_pn_mh_earndedn WHERE EARNDEDN_CD = %s LIMIT 1",
    ):
        try:
            row = _fetchone(sql, [cd])
            if row and row.get("d"):
                return str(row["d"]).strip().upper()
        except Exception:
            continue
    return f"EARN/DEDN {cd}"


def _load_td_lines(fam_fmpen_id: str) -> list[dict]:
    return _fetchall(
        """
        SELECT EARN_DEDN_TYPE, EARN_DEDN_CD, AMOUNT, ORIGINAL_AMT, AREAR_AMT
        FROM fi_pn_td_first_month_fpension
        WHERE FAM_FMPEN_ID = %s
        ORDER BY
          CASE WHEN UPPER(COALESCE(EARN_DEDN_TYPE,'E')) = 'E' THEN 0 ELSE 1 END,
          EARN_DEDN_CD
        """,
        [fam_fmpen_id],
    )


def _sum_gratuity_bill_earn_dedn(fam_fmpen_id: str) -> tuple[float, float]:
    """First bill (type N) print helper — gratuity earns + deductions only."""
    td = _load_td_lines(fam_fmpen_id)
    grat = 0.0
    dedn = 0.0
    for line in td:
        et = _clip(line.get("earn_dedn_type"), 1).upper() or "E"
        amt = _num(line.get("amount"))
        if et == "E":
            if _is_gratuity_line(line):
                grat += amt
        else:
            dedn += amt

    if grat <= 0.005:
        th = _fetchone(
            """
            SELECT GRATUITY_AMT
            FROM fi_pn_th_first_month_fpension
            WHERE FAM_FMPEN_ID = %s
            LIMIT 1
            """,
            [fam_fmpen_id],
        ) or {}
        grat = _num(th.get("gratuity_amt"))

    return _money(grat), _money(dedn)


def _oracle_sum_family_td(
    *,
    fam_fmpen_id: str | None = None,
    clmca_id: str | None = None,
    bill_type: str | None = None,
    month: int | None = None,
    year: int | None = None,
    bill_no: str | None = None,
) -> tuple[float, float]:
    """
    FINANCE.Please_Sum_Family — sum TD AMOUNT where earn_dedn_cd is in
    fi_pn_mh_earndedn (type E / D). Uses AMOUNT only (not ORIGINAL_AMT).

    Scope (one of):
      - fam_fmpen_id — one TH row
      - clmca_id + bill_type + month + year — Oracle Please_Sum_Family
      - bill_no — all TH rows linked to an issued PFN bill
    """
    earn_tail = """
        AND td.EARN_DEDN_CD IN (
            SELECT EARNDEDN_CD FROM fi_pn_mh_earndedn
            WHERE UPPER(COALESCE(EARNDEDN_TYPE, '')) = 'E'
        )
    """
    dedn_tail = """
        AND td.EARN_DEDN_CD IN (
            SELECT EARNDEDN_CD FROM fi_pn_mh_earndedn
            WHERE UPPER(COALESCE(EARNDEDN_TYPE, '')) = 'D'
        )
    """
    if fam_fmpen_id:
        scope = "WHERE td.FAM_FMPEN_ID = %s"
        params: list = [_clip(fam_fmpen_id, 22)]
    elif bill_no:
        scope = """
        WHERE td.FAM_FMPEN_ID IN (
            SELECT FAM_FMPEN_ID
            FROM fi_pn_th_first_month_fpension
            WHERE BILL_NO = %s
        )
        """
        params = [_clip(bill_no, 22)]
    else:
        scope = """
        WHERE td.FAM_FMPEN_ID IN (
            SELECT FAM_FMPEN_ID
            FROM fi_pn_th_first_month_fpension
            WHERE CLMCA_ID = %s
              AND FPENSION_TYPE = %s
              AND FPENSION_MONTH = %s
              AND FPENSION_YEAR = %s
        )
        """
        params = [
            _clip(clmca_id, 20),
            _clip(bill_type, 1) or "N",
            int(month or 0),
            int(year or 0),
        ]

    earn_row = _fetchone(
        f"""
        SELECT COALESCE(SUM(COALESCE(td.AMOUNT, 0)), 0) AS s
        FROM fi_pn_td_first_month_fpension td
        {scope}
        {earn_tail}
        """,
        params,
    )
    dedn_row = _fetchone(
        f"""
        SELECT COALESCE(SUM(COALESCE(td.AMOUNT, 0)), 0) AS s
        FROM fi_pn_td_first_month_fpension td
        {scope}
        {dedn_tail}
        """,
        params,
    )
    return _money(_num((earn_row or {}).get("s"))), _money(
        _num((dedn_row or {}).get("s"))
    )


def please_sum_family(
    clmca_id: str,
    bill_type: str,
    month: int,
    year: int,
) -> tuple[float, float]:
    """Port of FINANCE.Please_Sum_Family for one claim + bill period."""
    return _oracle_sum_family_td(
        clmca_id=clmca_id,
        bill_type=bill_type,
        month=month,
        year=year,
    )


def please_sum_family_for_bill(bill_no: str) -> tuple[float, float]:
    """Sum earn/dedn for every TH row on an issued PFN bill (multi-SL_NO safe)."""
    return _oracle_sum_family_td(bill_no=bill_no)


def _detail_lines_for_print(rows: list) -> tuple[list[dict], float, float, float, str]:
    """
    Build earn/dedn rows for the classic bill print.

    Returns (detail_lines, gross_earn, gross_dedn, hold_up_amt, hold_upto_disp).
    """
    gratuity_only = (
        _clip((rows[0] or {}).get("fpension_type"), 1).upper() or "N"
    ) == "N"
    merged: dict[tuple, dict] = {}
    gross_earn = 0.0
    gross_dedn = 0.0
    hold_up = 0.0
    hold_upto = ""
    accrued_cache = None

    for r in rows:
        fam_id = r["fam_fmpen_id"]
        td = _load_td_lines(fam_id)
        th_fp = _num(r.get("fpension_amt"))
        th_relief = _num(r.get("relief"))
        th_grat = _num(r.get("gratuity_amt"))

        if gratuity_only:
            if td:
                for line in td:
                    et = _clip(line.get("earn_dedn_type"), 1).upper() or "E"
                    if et == "E" and not _is_gratuity_line(line):
                        continue
                    cd = _clip(line.get("earn_dedn_cd"), 10)
                    desc = _earn_desc(cd)
                    amt = _num(line.get("amount"))
                    orig = _num(line.get("original_amt"))
                    key = (et, desc)
                    slot = merged.setdefault(
                        key,
                        {
                            "earn_dedn_type": et,
                            "desc": desc,
                            "amount": 0.0,
                            "original_amt": 0.0,
                        },
                    )
                    slot["amount"] = _money(slot["amount"] + amt)
                    slot["original_amt"] = _money(slot["original_amt"] + orig)
            if th_grat > 0 and not any(
                "GRATUITY" in v["desc"].upper()
                for v in merged.values()
                if v["earn_dedn_type"] == "E"
            ):
                key = ("E", "GRATUITY")
                slot = merged.setdefault(
                    key,
                    {
                        "earn_dedn_type": "E",
                        "desc": "GRATUITY",
                        "amount": 0.0,
                        "original_amt": 0.0,
                    },
                )
                slot["amount"] = _money(slot["amount"] + th_grat)
        elif not td:
            for desc, amt in (
                ("RELIEF", th_relief),
                ("PENSION(FAMILY)", th_fp),
                ("DEARNESS PENSION AMOUNT.", 0.0),
            ):
                key = ("E", desc)
                slot = merged.setdefault(
                    key,
                    {
                        "earn_dedn_type": "E",
                        "desc": desc,
                        "amount": 0.0,
                        "original_amt": 0.0,
                    },
                )
                slot["amount"] = _money(slot["amount"] + amt)
            if th_grat > 0:
                key = ("E", "GRATUITY")
                slot = merged.setdefault(
                    key,
                    {
                        "earn_dedn_type": "E",
                        "desc": "GRATUITY",
                        "amount": 0.0,
                        "original_amt": 0.0,
                    },
                )
                slot["amount"] = _money(slot["amount"] + th_grat)
        else:
            seen_relief = False
            td_earn_sum = 0.0
            for line in td:
                et = _clip(line.get("earn_dedn_type"), 1).upper() or "E"
                cd = _clip(line.get("earn_dedn_cd"), 10)
                desc = _earn_desc(cd)
                if "RELIEF" in desc:
                    seen_relief = True
                amt = _num(line.get("amount"))
                orig = _num(line.get("original_amt"))
                if et == "E":
                    td_earn_sum += amt
                key = (et, desc)
                slot = merged.setdefault(
                    key,
                    {
                        "earn_dedn_type": et,
                        "desc": desc,
                        "amount": 0.0,
                        "original_amt": 0.0,
                    },
                )
                slot["amount"] = _money(slot["amount"] + amt)
                slot["original_amt"] = _money(slot["original_amt"] + orig)

            # Oracle-style fixed lines often still show Relief / Dearness even if zero
            if not seen_relief and th_relief == 0:
                merged.setdefault(
                    ("E", "RELIEF"),
                    {
                        "earn_dedn_type": "E",
                        "desc": "RELIEF",
                        "amount": 0.0,
                        "original_amt": 0.0,
                    },
                )
            if "DEARNESS PENSION AMOUNT." not in {
                v["desc"] for v in merged.values() if v["earn_dedn_type"] == "E"
            }:
                merged.setdefault(
                    ("E", "DEARNESS PENSION AMOUNT."),
                    {
                        "earn_dedn_type": "E",
                        "desc": "DEARNESS PENSION AMOUNT.",
                        "amount": 0.0,
                        "original_amt": 0.0,
                    },
                )

            core = th_fp + th_relief
            if th_grat > 0 and abs(td_earn_sum - core) < 1.0:
                key = ("E", "GRATUITY")
                slot = merged.setdefault(
                    key,
                    {
                        "earn_dedn_type": "E",
                        "desc": "GRATUITY",
                        "amount": 0.0,
                        "original_amt": 0.0,
                    },
                )
                slot["amount"] = _money(slot["amount"] + th_grat)

            # Oracle monthly print: face = ORIGINAL (TH header when TD lacks it)
            pen_pay = sum(
                _num(ln.get("amount")) for ln in td if _is_pension_line(ln)
            )
            pen_orig = sum(
                max(_num(ln.get("original_amt")), _num(ln.get("amount")))
                for ln in td
                if _is_pension_line(ln)
            )
            rel_pay = sum(
                _num(ln.get("amount")) for ln in td if _is_relief_line(ln)
            )
            rel_orig = sum(
                max(_num(ln.get("original_amt")), _num(ln.get("amount")))
                for ln in td
                if _is_relief_line(ln)
            )
            pen_face = max(pen_orig, pen_pay)
            if th_fp > pen_pay + 0.005:
                pen_face = max(pen_face, th_fp)
            rel_face = max(rel_orig, rel_pay)
            if rel_pay > 0.005 and rel_face <= rel_pay + 0.005:
                if accrued_cache is None:
                    claim_id = _clip(r.get("clmca_id"), 20)
                    emp_key = _emp_key(r.get("emp_cd")) if r.get("emp_cd") else None
                    bill_m = int(r.get("fpension_month") or date.today().month)
                    bill_y = int(r.get("fpension_year") or date.today().year)
                    accrued_cache = _accrued_unpaid_fp(
                        claim_id=claim_id,
                        emp=emp_key,
                        bill_m=bill_m,
                        bill_y=bill_y,
                    )
                ro = _num(accrued_cache.get("relief_original"))
                if ro > rel_pay + 0.005:
                    rel_face = ro
            hold_up += max(0.0, pen_face - pen_pay)
            for slot in merged.values():
                if slot["earn_dedn_type"] != "E":
                    slot["face_amt"] = _money(slot.get("face_amt", slot["amount"]))
                    continue
                desc_u = slot["desc"].upper()
                if "PENSION(FAMILY)" in desc_u:
                    slot["face_amt"] = _money(slot.get("face_amt", 0) + pen_face)
                elif desc_u == "RELIEF" or desc_u.startswith("RELIEF"):
                    slot["face_amt"] = _money(slot.get("face_amt", 0) + rel_face)

        if gratuity_only:
            earn, dedn = _sum_gratuity_bill_earn_dedn(fam_id)
        else:
            earn, dedn = _sum_first_month_earn_dedn(fam_id)
        gross_earn += earn
        gross_dedn += dedn

    # Stable print order: Relief, Pension(Family), Dearness, other earns, then deductions
    def sort_key(item):
        desc = item["desc"].upper()
        et = item["earn_dedn_type"]
        if et != "E":
            return (1, desc)
        order = {
            "RELIEF": 0,
            "PENSION(FAMILY)": 1,
            "DEARNESS PENSION AMOUNT.": 2,
        }
        return (0, order.get(desc, 50), desc)

    details = sorted(merged.values(), key=sort_key)
    for d in details:
        if "face_amt" not in d:
            d["face_amt"] = _money(
                max(_num(d.get("original_amt")), _num(d.get("amount")))
            )
    # Oracle print gross uses face (original) amounts on earn lines
    pe = sum(_num(d["face_amt"]) for d in details if d["earn_dedn_type"] == "E")
    pd = sum(_num(d["amount"]) for d in details if d["earn_dedn_type"] != "E")
    if pe > 0:
        gross_earn = pe
    if pd > 0 or any(d["earn_dedn_type"] != "E" for d in details):
        gross_dedn = pd

    if hold_up > 0.005:
        # Upto date = last day of bill month of first row
        m = int(rows[0].get("fpension_month") or date.today().month)
        y = int(rows[0].get("fpension_year") or date.today().year)
        hold_upto = _fmt_bill_date(_last_day_of_month(m, y))

    return details, _money(gross_earn), _money(gross_dedn), _money(hold_up), hold_upto


def _clean_name(name) -> str:
    text = " ".join(str(name or "").split()).upper()
    for prefix in ("MRS.", "MR.", "MS.", "MISS.", "SHRI.", "SMT.", "LT.", "LATE"):
        if text.startswith(prefix + " "):
            return text[len(prefix) :].strip()
    return text


def _relation_desc(relation_cd) -> str:
    if relation_cd in (None, ""):
        return ""
    try:
        code = int(relation_cd)
    except (TypeError, ValueError):
        return _clip(relation_cd).upper()
    row = _fetchone(
        "SELECT RELATION_DESC FROM fi_pm_mh_relation WHERE RELATION_CD = %s LIMIT 1",
        [code],
    )
    if row and row.get("relation_desc"):
        return str(row["relation_desc"]).strip().upper()
    return str(code)


def _desig_desc(desig_cd) -> str:
    if desig_cd in (None, ""):
        return ""
    try:
        code = int(desig_cd)
    except (TypeError, ValueError):
        text = str(desig_cd).strip()
        return text.upper() if text and not text.isdigit() else ""
    if code == 0:
        return ""
    row = _fetchone(
        "SELECT DESIG_DESC FROM fi_xx_mh_desig WHERE DESIG_CD = %s LIMIT 1",
        [code],
    )
    if row and row.get("desig_desc"):
        return str(row["desig_desc"]).strip().upper()
    return ""


def _emp_desig_text(emp_cd: str) -> str:
    """Fallback designation when DESIG_CD is missing (older pensioners)."""
    emp = _emp_key(emp_cd)
    if not emp:
        return ""
    for sql, params in (
        (
            "SELECT DESIG AS d FROM fi_xx_mh_emp_data WHERE EMP_CD = %s LIMIT 1",
            [emp],
        ),
        (
            "SELECT designation AS d FROM employee_employee WHERE employee_code = %s LIMIT 1",
            [emp],
        ),
        (
            "SELECT designation AS d FROM first_pension_pensioncase WHERE emp_code = %s LIMIT 1",
            [emp],
        ),
        (
            "SELECT designation AS d FROM first_pension_pensioncase WHERE emp_code = %s LIMIT 1",
            [emp.lstrip("0") or emp],
        ),
    ):
        try:
            row = _fetchone(sql, params)
        except Exception:
            continue
        if row and row.get("d"):
            return str(row["d"]).strip().upper()
    return ""


def _family_roll_no(fp_roll, claim_roll, pension_roll) -> str:
    """
    Family pension bill roll: stored FP roll, else service PENSION_ROLL_NO with /F.
    Oracle print e.g. A/07217 → A/07217/F.
    """
    roll = _clip(fp_roll) or _clip(claim_roll) or _clip(pension_roll)
    if not roll:
        return ""
    upper = roll.upper()
    if upper.endswith("/F"):
        return roll
    return f"{roll}/F"


def _build_print_context(
    *,
    clmca_id: str,
    emp_cd: str,
    bill_no: str,
    bill_m: int,
    bill_y: int,
    rows: list,
    total_earn: float,
    total_dedn: float,
) -> dict:
    """
    Oracle-style First Family Pension Bill print payload
    (landscape monospaced report).
    """
    claim = _fetchone(
        """
        SELECT CLMCA_ID, CA_NO, EMP_CD, APPLICANT_NAME, APPLICANT_TYPE,
               GURDIAN_RELATION_CD, FPENSION_ROLL_NO, PENSION_OPT,
               DOD_EMP_PENSIONER
        FROM fi_pn_mh_fpen_caclaim
        WHERE CLMCA_ID = %s
        LIMIT 1
        """,
        [clmca_id],
    ) or {}

    fp = _fetchone(
        """
        SELECT EMP_RET_DT, DESIG_CD, FPENSION_ROLL_NO, PENSION_OPTION,
               CA_NUMBER, ORIGINAL_SINGLE_FPENSION_AMT, ORIGINAL_DOUBLE_FPENSION_AMT
        FROM fi_pn_mh_familypensioner
        WHERE CLMCA_ID = %s
        ORDER BY SL_NO
        LIMIT 1
        """,
        [clmca_id],
    ) or {}

    pensioner = _fetchone(
        """
        SELECT NAME, CA_NUMBER, DESIG_CD, EMP_RET_DT, PENSION_OPTION,
               PENSION_ROLL_NO
        FROM fi_pn_mh_pensioner
        WHERE EMP_CD = %s
        LIMIT 1
        """,
        [emp_cd],
    ) or {}

    proposal = _fetchone(
        """
        SELECT PENSION_ROLL_NO
        FROM fi_pn_mh_pension_proposal
        WHERE EMP_CD = %s
        ORDER BY PENSION_PROPOSAL_DT DESC
        LIMIT 1
        """,
        [emp_cd],
    ) or {}

    per = _fetchone(
        """
        SELECT FIRST_NAME, MIDDLE_NAME, LAST_NAME
        FROM fi_xx_mh_emp_per
        WHERE EMP_CD = %s
        LIMIT 1
        """,
        [emp_cd],
    ) or {}

    adm = _fetchone(
        """
        SELECT DESIG_CD, SEPARATION_DT, EXP_RET_DT
        FROM fi_xx_mh_emp_adm
        WHERE EMP_CD = %s
        LIMIT 1
        """,
        [emp_cd],
    ) or {}

    emp_data = _fetchone(
        """
        SELECT DESIG, DEPT_DESC, FA_DESC, ALLOC_DESC
        FROM fi_xx_mh_emp_data
        WHERE EMP_CD = %s
        LIMIT 1
        """,
        [emp_cd],
    ) or {}

    emp_name = _clean_name(pensioner.get("name"))
    if not emp_name:
        parts = [
            per.get("first_name"),
            per.get("middle_name"),
            per.get("last_name"),
        ]
        emp_name = _clean_name(" ".join(p for p in parts if p and str(p).strip()))

    relation = _relation_desc(claim.get("gurdian_relation_cd")) or "WIFE"
    applicant = _clean_name(claim.get("applicant_name"))
    deceased_label = f"Late {emp_name}" if emp_name else "Late"
    beneficiary = ""
    if applicant and emp_name:
        beneficiary = f"{applicant}, {relation} of late {emp_name}"
    elif applicant:
        beneficiary = applicant

    desig_cd = fp.get("desig_cd") or pensioner.get("desig_cd") or adm.get("desig_cd")
    designation = (
        _desig_desc(desig_cd)
        or _emp_desig_text(emp_cd)
        or _clip(emp_data.get("desig")).upper()
    )
    ret_dt = (
        fp.get("emp_ret_dt")
        or pensioner.get("emp_ret_dt")
        or adm.get("separation_dt")
        or adm.get("exp_ret_dt")
    )
    roll_no = _family_roll_no(
        fp.get("fpension_roll_no"),
        claim.get("fpension_roll_no"),
        pensioner.get("pension_roll_no") or proposal.get("pension_roll_no"),
    )
    case_no = (
        _clip(claim.get("ca_no"))
        or _clip(fp.get("ca_number"))
        or _clip(pensioner.get("ca_number"))
        or ""
    )
    pension_opt = (
        _clip(claim.get("pension_opt"), 1)
        or _clip(fp.get("pension_option"), 1)
        or _clip(pensioner.get("pension_option"), 1)
        or "G"
    )
    if str(pension_opt).upper().startswith("P"):
        scheme_department = "PORT PENSION SCHEME"
    else:
        scheme_department = "G.O.V.T.PENSION SCHEME"
    # Oracle First_Fpen_Bill_Report_Lic prints organisational department
    org_department = (
        _clip(emp_data.get("fa_desc")).upper()
        or _clip(emp_data.get("dept_desc")).upper()
        or _clip(emp_data.get("alloc_desc")).upper()
        or scheme_department
    )
    department = scheme_department

    details, g_earn, g_dedn, hold_up, hold_upto = _detail_lines_for_print(rows)
    # Prefer printed earn lines (TD) — bill header can be stale
    gross_earn = g_earn if g_earn else _money(total_earn)
    gross_dedn = g_dedn if (g_dedn or total_dedn is not None) else _money(total_dedn or 0)
    if total_dedn and not g_dedn:
        gross_dedn = _money(total_dedn)
    # Oracle bill face: Net = Gross Earn − Gross Dedn only; hold-up is a footnote
    net_earn = _money(gross_earn - gross_dedn)

    m_name = _MONTH_FULL[int(bill_m)] if 1 <= int(bill_m) <= 12 else str(bill_m)
    m_short = _MONTH_SHORT[int(bill_m)] if 1 <= int(bill_m) <= 12 else str(bill_m)
    yy = str(int(bill_y))[-2:]

    fp_type = _clip((rows[0] or {}).get("fpension_type"), 1).upper() or "N"
    # Oracle FI_PN_FPENBILL_GEN / First_Fpen_Bill_Report_Gen always prints this title
    report_title = f"First Family Pension Bill For {m_name} {int(bill_y)}"

    detail_lines = []
    for d in details:
        desc = d["desc"]
        # LIC / Oracle sample labels death gratuity explicitly
        if desc.upper() in ("GRATUITY", "DEATH GRATUITY"):
            desc = "DEATH GRATUITY"
        detail_lines.append(
            {
                "desc": desc,
                "amount": _money(d.get("face_amt", d["amount"])),
                "amount_disp": _fmt_amt(d.get("face_amt", d["amount"]), commas=False),
                "earn_dedn_type": d["earn_dedn_type"],
            }
        )

    eform_members = _gratuity_eform_members(
        emp_cd=emp_cd,
        applicant=applicant,
        relation=relation,
    )
    # Death gratuity from TH (printed) — used when HELD_GRAT_FLG = 'F'
    grat_for_hold = 0.0
    for d in detail_lines:
        if "GRATUITY" in str(d.get("desc") or "").upper():
            grat_for_hold += _money(d.get("amount"))
    if grat_for_hold <= 0.005:
        for r in rows:
            grat_for_hold += _money(r.get("gratuity_amt"))

    held_grat_amt, held_grat_reason = _held_gratuity_from_proposal(
        case_no=case_no,
        emp_cd=emp_cd,
        gratuity_amt=grat_for_hold,
    )
    lic_remarks = _lic_bill_remarks(
        held_grat_amt=held_grat_amt,
        held_grat_reason=held_grat_reason,
        eform_members=eform_members,
    )

    ctx = {
        "org_name": "KOLKATA PORT TRUST",
        "report_title": report_title,
        "fpension_type": fp_type,
        "page_no": 1,
        "total_pages": 1,
        "bill_no": bill_no,
        "bill_date": _fmt_bill_date(date.today()),
        "deceased_name": deceased_label,
        "roll_no": roll_no,
        "case_no": case_no,
        "designation": designation,
        "beneficiary": beneficiary,
        "department": department,
        "org_department": org_department,
        "scheme_department": scheme_department,
        "retirement_date": _fmt_dd_mm_yyyy(ret_dt),
        "month_label": f"{m_short} - {yy}",
        "detail_lines": detail_lines,
        "hold_up_amt": hold_up,
        "hold_up_disp": (
            f"*) Rs. {int(round(hold_up))} To be held up till {hold_upto}."
            if hold_up > 0.005
            else ""
        ),
        "held_grat_amt": held_grat_amt,
        "held_grat_reason": held_grat_reason,
        "eform_members": eform_members,
        "remarks": lic_remarks,
        "gross_earn": gross_earn,
        "gross_dedn": gross_dedn,
        "net_earn": net_earn,
        "gross_earn_disp": _fmt_amt(gross_earn, commas=False),
        "gross_dedn_disp": _fmt_amt(gross_dedn, commas=False),
        "net_earn_disp": _fmt_amt(net_earn, commas=False),
        "gross_earn_commas": _fmt_amt(gross_earn, commas=True),
        "gross_dedn_commas": _fmt_amt(gross_dedn, commas=True),
        "net_earn_commas": _fmt_amt(net_earn, commas=True),
        "amount_in_words": _amount_in_words(net_earn),
        "no_of_cases": max(1, len(rows)),
    }
    if fp_type == "N":
        ctx = _shape_lic_print(ctx)
    return ctx


def _held_gratuity_from_proposal(
    *,
    case_no: str,
    emp_cd: str,
    gratuity_amt: float,
) -> tuple[float, str]:
    """
    Oracle CF_GRAT_HELD_STRFORMULA (FI_PN_MH_PENSION_PROPOSAL).

    HELD_GRAT_FLG: F=full gratuity, P=partial HELD_GRAT_AMT, N=0.
    Reason text from QUARTER_STATUS / ID_CARD_SUBMITTED.
    """
    ca = _clip(case_no)
    emp = _emp_key(emp_cd)
    row = None
    if ca:
        row = _fetchone(
            """
            SELECT QUARTER_STATUS, ID_CARD_SUBMITTED, HELD_GRAT_FLG, HELD_GRAT_AMT
            FROM fi_pn_mh_pension_proposal
            WHERE TRIM(CA_NUMBER) = %s
            ORDER BY PENSION_PROPOSAL_DT DESC
            LIMIT 1
            """,
            [ca],
        )
    if not row and emp:
        row = _fetchone(
            """
            SELECT QUARTER_STATUS, ID_CARD_SUBMITTED, HELD_GRAT_FLG, HELD_GRAT_AMT
            FROM fi_pn_mh_pension_proposal
            WHERE EMP_CD = %s
            ORDER BY PENSION_PROPOSAL_DT DESC
            LIMIT 1
            """,
            [emp],
        )
    if not row:
        # Sample default: ID-Card note with Rs. 0 when no proposal flags
        return 0.0, "ID_CARD"

    qtr = _clip(row.get("quarter_status"), 1).upper()
    id_card = _clip(row.get("id_card_submitted"), 1).upper()
    flg = _clip(row.get("held_grat_flg"), 1).upper() or "N"
    amt = _money(row.get("held_grat_amt"))

    # Amount resolution (Oracle): only when quarter not vacant OR id card not Y
    if qtr != "V" or id_card != "Y":
        if flg == "F":
            amt = _money(gratuity_amt)
        elif flg == "P":
            amt = _money(row.get("held_grat_amt"))
        else:  # 'N' or blank
            amt = 0.0

    # Reason (Oracle active branch order)
    if qtr == "V":
        reason = "QUARTER"
    elif id_card == "Y":
        # Active Oracle formula uses = 'Y' for the ID-Card hold sentence
        reason = "ID_CARD"
    elif qtr == "O":
        reason = "ELEC"
    elif qtr == "Q":
        reason = "QTR_ELEC"
    elif qtr == "C":
        reason = "COURT"
    elif qtr == "S":
        reason = "QTR_ELEC_CRT"
    elif qtr == "T":
        reason = "QTR_CRT"
    elif qtr == "U":
        reason = "ELEC_CRT"
    elif qtr == "M":
        reason = "CREDIT_SOC"
    else:
        reason = "ID_CARD" if id_card != "Y" else ""

    return _money(amt), reason


def _held_gratuity_reason_text(reason: str) -> str:
    mapping = {
        "QUARTER": "held up for Quater Clearence",
        "ID_CARD": "held up for non submission of ID-Card",
        "ELEC": "held up for Electricity Clearence",
        "QTR_ELEC": "held up for Quter  & Elec Clearence",
        "COURT": "held up for Court Attachement",
        "QTR_ELEC_CRT": "held up for Quter Elec Crt Charges",
        "QTR_CRT": "held up for Qtr clear & Crt Attachemnt",
        "ELEC_CRT": "held up for Elec  & Crt Attachement",
        "CREDIT_SOC": "held up for Co-Operative Credit Society",
    }
    return mapping.get(_clip(reason).upper(), "held up for non submission of ID-Card")


def _gratuity_eform_members(
    *,
    emp_cd: str,
    applicant: str,
    relation: str,
) -> list[dict]:
    """
    DCR / E-FORM share list for First FP Bill (LIC) remarks.
    Prefer GR nominees; fall back to claim applicant at 100%.
    """
    members: list[dict] = []
    try:
        rows = _fetchall(
            """
            SELECT n.NOMINEE_NAME, n.SHARE_PCT, n.RELATION_CD,
                   COALESCE(r.RELATION_DESC, '') AS RELATION_DESC
            FROM fi_xx_md_nominee n
            LEFT JOIN fi_pm_mh_relation r ON r.RELATION_CD = n.RELATION_CD
            WHERE n.EMP_CD = %s
              AND UPPER(COALESCE(n.NOMIN_TYPE, '')) = 'GR'
            ORDER BY n.SL_NO
            """,
            [_emp_key(emp_cd)],
        )
    except Exception:
        rows = []
    for row in rows or []:
        name = _clean_name(row.get("nominee_name"))
        if not name:
            continue
        rel = _clean_name(row.get("relation_desc")) or _relation_desc(
            row.get("relation_cd")
        )
        pct = _money(row.get("share_pct"))
        members.append(
            {
                "name": name,
                "relation": rel,
                "share_pct": pct,
                "label": f"{name} {rel} {int(round(pct))}%".strip(),
            }
        )
    if not members and applicant:
        members.append(
            {
                "name": applicant,
                "relation": relation,
                "share_pct": 100.0,
                "label": f"{applicant} {relation} 100%".strip(),
            }
        )
    return members


def _lic_bill_remarks(
    *,
    held_grat_amt: float,
    held_grat_reason: str,
    eform_members: list[dict],
) -> list[str]:
    """Oracle First_Fpen_Bill_Report_Lic footnote block."""
    held = int(round(_money(held_grat_amt)))
    reason = _held_gratuity_reason_text(held_grat_reason or "ID_CARD")
    lines = [
        (
            f"*) Rs. {held} as payment of gratuity amount is to be {reason}. "
            "On Submission of I-D CARD the amount of DCR Gratuity is to be paid "
            "to the following Members. as per E-FORM."
        ),
        "*) Payment of DCR Gratuity is to be paid to the following members as per E-FORM.",
    ]
    for i, m in enumerate(eform_members or [], start=1):
        lines.append(f"{i}) {m.get('label') or m.get('name') or ''}")
    return lines


def _is_lic_bill_line(line: dict) -> bool:
    """LIC bill shows death gratuity + deductions only (no family pension)."""
    et = _clip(line.get("earn_dedn_type"), 1).upper() or "E"
    if et != "E":
        return True
    desc = _clip(line.get("desc")).upper()
    return "GRATUITY" in desc


def _shape_lic_print(print_ctx: dict) -> dict:
    """
    First_Fpen_Bill_Report_Lic: drop pension/relief lines; totals from
    gratuity + deductions only.
    """
    ctx = dict(print_ctx or {})
    lines = [ln for ln in (ctx.get("detail_lines") or []) if _is_lic_bill_line(ln)]
    # Drop zero-amount noise
    lines = [ln for ln in lines if abs(_money(ln.get("amount"))) > 0.005]
    gross_earn = _money(
        sum(_money(ln.get("amount")) for ln in lines if (_clip(ln.get("earn_dedn_type"), 1).upper() or "E") == "E")
    )
    gross_dedn = _money(
        sum(_money(ln.get("amount")) for ln in lines if (_clip(ln.get("earn_dedn_type"), 1).upper() or "E") != "E")
    )
    net_earn = _money(gross_earn - gross_dedn)
    ctx["detail_lines"] = lines
    ctx["gross_earn"] = gross_earn
    ctx["gross_dedn"] = gross_dedn
    ctx["net_earn"] = net_earn
    ctx["gross_earn_disp"] = _fmt_amt(gross_earn, commas=False)
    ctx["gross_dedn_disp"] = _fmt_amt(gross_dedn, commas=False)
    ctx["net_earn_disp"] = _fmt_amt(net_earn, commas=False)
    ctx["gross_earn_commas"] = _fmt_amt(gross_earn, commas=True)
    ctx["gross_dedn_commas"] = _fmt_amt(gross_dedn, commas=True)
    ctx["net_earn_commas"] = _fmt_amt(net_earn, commas=True)
    ctx["amount_in_words"] = _amount_in_words(net_earn)
    # Rebuild remarks with proposal held-grat (already on ctx)
    ctx["remarks"] = _lic_bill_remarks(
        held_grat_amt=_money(ctx.get("held_grat_amt")),
        held_grat_reason=_clip(ctx.get("held_grat_reason")) or "ID_CARD",
        eform_members=ctx.get("eform_members") or [],
    )
    return ctx


def _sum_first_month_earn_dedn(
    fam_fmpen_id: str, *, bill_type: str | None = None
) -> tuple[float, float]:
    """
    Please_Sum_Family equivalent for one FAM_FMPEN_ID.

    Matches Oracle: sum TD AMOUNT where earn_dedn_cd is E/D in fi_pn_mh_earndedn.
    bill_type is accepted for callers but not required (scope is fam_fmpen_id).
    """
    _ = bill_type  # kept for API compatibility with bill generation callers
    return _oracle_sum_family_td(fam_fmpen_id=fam_fmpen_id)


def _load_rows_for_bill(
    *,
    clmca_id: str,
    emp_cd: str | None,
    bill_type: str,
    month: int | None,
    year: int | None,
    regenerate: bool,
):
    params = [_clip(clmca_id, 20), _clip(bill_type, 1) or "N"]
    sql = """
        SELECT FAM_FMPEN_ID, FPENSION_MONTH, FPENSION_YEAR, FPENSION_TYPE,
               FPENSION_AMT, RELIEF, GRATUITY_AMT, BILL_NO, EMP_CD,
               CLMCA_ID, SL_NO, BANK_CD, LIC_BANK_CD
        FROM fi_pn_th_first_month_fpension
        WHERE CLMCA_ID = %s
          AND FPENSION_TYPE = %s
    """
    if emp_cd:
        sql += " AND EMP_CD = %s"
        params.append(_emp_key(emp_cd))
    if month and year:
        sql += " AND FPENSION_MONTH = %s AND FPENSION_YEAR = %s"
        params.extend([int(month), int(year)])
    if not regenerate:
        sql += " AND (BILL_NO IS NULL OR BILL_NO = '')"
    sql += " ORDER BY SL_NO, FAM_FMPEN_ID"
    return _fetchall(sql, params)


def _int_or_none(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_gratuity_line(line: dict) -> bool:
    cd = _clip(line.get("earn_dedn_cd"), 10)
    desc = _earn_desc(cd).upper()
    return cd in {"205", "104"} or "GRATUITY" in desc


def _line_monthly_amt(line: dict) -> float:
    orig = _num(line.get("original_amt"))
    return orig if orig > 0.005 else _num(line.get("amount"))


def _is_relief_line(line: dict) -> bool:
    cd = _clip(line.get("earn_dedn_cd"), 10)
    desc = _earn_desc(cd).upper()
    if cd in {"214"} or "AREAR" in desc:
        return False
    return cd in {"208", "110"} or "RELIEF" in desc


def _is_pension_line(line: dict) -> bool:
    cd = _clip(line.get("earn_dedn_cd"), 10)
    desc = _earn_desc(cd).upper()
    return cd in {"209", "106"} or "PENSION(FAMILY)" in desc


def _is_arrear_line(line: dict) -> bool:
    cd = _clip(line.get("earn_dedn_cd"), 10)
    desc = _earn_desc(cd).upper()
    return cd in {"214"} or "AREAR" in desc


def _td_has_monthly_relief(lines: list[dict]) -> bool:
    return any(_is_relief_line(ln) and _line_monthly_amt(ln) > 0.005 for ln in lines)


def _da_class_grp(emp_class) -> int:
    try:
        c = int(float(emp_class))
    except (TypeError, ValueError):
        return 3
    if c in (1, 2):
        return 1
    return 3


def _ceil_rupee(value) -> int:
    return int(math.ceil(float(value or 0)))


def _monthly_master(claim_id: str, emp: str | None) -> dict:
    """Class / CPI / monthly pension / relief tag from master + 277 upgrade."""
    cid = _clip(claim_id, 20)
    out = {
        "class_grp": 3,
        "cpi": 359,
        "relief_tag": "Y",
        "pension": 0.0,
        "arrear": 0.0,
    }
    fpner = _fetchone(
        """
        SELECT APP_CLASS, BASE_CPI, RELIEF_TAG,
               ORIGINAL_SINGLE_FPENSION_AMT, ORIGINAL_FAMILY_PENSION_AMT
        FROM fi_pn_mh_familypensioner
        WHERE CLMCA_ID = %s
        LIMIT 1
        """,
        [cid],
    )
    if not fpner and emp:
        fpner = _fetchone(
            """
            SELECT APP_CLASS, BASE_CPI, RELIEF_TAG,
                   ORIGINAL_SINGLE_FPENSION_AMT, ORIGINAL_FAMILY_PENSION_AMT
            FROM fi_pn_mh_familypensioner
            WHERE EMP_CD = %s
            ORDER BY DATE_CREATED DESC
            LIMIT 1
            """,
            [emp],
        )
    claim = _fetchone(
        "SELECT CLASS, RETIREMENT_CPI FROM fi_pn_mh_fpen_caclaim WHERE CLMCA_ID = %s LIMIT 1",
        [cid],
    )
    upgrade = _fetchone(
        """
        SELECT EMP_CLASS, UPGRADED_CPI, UPGRADED_BASIC,
               ARREAR_PENSION, ARREAR_RELIEF
        FROM fi_pn_family_277_upgrade
        WHERE CLAIM_ID = %s
        LIMIT 1
        """,
        [cid],
    )
    app = _fetchone(
        """
        SELECT RELIEF_TAG
        FROM fi_pn_md_fpen_appcn
        WHERE CLMCA_ID = %s AND FPEN_ACTIVE = 1
        LIMIT 1
        """,
        [cid],
    )
    cls = None
    if fpner and fpner.get("app_class") not in (None, ""):
        cls = fpner.get("app_class")
    elif upgrade and upgrade.get("emp_class") not in (None, ""):
        cls = upgrade.get("emp_class")
    elif claim and claim.get("class") not in (None, ""):
        cls = claim.get("class")
    out["class_grp"] = _da_class_grp(cls)

    cpi = None
    if upgrade and upgrade.get("upgraded_cpi") not in (None, ""):
        cpi = upgrade.get("upgraded_cpi")
    elif fpner and fpner.get("base_cpi") not in (None, ""):
        cpi = fpner.get("base_cpi")
    elif claim and claim.get("retirement_cpi") not in (None, ""):
        cpi = claim.get("retirement_cpi")
    try:
        out["cpi"] = int(float(cpi)) if cpi is not None else 359
    except (TypeError, ValueError):
        out["cpi"] = 359

    tag = _clip((app or {}).get("relief_tag"), 1) or _clip(
        (fpner or {}).get("relief_tag"), 1
    )
    out["relief_tag"] = tag or "Y"

    pension = 0.0
    if upgrade and _num(upgrade.get("upgraded_basic")) > 0.005:
        pension = _num(upgrade.get("upgraded_basic"))
    elif fpner:
        pension = _num(fpner.get("original_single_fpension_amt")) or _num(
            fpner.get("original_family_pension_amt")
        )
    out["pension"] = pension

    if upgrade:
        out["arrear"] = _num(upgrade.get("arrear_pension")) + _num(
            upgrade.get("arrear_relief")
        )
    return out


def _current_da_pct(class_grp: int, cpi: int, as_of: date) -> float:
    """DA% in force on as_of from fi_pr_mh_calc_da (359-era incept 2022, else 2017)."""
    incepts = (
        [date(2022, 1, 1), date(2017, 1, 1)]
        if int(cpi or 0) >= 359
        else [date(2017, 1, 1), date(2022, 1, 1)]
    )
    for inc in incepts:
        row = _fetchone(
            """
            SELECT DA_PCT AS da_pct
            FROM fi_pr_mh_calc_da
            WHERE EMP_CLASS_GRP = %s
              AND INCEPT_DT = %s
              AND WEF_DT <= %s
            ORDER BY WEF_DT DESC
            LIMIT 1
            """,
            [int(class_grp), inc, as_of],
        )
        if row and row.get("da_pct") is not None:
            return float(row["da_pct"])
    return 0.0


def _compute_monthly_relief(pension: float, claim_id: str, emp: str | None, as_of: date) -> float:
    master = _monthly_master(claim_id, emp)
    if master["relief_tag"] == "N":
        return 0.0
    pct = _current_da_pct(master["class_grp"], master["cpi"], as_of)
    if pct <= 0:
        return 0.0
    return float(_ceil_rupee((pension * pct) / 100.0))


def _wef_from_claim(claim_id: str) -> date | None:
    row = _fetchone(
        """
        SELECT DOD_EMP_PENSIONER, FPEN_START_MNTH, FPRN_START_YR, APPL_DOD, EMP_DOD
        FROM fi_pn_mh_fpen_caclaim
        WHERE CLMCA_ID = %s
        LIMIT 1
        """,
        [_clip(claim_id, 20)],
    )
    if not row:
        return None
    dod = None
    for key in ("dod_emp_pensioner", "appl_dod", "emp_dod"):
        val = row.get(key)
        if val is None or val == "":
            continue
        if isinstance(val, datetime):
            dod = val.date()
            break
        if isinstance(val, date):
            dod = val
            break
        text = str(val).strip()[:10]
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                dod = datetime.strptime(text, fmt).date()
                break
            except ValueError:
                continue
        if dod:
            break
    if dod:
        return dod + timedelta(days=1)
    try:
        m = int(row.get("fpen_start_mnth") or 0)
        y = int(row.get("fprn_start_yr") or 0)
        if m and y:
            return date(y, m, 1)
    except (TypeError, ValueError):
        pass
    return None


def _inactive_from(claim_id: str) -> date | None:
    row = _fetchone(
        """
        SELECT FPEN_INACTIVE_FROM_DT AS d
        FROM fi_pn_md_fpen_appcn
        WHERE CLMCA_ID = %s AND FPEN_ACTIVE = 1
        LIMIT 1
        """,
        [_clip(claim_id, 20)],
    )
    val = (row or {}).get("d")
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return None


def _prior_monthly_row(claim_id: str, bill_m: int, bill_y: int, emp: str | None):
    sql = """
        SELECT FAM_FMPEN_ID, FPENSION_MONTH, FPENSION_YEAR, FPENSION_AMT, RELIEF, BILL_NO
        FROM fi_pn_th_first_month_fpension
        WHERE CLMCA_ID = %s
          AND FPENSION_TYPE = 'M'
          AND (FPENSION_YEAR < %s OR (FPENSION_YEAR = %s AND FPENSION_MONTH < %s))
    """
    params = [_clip(claim_id, 20), int(bill_y), int(bill_y), int(bill_m)]
    if emp:
        sql += " AND EMP_CD = %s"
        params.append(emp)
    sql += " ORDER BY FPENSION_YEAR DESC, FPENSION_MONTH DESC LIMIT 1"
    return _fetchone(sql, params)


def _is_unit_rate(amount: float, rate: float) -> bool:
    if rate <= 0.005:
        return True
    return float(amount or 0) <= float(rate) * 1.05 + 1.0


def _accrued_unpaid_fp(
    *,
    claim_id: str,
    emp: str | None,
    bill_m: int,
    bill_y: int,
) -> dict:
    """
    Unpaid FP from WEF through the bill month.

    Oracle first/monthly print for emp 17663 Jul-2026:
      AMOUNT 209 = WEF..previous month (288879)
      ORIGINAL 209 = AMOUNT + current month rate (hold 15656 till month-end)
      208 = DA on the *paid* months only (48194)
    """
    master = _monthly_master(claim_id, emp)
    rate = float(master["pension"] or 0)
    wef = _wef_from_claim(claim_id) or date(bill_y, bill_m, 1)
    bill_start = date(int(bill_y), int(bill_m), 1)
    bill_end = _last_day_of_month(bill_m, bill_y)
    inactive = _inactive_from(claim_id)
    period_end = bill_end
    if inactive and inactive < period_end:
        period_end = inactive
    if wef > period_end or rate <= 0.005:
        return {
            "pension_amount": 0.0,
            "pension_original": 0.0,
            "relief": 0.0,
            "relief_original": 0.0,
            "rate": rate,
            "multi_month": False,
        }

    hold_current = wef < bill_start
    orig = 0
    amt = 0
    relief = 0
    relief_original = 0
    y, m = wef.year, wef.month
    while True:
        first = date(y, m, 1)
        last = _last_day_of_month(m, y)
        pay_from = wef if wef > first else first
        pay_to = last if last < period_end else period_end
        if pay_to >= pay_from:
            days = (pay_to - pay_from).days + 1
            totdays = last.day
            if days >= totdays:
                pen = _ceil_rupee(rate) if abs(rate - round(rate)) > 1e-9 else int(round(rate))
            else:
                pen = _ceil_rupee((rate * days) / totdays)
            is_hold = hold_current and (y, m) == (int(bill_y), int(bill_m))
            orig += pen
            if not is_hold:
                amt += pen
            if master["relief_tag"] != "N":
                pct = _current_da_pct(master["class_grp"], master["cpi"], pay_to)
                if pct > 0:
                    month_rlf = _ceil_rupee((rate * pct) / 100.0)
                    if days < totdays:
                        month_rlf = _ceil_rupee((month_rlf * days) / totdays)
                    relief_original += month_rlf
                    if not is_hold:
                        relief += month_rlf
        if (y, m) == (period_end.year, period_end.month):
            break
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1

    return {
        "pension_amount": float(amt),
        "pension_original": float(orig),
        "relief": float(relief),
        "relief_original": float(relief_original),
        "rate": rate,
        "multi_month": hold_current and orig > rate * 1.05,
    }


def _first_fp_source(claim_id: str, emp: str | None) -> dict | None:
    sql = """
        SELECT FAM_FMPEN_ID, FPENSION_MONTH, FPENSION_YEAR, FPENSION_TYPE,
               FPENSION_AMT, RELIEF, GRATUITY_AMT, BILL_NO, EMP_CD,
               CLMCA_ID, SL_NO, BANK_CD, LIC_BANK_CD, CPI_NO
        FROM fi_pn_th_first_month_fpension
        WHERE CLMCA_ID = %s AND FPENSION_TYPE = 'N'
    """
    params = [claim_id]
    if emp:
        sql += " AND EMP_CD = %s"
        params.append(emp)
    sql += " ORDER BY FPENSION_YEAR DESC, FPENSION_MONTH DESC, DATE_CREATED DESC LIMIT 1"
    row = _fetchone(sql, params)
    if row or not emp:
        return row
    return _fetchone(
        """
        SELECT FAM_FMPEN_ID, FPENSION_MONTH, FPENSION_YEAR, FPENSION_TYPE,
               FPENSION_AMT, RELIEF, GRATUITY_AMT, BILL_NO, EMP_CD,
               CLMCA_ID, SL_NO, BANK_CD, LIC_BANK_CD, CPI_NO
        FROM fi_pn_th_first_month_fpension
        WHERE CLMCA_ID = %s AND FPENSION_TYPE = 'N'
        ORDER BY FPENSION_YEAR DESC, FPENSION_MONTH DESC, DATE_CREATED DESC
        LIMIT 1
        """,
        [claim_id],
    )


def _standing_monthly_source(claim_id: str, emp: str | None) -> dict | None:
    """Latest type-M row that already has monthly relief (208), e.g. emp 47529."""
    sql = """
        SELECT th.FAM_FMPEN_ID, th.FPENSION_MONTH, th.FPENSION_YEAR, th.FPENSION_TYPE,
               th.FPENSION_AMT, th.RELIEF, th.GRATUITY_AMT, th.BILL_NO, th.EMP_CD,
               th.CLMCA_ID, th.SL_NO, th.BANK_CD, th.LIC_BANK_CD, th.CPI_NO
        FROM fi_pn_th_first_month_fpension th
        JOIN fi_pn_td_first_month_fpension td
          ON td.FAM_FMPEN_ID = th.FAM_FMPEN_ID
        WHERE th.CLMCA_ID = %s
          AND th.FPENSION_TYPE = 'M'
          AND td.EARN_DEDN_CD IN ('208', '110')
          AND COALESCE(td.ORIGINAL_AMT, td.AMOUNT) > 0
    """
    params = [claim_id]
    if emp:
        sql += " AND th.EMP_CD = %s"
        params.append(emp)
    sql += """
        ORDER BY th.FPENSION_YEAR DESC, th.FPENSION_MONTH DESC, th.DATE_CREATED DESC
        LIMIT 1
    """
    row = _fetchone(sql, params)
    if row or not emp:
        return row
    return _fetchone(
        """
        SELECT th.FAM_FMPEN_ID, th.FPENSION_MONTH, th.FPENSION_YEAR, th.FPENSION_TYPE,
               th.FPENSION_AMT, th.RELIEF, th.GRATUITY_AMT, th.BILL_NO, th.EMP_CD,
               th.CLMCA_ID, th.SL_NO, th.BANK_CD, th.LIC_BANK_CD, th.CPI_NO
        FROM fi_pn_th_first_month_fpension th
        JOIN fi_pn_td_first_month_fpension td
          ON td.FAM_FMPEN_ID = th.FAM_FMPEN_ID
        WHERE th.CLMCA_ID = %s
          AND th.FPENSION_TYPE = 'M'
          AND td.EARN_DEDN_CD IN ('208', '110')
          AND COALESCE(td.ORIGINAL_AMT, td.AMOUNT) > 0
        ORDER BY th.FPENSION_YEAR DESC, th.FPENSION_MONTH DESC, th.DATE_CREATED DESC
        LIMIT 1
        """,
        [claim_id],
    )


def _header_source(claim_id: str, emp: str | None) -> dict | None:
    standing = _standing_monthly_source(claim_id, emp)
    if standing:
        return standing
    first = _first_fp_source(claim_id, emp)
    if first:
        return first
    return _fetchone(
        """
        SELECT FAM_FMPEN_ID, FPENSION_MONTH, FPENSION_YEAR, FPENSION_TYPE,
               FPENSION_AMT, RELIEF, GRATUITY_AMT, BILL_NO, EMP_CD,
               CLMCA_ID, SL_NO, BANK_CD, LIC_BANK_CD, CPI_NO
        FROM fi_pn_th_first_month_fpension
        WHERE CLMCA_ID = %s
        ORDER BY FPENSION_YEAR DESC, FPENSION_MONTH DESC, DATE_CREATED DESC
        LIMIT 1
        """,
        [claim_id],
    )


def _pension_from_td(lines: list[dict]) -> float:
    return sum(_line_monthly_amt(ln) for ln in lines if _is_pension_line(ln))


def _relief_from_td(lines: list[dict]) -> float:
    return sum(_line_monthly_amt(ln) for ln in lines if _is_relief_line(ln))


def _sync_pension_bill_totals(cur, bill_no: str, fam_id: str | None = None):
    """Refresh bill header totals — all TH rows on bill_no (Oracle claim-level sum)."""
    _ = fam_id  # kept for callers; totals are bill-wide not single-row
    bno = _clip(bill_no, 22)
    if not bno:
        return
    earn, dedn = please_sum_family_for_bill(bno)
    cur.execute(
        """
        UPDATE fi_pn_th_pension_bill
        SET TOTAL_AMT_EARNED = %s, TOTAL_AMT_DEDUCTED = %s
        WHERE BILL_NO = %s
        """,
        [_money(earn), _money(dedn), bno],
    )


def _write_core_monthly_td(
    cur,
    *,
    fam_id: str,
    pension_amount: float,
    pension_original: float,
    relief_amt: float,
    relief_original: float | None = None,
    arrear_amt: float,
    extra_lines: list[dict],
    user: str,
    replace: bool,
):
    relief_orig = (
        float(relief_original)
        if relief_original is not None
        else float(relief_amt)
    )
    th_fp = (
        pension_original
        if pension_original > pension_amount + 0.005
        else pension_amount
    )
    if replace:
        cur.execute(
            """
            DELETE FROM fi_pn_td_first_month_fpension
            WHERE FAM_FMPEN_ID = %s
              AND EARN_DEDN_CD IN ('208', '209', '214', '110', '106')
            """,
            [fam_id],
        )
    _insert_td_line(
        cur,
        fam_id=fam_id,
        earn_type="E",
        earn_cd="209",
        amount=pension_amount,
        original_amt=pension_original,
        user=user,
    )
    if relief_amt > 0.005:
        _insert_td_line(
            cur,
            fam_id=fam_id,
            earn_type="E",
            earn_cd="208",
            amount=relief_amt,
            original_amt=relief_orig,
            user=user,
        )
    if arrear_amt > 0.005:
        _insert_td_line(
            cur,
            fam_id=fam_id,
            earn_type="E",
            earn_cd="214",
            amount=arrear_amt,
            original_amt=arrear_amt,
            user=user,
        )
    for ln in extra_lines:
        cd = _clip(ln.get("earn_dedn_cd"), 10)
        if cd in {"208", "209", "214", "110", "106"}:
            continue
        _insert_td_line(
            cur,
            fam_id=fam_id,
            earn_type=_clip(ln.get("earn_dedn_type"), 1) or "E",
            earn_cd=cd,
            amount=ln.get("_monthly_amt"),
            original_amt=ln.get("_monthly_orig", ln.get("_monthly_amt")),
            user=user,
        )
    cur.execute(
        """
        UPDATE fi_pn_th_first_month_fpension
        SET FPENSION_AMT = %s,
            RELIEF = %s,
            DATE_MODIFIED = NOW(),
            MODIFIED_BY = %s
        WHERE FAM_FMPEN_ID = %s
        """,
        [_money(th_fp), _money(relief_amt), user, fam_id],
    )


def _monthly_build_amounts(claim_id: str, emp: str | None, bill_m: int, bill_y: int, standing: dict | None):
    """
    Regular ongoing monthly (47529): one month pension + current DA (+ 214).
    First monthly after First FP with unpaid months (17663): accrue from WEF
    with current month held up.
    """
    master = _monthly_master(claim_id, emp)
    accrued = _accrued_unpaid_fp(
        claim_id=claim_id, emp=emp, bill_m=bill_m, bill_y=bill_y
    )
    prior = _prior_monthly_row(claim_id, bill_m, bill_y, emp)
    rate = accrued["rate"] or master["pension"]
    as_of = _last_day_of_month(bill_m, bill_y)

    standing_lines = []
    standing_is_regular = False
    if standing:
        standing_lines = [
            ln
            for ln in _load_td_lines(standing["fam_fmpen_id"])
            if not _is_gratuity_line(ln)
        ]
        pen_st = _pension_from_td(standing_lines)
        has_214 = any(_is_arrear_line(ln) for ln in standing_lines)
        standing_is_regular = has_214 or _is_unit_rate(pen_st, rate)

    if prior or standing_is_regular:
        if standing_is_regular:
            fp_amt = _pension_from_td(standing_lines)
            fp_orig = fp_amt
            for ln in standing_lines:
                if _is_pension_line(ln):
                    fp_orig = max(_num(ln.get("original_amt")), _line_monthly_amt(ln), fp_orig)
            relief_amt = _relief_from_td(standing_lines)
            if relief_amt <= 0.005:
                relief_amt = _compute_monthly_relief(fp_amt or rate, claim_id, emp, as_of)
            arrear_amt = sum(
                _line_monthly_amt(ln) for ln in standing_lines if _is_arrear_line(ln)
            )
            extras = standing_lines
            return {
                "fp_amt": fp_amt or rate,
                "fp_orig": fp_orig or fp_amt or rate,
                "relief": relief_amt,
                "arrear": arrear_amt,
                "extras": extras,
                "clone": True,
            }
        relief_amt = _compute_monthly_relief(rate, claim_id, emp, as_of)
        return {
            "fp_amt": rate,
            "fp_orig": rate,
            "relief": relief_amt,
            "arrear": 0.0,
            "extras": [],
            "clone": False,
        }

    if accrued["multi_month"]:
        return {
            "fp_amt": accrued["pension_amount"],
            "fp_orig": accrued["pension_original"],
            "relief": accrued["relief"],
            "relief_original": accrued.get("relief_original", accrued["relief"]),
            "arrear": 0.0,
            "extras": [],
            "clone": False,
        }

    relief_amt = _compute_monthly_relief(rate, claim_id, emp, as_of)
    return {
        "fp_amt": rate,
        "fp_orig": rate,
        "relief": relief_amt,
        "relief_original": relief_amt,
        "arrear": master["arrear"],
        "extras": [],
        "clone": False,
    }


def _complete_monthly_td(
    *,
    row: dict,
    claim_id: str,
    emp: str | None,
    user: str,
) -> dict:
    """Fill or rebuild type-M TD so print matches Oracle monthly/first bill."""
    fam_id = row["fam_fmpen_id"]
    bill_m = int(row.get("fpension_month") or date.today().month)
    bill_y = int(row.get("fpension_year") or date.today().year)
    lines = [ln for ln in _load_td_lines(fam_id) if not _is_gratuity_line(ln)]
    master = _monthly_master(claim_id, emp)
    rate = master["pension"]
    pen_now = _pension_from_td(lines) or _num(row.get("fpension_amt"))
    has_214 = any(_is_arrear_line(ln) for ln in lines)
    prior = _prior_monthly_row(claim_id, bill_m, bill_y, emp)
    accrued = _accrued_unpaid_fp(
        claim_id=claim_id, emp=emp, bill_m=bill_m, bill_y=bill_y
    )

    rebuild = (
        accrued.get("multi_month")
        and not has_214
        and not prior
        and _is_unit_rate(pen_now, rate)
    )
    if not rebuild:
        if _td_has_monthly_relief(lines) or has_214:
            return row
        built = _monthly_build_amounts(
            claim_id,
            emp,
            bill_m,
            bill_y,
            _standing_monthly_source(claim_id, emp),
        )
    else:
        built = {
            "fp_amt": accrued["pension_amount"],
            "fp_orig": accrued["pension_original"],
            "relief": accrued["relief"],
            "relief_original": accrued.get("relief_original", accrued["relief"]),
            "arrear": 0.0,
            "extras": [],
            "clone": False,
        }

    try:
        with transaction.atomic():
            with connection.cursor() as cur:
                _write_core_monthly_td(
                    cur,
                    fam_id=fam_id,
                    pension_amount=built["fp_amt"],
                    pension_original=built["fp_orig"],
                    relief_amt=built["relief"],
                    relief_original=built.get("relief_original"),
                    arrear_amt=built["arrear"],
                    extra_lines=[],
                    user=user,
                    replace=rebuild or True,
                )
                _sync_pension_bill_totals(cur, row.get("bill_no"), fam_id)
    except FirstFamilyPensionError as exc:
        raise FirstFpBillError(str(exc)) from exc

    return _fetchone(
        """
        SELECT FAM_FMPEN_ID, FPENSION_MONTH, FPENSION_YEAR, FPENSION_TYPE,
               FPENSION_AMT, RELIEF, GRATUITY_AMT, BILL_NO, EMP_CD,
               CLMCA_ID, SL_NO, BANK_CD, LIC_BANK_CD
        FROM fi_pn_th_first_month_fpension
        WHERE FAM_FMPEN_ID = %s
        LIMIT 1
        """,
        [fam_id],
    ) or row


def ensure_monthly_fp_row(
    *,
    clmca_id: str,
    emp_cd: str | None,
    month: int,
    year: int,
    user_id: str = "SMPK",
) -> dict:
    """
    Oracle Monthly Bill (TXT_BILL_TYPE = 'M'): type-M TH/TD for this claim
    + month/year.

    Regular monthly (47529) keeps standing 208/209/214. First monthly after
    First FP with unpaid months (17663) accrues pension + DA from WEF and
    holds the current month's rate until month-end.
    """
    claim_id = _clip(clmca_id, 20)
    emp = _emp_key(emp_cd) if emp_cd else None
    user = _clip(user_id, 5) or "SMPK"
    bill_m = int(month)
    bill_y = int(year)

    existing_sql = """
        SELECT FAM_FMPEN_ID, FPENSION_MONTH, FPENSION_YEAR, FPENSION_TYPE,
               FPENSION_AMT, RELIEF, GRATUITY_AMT, BILL_NO, EMP_CD,
               CLMCA_ID, SL_NO, BANK_CD, LIC_BANK_CD
        FROM fi_pn_th_first_month_fpension
        WHERE CLMCA_ID = %s
          AND FPENSION_TYPE = 'M'
          AND FPENSION_MONTH = %s
          AND FPENSION_YEAR = %s
    """
    params = [claim_id, bill_m, bill_y]
    if emp:
        existing_sql += " AND EMP_CD = %s"
        params.append(emp)
    existing_sql += " ORDER BY SL_NO, FAM_FMPEN_ID LIMIT 1"
    existing = _fetchone(existing_sql, params)
    if existing:
        return _complete_monthly_td(
            row=existing, claim_id=claim_id, emp=emp, user=user
        )

    standing = _standing_monthly_source(claim_id, emp)
    first = _first_fp_source(claim_id, emp)
    source = standing or first or _header_source(claim_id, emp)
    if not source:
        raise FirstFpBillError(
            "No First Family Pension found for this claim. "
            "Run Generate First FP before Monthly Bill."
        )

    built = _monthly_build_amounts(claim_id, emp, bill_m, bill_y, standing)
    extras = []
    if built.get("clone"):
        extras = built.get("extras") or []
        for ln in extras:
            ln["_monthly_amt"] = _line_monthly_amt(ln)
            orig = _num(ln.get("original_amt"))
            ln["_monthly_orig"] = orig if orig > 0.005 else ln["_monthly_amt"]
    else:
        n_src = first or source
        n_lines = [
            ln
            for ln in _load_td_lines(n_src["fam_fmpen_id"])
            if not _is_gratuity_line(ln)
        ]
        for ln in n_lines:
            if _is_pension_line(ln) or _is_relief_line(ln) or _is_arrear_line(ln):
                continue
            ln["_monthly_amt"] = _line_monthly_amt(ln)
            extras.append(ln)

    try:
        with transaction.atomic():
            with connection.cursor() as cur:
                fam_id = _allocate_fpen_id(cur, "M")
                cur.execute(
                    """
                    INSERT INTO fi_pn_th_first_month_fpension (
                        FAM_FMPEN_ID, FPENSION_MONTH, FPENSION_YEAR, FPENSION_TYPE,
                        FPENSION_AMT, RELIEF, GRATUITY_AMT,
                        PAID_MONTH, PAID_YR,
                        DATE_CREATED, CREATED_BY,
                        CLMCA_ID, SL_NO, BANK_CD,
                        FPEN_PROC_TAG, CPI_NO, EMP_CD, LIC_BANK_CD
                    ) VALUES (
                        %s, %s, %s, 'M',
                        %s, %s, 0,
                        0, 0,
                        NOW(), %s,
                        %s, %s, %s,
                        'P', %s, %s, %s
                    )
                    """,
                    [
                        fam_id,
                        bill_m,
                        bill_y,
                        _money(built["fp_amt"]),
                        _money(built["relief"]),
                        user,
                        claim_id,
                        source.get("sl_no") or 1,
                        _clip(source.get("bank_cd"), 6) or None,
                        source.get("cpi_no"),
                        _emp_key(source.get("emp_cd") or emp),
                        _clip(source.get("lic_bank_cd"), 6) or None,
                    ],
                )
                _write_core_monthly_td(
                    cur,
                    fam_id=fam_id,
                    pension_amount=built["fp_amt"],
                    pension_original=built["fp_orig"],
                    relief_amt=built["relief"],
                    relief_original=built.get("relief_original"),
                    arrear_amt=built["arrear"],
                    extra_lines=extras,
                    user=user,
                    replace=False,
                )
    except FirstFamilyPensionError as exc:
        raise FirstFpBillError(str(exc)) from exc

    created = _fetchone(
        """
        SELECT FAM_FMPEN_ID, FPENSION_MONTH, FPENSION_YEAR, FPENSION_TYPE,
               FPENSION_AMT, RELIEF, GRATUITY_AMT, BILL_NO, EMP_CD,
               CLMCA_ID, SL_NO, BANK_CD, LIC_BANK_CD
        FROM fi_pn_th_first_month_fpension
        WHERE FAM_FMPEN_ID = %s
        LIMIT 1
        """,
        [fam_id],
    )
    return created or {"fam_fmpen_id": fam_id}


def _load_type_n_rows(claim_id: str, emp: str | None, regenerate: bool) -> list[dict]:
    params = [_clip(claim_id, 20)]
    sql = """
        SELECT FAM_FMPEN_ID, FPENSION_MONTH, FPENSION_YEAR, FPENSION_TYPE,
               FPENSION_AMT, RELIEF, GRATUITY_AMT, BILL_NO, EMP_CD,
               CLMCA_ID, SL_NO, BANK_CD, LIC_BANK_CD
        FROM fi_pn_th_first_month_fpension
        WHERE CLMCA_ID = %s
          AND FPENSION_TYPE = 'N'
    """
    if emp:
        sql += " AND EMP_CD = %s"
        params.append(emp)
    if not regenerate:
        sql += " AND (BILL_NO IS NULL OR BILL_NO = '')"
    sql += " ORDER BY SL_NO, FAM_FMPEN_ID"
    return _fetchall(sql, params)


def apply_first_fp_disbursement(
    *,
    clmca_id: str,
    emp_cd: str | None,
    month: int,
    year: int,
    user_id: str = "SMPK",
    regenerate: bool = False,
) -> list[dict]:
    """
    First Family Pension disbursement.

    Generate First FP only stores the monthly *rate*. Claims take time to
    initiate / validate / process, so the first PFN (type N) is raised in a
    later month and must include family pension + DA from WEF through the
    previous month, with the disbursement month held until month-end.
    """
    claim_id = _clip(clmca_id, 20)
    emp = _emp_key(emp_cd) if emp_cd else None
    user = _clip(user_id, 5) or "SMPK"
    bill_m = int(month)
    bill_y = int(year)
    rows = _load_type_n_rows(claim_id, emp, regenerate=regenerate)
    if not rows:
        return []

    accrued = _accrued_unpaid_fp(
        claim_id=claim_id, emp=emp, bill_m=bill_m, bill_y=bill_y
    )
    if not accrued.get("multi_month"):
        return rows

    out = []
    try:
        with transaction.atomic():
            with connection.cursor() as cur:
                for r in rows:
                    if r.get("bill_no") and not regenerate:
                        out.append(r)
                        continue
                    fam_id = r["fam_fmpen_id"]
                    cur.execute(
                        """
                        UPDATE fi_pn_th_first_month_fpension
                        SET FPENSION_MONTH = %s,
                            FPENSION_YEAR = %s,
                            DATE_MODIFIED = NOW(),
                            MODIFIED_BY = %s
                        WHERE FAM_FMPEN_ID = %s
                        """,
                        [bill_m, bill_y, user, fam_id],
                    )
                    _write_core_monthly_td(
                        cur,
                        fam_id=fam_id,
                        pension_amount=accrued["pension_amount"],
                        pension_original=accrued["pension_original"],
                        relief_amt=accrued["relief"],
                        relief_original=accrued.get("relief_original"),
                        arrear_amt=0.0,
                        extra_lines=[],
                        user=user,
                        replace=True,
                    )
                    _sync_pension_bill_totals(cur, r.get("bill_no"), fam_id)
                    updated = _fetchone(
                        """
                        SELECT FAM_FMPEN_ID, FPENSION_MONTH, FPENSION_YEAR,
                               FPENSION_TYPE, FPENSION_AMT, RELIEF, GRATUITY_AMT,
                               BILL_NO, EMP_CD, CLMCA_ID, SL_NO, BANK_CD, LIC_BANK_CD
                        FROM fi_pn_th_first_month_fpension
                        WHERE FAM_FMPEN_ID = %s
                        LIMIT 1
                        """,
                        [fam_id],
                    )
                    out.append(updated or r)
    except FirstFamilyPensionError as exc:
        raise FirstFpBillError(str(exc)) from exc
    return out


def generate_first_fp_bill(
    *,
    clmca_id: str,
    emp_cd: str | None = None,
    bill_type: str = "N",
    month: int | None = None,
    year: int | None = None,
    user_id: str = "SMPK",
    regenerate: bool = False,
    bank_cd: str = "NOBANK",
) -> dict:
    """
    Generate PFN bill for one claim.

    bill_type N = First Family Pension Bill (disbursement).
      Generate First FP stores the monthly rate; this bill pays the unpaid
      period from WEF through the disbursement month (processing delay),
      holding the current month until month-end.

    bill_type M = later monthly bills after first disbursement.
    """
    claim_id = _clip(clmca_id, 20)
    if not claim_id:
        raise FirstFpBillError("clmca_id is required")

    bt = (_clip(bill_type, 1) or "N").upper()
    bill_m_in = _int_or_none(month)
    bill_y_in = _int_or_none(year)

    today = date.today()
    if bt == "N":
        bill_m_in = bill_m_in or today.month
        bill_y_in = bill_y_in or today.year
        apply_first_fp_disbursement(
            clmca_id=claim_id,
            emp_cd=emp_cd,
            month=bill_m_in,
            year=bill_y_in,
            user_id=user_id,
            regenerate=regenerate,
        )

    if bt == "M":
        bill_m_in = bill_m_in or today.month
        bill_y_in = bill_y_in or today.year
        ensure_monthly_fp_row(
            clmca_id=claim_id,
            emp_cd=emp_cd,
            month=bill_m_in,
            year=bill_y_in,
            user_id=user_id,
        )

    rows = _load_rows_for_bill(
        clmca_id=claim_id,
        emp_cd=emp_cd,
        bill_type=bt,
        month=None if bt == "N" else bill_m_in,
        year=None if bt == "N" else bill_y_in,
        regenerate=regenerate,
    )
    if not rows:
        kind_label = (
            "Monthly Family Pension" if bt == "M" else "First Family Pension"
        )
        already_label = "Monthly FP" if bt == "M" else "First FP"
        any_fp = _fetchone(
            """
            SELECT COUNT(*) AS cnt
            FROM fi_pn_th_first_month_fpension
            WHERE CLMCA_ID = %s AND FPENSION_TYPE = %s
            """,
            [claim_id, bt],
        )
        if int((any_fp or {}).get("cnt") or 0) == 0:
            raise FirstFpBillError(
                f"No {kind_label} found for this claim. "
                + (
                    "Run Generate First FP before Monthly Bill."
                    if bt == "M"
                    else "Run Generate First FP before Bill Generation."
                )
            )
        if not regenerate:
            billed_sql = """
                SELECT FAM_FMPEN_ID, BILL_NO, FPENSION_MONTH, FPENSION_YEAR
                FROM fi_pn_th_first_month_fpension
                WHERE CLMCA_ID = %s AND FPENSION_TYPE = %s
                  AND BILL_NO IS NOT NULL AND BILL_NO <> ''
            """
            billed_params = [claim_id, bt]
            if bt != "N" and bill_m_in and bill_y_in:
                billed_sql += " AND FPENSION_MONTH = %s AND FPENSION_YEAR = %s"
                billed_params.extend([bill_m_in, bill_y_in])
            billed_sql += " ORDER BY SL_NO"
            billed = _fetchall(billed_sql, billed_params)
            raise FirstFpBillError(
                f"{already_label} already billed for this claim "
                f"(bill {billed[0].get('bill_no') if billed else '—'}). "
                "Pass regenerate=true to replace and issue a new PFN bill."
            )
        raise FirstFpBillError(f"No family pension rows to bill (type {bt})")

    # Prefer month/year already resolved (Monthly) else row / today
    bill_m = int(bill_m_in or rows[0].get("fpension_month") or date.today().month)
    bill_y = int(bill_y_in or rows[0].get("fpension_year") or date.today().year)

    if _bill_period_closed(bt, bill_m, bill_y):
        raise FirstFpBillError(
            f"Bill period {bill_m:02d}/{bill_y} (type {bt}) is closed — "
            "no further generation allowed"
        )

    emp = _emp_key(emp_cd or rows[0].get("emp_cd"))
    user = _clip(user_id, 5) or "SMPK"
    bank = None if bt == "F" else (_clip(bank_cd, 6) or "NOBANK")

    total_earn = 0.0
    total_dedn = 0.0
    lined = []
    gen_lic = "G"

    for r in rows:
        fam_id = r["fam_fmpen_id"]
        earn, dedn = _sum_first_month_earn_dedn(fam_id, bill_type=bt)
        if r.get("lic_bank_cd"):
            gen_lic = "L"
        lined.append(
            {
                "fam_fmpen_id": fam_id,
                "sl_no": r.get("sl_no"),
                "earn": earn,
                "dedn": dedn,
                "prior_bill_no": r.get("bill_no"),
            }
        )

    # Oracle Please_Sum_Family — claim + period (all SL_NO / FAM_FMPEN_ID rows)
    total_earn, total_dedn = please_sum_family(claim_id, bt, bill_m, bill_y)

    with transaction.atomic():
        with connection.cursor() as cur:
            # If regenerating: clear BILL_NO on these rows (and optionally remove orphan header)
            if regenerate:
                old_bills = {
                    str(r.get("bill_no")).strip()
                    for r in rows
                    if r.get("bill_no")
                }
                for old in old_bills:
                    # Only delete header if no other TH still points at it
                    cur.execute(
                        """
                        SELECT COUNT(*) FROM fi_pn_th_first_month_fpension
                        WHERE BILL_NO = %s AND CLMCA_ID <> %s
                        """,
                        [old, claim_id],
                    )
                    others = int(cur.fetchone()[0] or 0)
                    if others == 0:
                        cur.execute(
                            "DELETE FROM fi_pn_th_pension_bill WHERE BILL_NO = %s",
                            [old],
                        )
                for r in rows:
                    cur.execute(
                        """
                        UPDATE fi_pn_th_first_month_fpension
                        SET BILL_NO = NULL
                        WHERE FAM_FMPEN_ID = %s
                        """,
                        [r["fam_fmpen_id"]],
                    )

            bill_no = _allocate_pfn_bill_no(cur, bill_m, bill_y)

            for r in rows:
                cur.execute(
                    """
                    UPDATE fi_pn_th_first_month_fpension
                    SET BILL_NO = %s,
                        DATE_MODIFIED = NOW(),
                        MODIFIED_BY = %s
                    WHERE FAM_FMPEN_ID = %s
                    """,
                    [bill_no, user, r["fam_fmpen_id"]],
                )

            cur.execute(
                """
                INSERT INTO fi_pn_th_pension_bill (
                    BILL_NO, BILL_TYPE, BILL_MONTH, BILL_YR,
                    BANK_CD, TOTAL_AMT_EARNED, TOTAL_AMT_DEDUCTED,
                    DATE_CREATED, CREATED_BY, GEN_LIC_TAG, POSTED
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    NOW(), %s, %s, 'N'
                )
                """,
                [
                    bill_no,
                    bt,
                    bill_m,
                    bill_y,
                    bank,
                    _money(total_earn),
                    _money(total_dedn),
                    user,
                    gen_lic,
                ],
            )

            _mark_pmthsetup_processed(cur, bt, bill_m, bill_y)

    print_ctx = _build_print_context(
        clmca_id=claim_id,
        emp_cd=emp,
        bill_no=bill_no,
        bill_m=bill_m,
        bill_y=bill_y,
        rows=rows,
        total_earn=total_earn,
        total_dedn=total_dedn,
    )

    return {
        "ok": True,
        "message": (
            "Monthly Family Pension bill generated successfully"
            if bt == "M"
            else "First Family Pension bill generated successfully"
        ),
        "bill_no": bill_no,
        "bill_type": bt,
        "bill_month": bill_m,
        "bill_year": bill_y,
        "bank_cd": bank,
        "clmca_id": claim_id,
        "emp_cd": emp,
        "total_amt_earned": _money(total_earn),
        "total_amt_deducted": _money(total_dedn),
        "gen_lic_tag": gen_lic,
        "lines": lined,
        "regenerate": regenerate,
        "print": print_ctx,
    }


def load_first_fp_bill_print(
    *,
    bill_no: str | None = None,
    clmca_id: str | None = None,
    emp_cd: str | None = None,
    bill_type: str | None = None,
    month: int | None = None,
    year: int | None = None,
    gen_lic_tag: str | None = None,
    print_style: str | None = None,
) -> dict:
    """
    Oracle FI_PN_FPENBILL_GEN / FI_PN_FPENBILL_LIC: load an existing PFN bill
    and build print payload.

    Prefer bill_no; else latest billed first-month row(s) for claim or emp.
    Filter by bill_type (N/M) and optional month/year so Monthly does not
    hide First Bill (and vice versa).
    gen_lic_tag='L' prefers LIC-tagged bills (First_Fpen_Bill_Report_Lic).
    print_style='lic' shapes print: gratuity+deductions only, held-grat remarks.
    """
    bno = _clip(bill_no, 22)
    claim_id = _clip(clmca_id, 20)
    emp = _emp_key(emp_cd) if emp_cd else ""
    bt = (_clip(bill_type, 1) or "").upper()
    bill_m = _int_or_none(month)
    bill_y = _int_or_none(year)
    lic = (_clip(gen_lic_tag, 1) or "").upper()
    style = (_clip(print_style) or "").lower()
    if not style and lic == "L":
        style = "lic"

    if not bno and not claim_id and not emp:
        raise FirstFpBillError("bill_no, clmca_id, or emp_cd is required")

    if not bno and (claim_id or emp):
        params: list = []
        sql = """
            SELECT t.BILL_NO, t.CLMCA_ID
            FROM fi_pn_th_first_month_fpension t
        """
        if lic in ("L", "G"):
            sql += """
            LEFT JOIN fi_pn_th_pension_bill b ON b.BILL_NO = t.BILL_NO
            """
        sql += """
            WHERE t.BILL_NO IS NOT NULL AND t.BILL_NO <> ''
              AND t.BILL_NO LIKE 'PFN%%'
        """
        if claim_id:
            sql += " AND t.CLMCA_ID = %s"
            params.append(claim_id)
        if emp:
            sql += " AND t.EMP_CD = %s"
            params.append(emp)
        if bt in ("N", "M", "F"):
            sql += " AND t.FPENSION_TYPE = %s"
            params.append(bt)
        if bill_m and bill_y:
            sql += " AND t.FPENSION_MONTH = %s AND t.FPENSION_YEAR = %s"
            params.extend([bill_m, bill_y])
        if lic in ("L", "G"):
            sql += " AND UPPER(COALESCE(b.GEN_LIC_TAG, '')) = %s"
            params.append(lic)
        sql += """
            ORDER BY t.FPENSION_YEAR DESC, t.FPENSION_MONTH DESC, t.DATE_CREATED DESC
            LIMIT 1
        """
        hit = _fetchone(sql, params)
        if not hit or not hit.get("bill_no"):
            # LIC filter may be too strict — retry without tag
            if lic in ("L", "G"):
                return load_first_fp_bill_print(
                    bill_no=None,
                    clmca_id=claim_id or None,
                    emp_cd=emp or None,
                    bill_type=bt or None,
                    month=bill_m,
                    year=bill_y,
                    gen_lic_tag=None,
                    print_style=style or None,
                )
            kind = (
                "Monthly Family Pension"
                if bt == "M"
                else "First Family Pension"
                if bt == "N"
                else "PFN"
            )
            who = (
                f"claim {claim_id}"
                if claim_id
                else f"employee {emp}"
            )
            period = (
                f" for {bill_m:02d}/{bill_y}" if bill_m and bill_y else ""
            )
            raise FirstFpBillError(
                f"No {kind} bill found for this {who}{period}. "
                "Use Bill Generation first, or pass an existing bill_no."
            )
        bno = _clip(hit["bill_no"], 22)
        if not claim_id and hit.get("clmca_id"):
            claim_id = _clip(hit["clmca_id"], 20)

    header = _fetchone(
        """
        SELECT BILL_NO, BILL_TYPE, BILL_MONTH, BILL_YR, BANK_CD,
               TOTAL_AMT_EARNED, TOTAL_AMT_DEDUCTED, GEN_LIC_TAG,
               DATE_CREATED
        FROM fi_pn_th_pension_bill
        WHERE BILL_NO = %s
        LIMIT 1
        """,
        [bno],
    )
    rows = _fetchall(
        """
        SELECT FAM_FMPEN_ID, FPENSION_MONTH, FPENSION_YEAR, FPENSION_TYPE,
               FPENSION_AMT, RELIEF, GRATUITY_AMT, BILL_NO, EMP_CD,
               CLMCA_ID, SL_NO, BANK_CD, LIC_BANK_CD
        FROM fi_pn_th_first_month_fpension
        WHERE BILL_NO = %s
        ORDER BY SL_NO, FAM_FMPEN_ID
        """,
        [bno],
    )
    if not rows and not header:
        raise FirstFpBillError(f"Bill not found: {bno}")

    # If TH not linked but header exists, try claim/month from header alone fails print
    if not rows:
        raise FirstFpBillError(
            f"Bill {bno} has no linked first-month family pension lines"
        )

    claim_id = claim_id or _clip(rows[0].get("clmca_id"), 20)
    emp = _emp_key(emp_cd or rows[0].get("emp_cd"))
    if (bt or rows[0].get("fpension_type") or "") == "M":
        rows = [
            _complete_monthly_td(
                row=r,
                claim_id=claim_id,
                emp=emp,
                user="SMPK",
            )
            if str(r.get("fpension_type") or "").upper() == "M"
            else r
            for r in rows
        ]
    bill_m = int(
        (header or {}).get("bill_month")
        or rows[0].get("fpension_month")
        or date.today().month
    )
    bill_y = int(
        (header or {}).get("bill_yr")
        or rows[0].get("fpension_year")
        or date.today().year
    )

    total_earn = 0.0
    total_dedn = 0.0
    lined = []
    for r in rows:
        earn, dedn = _sum_first_month_earn_dedn(
            r["fam_fmpen_id"],
            bill_type=r.get("fpension_type") or (header or {}).get("bill_type"),
        )
        lined.append(
            {
                "fam_fmpen_id": r["fam_fmpen_id"],
                "sl_no": r.get("sl_no"),
                "earn": earn,
                "dedn": dedn,
            }
        )

    if bno:
        total_earn, total_dedn = please_sum_family_for_bill(bno)
    elif claim_id and rows:
        total_earn, total_dedn = please_sum_family(
            claim_id,
            _clip(rows[0].get("fpension_type") or (header or {}).get("bill_type"), 1)
            or "N",
            bill_m,
            bill_y,
        )

    print_ctx = _build_print_context(
        clmca_id=claim_id,
        emp_cd=emp,
        bill_no=bno,
        bill_m=bill_m,
        bill_y=bill_y,
        rows=rows,
        total_earn=total_earn,
        total_dedn=total_dedn,
    )

    # Prefer report bill date from header create date when available
    if header and header.get("date_created"):
        try:
            dc = header["date_created"]
            if isinstance(dc, datetime):
                print_ctx["bill_date"] = _fmt_bill_date(dc.date())
            elif isinstance(dc, date):
                print_ctx["bill_date"] = _fmt_bill_date(dc)
        except Exception:
            pass

    if style == "lic":
        print_ctx = _shape_lic_print(print_ctx)

    return {
        "ok": True,
        "bill_no": bno,
        "bill_type": (header or {}).get("bill_type") or rows[0].get("fpension_type"),
        "bill_month": bill_m,
        "bill_year": bill_y,
        "bank_cd": (header or {}).get("bank_cd") or rows[0].get("bank_cd"),
        "clmca_id": claim_id,
        "emp_cd": emp,
        "total_amt_earned": print_ctx.get("gross_earn", _money(total_earn)),
        "total_amt_deducted": print_ctx.get("gross_dedn", _money(total_dedn)),
        "gen_lic_tag": (header or {}).get("gen_lic_tag") or "G",
        "print_style": style or "gen",
        "lines": lined,
        "print": print_ctx,
        "source": "existing",
    }
