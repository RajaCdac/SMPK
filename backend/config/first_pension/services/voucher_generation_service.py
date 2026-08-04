"""
Journal voucher generation — port of FI_PN_VOUCHER_GENRATION_INTERM.fmb (PPN / Voucher_First_Pension_Bill).
MySQL writes only; Oracle is not updated.
"""

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from master_data.models import (
    FiPnMdJrnltype,
    FiPnMhEarndedn,
    FiPnMhErndednmap,
    FiPnMhJrnltype,
    FiXxXxMDFinCtrl,
)
from master_data.services.fin_year_service import fin_year_for_date

from ..oracle_mirror import (
    FiPnMhPensioner,
    FiPnTdFirstMonthPension,
    FiPnTdJv,
    FiPnThFirstMonthPension,
    FiPnThJv,
    FiPnThPensionBill,
)


from .journal_narration_service import build_default_journal_narration


class VoucherGenerationError(Exception):
    pass


DOC_ABV_PNJV = "PNJV"
TRAN_TYPE_PPN = "PNJV/P"
MAP_CD_BALANCE = 112
LIC_EXCLUDED_EARN = frozenset({"200", "202", "208", "210"})
LIC_GRAT_EARN = frozenset({"205", "201"})
LIC_COMM_EARN = frozenset({"203"})


def _user_code(user):
    if not user or not getattr(user, "is_authenticated", False):
        return "A0001"
    return str(getattr(user, "username", None) or "A0001").strip()[:5].upper() or "A0001"


