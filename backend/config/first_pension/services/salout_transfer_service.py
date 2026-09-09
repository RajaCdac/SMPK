"""
PR → PN salout transfer (Oracle Forms BLKCT_CNTL payroll-to-pension block).

Reads last 10 months of payroll from FI_PR_*_SALOUT (from proposal start date),
overrides basic from FI_XX_MD_FINSCALE, writes FI_PN_*_SALOUT mirrors in MySQL.
"""

from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone

from employee.services.oracle_service import (
    get_oracle_connection,
    oracle_reads_enabled,
    try_oracle_connection,
)

from ..models import PensionCase, PensionProposal
from ..oracle_mirror import (
    FiPnMhPensionProposal,
    FiPnTdSalout,
    FiPnThSalout,
)
from .da_rate_service import lookup_ada_da_percent


class SaloutTransferError(Exception):
    pass


def _clip_emp(emp_cd):
    return str(emp_cd).strip()[:5]


def _resolve_pension_start(emp_cd):
    """start_month / start_yr from proposal (SMPK or Oracle mirror), else separation."""
    emp_key = _clip_emp(emp_cd)
    proposal = PensionProposal.objects.filter(emp_cd=emp_key).first()
    if not proposal and emp_key.isdigit():
        proposal = PensionProposal.objects.filter(emp_cd=str(int(emp_key))).first()
    if proposal and proposal.start_month and proposal.start_year:
        return int(proposal.start_month), int(proposal.start_year)

    mirror = FiPnMhPensionProposal.objects.filter(emp_cd=emp_key).first()
    if mirror and mirror.start_month and mirror.start_yr:
        return int(mirror.start_month), int(mirror.start_yr)

    case = PensionCase.objects.filter(emp_code=emp_key).first()
    if not case and emp_key.isdigit():
        case = PensionCase.objects.filter(emp_code=str(int(emp_key))).first()
    ref = case.separation_date or case.retirement_date if case else None
    if ref:
        return int(ref.month), int(ref.year)

    raise SaloutTransferError(
        "Pension start month/year not found. Save pension proposal with start date first."
    )


def _salary_month_date(sal_mth, sal_yr):
    return date(int(sal_yr), int(sal_mth), 1)


def _resolve_month_basic(fin_basic, pr_header_basic, pr_td_net):
    """
    Oracle uses finscale at transfer time. When a higher finscale sl_no was added
    after the payroll bill (e.g. pay revision), use the drawn payroll basic.
    """
    fin = Decimal(str(fin_basic or 0))
    pr_hdr = Decimal(str(pr_header_basic or 0))
    pr_td = Decimal(str(pr_td_net or 0))
    pr_drawn = pr_hdr if pr_hdr > 0 else pr_td

    if pr_drawn <= 0 and fin > 0:
        return pr_drawn
    if pr_drawn <= 0:
        return Decimal("0")
    if pr_drawn > 0 and fin > pr_drawn:
        return pr_drawn
    return fin


def _finscale_basic(cur, emp_cd, sal_mth, sal_yr):
    sal_dt = f"01-{int(sal_mth)}-{int(sal_yr)}"
    cur.execute(
        """
        SELECT BASIC_AMT, SCALE_SL FROM FINANCE.FI_XX_MD_FINSCALE
        WHERE EMP_CD = :emp
          AND WEF_DT = (
            SELECT MAX(WEF_DT) FROM FINANCE.FI_XX_MD_FINSCALE
            WHERE EMP_CD = :emp
              AND WEF_DT <= TO_DATE(:sal_dt, 'DD-MM-YYYY')
              AND TO_DATE(:sal_dt, 'DD-MM-YYYY') <= TRUNC(SYSDATE)
          )
          AND SL_NO = (
            SELECT MAX(SL_NO) FROM FINANCE.FI_XX_MD_FINSCALE
            WHERE EMP_CD = :emp
              AND WEF_DT = (
                SELECT MAX(WEF_DT) FROM FINANCE.FI_XX_MD_FINSCALE
                WHERE EMP_CD = :emp
                  AND WEF_DT <= TO_DATE(:sal_dt, 'DD-MM-YYYY')
                  AND TO_DATE(:sal_dt, 'DD-MM-YYYY') <= TRUNC(SYSDATE)
              )
          )
        """,
        {"emp": emp_cd, "sal_dt": sal_dt},
    )
    row = cur.fetchone()
    if not row:
        return Decimal("0"), ""
    basic = Decimal(str(row[0] or 0))
    scale = str(row[1] or "").strip()
    return basic, scale


