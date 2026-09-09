"""
Die-in-Harness family pension application report.

Oracle layout/text: fi_pn_mh_fpension_dnh_appl.rdf
Data/calculations: same services as family pension proposal report (no Oracle-only tables).
"""

from __future__ import annotations

from datetime import timedelta

from django.db import connection

from employee.utils.age import calculate_age
from master_data.services.earndedn_service import lookup_earndedn_by_code

from first_pension.services.proposal_sanction_report_service import _department_name

from .dcr_gratuity_service import ffunc_dcr_gratuity
from .nominee_service import list_nominees
from .proposal_report_service import (
    ORG_NAME,
    FamilyPensionProposalReportError,
    _as_date,
    _clip,
    _desig_desc,
    _emp_key,
    _family_pension_amounts,
    _fetch_adm,
    _fetch_claim,
    _fetch_familypensioner,
    _fetch_pensioner,
    _fetch_per,
    _fmt_amount_int,
    _fmt_dd_mm_yyyy,
    _fmt_run_date,
    _num,
    _clean_name,
    _employee_name,
    _relation_label,
    _wef_date,
    _pension_scheme_label,
)

DNH_REPORT_TITLE = "APPLICATION FOR PENSION"
GIS_GRATUITY_LINE = (
    " Family Pension DCR Gratuity Calculated in GIS letter NO A/38011/4/98/PE   "
    "Dated.3/1/01"
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


def _fmt_oracle_short(value):
    dt = _as_date(value)
    if not dt:
        return _clip(value)
    return dt.strftime("%d-%b-%y").upper()


def _system_skip_codes():
    codes = {"204", "205", "208", "209"}
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT EARNDEDN_CD
            FROM fi_pn_mh_erndednmap
            WHERE MAP_CD IN (104, 106, 110)
            """
        )
        for (cd,) in cur.fetchall():
            if cd:
                codes.add(str(cd).strip())
    return codes


def _earndedn_desc(code):
    master = lookup_earndedn_by_code(code)
    if master and getattr(master, "earndedn_desc", None):
        return str(master.earndedn_desc).strip()
    row = _fetchone(
        """
        SELECT EARNDEDN_DESC AS d
        FROM fi_pn_mh_earndedn
        WHERE EARNDEDN_CD = %s
        LIMIT 1
        """,
        [_clip(code, 10)],
    )
    return _clip((row or {}).get("d"))


def _deduction_credit_gl(earn_cd, *, as_of_date=None):
    try:
        from first_pension.services.voucher_generation_service import (
            credit_gl_triplet_for_earn,
        )
    except Exception:
        return None
    for bill_type in ("PFN", "PPN"):
        try:
            gl = credit_gl_triplet_for_earn(
                earn_cd, bill_type=bill_type, as_of_date=as_of_date
            )
        except Exception:
            gl = None
        if gl:
            return gl
    return None


def _deduction_note_text(row, *, as_of_date=None):
    desc = _clip(row.get("desc")) or _clip(row.get("code"))
    amount = _num(row.get("amount"))
    if amount is None:
        base = f"Rs. 0 is to be deducted for {desc}" if desc else ""
    else:
        amt_text = _fmt_amount_int(amount)
        base = (
            f"Rs. {amt_text} is to be deducted for {desc}"
            if desc
            else f"Rs. {amt_text} is to be deducted"
        )
    if not base:
        return ""
    code = _clip(row.get("code"), 10)
    gl = _deduction_credit_gl(code, as_of_date=as_of_date) if code else None
    if gl:
        return f"* {base} and Credited to {gl}."
    return f"* {base}."


def _resolve_report_ca_number(claim, emp):
    ca = _clip(claim.get("ca_no"), 22)
    if ca:
        return ca
    row = _fetchone(
        """
        SELECT CA_NUMBER FROM fi_pn_mh_pensioner WHERE EMP_CD = %s LIMIT 1
        """,
        [_emp_key(emp)],
    )
    ca = _clip((row or {}).get("ca_number"), 22)
    if ca:
        return ca
    row = _fetchone(
        """
        SELECT CA_NUMBER
        FROM fi_pn_mh_pension_proposal
        WHERE EMP_CD = %s
        ORDER BY
          CASE WHEN PENSION_TYPE IN ('F','FP','FAMILY') THEN 0 ELSE 1 END,
          PENSION_PROPOSAL_DT DESC
        LIMIT 1
        """,
        [_emp_key(emp)],
    )
    return _clip((row or {}).get("ca_number"), 22)


def _proposal_deduction_rows(ca_number, skip_codes):
    ca = _clip(ca_number, 22)
    if not ca:
        return []
    rows = []
    for line in _fetchall(
        """
        SELECT EARNDEDN_CD, EARN_DEDN_TYPE, AMOUNT, DEDUCTED_AMT
        FROM fi_pn_md_pension_proposal
        WHERE CA_NUMBER = %s
        ORDER BY EARNDEDN_CD, EARN_DEDN_TYPE
        """,
        [ca],
    ):
        if _clip(line.get("earn_dedn_type"), 1).upper() != "D":
            continue
        cd = _clip(line.get("earndedn_cd"), 10)
        if not cd or cd in skip_codes:
            continue
        amt = _num(line.get("amount"))
        if amt is None:
            amt = _num(line.get("deducted_amt"))
        rows.append({"code": cd, "desc": _earndedn_desc(cd), "amount": amt})
    return rows


def _deduction_lines(claim, emp, amounts=None):
    skip = _system_skip_codes()
    ca = _resolve_report_ca_number(claim, emp)
    rows = _proposal_deduction_rows(ca, skip)
    as_of = (amounts or {}).get("wef") or _as_date(claim.get("dod_emp_pensioner"))
    lines = []
    seen = set()
    for row in rows:
        code = _clip(row.get("code"), 10)
        if not code or code in seen:
            continue
        seen.add(code)
        text = _deduction_note_text(row, as_of_date=as_of)
        if text:
            lines.append(text)
    return lines


def _format_case_no(claim, pensioner):
    ca = _clip(claim.get("ca_no")) or _clip(pensioner.get("ca_number"))
    if not ca:
        return ""
    if ca.upper().endswith("C/A"):
        return ca
    return f"{ca}C/A"


def _expired_reason(adm, per, dod):
    sep_dt = _as_date(adm.get("separation_dt"))
    birth_dt = _as_date(per.get("birth_dt"))
    dod_s = _fmt_oracle_short(dod)
    age = calculate_age(birth_dt, sep_dt) if birth_dt and sep_dt else None
    if not age:
        return f"Expired on {dod_s}" if dod_s else "Expired"
    return (
        f"Expired on {dod_s} {age['years']} years "
        f"{age['months']} months {age['days']} days"
    )


def _dcr_gratuity_block(emp, claim, fp, pensioner, adm):
    pension_opt = (
        claim.get("pension_opt")
        or fp.get("pension_option")
        or pensioner.get("pension_option")
        or "G"
    )
    last_basic = _num(claim.get("last_basic_at_ret"))
    retirement_dt = (
        _as_date(fp.get("emp_ret_dt"))
        or _as_date(pensioner.get("emp_ret_dt"))
        or _as_date(adm.get("separation_dt"))
        or _as_date(adm.get("exp_ret_dt"))
    )
    try:
        gr = ffunc_dcr_gratuity(
            emp,
            pension_option=str(pension_opt or "G"),
            gratuity_option=2,
            last_basic_fallback=last_basic,
            retirement_dt=retirement_dt,
        )
    except Exception:
        return "", 0, 0, 0, 0
    amt = gr.get("gratuity_amt") or gr.get("gross_gratuity") or 0
    yr = int(gr.get("tqs_yr") or 0)
    mo = int(gr.get("tqs_month") or 0)
    dy = int(gr.get("tqs_days") or 0)
    if not amt:
        return "", amt, yr, mo, dy
    text = (
        f"DCR Gratuity Rs. {_fmt_amount_int(amt)}/- only payable for  his total "
        f"qualifying service of {yr} Years {mo} Months {dy} Days"
    )
    return text, amt, yr, mo, dy


def _family_pension_line(claim, fp, amounts):
    """Oracle CF_REM1 wording; amounts from existing _family_pension_amounts()."""
    amounts = amounts or {}
    eligible = amounts.get("eligible")
    if eligible is None:
        eligible = claim.get("double_fpen_eligibility") in (1, "1", True)

    single = amounts.get("single")
    if single is None:
        single = _num(fp.get("original_single_fpension_amt")) or _num(
            fp.get("original_family_pension_amt")
        )
    double = amounts.get("double")
    if double is None:
        double = _num(fp.get("original_double_fpension_amt"))

    dod = _as_date(claim.get("dod_emp_pensioner"))
    eff_from = dod + timedelta(days=1) if dod else amounts.get("wef") or _wef_date(claim, fp)
    double_upto = amounts.get("double_upto") or _as_date(
        claim.get("double_fpen_upto")
    ) or _as_date(fp.get("double_fpension_upto"))
    eff_s = _fmt_dd_mm_yyyy(eff_from)

    if eligible and double is not None and single is not None and eff_from and double_upto:
        thereafter = double_upto + timedelta(days=1)
        return (
            f"*) Family pension to be paid @ {_fmt_amount_int(double)} P.M. "
            f"w.e.f. {eff_s} to {_fmt_oracle_short(double_upto)} "
            f"and thereafter @ {_fmt_amount_int(single)} P.M. w.e.f. "
            f"{_fmt_oracle_short(thereafter)} till Death or Re-Marriage whichever is earlier."
        )
    if single is not None and eff_from:
        return (
            f"*) Family pension to be paid @ {_fmt_amount_int(single)} P.M. "
            f"w.e.f. {eff_s} till Death or Re-Marriage whichever is earlier."
        )
    return ""


def _nominee_text(claim, emp, relation):
    applicant = _clean_name(claim.get("applicant_name"))
    rel = _clip(relation).upper() or "WIFE"
    try:
        gr_noms = [
            n for n in list_nominees(emp) if _clip(n.get("nomin_type")).upper() == "GR"
        ]
    except Exception:
        gr_noms = []

    if not gr_noms:
        return (
            "Sanction is solicited to the payment of DCR Gratuity to the widow/widower "
            f"namely {applicant} in full as per Nomination."
        )

    if len(gr_noms) == 1:
        nom = gr_noms[0]
        share = nom.get("share_pct")
        share_s = f"{int(float(share))}%" if share is not None else "100%"
        return (
            "Sanction is solicited to the payment of DCR Gratuity to the following "
            f"members as per Nomination.\n"
            f"{nom.get('sl_no')}) {nom.get('nominee_name')} "
            f"{nom.get('relation_desc') or rel} {share_s}".strip()
        )

    lines = [
        "Sanction is solicited to the payment of DCR Gratuity to the following "
        "members as per Nomination.",
    ]
    for nom in gr_noms:
        share = nom.get("share_pct")
        share_s = f"{int(float(share))}%" if share is not None else ""
        lines.append(
            f"{nom.get('sl_no')}) {nom.get('nominee_name')} "
            f"{nom.get('relation_desc') or rel} {share_s}".strip()
        )
    return "\n".join(lines)


def _widow_prayer_text(claim, emp):
    """Oracle CF_regn_no_Dt wording (uses proposal regn when available)."""
    ca = _resolve_report_ca_number(claim, emp)
    regn_no = ""
    regn_dt = ""
    try:
        row = _fetchone(
            """
            SELECT REGN_NO, REGN_DATE
            FROM fi_pn_mh_pension_proposal
            WHERE CA_NUMBER = %s
            ORDER BY CASE WHEN PENSION_TYPE IN ('F','FP','FAMILY') THEN 0 ELSE 1 END,
                     PENSION_PROPOSAL_DT DESC
            LIMIT 1
            """,
            [_clip(ca, 22)],
        )
        if not row:
            row = _fetchone(
                """
                SELECT REGN_NO, REGN_DATE
                FROM fi_pn_mh_pension_proposal
                WHERE EMP_CD = %s
                ORDER BY CASE WHEN PENSION_TYPE IN ('F','FP','FAMILY') THEN 0 ELSE 1 END,
                         PENSION_PROPOSAL_DT DESC
                LIMIT 1
                """,
                [_emp_key(emp)],
            )
        if row:
            regn_no = _clip(row.get("regn_no"))
            regn_dt = _fmt_dd_mm_yyyy(row.get("regn_date"))
    except Exception:
        pass

    base = (
        "was a permanent employee and did not opt central Govt. pension scheme."
        " The widow of the deceased prayed for Central Govt. pension scheme"
    )
    if regn_no and regn_dt:
        return f"{base} vide P.S Regn. No.{regn_no} Dated : {regn_dt}"
    appcn_dt = _as_date(claim.get("appcn_date"))
    if appcn_dt:
        return f"{base} vide P.S Regn. No. Dated : {_fmt_dd_mm_yyyy(appcn_dt)}"
    return f"{base}."


def _build_reason_notes(
    claim, fp, base_cpi, amounts, emp, relation, adm, pensioner, per
):
    """*) note block below dates — excludes the Expired line (shown separately)."""
    notes = []

    fp_line = _family_pension_line(claim, fp, amounts)
    if fp_line:
        notes.append(fp_line)

    notes.append(
        f"*) Submitted to the FA & CAO for Sanction.{GIS_GRATUITY_LINE}"
    )

    nominee = _nominee_text(claim, emp, relation)
    if nominee:
        notes.append(f"*) {nominee}")

    emp_name = _employee_name(pensioner, per)
    if emp_name:
        notes.append(f"*) {_clip(emp_name)} {_widow_prayer_text(claim, emp)}")

    cpi = amounts.get("process_cpi")
    if cpi is None:
        cpi = _num(base_cpi)
    if cpi is not None:
        notes.append(f"*) Relief to be given over {int(cpi)} CPI.")

    for ded in _deduction_lines(claim, emp, amounts=amounts):
        notes.append(ded)

    return notes


def _build_dnh_remarks(department):
    dept = _clip(department) or "office records"
    return [
        f"Service verified from office records furnished by {dept}",
        "In terms of lib . Pension rules and family pension Scheme.",
    ]


def _assert_die_in_harness(adm):
    sep_type = _clip(adm.get("separation_type"), 10).upper()
    if sep_type != "DT":
        raise FamilyPensionProposalReportError(
            "Die-in-Harness report applies only when separation type is DT (death)."
        )


def _compose_page(*, claim, emp, adm, per, pensioner, fp, amounts, base_cpi):
    emp_name = _employee_name(pensioner, per)
    relation = _relation_label(claim.get("gurdian_relation_cd"), fallback="")
    if not relation and str(claim.get("gurdian_relation_cd") or "") == "1":
        relation = "WIFE"

    desig_cd = fp.get("desig_cd") or pensioner.get("desig_cd") or adm.get("desig_cd")
    join_dt = adm.get("join_dt")
    retirement_dt = (
        fp.get("emp_ret_dt")
        or pensioner.get("emp_ret_dt")
        or adm.get("separation_dt")
        or adm.get("exp_ret_dt")
    )
    dod = claim.get("dod_emp_pensioner")
    department = _department_name(emp)
    dcr_line, _, _, _, _ = _dcr_gratuity_block(emp, claim, fp, pensioner, adm)
    pension_opt = (
        claim.get("pension_opt")
        or fp.get("pension_option")
        or pensioner.get("pension_option")
        or "G"
    )
    deceased = _clip(emp_name).upper()
    rel = _clip(relation).upper() or "WIFE"
    applicant = _clean_name(claim.get("applicant_name")).upper()
    expired = _expired_reason(adm, per, dod)

    return {
        "page_no": 1,
        "total_pages": 1,
        "report_no": _clip(claim.get("ca_no")) or _clip(pensioner.get("ca_number")),
        "case_no": _format_case_no(claim, pensioner),
        "roll_no": _clip(fp.get("fpension_roll_no")),
        "clmca_id": _clip(claim.get("clmca_id")),
        "name_line_employee": f"Late {deceased}" if deceased else "",
        "name_line_pensioner": (
            f"{applicant} {rel} of Late {deceased}"
            if applicant and deceased
            else applicant
        ),
        "emp_cd": emp,
        "designation": _desig_desc(desig_cd),
        "department": department,
        "pension_scheme": _pension_scheme_label(pension_opt),
        "pay": _fmt_amount_int(claim.get("last_basic_at_ret")),
        "spl_pay": "0",
        "entered_service": _fmt_dd_mm_yyyy(join_dt),
        "retired_from": _fmt_dd_mm_yyyy(retirement_dt),
        "expired_reason": expired,
        "reason_notes": _build_reason_notes(
            claim, fp, base_cpi, amounts, emp, relation, adm, pensioner, per
        ),
        "dcr_gratuity_line": dcr_line,
        "remarks": _build_dnh_remarks(department),
    }


def build_family_pension_dnh_proposal_report(*, clmca_id=None, emp_cd=None):
    claim = _fetch_claim(clmca_id=clmca_id, emp_cd=emp_cd)
    if not claim:
        raise FamilyPensionProposalReportError(
            "Family pension claim not found. Save the claim first."
        )

    emp = _emp_key(claim.get("emp_cd") or emp_cd)
    adm = _fetch_adm(emp)
    _assert_die_in_harness(adm)

    pensioner = _fetch_pensioner(emp)
    fp = _fetch_familypensioner(claim.get("clmca_id"), emp)
    per = _fetch_per(emp)

    amounts = _family_pension_amounts(claim, fp, pensioner, adm, per, emp)
    base_cpi = (
        amounts.get("process_cpi")
        or fp.get("base_cpi")
        or claim.get("retirement_cpi")
        or pensioner.get("base_cpi")
    )

    page = _compose_page(
        claim=claim,
        emp=emp,
        adm=adm,
        per=per,
        pensioner=pensioner,
        fp=fp,
        amounts=amounts,
        base_cpi=base_cpi,
    )

    return {
        "org_name": ORG_NAME,
        "report_title": DNH_REPORT_TITLE,
        "run_date": _fmt_run_date(),
        "pages": [page],
    }


def list_dnh_claims_for_period(*, from_dt, to_dt):
    start = _as_date(from_dt)
    end = _as_date(to_dt)
    if not start or not end:
        raise FamilyPensionProposalReportError("from_dt and to_dt are required.")
    if start > end:
        raise FamilyPensionProposalReportError("from_dt must be on or before to_dt.")

    rows = _fetchall(
        """
        SELECT A.SL_NO, A.NAME, A.CLMCA_ID, B.EMP_CD, C.SEPARATION_DT
        FROM fi_pn_md_fpen_appcn A
        JOIN fi_pn_mh_fpen_caclaim B ON A.CLMCA_ID = B.CLMCA_ID
        JOIN fi_xx_mh_emp_adm C ON B.EMP_CD = C.EMP_CD
        WHERE C.SEPARATION_DT BETWEEN %s AND %s
          AND C.SEPARATION_TYPE = 'DT'
          AND A.FPEN_ACTIVE = 1
        ORDER BY C.SEPARATION_DT, B.EMP_CD, A.SL_NO
        """,
        [start, end],
    )
    return [
        {
            "sl_no": r.get("sl_no"),
            "name": _clip(r.get("name")),
            "clmca_id": _clip(r.get("clmca_id")),
            "emp_cd": _emp_key(r.get("emp_cd")),
            "separation_dt": _fmt_dd_mm_yyyy(r.get("separation_dt")),
        }
        for r in rows
    ]


def build_family_pension_dnh_proposal_report_batch(
    *,
    from_dt=None,
    to_dt=None,
    emp_cds=None,
):
    pages = []
    targets = []

    if emp_cds:
        for raw in emp_cds:
            key = _emp_key(raw)
            if key:
                targets.append(key)
    elif from_dt and to_dt:
        for row in list_dnh_claims_for_period(from_dt=from_dt, to_dt=to_dt):
            targets.append(row["emp_cd"])
    else:
        raise FamilyPensionProposalReportError(
            "Provide emp_cds or from_dt and to_dt."
        )

    seen = set()
    for emp in targets:
        if emp in seen:
            continue
        seen.add(emp)
        single = build_family_pension_dnh_proposal_report(emp_cd=emp)
        if single.get("pages"):
            page = dict(single["pages"][0])
            page["page_no"] = len(pages) + 1
            pages.append(page)

    if not pages:
        raise FamilyPensionProposalReportError(
            "No die-in-harness family pension claims found for the selection."
        )

    for idx, page in enumerate(pages, start=1):
        page["page_no"] = idx
        page["total_pages"] = len(pages)

    return {
        "org_name": ORG_NAME,
        "report_title": DNH_REPORT_TITLE,
        "run_date": _fmt_run_date(),
        "pages": pages,
    }
