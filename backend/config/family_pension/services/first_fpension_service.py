"""
Generate First Family Pension (type N).

Oracle form: FI_PN_MH_First_FPension.fmb / fproc_calculate_fpension2 + inserts.
SMPK: amount from Methodology I (family_pension_calculation_service); inserts mirror
fproc_ins_fpensioner + fproc_ins_1mth_fpension.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import connection, transaction
from django.utils import timezone

from methodology1.services.family_pension_calculation_service import (
    calculate_family_pension,
)
from family_pension.services.dcr_gratuity_service import (
    DcrGratuityError,
    ffunc_dcr_gratuity,
)


class FirstFamilyPensionError(Exception):
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


def _as_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _num(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _money(value):
    """Nearest rupee, half-up (similar to highest-side style for whole rupees)."""
    n = _num(value)
    if n is None:
        return Decimal("0")
    return Decimal(str(n)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


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


def _load_claim(clmca_id):
    claim = _fetchone(
        """
        SELECT CLMCA_ID, CLM_CA_TYPE, CA_NO, EMP_CD, APPCN_NO, APPCN_DATE,
               APPCN_STATUS, DOUBLE_FPEN_ELIGIBILITY, DOUBLE_FPEN_UPTO,
               APPLICANT_TYPE, APPLICANT_NAME, DOD_EMP_PENSIONER,
               GURDIAN_RELATION_CD, SERVICE_PENSION_AMT, FPEN_START_MNTH,
               FPRN_START_YR, RETIREMENT_CPI, PENSION_OPT, LAST_BASIC_AT_RET,
               SCALE_CD, FPENSION_ROLL_NO, INCENTIVE_HOLDER_FLG, CLASS,
               EQUIV_PAY_AT_BASE_CPI
        FROM fi_pn_mh_fpen_caclaim
        WHERE CLMCA_ID = %s
        LIMIT 1
        """,
        [_clip(clmca_id, 20)],
    )
    if not claim:
        raise FirstFamilyPensionError(f"Claim {_clip(clmca_id)} not found")
    return claim


def _load_applicants(clmca_id):
    rows = _fetchall(
        """
        SELECT SL_NO, NAME, DOB, RELATION_CD, BANK_CD, ACCOUNT_NO, LIC_BANK_CD,
               HANDICAP_FLG, FPEN_ACTIVE, STATUS_FLG, SEX, RELIEF_TAG
        FROM fi_pn_md_fpen_appcn
        WHERE CLMCA_ID = %s
        ORDER BY SL_NO
        """,
        [_clip(clmca_id, 20)],
    )
    if not rows:
        raise FirstFamilyPensionError(
            "No applicants on claim — add at least one applicant before generate"
        )
    active = [
        r
        for r in rows
        if r.get("fpen_active") in (None, 1, "1", True)
        and str(r.get("status_flg") or "S").upper() != "C"
    ]
    return active or rows


def _load_adm(emp_cd):
    return (
        _fetchone(
            """
            SELECT JOIN_DT, SEPARATION_DT, SEPARATION_TYPE, DESIG_CD, EXP_RET_DT
            FROM fi_xx_mh_emp_adm
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [_emp_key(emp_cd)],
        )
        or {}
    )


def _load_fin(emp_cd):
    return (
        _fetchone(
            """
            SELECT EMP_CLASS, SCALE_SL
            FROM fi_xx_mh_emp_fin
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [_emp_key(emp_cd)],
        )
        or {}
    )


def _load_pensioner(emp_cd):
    return (
        _fetchone(
            """
            SELECT NAME, CA_NUMBER, PENSION_EMOLUMENTS, BASE_CPI, DESIG_CD,
                   EMP_RET_DT, APP_CLASS, GRATUITY, PENSION_OPTION
            FROM fi_pn_mh_pensioner
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [_emp_key(emp_cd)],
        )
        or {}
    )


def _scale_desc(scale_cd):
    code = _clip(scale_cd)
    if not code:
        return None
    row = _fetchone(
        """
        SELECT SCALE_DESC
        FROM fi_pm_mh_payscale
        WHERE SCALE_CD = %s
        LIMIT 1
        """,
        [code],
    )
    if row and row.get("scale_desc"):
        return str(row["scale_desc"]).strip()
    # fall back to first 3 segments as scale code only
    parts = code.split("/")
    if len(parts) >= 3:
        short = "/".join(parts[:3])
        if short != code:
            row = _fetchone(
                "SELECT SCALE_DESC FROM fi_pm_mh_payscale WHERE SCALE_CD = %s LIMIT 1",
                [short],
            )
            if row and row.get("scale_desc"):
                return str(row["scale_desc"]).strip()
    return code