def _clip(value, max_len, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return text[:max_len]


def _dec(value):
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _resolve_fin_year_for_jv_month(jv_month, jv_year):
    if jv_month == 12:
        last_day = date(int(jv_year), 12, 31)
    else:
        from calendar import monthrange

        last_day = date(int(jv_year), int(jv_month), monthrange(int(jv_year), int(jv_month))[1])
    fin_yr = fin_year_for_date(last_day)
    if fin_yr is not None:
        return fin_yr
    raise VoucherGenerationError(
        f"No active financial year for JV month {int(jv_month):02d}/{int(jv_year)}."
    )


def _calendar_fin_year_for_alloc(ref_date):
    """M_FinYear in Oracle Forms — used when ALOC_CD2 is '000'."""
    dt = ref_date or timezone.localdate()
    month = dt.month if hasattr(dt, "month") else int(dt)
    year = dt.year if hasattr(dt, "year") else int(dt)
    return year - 1 if month < 4 else year


def _ensure_pnjv_fin_ctrl(fin_yr, user_code, today):
    ctrl, _created = FiXxXxMDFinCtrl.objects.get_or_create(
        fin_yr=fin_yr,
        doc_abv=DOC_ABV_PNJV,
        defaults={
            "doc_desc": "PENSION JOURNAL VOUCHER",
            "l_trn_no": 0,
            "created_by": user_code,
            "created_on": today,
        },
    )
    return ctrl


def _allocate_pnjv_serial(fin_yr, user_code, today):
    _ensure_pnjv_fin_ctrl(fin_yr, user_code, today)
    try:
        ctrl = FiXxXxMDFinCtrl.objects.select_for_update().get(
            fin_yr=fin_yr,
            doc_abv=DOC_ABV_PNJV,
        )
    except FiXxXxMDFinCtrl.DoesNotExist as exc:
        raise VoucherGenerationError(
            f"FIN_CTRL row missing for DOC_ABV={DOC_ABV_PNJV}, FIN_YR={fin_yr}."
        ) from exc
    serial = int(ctrl.l_trn_no or 0) + 1
    ctrl.l_trn_no = serial
    ctrl.save(update_fields=["l_trn_no"])
    return serial


def _format_voucher_no(fin_yr, jv_month, serial):
    return f"PNJV/{int(fin_yr)}/{int(jv_month)}/{int(serial):05d}"


def _normalize_zonal(zonal_cd):
    z = int(zonal_cd or 0)
    return 30 if z == 11 else z


def _earn_account(earn_cd):
    row = FiPnMhEarndedn.objects.filter(earndedn_cd=_clip(earn_cd, 3)).first()
    if not row or row.zonal_cd is None:
        raise VoucherGenerationError(
            f"Earn/dedn {earn_cd} has no zonal/allocation in MySQL. "
            "Run: python manage.py sync_voucher_masters_from_oracle"
        )
    return int(row.zonal_cd), _clip(row.alloc_cd, 4)


def _deduction_earn_codes():
    codes = list(
        FiPnMhErndednmap.objects.filter(e_d_type="D")
        .values_list("earndedn_cd", flat=True)
        .distinct()
    )
    if codes:
        return codes
    from employee.services.oracle_service import get_oracle_connection

    with get_oracle_connection().cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT EARNDEDN_CD
            FROM FINANCE.FI_PN_MH_ERNDEDNMAP
            WHERE E_D_TYPE = 'D'
            """
        )
        return [_clip(r[0], 3) for r in cursor.fetchall() if r[0]]


def _jrnl_md_match(*, bill_type, zonal_cd, alloc_cd1, dr_cr):
    jrnal = FiPnMhJrnltype.objects.filter(type=_clip(bill_type, 6)).first()
    if not jrnal:
        raise VoucherGenerationError(f"Journal type {bill_type} not found in MySQL.")

    rows = FiPnMdJrnltype.objects.filter(
        jrnal_srl_no=jrnal.jrnal_srl_no,
        zonal_cd=int(zonal_cd),
        aloc_cd1=_clip(alloc_cd1, 4),
        dr_cr_flg=_clip(dr_cr, 1),
    )
    row = rows.first()
    if not row:
        raise VoucherGenerationError(
            f"No journal allocation for type={bill_type}, zonal={zonal_cd}, "
            f"alloc={alloc_cd1}, dr_cr={dr_cr}."
        )
    return row


def _lic_alloc_decode(earn_cd, alloc_cd1, alloc_cd3, fin_year_label):
    cd1 = int(alloc_cd1) if str(alloc_cd1).isdigit() else alloc_cd1
    if earn_cd in LIC_GRAT_EARN and cd1 == 120:
        cd1 = 121
    if earn_cd in LIC_COMM_EARN and cd1 == 123:
        cd1 = 121
    cd2 = str(fin_year_label)
    cd3 = alloc_cd3
    if str(alloc_cd3) in ("0", "000"):
        if earn_cd in LIC_GRAT_EARN:
            cd3 = "576"
        elif earn_cd in LIC_COMM_EARN:
            cd3 = "575"
    return str(cd1), cd2, str(cd3)


def _add_group(groups, *, dr_cr, zonal_cd, aloc_cd1, aloc_cd2, aloc_cd3, amount):
    if not amount:
        return
    key = (
        dr_cr,
        int(zonal_cd),
        _clip(aloc_cd1, 4),
        _clip(aloc_cd2, 4),
        _clip(aloc_cd3, 7),
    )
    groups[key] += _dec(amount)


def _build_ppn_jv_groups(bill, *, jv_month, jv_year):
    bill_type = _clip(bill.bill_no, 3)[:3] or "PPN"
    fin_year_label = _calendar_fin_year_for_alloc(
        date(int(jv_year), int(jv_month), 1)
    )
    groups = defaultdict(lambda: Decimal("0"))
    dedn_codes = set(_deduction_earn_codes())

    headers = FiPnThFirstMonthPension.objects.filter(bill_no=bill.bill_no)
    for header in headers:
        pensioner = FiPnMhPensioner.objects.filter(ca_number=header.ca_no).first()
        lic = bool(
            str(header.lic_bank_cd or "").strip()
            or (pensioner and str(pensioner.lic_bank_cd or "").strip())
        )

        lines = FiPnTdFirstMonthPension.objects.filter(fmpen_id=header.fmpen_id)
        for line in lines:
            earn_cd = _clip(line.earn_dedn_cd, 3)
            amt = _dec(line.amount)
            if not amt:
                continue

            if lic:
                if earn_cd in LIC_EXCLUDED_EARN:
                    continue
                if line.earn_dedn_type == "E":
                    if earn_cd not in LIC_GRAT_EARN | LIC_COMM_EARN:
                        continue
                if line.earn_dedn_type == "D" and earn_cd not in dedn_codes:
                    continue

            zonal_raw, alloc_raw = _earn_account(earn_cd)
            md = _jrnl_md_match(
                bill_type=bill_type,
                zonal_cd=zonal_raw,
                alloc_cd1=alloc_raw,
                dr_cr="D" if line.earn_dedn_type == "E" else "C",
            )
            zonal = _normalize_zonal(zonal_raw)
            aloc1, aloc2, aloc3 = md.aloc_cd1, md.aloc_cd2, md.aloc_cd3

            if lic and line.earn_dedn_type == "E":
                aloc1, aloc2, aloc3 = _lic_alloc_decode(
                    earn_cd, aloc1, aloc3, fin_year_label
                )
            elif str(aloc2) in ("0", "000"):
                aloc2 = str(fin_year_label)
            if str(aloc3) in ("0", "000") and line.earn_dedn_type == "E" and not lic:
                aloc3 = "576" if earn_cd in LIC_GRAT_EARN else aloc3

            dr_cr = md.dr_cr_flg
            _add_group(
                groups,
                dr_cr=dr_cr,
                zonal_cd=zonal,
                aloc_cd1=aloc1,
                aloc_cd2=aloc2,
                aloc_cd3=aloc3,
                amount=amt,
            )

    return groups


def _balance_credit_row(bill_type, *, jv_month=None, jv_year=None):
    map_row = FiPnMhErndednmap.objects.filter(map_cd=MAP_CD_BALANCE).first()
    earn_cd = _clip(map_row.earndedn_cd if map_row else "211", 3)
    if not map_row:
        from employee.services.oracle_service import get_oracle_connection

        with get_oracle_connection().cursor() as cursor:
            cursor.execute(
                """
                SELECT EARNDEDN_CD FROM FINANCE.FI_PN_MH_ERNDEDNMAP
                WHERE MAP_CD = :mc
                """,
                {"mc": MAP_CD_BALANCE},
            )
            row = cursor.fetchone()
            if row:
                earn_cd = _clip(row[0], 3)

    zonal_raw, alloc_raw = _earn_account(earn_cd)
    md = _jrnl_md_match(
        bill_type=bill_type,
        zonal_cd=zonal_raw,
        alloc_cd1=alloc_raw,
        dr_cr="C",
    )
    fin_year_label = None
    if jv_month is not None and jv_year is not None:
        fin_year_label = _calendar_fin_year_for_alloc(
            date(int(jv_year), int(jv_month), 1)
        )
    # Master FI_PN_MD_JRNLTYPE may hold a stale year (e.g. 2024); live Oracle
    # balance credits use M_FinYear for the JV month (see earn-line DECODE + production data).
    if fin_year_label is not None:
        aloc2 = str(fin_year_label)
    else:
        aloc2 = md.aloc_cd2
    return {
        "zonal_cd": _normalize_zonal(zonal_raw),
        "aloc_cd1": md.aloc_cd1,
        "aloc_cd2": aloc2,
        "aloc_cd3": md.aloc_cd3,
        "type_cd": md.jrnal_srl_no,
    }


def _existing_voucher(bill_no, fin_yr, jv_month):
    return FiPnThJv.objects.filter(
        yr=int(fin_yr),
        mth=int(jv_month),
        ref_no=_clip(bill_no, 25),
    ).first()


def _delete_jv_for_bill(bill_no, fin_yr, jv_month):
    qs = FiPnThJv.objects.filter(
        yr=int(fin_yr),
        mth=int(jv_month),
        ref_no=_clip(bill_no, 25),
    )
    voucher_nos = list(qs.values_list("voucher_no", flat=True))
    if voucher_nos:
        FiPnTdJv.objects.filter(voucher_no__in=voucher_nos).delete()
        qs.delete()


def _fmt_iso_date(value):
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text[:10] if len(text) >= 10 else text


def _finance_fetchone(sql, params):
    try:
        from django.db import connections

        with connections["default"].cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cur.description]
            return {str(c).upper(): v for c, v in zip(cols, row)}
    except Exception:
        return None


def _finance_fetchall(sql, params):
    try:
        from django.db import connections

        with connections["default"].cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            cols = [str(c[0]).upper() for c in cur.description]
            return [{c: v for c, v in zip(cols, row)} for row in rows]
    except Exception:
        return []


def _finance_billpass(bill_no):
    return _finance_fetchone(
        """
        SELECT BILL_CD, DBILL_REG_NO, DBILL_REG_DT, ABSTRACT_NO, ABSTRACT_DT,
               BILL_AMT, DEDUCT_AMT, NET_AMT, ABS_VOUCHER_NO
        FROM FI_PN_TH_BILLPASS
        WHERE DBILL_REG_NO = %s
        LIMIT 1
        """,
        [_clip(bill_no, 22)],
    )


def _finance_legacy_bill_for_employee(*, emp_cd, bill_month=None, bill_yr=None):
    emp = _clip(emp_cd, 5)
    if not emp:
        return None

    row = None
    if bill_month is not None and bill_yr is not None:
        row = _finance_fetchone(
            """
            SELECT b.BILL_NO, b.BILL_MONTH, b.BILL_YR, b.VOUCHER_NO,
                   b.BILL_ABSTRACT_NO, b.ABSTRACT_DATE, b.BANK_CD
            FROM FI_PN_TH_PENSION_BILL b
            INNER JOIN FI_PN_TH_FIRST_MONTH_PENSION h ON h.BILL_NO = b.BILL_NO
            WHERE h.EMP_CD = %s
              AND h.PENSION_MONTH = %s
              AND h.PENSION_YR = %s
            ORDER BY b.BILL_NO DESC
            LIMIT 1
            """,
            [emp, int(bill_month), int(bill_yr)],
        )
    if not row:
        row = _finance_fetchone(
            """
            SELECT b.BILL_NO, b.BILL_MONTH, b.BILL_YR, b.VOUCHER_NO,
                   b.BILL_ABSTRACT_NO, b.ABSTRACT_DATE, b.BANK_CD
            FROM FI_PN_TH_PENSION_BILL b
            INNER JOIN FI_PN_TH_FIRST_MONTH_PENSION h ON h.BILL_NO = b.BILL_NO
            WHERE h.EMP_CD = %s
            ORDER BY b.BILL_YR DESC, b.BILL_MONTH DESC, b.BILL_NO DESC
            LIMIT 1
            """,
            [emp],
        )
    return row


def _finance_jv_payload(voucher_no=None, ref_no=None):
    voucher_no = _clip(voucher_no, 25)
    ref_no = _clip(ref_no, 25)
    header = None
    if voucher_no:
        header = _finance_fetchone(
            """
            SELECT VOUCHER_NO, VOUCHER_DT, YR, MTH, TOT_AMT, NARRATION, REF_NO
            FROM FI_PN_TH_JV
            WHERE VOUCHER_NO = %s
            LIMIT 1
            """,
            [voucher_no],
        )
    if not header and ref_no:
        header = _finance_fetchone(
            """
            SELECT VOUCHER_NO, VOUCHER_DT, YR, MTH, TOT_AMT, NARRATION, REF_NO
            FROM FI_PN_TH_JV
            WHERE REF_NO = %s
            ORDER BY VOUCHER_DT DESC
            LIMIT 1
            """,
            [ref_no],
        )
    if not header:
        return None, []

    details = _finance_fetchall(
        """
        SELECT SL_NO, DR_CR_FLAG, ZONAL_CD, ALOC_CD1, ALOC_CD2, ALOC_CD3, AMOUNT
        FROM FI_PN_TD_JV
        WHERE VOUCHER_NO = %s
        ORDER BY SL_NO
        """,
        [_clip(header.get("VOUCHER_NO"), 25)],
    )
    jv = {
        "voucher_no": header.get("VOUCHER_NO") or "",
        "voucher_dt": _fmt_iso_date(header.get("VOUCHER_DT")),
        "yr": header.get("YR"),
        "mth": header.get("MTH"),
        "tot_amt": float(header.get("TOT_AMT") or 0),
        "narration": (header.get("NARRATION") or "").strip(),
        "ref_no": header.get("REF_NO") or "",
    }
    lines = [
        {
            "dr_cr_flag": (d.get("DR_CR_FLAG") or "").strip(),
            "zonal_cd": d.get("ZONAL_CD"),
            "aloc_cd1": d.get("ALOC_CD1") or "",
            "aloc_cd2": d.get("ALOC_CD2") or "",
            "aloc_cd3": d.get("ALOC_CD3") or "",
            "amount": float(d.get("AMOUNT") or 0),
        }
        for d in details
    ]
    return jv, lines


def _enrich_voucher_status_from_finance(payload, *, emp_cd, bill_month, bill_yr):
    """
    When local SMPK bill was regenerated without abstract/JV, fill from finance archive
    (Oracle dump on 3307): FI_PN_TH_PENSION_BILL + FI_PN_TH_BILLPASS + FI_PN_TH/TD_JV.
    """
    needs_abstract = not (payload.get("bill_abstract_no") or "").strip()
    needs_voucher = not (payload.get("voucher_no") or "").strip()
    needs_narration = not (
        (payload.get("jv") or {}).get("narration")
        or (payload.get("default_narration") or "")
    ).strip()
    if not (needs_abstract or needs_voucher or needs_narration):
        return payload

    legacy_bill = _finance_legacy_bill_for_employee(
        emp_cd=emp_cd, bill_month=bill_month, bill_yr=bill_yr
    )
    if not legacy_bill:
        # Still try billpass against the local bill_no (same number in archive).
        billpass = _finance_billpass(payload.get("bill_no"))
        if billpass and needs_abstract:
            payload["bill_abstract_no"] = _clip(billpass.get("ABSTRACT_NO"), 22)
            payload["abstract_date"] = _fmt_iso_date(billpass.get("ABSTRACT_DT"))
            payload["source"] = "finance_archive"
        return payload

    legacy_bill_no = _clip(legacy_bill.get("BILL_NO"), 22)
    payload["legacy_bill_no"] = legacy_bill_no

    # Abstract lives on billpass in Oracle, often blank on FI_PN_TH_PENSION_BILL.
    if needs_abstract:
        billpass = _finance_billpass(legacy_bill_no) or _finance_billpass(
            payload.get("bill_no")
        )
        if billpass and billpass.get("ABSTRACT_NO"):
            payload["bill_abstract_no"] = _clip(billpass.get("ABSTRACT_NO"), 22)
            payload["abstract_date"] = _fmt_iso_date(billpass.get("ABSTRACT_DT"))
        elif legacy_bill.get("BILL_ABSTRACT_NO"):
            payload["bill_abstract_no"] = _clip(legacy_bill.get("BILL_ABSTRACT_NO"), 22)
            payload["abstract_date"] = _fmt_iso_date(legacy_bill.get("ABSTRACT_DATE"))

    if needs_voucher or needs_narration or not payload.get("jv"):
        jv, lines = _finance_jv_payload(
            voucher_no=legacy_bill.get("VOUCHER_NO"),
            ref_no=legacy_bill_no,
        )
        if jv:
            if needs_voucher:
                payload["voucher_no"] = jv["voucher_no"]
                payload["has_voucher"] = True
            if not payload.get("jv"):
                payload["jv"] = jv
            elif needs_narration and jv.get("narration"):
                payload["jv"] = {**(payload.get("jv") or {}), "narration": jv["narration"]}
            if jv.get("narration"):
                payload["default_narration"] = jv["narration"]
            if lines:
                total_dr = sum(x["amount"] for x in lines if x["dr_cr_flag"] == "D")
                total_cr = sum(x["amount"] for x in lines if x["dr_cr_flag"] == "C")
                payload["preview"] = {
                    "lines": lines,
                    "total_dr": float(total_dr),
                    "total_cr": float(total_cr),
                    "source": "finance_archive",
                }

    payload["source"] = "finance_archive"
    return payload


def get_voucher_status(*, bill_no):
    bill_no = _clip(bill_no, 22)
    bill = FiPnThPensionBill.objects.filter(bill_no=bill_no).first()
    if not bill:
        raise VoucherGenerationError(f"Bill {bill_no} not found.")

    jv = None
    if bill.voucher_no:
        jv = FiPnThJv.objects.filter(voucher_no=bill.voucher_no).first()

    header = FiPnThFirstMonthPension.objects.filter(bill_no=bill_no).first()
    default_narration = ""
    if not jv or not (jv.narration or "").strip():
        default_narration = build_default_journal_narration(
            emp_cd=header.emp_cd if header else None,
            bill_no=bill_no,
        )

    payload = {
        "bill_no": bill.bill_no,
        "bill_month": bill.bill_month,
        "bill_yr": bill.bill_yr,
        "bank_cd": bill.bank_cd,
        "gen_lic_tag": bill.gen_lic_tag,
        "voucher_no": bill.voucher_no or "",
        "bill_abstract_no": bill.bill_abstract_no or "",
        "abstract_date": bill.abstract_date.isoformat() if bill.abstract_date else "",
        "has_voucher": bool(bill.voucher_no),
        "default_narration": default_narration,
        "source": "local",
        "jv": (
            {
                "voucher_no": jv.voucher_no,
                "voucher_dt": jv.voucher_dt.isoformat() if jv.voucher_dt else "",
                "yr": jv.yr,
                "mth": jv.mth,
                "tot_amt": float(jv.tot_amt or 0),
                "narration": jv.narration or "",
            }
            if jv
            else None
        ),
    }

    return _enrich_voucher_status_from_finance(
        payload,
        emp_cd=header.emp_cd if header else None,
        bill_month=bill.bill_month or (header.pension_month if header else None),
        bill_yr=bill.bill_yr or (header.pension_yr if header else None),
    )


def preview_ppn_voucher(
    *,
    bill_no,
    jv_month,
    jv_year,
):
    bill = FiPnThPensionBill.objects.filter(bill_no=_clip(bill_no, 22)).first()
    if not bill:
        raise VoucherGenerationError(f"Bill {bill_no} not found.")

    groups = _build_ppn_jv_groups(bill, jv_month=int(jv_month), jv_year=int(jv_year))
    lines = []
    total_dr = total_cr = Decimal("0")
    for (dr_cr, zonal, a1, a2, a3), amt in sorted(groups.items()):
        lines.append(
            {
                "dr_cr_flag": dr_cr,
                "zonal_cd": zonal,
                "aloc_cd1": a1,
                "aloc_cd2": a2,
                "aloc_cd3": a3,
                "amount": float(amt),
            }
        )
        if dr_cr == "D":
            total_dr += amt
        else:
            total_cr += amt

    balance = total_dr - total_cr
    if balance:
        bal = _balance_credit_row(
            _clip(bill.bill_no, 3)[:3] or "PPN",
            jv_month=jv_month,
            jv_year=jv_year,
        )
        lines.append(
            {
                "dr_cr_flag": "C",
                "zonal_cd": bal["zonal_cd"],
                "aloc_cd1": bal["aloc_cd1"],
                "aloc_cd2": bal["aloc_cd2"],
                "aloc_cd3": bal["aloc_cd3"],
                "amount": float(balance),
                "balancing": True,
            }
        )
        total_cr += balance

    return {
        "bill_no": bill.bill_no,
        "jv_month": int(jv_month),
        "jv_year": int(jv_year),
        "lines": lines,
        "total_dr": float(total_dr),
        "total_cr": float(total_cr),
    }


def _parse_optional_date(value):
    if not value:
        return None
    if hasattr(value, "year"):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            from datetime import datetime

            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


@transaction.atomic
def generate_ppn_voucher(
    *,
    bill_no,
    jv_month,
    jv_year,
    abstract_no="",
    abstract_date=None,
    narration="",
    user=None,
    regenerate=False,
    voucher_no=None,
):
    """Generate PPN journal voucher in MySQL (Voucher_First_Pension_Bill)."""
    bill_no = _clip(bill_no, 22)
    bill = FiPnThPensionBill.objects.filter(bill_no=bill_no).first()
    if not bill:
        raise VoucherGenerationError(f"Bill {bill_no} not found.")
    if not bill_no.upper().startswith("PPN"):
        raise VoucherGenerationError("Only PPN bills are supported in this release.")

    jv_month = int(jv_month)
    jv_year = int(jv_year)
    fin_yr = _resolve_fin_year_for_jv_month(jv_month, jv_year)
    user_code = _user_code(user)
    today = timezone.localdate()
    voucher_dt = _parse_optional_date(abstract_date) or today

    header = FiPnThFirstMonthPension.objects.filter(bill_no=bill_no).first()
    if not str(narration or "").strip():
        narration = build_default_journal_narration(
            emp_cd=header.emp_cd if header else None,
            bill_no=bill_no,
        )

    existing = _existing_voucher(bill_no, fin_yr, jv_month)
    # Prefer the voucher already linked to the bill (may differ by fin yr/month key).
    reuse_voucher_no = (
        _clip(voucher_no, 25)
        or _clip(bill.voucher_no, 25)
        or (_clip(existing.voucher_no, 25) if existing else "")
    )

    # Finance-archive prefill only (no local JV yet): keep the historical PNJV id.
    if regenerate and not reuse_voucher_no and header:
        legacy = _finance_legacy_bill_for_employee(
            emp_cd=header.emp_cd,
            bill_month=bill.bill_month or header.pension_month,
            bill_yr=bill.bill_yr or header.pension_yr,
        )
        if legacy and legacy.get("VOUCHER_NO"):
            reuse_voucher_no = _clip(legacy.get("VOUCHER_NO"), 25)

    if reuse_voucher_no and not regenerate:
        raise VoucherGenerationError(
            f"Voucher already exists: {reuse_voucher_no}. Use regenerate to replace."
        )

    old_voucher_dt = existing.voucher_dt if existing else None
    if reuse_voucher_no and not old_voucher_dt:
        prior = FiPnThJv.objects.filter(voucher_no=reuse_voucher_no).first()
        if prior:
            old_voucher_dt = prior.voucher_dt

    # Drop prior JV rows for this bill / reused voucher before rewrite.
    if regenerate or existing or reuse_voucher_no:
        _delete_jv_for_bill(bill_no, fin_yr, jv_month)
        if reuse_voucher_no:
            FiPnTdJv.objects.filter(voucher_no=reuse_voucher_no).delete()
            FiPnThJv.objects.filter(voucher_no=reuse_voucher_no).delete()
        if bill.voucher_no and bill.voucher_no != reuse_voucher_no:
            FiPnTdJv.objects.filter(voucher_no=bill.voucher_no).delete()
            FiPnThJv.objects.filter(voucher_no=bill.voucher_no).delete()

    if reuse_voucher_no:
        out_voucher_no = reuse_voucher_no
        if not _parse_optional_date(abstract_date) and old_voucher_dt:
            voucher_dt = old_voucher_dt
    else:
        serial = _allocate_pnjv_serial(fin_yr, user_code, today)
        out_voucher_no = _format_voucher_no(fin_yr, jv_month, serial)

    groups = _build_ppn_jv_groups(bill, jv_month=jv_month, jv_year=jv_year)
    total_dr = Decimal("0")
    total_cr = Decimal("0")
    sl_no = 0
    detail_rows = []

    for (dr_cr, zonal, a1, a2, a3), amt in sorted(groups.items()):
        sl_no += 1
        detail_rows.append(
            FiPnTdJv(
                voucher_no=out_voucher_no,
                voucher_dt=voucher_dt,
                yr=fin_yr,
                mth=jv_month,
                sl_no=sl_no,
                zonal_cd=zonal,
                aloc_cd1=a1,
                aloc_cd2=a2,
                aloc_cd3=a3,
                dr_cr_flag=dr_cr,
                type_cd=1,
                amount=amt,
                ref=bill_no,
                created_by=user_code,
                created_on=today,
            )
        )
        if dr_cr == "D":
            total_dr += amt
        else:
            total_cr += amt

    balance = total_dr - total_cr
    if balance:
        bill_type = _clip(bill.bill_no, 3)[:3] or "PPN"
        bal = _balance_credit_row(
            bill_type,
            jv_month=jv_month,
            jv_year=jv_year,
        )
        sl_no += 1
        detail_rows.append(
            FiPnTdJv(
                voucher_no=out_voucher_no,
                voucher_dt=voucher_dt,
                yr=fin_yr,
                mth=jv_month,
                sl_no=sl_no,
                zonal_cd=bal["zonal_cd"],
                aloc_cd1=bal["aloc_cd1"],
                aloc_cd2=bal["aloc_cd2"],
                aloc_cd3=bal["aloc_cd3"],
                dr_cr_flag="C",
                type_cd=bal["type_cd"],
                amount=balance,
                ref=bill_no,
                created_by=user_code,
                created_on=today,
            )
        )
        total_cr += balance

    FiPnThJv.objects.filter(voucher_no=out_voucher_no).delete()
    FiPnThJv.objects.create(
        voucher_no=out_voucher_no,
        yr=fin_yr,
        mth=jv_month,
        voucher_dt=voucher_dt,
        tran_type=TRAN_TYPE_PPN,
        ref_no=bill_no,
        ref_dt=bill.date_created or today,
        narration=_clip(narration, 500),
        tot_amt=total_dr,
        created_by=user_code,
        created_on=today,
        voucher_for="P",
    )
    FiPnTdJv.objects.bulk_create(detail_rows)

    bill.voucher_no = out_voucher_no
    if abstract_no:
        bill.bill_abstract_no = _clip(abstract_no, 22)
    parsed_abstract_dt = _parse_optional_date(abstract_date)
    if parsed_abstract_dt:
        bill.abstract_date = parsed_abstract_dt
    bill.date_modified = today
    bill.modified_by = user_code
    bill.save(
        update_fields=[
            "voucher_no",
            "bill_abstract_no",
            "abstract_date",
            "date_modified",
            "modified_by",
        ]
    )

    return {
        "voucher_no": out_voucher_no,
        "voucher_dt": voucher_dt.isoformat(),
        "fin_yr": fin_yr,
        "jv_month": jv_month,
        "jv_year": jv_year,
        "bill_no": bill_no,
        "tot_amt": float(total_dr),
        "total_dr": float(total_dr),
        "total_cr": float(total_cr),
        "line_count": len(detail_rows),
        "abstract_no": bill.bill_abstract_no or "",
        "abstract_date": bill.abstract_date.isoformat() if bill.abstract_date else "",
        "regenerated": bool(regenerate and reuse_voucher_no),
    }