def _pr_td_basic_line(cur, emp_cd, sal_mth, sal_yr):
    cur.execute(
        """
        SELECT EMP_CD, SAL_MTH, SAL_YR, EARNDEDN_CD, EARNDEDN_TYPE,
               NO_OF_UNITS, RATE, RATE_PCT_FLG, ACT_EARNDEDN_AMT,
               ADJ_EARNDEDN_AMT, ARR_EARN_AMT
        FROM FINANCE.FI_PR_TD_SALOUT
        WHERE EMP_CD = :emp AND SAL_MTH = :mth AND SAL_YR = :yr
          AND EARNDEDN_CD = '001'
        """,
        {"emp": emp_cd, "mth": sal_mth, "yr": sal_yr},
    )
    return cur.fetchone()


def _resolve_emp_class(emp_cd):
    emp_key = _clip_emp(emp_cd)
    case = PensionCase.objects.filter(emp_code=emp_key).first()
    if not case and emp_key.isdigit():
        case = PensionCase.objects.filter(emp_code=str(int(emp_key))).first()
    return (case.emp_class if case else None) or "III"


def _oracle_pr_headers(cur, emp_cd, window_start, pension_start):
    cur.execute(
        """
        SELECT EMP_CD, SAL_MTH, SAL_YR, FA_NO, SAL_BILL_NO, GROSS_EARN_AMT,
               GROSS_DEDN_AMT, NET_EARN_AMT, SCALE_DESC, BASIC_RATE,
               WG_ST_DT, WG_END_DT, DATE_CREATED, DATE_MODIFIED,
               MODIFIED_BY, CREATED_BY
        FROM FINANCE.FI_PR_TH_SALOUT
        WHERE EMP_CD = :emp
          AND TO_DATE(
                '01/' || LPAD(SAL_MTH, 2, '0') || '/' || LPAD(SAL_YR, 4, '0'),
                'DD/MM/RRRR'
              ) >= :window_start
          AND TO_DATE(
                '01/' || LPAD(SAL_MTH, 2, '0') || '/' || LPAD(SAL_YR, 4, '0'),
                'DD/MM/RRRR'
              ) < :pension_start
        ORDER BY SAL_YR, SAL_MTH
        """,
        {
            "emp": emp_cd,
            "window_start": window_start,
            "pension_start": pension_start,
        },
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _as_date(val):
    if val is None:
        return None
    if isinstance(val, date):
        return val
    return val.date() if hasattr(val, "date") else val


@transaction.atomic
def _persist_salout(emp_cd, headers, td_rows, th_rows):
    FiPnTdSalout.objects.filter(emp_cd=emp_cd).delete()
    FiPnThSalout.objects.filter(emp_cd=emp_cd).delete()

    if th_rows:
        FiPnThSalout.objects.bulk_create(
            [FiPnThSalout(**row) for row in th_rows]
        )
    if td_rows:
        FiPnTdSalout.objects.bulk_create(
            [FiPnTdSalout(**row) for row in td_rows]
        )


def transfer_payroll_salout_to_pension(emp_cd, *, user_code=""):
    """
    Copy payroll salout (FI_PR_*) into pension salout mirrors (fi_pn_*_salout).

    Returns summary dict with month count and last drawn basic.
    """
    emp_key = _clip_emp(emp_cd)
    start_mth, start_yr = _resolve_pension_start(emp_key)
    pension_start = date(start_yr, start_mth, 1)
    window_start = pension_start + relativedelta(months=-10)
    pension_start_minus_one = pension_start - timedelta(days=1)
    emp_class = _resolve_emp_class(emp_key)

    conn = try_oracle_connection()
    if conn is None:
        if FiPnThSalout.objects.filter(emp_cd=emp_key).exists():
            return get_salout_status(emp_key)
        raise SaloutTransferError(
            "Oracle is unavailable and no pension salout exists in MySQL. "
            "Enable ORACLE_READ_ENABLED to transfer payroll salout, or import salout mirrors."
        )
    cur = conn.cursor()
    try:
        headers = _oracle_pr_headers(cur, emp_key, window_start, pension_start)
        if not headers:
            raise SaloutTransferError(
                "No payroll salout data found for the 10-month pension window."
            )

        th_rows = []
        td_rows = []
        today = timezone.localdate()

        for rec in headers:
            sal_mth = int(rec["SAL_MTH"])
            sal_yr = int(rec["SAL_YR"])
            fin_basic, scale_sl = _finscale_basic(cur, emp_key, sal_mth, sal_yr)
            pr_line = _pr_td_basic_line(cur, emp_key, sal_mth, sal_yr)
            pr_td_net = Decimal("0")
            if pr_line:
                pr_td_net = Decimal(str(pr_line[8] or 0)) + Decimal(
                    str(pr_line[9] or 0)
                )
            month_basic = _resolve_month_basic(
                fin_basic,
                rec.get("BASIC_RATE"),
                pr_td_net,
            )
            if month_basic <= 0:
                continue

            wg_st_dt = _as_date(rec.get("WG_ST_DT"))
            wg_end_dt = _as_date(rec.get("WG_END_DT"))
            date_created = _as_date(rec.get("DATE_CREATED")) or today
            date_modified = _as_date(rec.get("DATE_MODIFIED"))

            th_rows.append(
                {
                    "emp_cd": emp_key,
                    "sal_mth": sal_mth,
                    "sal_yr": sal_yr,
                    "fa_no": str(rec.get("FA_NO") or "")[:10],
                    "sal_bill_no": str(rec.get("SAL_BILL_NO") or "")[:22],
                    "gross_earn_amt": rec.get("GROSS_EARN_AMT"),
                    "gross_dedn_amt": rec.get("GROSS_DEDN_AMT"),
                    "net_earn_amt": rec.get("NET_EARN_AMT"),
                    "scale_desc": (scale_sl or str(rec.get("SCALE_DESC") or ""))[:100],
                    "basic_rate": month_basic,
                    "wg_st_dt": wg_st_dt,
                    "wg_end_dt": wg_end_dt,
                    "date_created": date_created,
                    "date_modified": date_modified,
                    "modified_by": str(rec.get("MODIFIED_BY") or user_code or "")[:5],
                    "created_by": str(rec.get("CREATED_BY") or user_code or "")[:5],
                }
            )

            if not pr_line:
                continue

            td_common = {
                "emp_cd": emp_key,
                "sal_mth": sal_mth,
                "sal_yr": sal_yr,
                "earndedn_type": str(pr_line[4] or "E")[:1],
                "no_of_units": pr_line[5],
                "rate_pct_flg": pr_line[7],
                "adj_earndedn_amt": pr_line[9],
                "arr_earn_amt": pr_line[10],
                "date_created": date_created,
                "date_modified": date_modified,
                "modified_by": str(rec.get("MODIFIED_BY") or user_code or "")[:5],
                "created_by": str(rec.get("CREATED_BY") or user_code or "")[:5],
            }

            td_rows.append(
                {
                    **td_common,
                    "earndedn_cd": "001",
                    "rate": month_basic,
                    "act_earndedn_amt": month_basic,
                    "no_of_units": pr_line[5],
                }
            )

            if (
                wg_end_dt
                and wg_end_dt == pension_start_minus_one
                and month_basic > 0
            ):
                da_pct = lookup_ada_da_percent(wg_end_dt, emp_class)
                if da_pct is not None:
                    da_amt = (month_basic * da_pct / Decimal("100")).quantize(
                        Decimal("0.01")
                    )
                    td_rows.append(
                        {
                            **td_common,
                            "earndedn_cd": "007",
                            "rate": da_amt,
                            "act_earndedn_amt": da_amt,
                            "no_of_units": pr_line[5],
                        }
                    )

        _persist_salout(emp_key, headers, td_rows, th_rows)

        last_row = th_rows[-1] if th_rows else None
        last_basic = float(last_row["basic_rate"]) if last_row else 0.0
        if last_row:
            last_mth, last_yr = int(last_row["sal_mth"]), int(last_row["sal_yr"])
        else:
            last_rec = headers[-1]
            last_mth, last_yr = int(last_rec["SAL_MTH"]), int(last_rec["SAL_YR"])

        return {
            "emp_cd": emp_key,
            "start_month": start_mth,
            "start_year": start_yr,
            "window_start": window_start.isoformat(),
            "pension_start": pension_start.isoformat(),
            "months_transferred": len(th_rows),
            "td_lines": len(td_rows),
            "last_drawn_basic": last_basic,
            "last_salary_month": last_mth,
            "last_salary_year": last_yr,
        }
    finally:
        cur.close()
        conn.close()


def get_salout_status(emp_cd):
    emp_key = _clip_emp(emp_cd)
    pension_start = _pension_start_for_emp(emp_key)
    headers = list(
        _salout_headers_queryset(emp_key, pension_start).order_by("sal_yr", "sal_mth")
    )
    last_basic = get_last_drawn_basic_from_salout(emp_key)
    try:
        start_mth, start_yr = _resolve_pension_start(emp_key)
        window_start = date(start_yr, start_mth, 1) + relativedelta(months=-10)
        start_info = {
            "start_month": start_mth,
            "start_year": start_yr,
            "window_start": window_start.isoformat(),
        }
    except SaloutTransferError:
        start_info = {}

    return {
        "emp_cd": emp_key,
        "has_salout": bool(headers),
        "months_count": len(headers),
        "last_drawn_basic": last_basic,
        "months": [
            {
                "sal_mth": h.sal_mth,
                "sal_yr": h.sal_yr,
                "basic_rate": float(h.basic_rate or 0),
            }
            for h in headers
        ],
        **start_info,
    }


def _pension_start_for_emp(emp_cd):
    try:
        start_mth, start_yr = _resolve_pension_start(emp_cd)
        return date(int(start_yr), int(start_mth), 1)
    except SaloutTransferError:
        return None


def _salout_headers_queryset(emp_cd, pension_start=None):
    qs = FiPnThSalout.objects.filter(emp_cd=_clip_emp(emp_cd))
    if pension_start is None:
        pension_start = _pension_start_for_emp(emp_cd)
    if pension_start:
        qs = qs.exclude(sal_yr__gt=pension_start.year).exclude(
            sal_yr=pension_start.year,
            sal_mth__gte=pension_start.month,
        )
    return qs


def _salout_needs_refresh(emp_cd):
    """Stale salout: months on/after pension start or finscale-only post-separation row."""
    pension_start = _pension_start_for_emp(emp_cd)
    if not pension_start:
        return False
    emp_key = _clip_emp(emp_cd)
    if FiPnThSalout.objects.filter(
        emp_cd=emp_key,
        sal_yr=pension_start.year,
        sal_mth__gte=pension_start.month,
    ).exists():
        return True
    return False


def get_last_drawn_basic_from_salout(emp_cd):
    """
    Last drawn basic = last payroll month before pension start (not finscale / lastpay).
    """
    emp_key = _clip_emp(emp_cd)
    pension_start = _pension_start_for_emp(emp_key)
    header = _salout_headers_queryset(emp_key, pension_start).order_by(
        "-sal_yr", "-sal_mth"
    ).first()
    if header and header.basic_rate is not None and float(header.basic_rate) > 0:
        return float(header.basic_rate)

    line_qs = FiPnTdSalout.objects.filter(emp_cd=emp_key, earndedn_cd="001")
    if pension_start:
        line_qs = line_qs.exclude(sal_yr__gt=pension_start.year).exclude(
            sal_yr=pension_start.year,
            sal_mth__gte=pension_start.month,
        )
    line = line_qs.order_by("-sal_yr", "-sal_mth").first()
    if line:
        net = float(line.act_earndedn_amt or 0) + float(line.adj_earndedn_amt or 0)
        if net:
            return net
        if line.rate is not None:
            return float(line.rate)
    return None


def _as_date_value(value):
    if value is None:
        return None
    if isinstance(value, date) and not hasattr(value, "hour"):
        return value
    if hasattr(value, "date") and callable(value.date):
        try:
            return value.date()
        except Exception:
            pass
    return value


def _emoluments_as_of(emp_cd):
    """
    Last day of service for last-pay / finscale as-on lookup.

    Pension start month (e.g. 01-Jul) → basic as on 30-Jun (last day before start).
    """
    pension_start = _pension_start_for_emp(emp_cd)
    if pension_start:
        return pension_start - timedelta(days=1)
    case = PensionCase.objects.filter(emp_code=_clip_emp(emp_cd)).first()
    if not case and str(emp_cd).strip().isdigit():
        case = PensionCase.objects.filter(emp_code=str(int(str(emp_cd).strip()))).first()
    if case and case.retirement_date:
        return _as_date_value(case.retirement_date) - timedelta(days=1)
    if case and case.separation_date:
        return _as_date_value(case.separation_date) - timedelta(days=1)
    return None


def get_finscale_basic_as_of(emp_cd, as_of=None):
    """
    Latest FI_XX_MD_FINSCALE.BASIC_AMT with WEF on/before as_of
    (e.g. 30-Jun → WEF 01-Jan-2026 for emp who got Jan GI to 158570).
    """
    from datetime import datetime, timezone as dt_tz

    from employee.oracle_mirror import FiXxMdFinscale

    emp_key = _clip_emp(emp_cd)
    qs = FiXxMdFinscale.objects.filter(emp_cd=emp_key)
    as_of = _as_date_value(as_of) if as_of is not None else _emoluments_as_of(emp_key)
    if as_of:
        exclusive_end = datetime(
            as_of.year, as_of.month, as_of.day, tzinfo=dt_tz.utc
        ) + timedelta(days=1)
        # WEF stored as UTC midnight calendar day — avoid __date (TZ bug).
        qs = qs.filter(wef_dt__lt=exclusive_end)

    row = qs.order_by("-wef_dt", "-sl_no").first()
    if not row:
        return None
    if row.basic_amt is not None and float(row.basic_amt) > 0:
        return float(row.basic_amt)
    if row.stag_pay_amt is not None and float(row.stag_pay_amt) > 0:
        return float(row.stag_pay_amt)
    return None


def resolve_emoluments_basic(emp_cd, *, fallback_last_basic=None):
    """
    Pension emoluments (last pay) for calc:

    1. PN salout last drawn month before pension start (actual payroll)
    2. Finscale basic as on day before pension start (covers GI after case was
       opened, e.g. case still has 153950 while finscale is 158570 from 01-Jan)
    3. case.last_basic fallback
    """
    salout_basic = get_last_drawn_basic_from_salout(emp_cd)
    if salout_basic is not None and salout_basic > 0:
        return salout_basic, "salout"

    fin_basic = get_finscale_basic_as_of(emp_cd)
    if fin_basic is not None and fin_basic > 0:
        return fin_basic, "finscale"

    if fallback_last_basic is not None:
        return float(fallback_last_basic), "case_last_basic"
    return 0.0, "none"


def ensure_salout_for_calculation(emp_cd, *, user_code="", force=False):
    """
    Transfer PR→PN salout when missing or stale. Swallows Oracle errors if
    existing salout rows are present.
    """
    emp_key = _clip_emp(emp_cd)
    needs_refresh = _salout_needs_refresh(emp_key)
    if not force and not needs_refresh and FiPnThSalout.objects.filter(emp_cd=emp_key).exists():
        return get_salout_status(emp_key)

    try:
        return transfer_payroll_salout_to_pension(
            emp_key, user_code=user_code
        )
    except SaloutTransferError:
        raise
    except Exception as exc:
        if FiPnThSalout.objects.filter(emp_cd=emp_key).exists():
            return get_salout_status(emp_key)
        raise SaloutTransferError(f"Salout transfer failed: {exc}") from exc