def _resolve_category(claim, fin, pensioner):
    for raw in (
        claim.get("class"),
        fin.get("emp_class"),
        pensioner.get("app_class"),
    ):
        if raw in (None, ""):
            continue
        text = str(raw).strip().upper()
        mapping = {"I": "1", "II": "2", "III": "3", "IV": "4", "O": "1", "E": "3"}
        text = mapping.get(text, text)
        if text in {"1", "2", "3", "4"}:
            return text
        try:
            n = int(float(text))
            if n in (1, 2, 3, 4):
                return str(n)
        except (TypeError, ValueError):
            pass
    return "3"


def _resolve_last_pay(claim, pensioner):
    for key, src in (
        ("last_basic_at_ret", claim),
        ("equiv_pay_at_base_cpi", claim),
        ("pension_emoluments", pensioner),
    ):
        n = _num(src.get(key))
        if n and n > 0:
            return n
    return None


def _resolve_separation_date(claim, adm, pensioner):
    return (
        _as_date(adm.get("separation_dt"))
        or _as_date(adm.get("exp_ret_dt"))
        or _as_date(pensioner.get("emp_ret_dt"))
        or _as_date(claim.get("dod_emp_pensioner"))
    )


def _wef_date(claim):
    dod = _as_date(claim.get("dod_emp_pensioner"))
    if dod:
        return dod + timedelta(days=1)
    m = claim.get("fpen_start_mnth")
    y = claim.get("fprn_start_yr")
    try:
        if m and y:
            return date(int(y), int(m), 1)
    except (TypeError, ValueError):
        pass
    return timezone.localdate()


def _bill_month_year(claim, wef, override_m=None, override_y=None):
    if override_m and override_y:
        return int(override_m), int(override_y)
    m = claim.get("fpen_start_mnth")
    y = claim.get("fprn_start_yr")
    if m and y:
        return int(m), int(y)
    if wef:
        return wef.month, wef.year
    today = timezone.localdate()
    return today.month, today.year


def _m1_amount_and_cpi(m1_result):
    """Pick payable family pension amount and BASE/CPI tag from M1 output."""
    if not m1_result or m1_result.get("error"):
        raise FirstFamilyPensionError(
            m1_result.get("error") if m1_result else "Methodology1 calculation failed"
        )
    fp_359 = _num(m1_result.get("FP_359_cpi"))
    fp_277 = _num(m1_result.get("FP_277_cpi"))
    if fp_359 is not None and fp_359 > 0:
        return fp_359, Decimal("359")
    if fp_277 is not None and fp_277 > 0:
        return fp_277, Decimal("277")
    raise FirstFamilyPensionError(
        "Methodology1 returned no family pension amount (277/359 empty)"
    )


def _allocate_fpen_id(cur, fpension_type="N"):
    """
    Next FAM_FMPEN_ID like FPEN/N/2026/135 using FI_XX_XX_M_*_FIN_CTRL DOC_ABV=FPEN.
    """
    cur.execute(
        """
        SELECT det.L_TRN_NO, mas.FIN_YR
        FROM fi_xx_xx_m_d_fin_ctrl det
        JOIN fi_xx_xx_m_h_fin_ctrl mas ON det.FIN_YR = mas.FIN_YR
        WHERE det.DOC_ABV = 'FPEN'
          AND mas.FIN_STAT = 0
          AND CURDATE() BETWEEN DATE(mas.YR_ST_DT) AND DATE(mas.YR_END_DT)
        ORDER BY mas.FIN_YR DESC
        LIMIT 1
        FOR UPDATE
        """
    )
    row = cur.fetchone()
    if not row:
        # fall back to latest FPEN open year
        cur.execute(
            """
            SELECT det.L_TRN_NO, mas.FIN_YR
            FROM fi_xx_xx_m_d_fin_ctrl det
            JOIN fi_xx_xx_m_h_fin_ctrl mas ON det.FIN_YR = mas.FIN_YR
            WHERE det.DOC_ABV = 'FPEN' AND mas.FIN_STAT = 0
            ORDER BY mas.FIN_YR DESC
            LIMIT 1
            FOR UPDATE
            """
        )
        row = cur.fetchone()
    if not row:
        raise FirstFamilyPensionError(
            "No FPEN document control (fi_xx_xx_m_d_fin_ctrl DOC_ABV=FPEN)"
        )

    last_no = int(row[0] or 0)
    fin_yr = int(row[1])
    next_no = last_no + 1
    cur.execute(
        """
        UPDATE fi_xx_xx_m_d_fin_ctrl
        SET L_TRN_NO = %s
        WHERE DOC_ABV = 'FPEN' AND FIN_YR = %s
        """,
        [next_no, fin_yr],
    )
    tag = _clip(fpension_type, 1) or "N"
    return f"FPEN/{tag}/{fin_yr}/{next_no}"


def _earn_map(map_cd):
    row = _fetchone(
        """
        SELECT EARNDEDN_CD, E_D_TYPE
        FROM fi_pn_mh_erndednmap
        WHERE MAP_CD = %s
        LIMIT 1
        """,
        [map_cd],
    )
    if not row:
        # defaults observed from live data
        defaults = {
            106: ("209", "E"),  # FAMILY PENSION
            110: ("208", "E"),  # RELIEF
        }
        return defaults.get(int(map_cd) if str(map_cd).isdigit() else map_cd, ("209", "E"))
    return str(row["earndedn_cd"]).strip(), str(row["e_d_type"] or "E").strip()


def _delete_existing_first_fp(cur, clmca_id):
    """Remove prior type-N generation rows for this claim (regenerate)."""
    clm = _clip(clmca_id, 20)
    cur.execute(
        """
        SELECT FAM_FMPEN_ID
        FROM fi_pn_th_first_month_fpension
        WHERE CLMCA_ID = %s AND FPENSION_TYPE = 'N'
        """,
        [clm],
    )
    ids = [r[0] for r in cur.fetchall()]
    for fam_id in ids:
        cur.execute(
            "DELETE FROM fi_pn_td_first_month_fpension WHERE FAM_FMPEN_ID = %s",
            [fam_id],
        )
    cur.execute(
        """
        DELETE FROM fi_pn_th_first_month_fpension
        WHERE CLMCA_ID = %s AND FPENSION_TYPE = 'N'
        """,
        [clm],
    )
    cur.execute(
        "DELETE FROM fi_pn_mh_familypensioner WHERE CLMCA_ID = %s",
        [clm],
    )


def _already_generated(clmca_id):
    row = _fetchone(
        """
        SELECT COUNT(*) AS cnt
        FROM fi_pn_th_first_month_fpension
        WHERE CLMCA_ID = %s AND FPENSION_TYPE = 'N'
        """,
        [_clip(clmca_id, 20)],
    )
    return int((row or {}).get("cnt") or 0) > 0


def generate_first_family_pension(
    *,
    clmca_id,
    month=None,
    year=None,
    user_id="SMPK",
    regenerate=False,
):
    """
    Generate First FP (type N) for a saved claim.

    Returns summary dict with amounts and document ids.
    """
    claim = _load_claim(clmca_id)
    applicants = _load_applicants(claim["clmca_id"])
    emp = _emp_key(claim.get("emp_cd"))
    if not emp:
        raise FirstFamilyPensionError("Claim has no EMP_CD")

    if not _as_date(claim.get("dod_emp_pensioner")):
        raise FirstFamilyPensionError(
            "Pensioner date of death (DOD) is required on the claim"
        )

    adm = _load_adm(emp)
    fin = _load_fin(emp)
    pensioner = _load_pensioner(emp)

    last_pay = _resolve_last_pay(claim, pensioner)
    if not last_pay:
        raise FirstFamilyPensionError(
            "Last basic / last pay missing on claim (LAST_BASIC_AT_RET)"
        )

    sep_dt = _resolve_separation_date(claim, adm, pensioner)
    if not sep_dt:
        raise FirstFamilyPensionError(
            "Separation / retirement date not found for employee"
        )

    category = _resolve_category(claim, fin, pensioner)
    scale = _scale_desc(claim.get("scale_cd")) or _clip(fin.get("scale_sl"))

    m1 = calculate_family_pension(
        separation_date=sep_dt.isoformat(),
        category=category,
        pay=last_pay,
        scale=scale,
    )
    fp_amt, cpi_tag = _m1_amount_and_cpi(m1)
    fp_amt_dec = _money(fp_amt)

    # Double FP amount still needs Oracle circular rules; store 0 from M1 for now.
    double_amt = Decimal("0")

    wef = _wef_date(claim)
    bill_m, bill_y = _bill_month_year(claim, wef, month, year)
    user = _clip(user_id, 5) or "SMPK"
    ca_no = _clip(claim.get("ca_no"), 22)
    ret_dt = (
        _as_date(adm.get("separation_dt"))
        or _as_date(pensioner.get("emp_ret_dt"))
        or sep_dt
    )
    desig_cd = (
        pensioner.get("desig_cd")
        or adm.get("desig_cd")
    )
    app_class = None
    try:
        app_class = int(category)
    except (TypeError, ValueError):
        app_class = None

    base_cpi = _num(claim.get("retirement_cpi")) or _num(pensioner.get("base_cpi"))
    # stamp process CPI (277/359) separately; BASE_CPI on master often holds process CPI in recent gens
    process_cpi = float(cpi_tag)

    # Death DCR gratuity — FFUNC_DCR_GRATUITY option 2 (form half-year path, not chart 33 alone)
    pension_opt = (
        _clip(claim.get("pension_opt"), 1)
        or _clip(pensioner.get("pension_option"), 1)
        or "G"
    )
    incentive = _clip(claim.get("incentive_holder_flg"), 1) or "N"
    try:
        dcr = ffunc_dcr_gratuity(
            emp,
            pension_option=pension_opt,
            gratuity_option=2,
            incentive_holder=incentive,
            last_basic_fallback=last_pay,
            emp_class=category,
            retirement_dt=ret_dt,
        )
    except DcrGratuityError as exc:
        raise FirstFamilyPensionError(str(exc)) from exc

    gratuity_amt = _money(dcr.get("gratuity_amt"))
    tqs_val = _num(dcr.get("tqs")) or 0
    tccs_val = _num(dcr.get("tccs")) or 0
    pos_val = _num(dcr.get("period_of_service")) or 0
    tqs_yr = int(dcr.get("tqs_yr") or 0)
    tqs_month = int(dcr.get("tqs_month") or 0)
    tqs_days = int(dcr.get("tqs_days") or 0)

    earn_cd, earn_type = _earn_map(106)
    relief_cd, relief_type = _earn_map(110)
    relief_amt = Decimal("0")  # relief/ADA not ported; matches many recent N bills

    if _already_generated(claim["clmca_id"]) and not regenerate:
        raise FirstFamilyPensionError(
            "First FP already generated for this claim. "
            "Pass regenerate=true to replace type-N rows."
        )

    created = []
    with transaction.atomic():
        with connection.cursor() as cur:
            if regenerate:
                _delete_existing_first_fp(cur, claim["clmca_id"])

            for ap in applicants:
                sl_no = int(ap.get("sl_no") or 1)
                fam_id = _allocate_fpen_id(cur, "N")

                # Master row
                cur.execute(
                    """
                    INSERT INTO fi_pn_mh_familypensioner (
                        CLMCA_ID, SL_NO, EMP_CD, APPCN_NO,
                        PERIOD_OF_SERVICE, TCCS, TQS,
                        GRATUITY_AMT, ORIGINAL_PENSION_AMT,
                        ORIGINAL_FAMILY_PENSION_AMT,
                        PAID_MONTH_FPEN, PAID_YR_FPEN,
                        DATE_CREATED, CREATED_BY,
                        CA_NUMBER,
                        ORIGINAL_SINGLE_FPENSION_AMT,
                        ORIGINAL_DOUBLE_FPENSION_AMT,
                        DOUBLE_FPENSION_UPTO,
                        FPENSION_ROLL_NO, RELIEF_TAG,
                        BASE_CPI, SEX, DOB, EMP_RET_DT, DESIG_CD,
                        WEF_DT, APP_CLASS, INCENTIVE_HOLDER_FLAG,
                        TQS_YR, TQS_MONTH, TQS_DAYS, PENSION_OPTION
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, 0,
                        %s,
                        %s, %s,
                        NOW(), %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    """,
                    [
                        claim["clmca_id"],
                        sl_no,
                        emp,
                        _clip(claim.get("appcn_no"), 20) or None,
                        float(pos_val),
                        float(tccs_val),
                        float(tqs_val),
                        float(gratuity_amt),
                        float(fp_amt_dec),
                        bill_m,
                        bill_y,
                        user,
                        ca_no or None,
                        float(fp_amt_dec),
                        float(double_amt),
                        _as_date(claim.get("double_fpen_upto")),
                        _clip(claim.get("fpension_roll_no"), 30) or None,
                        _clip(ap.get("relief_tag"), 1) or "Y",
                        process_cpi if process_cpi else base_cpi,
                        _clip(ap.get("sex"), 1) or None,
                        _as_date(ap.get("dob")),
                        ret_dt,
                        desig_cd,
                        wef,
                        app_class,
                        incentive,
                        tqs_yr,
                        tqs_month,
                        tqs_days,
                        pension_opt,
                    ],
                )

                # First-month header
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
                        %s, %s, %s, 'N',
                        %s, %s, %s,
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
                        float(fp_amt_dec),
                        float(relief_amt),
                        float(gratuity_amt),
                        user,
                        claim["clmca_id"],
                        sl_no,
                        _clip(ap.get("bank_cd"), 6) or None,
                        process_cpi,
                        emp,
                        _clip(ap.get("lic_bank_cd"), 6) or None,
                    ],
                )

                # Detail — Family Pension earn line (map 106 → cd 209)
                cur.execute(
                    """
                    INSERT INTO fi_pn_td_first_month_fpension (
                        EARN_DEDN_TYPE, EARN_DEDN_CD, AMOUNT,
                        DATE_CREATED, CREATED_BY,
                        FAM_FMPEN_ID, ORIGINAL_AMT, AREAR_AMT
                    ) VALUES (
                        %s, %s, %s,
                        NOW(), %s,
                        %s, %s, NULL
                    )
                    """,
                    [
                        earn_type,
                        earn_cd,
                        float(fp_amt_dec),
                        user,
                        fam_id,
                        float(fp_amt_dec),
                    ],
                )

                if relief_amt and float(relief_amt) > 0:
                    cur.execute(
                        """
                        INSERT INTO fi_pn_td_first_month_fpension (
                            EARN_DEDN_TYPE, EARN_DEDN_CD, AMOUNT,
                            DATE_CREATED, CREATED_BY,
                            FAM_FMPEN_ID, ORIGINAL_AMT, AREAR_AMT
                        ) VALUES (
                            %s, %s, %s,
                            NOW(), %s,
                            %s, %s, NULL
                        )
                        """,
                        [
                            relief_type,
                            relief_cd,
                            float(relief_amt),
                            user,
                            fam_id,
                            float(relief_amt),
                        ],
                    )

                created.append(
                    {
                        "fam_fmpen_id": fam_id,
                        "clmca_id": claim["clmca_id"],
                        "sl_no": sl_no,
                        "applicant_name": _clip(ap.get("name")),
                        "fpension_amt": float(fp_amt_dec),
                        "relief": float(relief_amt),
                        "gratuity_amt": float(gratuity_amt),
                    }
                )

    return {
        "ok": True,
        "message": "First Family Pension generated successfully",
        "clmca_id": claim["clmca_id"],
        "emp_cd": emp,
        "fpension_type": "N",
        "month": bill_m,
        "year": bill_y,
        "wef_dt": wef.isoformat() if wef else None,
        "separation_date": sep_dt.isoformat(),
        "last_pay": last_pay,
        "category": category,
        "scale": scale,
        "methodology1": {
            "FP_277_cpi": m1.get("FP_277_cpi"),
            "FP_359_cpi": m1.get("FP_359_cpi"),
            "selected_amount": float(fp_amt_dec),
            "process_cpi": process_cpi,
        },
        "dcr_gratuity": {
            "amount": float(gratuity_amt),
            "gross": dcr.get("gross_gratuity"),
            "emoluments": dcr.get("emoluments"),
            "multi_factor": dcr.get("multi_factor"),
            "tqs": dcr.get("tqs"),
            "tqs_yr": tqs_yr,
            "tqs_month": tqs_month,
            "tqs_days": tqs_days,
            "tccs": dcr.get("tccs"),
            "ceiling_applied": dcr.get("ceiling_applied"),
            "emoluments_detail": dcr.get("emoluments_detail"),
        },
        "bills": created,
    }
