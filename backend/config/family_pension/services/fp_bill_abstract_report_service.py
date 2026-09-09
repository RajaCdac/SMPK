"""
Family Pension Bill Abstract — per employee/claim (PFN bills).

Oracle: FI_PN_BILL_ABSTRACT.rdf (PFN branch) — individual bill register row
after PFN bill generation, not the batch BILL_CD LOV.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db import connection

from employee.oracle_mirror import FiXxMhEmpFin
from first_pension.oracle_mirror import FiPnMhPensioner, FiPnThPensionBill
from first_pension.services.bill_abstract_report_service import (
    _amount_fields,
    _bank_details,
    _display_ifsc,
    _fetch_billpass_from_oracle,
    _format_amount,
    _format_dd_mm_yy,
    _format_dd_mm_yyyy,
    _sync_bill_from_billpass,
)
from first_pension.utils.amount_words import rupees_amount_in_words
from master_data.models import FiPnMhEarndedn

from .first_fp_bill_service import (
    _clip,
    _emp_key,
    _fetchone,
    _gratuity_eform_members,
    _oracle_sum_family_td,
    _relation_desc,
)


class FpBillAbstractReportError(Exception):
    pass


# Oracle bill abstract — exclude monthly pension / relief on LIC-tagged PFN bills.
LIC_ABSTRACT_EXCLUDED_EARN = frozenset({"200", "208", "209"})
GRATUITY_EARN_CODES = frozenset({"205", "104", "204"})


def _dec(value):
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _fetchall(sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params or [])
        cols = [d[0].lower() for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _load_td_lines(fam_fmpen_id: str) -> list[dict]:
    return _fetchall(
        """
        SELECT earn_dedn_type, earn_dedn_cd, amount, original_amt
        FROM fi_pn_td_first_month_fpension
        WHERE fam_fmpen_id = %s
        ORDER BY earn_dedn_type, earn_dedn_cd
        """,
        [_clip(fam_fmpen_id, 20)],
    )


def _is_gratuity_line(line: dict) -> bool:
    cd = _clip(line.get("earn_dedn_cd"), 10)
    if cd in GRATUITY_EARN_CODES:
        return True
    desc = ""
    if cd:
        row = FiPnMhEarndedn.objects.filter(earndedn_cd=cd).first()
        if row and row.earndedn_desc:
            desc = str(row.earndedn_desc).upper()
    return "GRATUITY" in desc


def _line_totals_for_fp_abstract(
    fam_fmpen_id: str,
    *,
    fpension_type: str,
    gen_lic_tag: str | None,
    lic_bank_cd: str | None,
) -> tuple[Decimal, Decimal]:
    """PFN earn/dedn totals for bill abstract print (payable TD AMOUNT)."""
    gratuity_only = (_clip(fpension_type, 1).upper() or "N") == "N"

    if gratuity_only:
        earn = Decimal("0")
        dedn = Decimal("0")
        for line in _load_td_lines(fam_fmpen_id):
            et = _clip(line.get("earn_dedn_type"), 1).upper() or "E"
            amt = _dec(line.get("amount"))
            if et == "E":
                if _is_gratuity_line(line):
                    earn += amt
            else:
                dedn += amt

        if earn <= Decimal("0"):
            th = _fetchone(
                """
                SELECT gratuity_amt
                FROM fi_pn_th_first_month_fpension
                WHERE fam_fmpen_id = %s
                LIMIT 1
                """,
                [_clip(fam_fmpen_id, 20)],
            ) or {}
            earn = _dec(th.get("gratuity_amt"))
        return earn, dedn

    earn_f, dedn_f = _oracle_sum_family_td(fam_fmpen_id=fam_fmpen_id)
    earn = _dec(earn_f)
    dedn = _dec(dedn_f)

    # LIC-tagged FP bills pay commutation/gratuity only — not monthly pension/relief.
    if str(lic_bank_cd or "").strip():
        excluded = Decimal("0")
        for line in _load_td_lines(fam_fmpen_id):
            et = _clip(line.get("earn_dedn_type"), 1).upper() or "E"
            cd = _clip(line.get("earn_dedn_cd"), 10)
            if et == "E" and cd in LIC_ABSTRACT_EXCLUDED_EARN:
                excluded += _dec(line.get("amount"))
        earn -= excluded

    return earn, dedn


def _active_applicant(clmca_id: str) -> dict:
    return (
        _fetchone(
            """
            SELECT name, bank_cd, account_no
            FROM fi_pn_md_fpen_appcn
            WHERE clmca_id = %s AND fpen_active = 1
            ORDER BY sl_no
            LIMIT 1
            """,
            [_clip(clmca_id, 20)],
        )
        or {}
    )


def _rendered_name(clmca_id: str, emp_cd: str, header: dict) -> str:
    applicant = _active_applicant(clmca_id)
    name = _clip(applicant.get("name"), 62)
    if name:
        return name.upper()
    claim = _fetchone(
        """
        SELECT applicant_name
        FROM fi_pn_mh_fpen_caclaim
        WHERE clmca_id = %s
        LIMIT 1
        """,
        [_clip(clmca_id, 20)],
    ) or {}
    name = _clip(claim.get("applicant_name"), 62)
    if name:
        return name.upper()
    pensioner = FiPnMhPensioner.objects.filter(emp_cd=_clip(emp_cd, 5)).first()
    if pensioner and pensioner.name:
        return str(pensioner.name).strip().upper()
    return _clip(emp_cd, 5)


def _payee_block(clmca_id: str, emp_cd: str, header: dict) -> dict:
    applicant = _active_applicant(clmca_id)
    pensioner = FiPnMhPensioner.objects.filter(emp_cd=_clip(emp_cd, 5)).first()

    ret_dt = None
    fp = _fetchone(
        """
        SELECT emp_ret_dt
        FROM fi_pn_mh_familypensioner
        WHERE clmca_id = %s
        ORDER BY sl_no
        LIMIT 1
        """,
        [_clip(clmca_id, 20)],
    )
    if fp and fp.get("emp_ret_dt"):
        ret_dt = fp["emp_ret_dt"]
    elif pensioner and pensioner.emp_ret_dt:
        ret_dt = pensioner.emp_ret_dt

    bank_cd = _clip(applicant.get("bank_cd"), 6) or _clip(header.get("bank_cd"), 6)
    account_no = _clip(applicant.get("account_no"), 20)
    if not bank_cd:
        fin = FiXxMhEmpFin.objects.filter(emp_cd=_clip(emp_cd, 5)).first()
        if fin and fin.bank_cd:
            bank_cd = _clip(fin.bank_cd, 6)
            account_no = account_no or _clip(fin.bank_ac_no, 20)
    if not account_no and pensioner:
        account_no = _clip(pensioner.account_no, 20)

    bank_info = _bank_details(bank_cd)
    payee_name = _rendered_name(clmca_id, emp_cd, header)

    return {
        "emp_cd": _clip(emp_cd, 5),
        "payee_name": payee_name,
        "retirement_dt": _format_dd_mm_yyyy(ret_dt),
        "bank": bank_info["bank"],
        "address": bank_info["address"],
        "ifsc": _display_ifsc(bank_info["rbi_cd"], emp_cd),
        "account_no": account_no,
        "payment_not_before": _format_dd_mm_yyyy(ret_dt),
    }


def _resolve_bill_no(*, bill_no=None, clmca_id=None, emp_cd=None) -> str:
    bno = _clip(bill_no, 22)
    if bno:
        return bno

    claim_id = _clip(clmca_id, 20)
    emp = _emp_key(emp_cd) if emp_cd else ""
    params: list = []
    sql = """
        SELECT bill_no
        FROM fi_pn_th_first_month_fpension
        WHERE bill_no IS NOT NULL AND bill_no <> ''
          AND bill_no LIKE 'PFN%%'
    """
    if claim_id:
        sql += " AND clmca_id = %s"
        params.append(claim_id)
    if emp:
        sql += " AND emp_cd = %s"
        params.append(emp)
    sql += """
        ORDER BY fpension_year DESC, fpension_month DESC, date_created DESC
        LIMIT 1
    """
    hit = _fetchone(sql, params)
    if not hit or not hit.get("bill_no"):
        who = f"claim {claim_id}" if claim_id else f"employee {emp}"
        raise FpBillAbstractReportError(
            f"No PFN bill found for {who}. Generate the family pension bill first."
        )
    return _clip(hit["bill_no"], 22)


def _load_active_applicants(clmca_id: str) -> list[dict]:
    return _fetchall(
        """
        SELECT name, relation_cd, sl_no
        FROM fi_pn_md_fpen_appcn
        WHERE clmca_id = %s AND fpen_active = 1
        ORDER BY sl_no
        """,
        [_clip(clmca_id, 20)],
    )


def _build_beneficiaries(
    *,
    clmca_id: str,
    emp_cd: str,
    net_amount: Decimal,
    fpension_type: str,
    gratuity_amt: Decimal = Decimal("0"),
) -> list[dict]:
    """
    Oracle bill abstract detail under Rendered:
    ``1) NAME   RELATION  100%`` with net share amount.
    """
    members: list[dict] = []
    gratuity_only = (_clip(fpension_type, 1).upper() or "N") == "N"

    if gratuity_only or gratuity_amt > Decimal("0"):
        claim = _fetchone(
            """
            SELECT applicant_name, gurdian_relation_cd
            FROM fi_pn_mh_fpen_caclaim
            WHERE clmca_id = %s
            LIMIT 1
            """,
            [_clip(clmca_id, 20)],
        ) or {}
        applicant = _clip(claim.get("applicant_name"), 62)
        relation = _relation_desc(claim.get("gurdian_relation_cd")) or "WIFE"
        for m in _gratuity_eform_members(
            emp_cd=emp_cd,
            applicant=applicant,
            relation=relation,
        ):
            members.append(
                {
                    "name": str(m.get("name") or "").strip().upper(),
                    "relation": str(m.get("relation") or "").strip().upper(),
                    "share_pct": float(m.get("share_pct") or 0),
                }
            )

    if not members:
        for app in _load_active_applicants(clmca_id):
            name = _clip(app.get("name"), 62)
            if not name:
                continue
            members.append(
                {
                    "name": name.upper(),
                    "relation": _relation_desc(app.get("relation_cd")),
                    "share_pct": 0.0,
                }
            )
        if len(members) == 1:
            members[0]["share_pct"] = 100.0
        elif len(members) > 1:
            share = round(100.0 / len(members), 2)
            for m in members:
                m["share_pct"] = share

    if not members:
        name = _rendered_name(clmca_id, emp_cd, {})
        members.append({"name": name, "relation": "", "share_pct": 100.0})

    net = _dec(net_amount)
    total_pct = sum(_dec(m["share_pct"]) for m in members) or Decimal("100")
    allocated = Decimal("0")
    out: list[dict] = []
    for i, member in enumerate(members, start=1):
        pct = _dec(member["share_pct"])
        if i == len(members):
            amt = net - allocated
        else:
            amt = (net * pct / total_pct).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            allocated += amt
        share_int = int(round(float(pct)))
        name = str(member.get("name") or "").strip().upper()
        relation = str(member.get("relation") or "").strip().upper()
        parts = [f"{i})", name]
        if relation:
            parts.append(relation)
        parts.append(f"{share_int}%")
        label = "   ".join(parts)
        out.append(
            {
                "seq": i,
                "name": name,
                "relation": relation,
                "share_pct": float(pct),
                "share_pct_display": f"{share_int}%",
                "amount": float(amt),
                "amount_display": _format_amount(amt),
                "label": label,
            }
        )
    return out


def _sync_beneficiary_amounts(row: dict) -> None:
    """Re-allocate beneficiary shares after billpass totals override."""
    beneficiaries = row.get("beneficiaries") or []
    if not beneficiaries:
        return
    net = _dec(row.get("net_payable"))
    total_pct = sum(_dec(b.get("share_pct")) for b in beneficiaries) or Decimal("100")
    allocated = Decimal("0")
    for i, beneficiary in enumerate(beneficiaries):
        pct = _dec(beneficiary.get("share_pct"))
        if i == len(beneficiaries) - 1:
            amt = net - allocated
        else:
            amt = (net * pct / total_pct).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            allocated += amt
        beneficiary["amount"] = float(amt)
        beneficiary["amount_display"] = _format_amount(amt)


def _build_row(header: dict, bill: FiPnThPensionBill, *, billpass=None) -> dict:
    fam_id = header["fam_fmpen_id"]
    emp_cd = header["emp_cd"]
    clmca_id = header.get("clmca_id") or ""

    earn, dedn = _line_totals_for_fp_abstract(
        fam_id,
        fpension_type=header.get("fpension_type"),
        gen_lic_tag=bill.gen_lic_tag,
        lic_bank_cd=header.get("lic_bank_cd"),
    )

    bill_reg_dt = bill.date_created
    if billpass and billpass.get("dbill_reg_dt"):
        bill_reg_dt = billpass["dbill_reg_dt"]

    employee = _payee_block(clmca_id, emp_cd, header)
    rendered = _rendered_name(clmca_id, emp_cd, header)
    amounts = _amount_fields(earn, dedn)

    th = _fetchone(
        """
        SELECT gratuity_amt
        FROM fi_pn_th_first_month_fpension
        WHERE fam_fmpen_id = %s
        LIMIT 1
        """,
        [_clip(fam_id, 20)],
    ) or {}
    beneficiaries = _build_beneficiaries(
        clmca_id=clmca_id,
        emp_cd=emp_cd,
        net_amount=_dec(amounts["net_payable"]),
        fpension_type=header.get("fpension_type"),
        gratuity_amt=_dec(th.get("gratuity_amt")),
    )

    return {
        "bill_reg_no": bill.bill_no,
        "bill_reg_dt": _format_dd_mm_yy(bill_reg_dt),
        "rendered": rendered,
        "cheque_no": str(bill.cheque_no or ""),
        **amounts,
        "beneficiaries": beneficiaries,
        "employee": employee,
    }


def build_fp_bill_abstract_report(
    *,
    bill_no: str | None = None,
    clmca_id: str | None = None,
    emp_cd: str | None = None,
):
    """
    Build bill abstract for one PFN bill (one or more FPension lines on that bill).

    Prefer bill_no after bill generation; else latest PFN for claim/emp.
    """
    bill_key = _resolve_bill_no(bill_no=bill_no, clmca_id=clmca_id, emp_cd=emp_cd)
    bill = FiPnThPensionBill.objects.filter(bill_no=bill_key).first()
    if not bill:
        raise FpBillAbstractReportError(f"Bill {bill_key} not found.")
    if not bill_key.startswith("PFN"):
        raise FpBillAbstractReportError(
            "Family pension bill abstract requires a PFN bill number."
        )

    billpass = _fetch_billpass_from_oracle(bill.bill_no)
    _sync_bill_from_billpass(bill, billpass)

    params = [bill.bill_no]
    sql = """
        SELECT fam_fmpen_id, emp_cd, clmca_id, fpension_type,
               bank_cd, lic_bank_cd, sl_no
        FROM fi_pn_th_first_month_fpension
        WHERE bill_no = %s
    """
    emp = _emp_key(emp_cd) if emp_cd else ""
    if emp:
        sql += " AND emp_cd = %s"
        params.append(emp)
    claim_id = _clip(clmca_id, 20)
    if claim_id:
        sql += " AND clmca_id = %s"
        params.append(claim_id)
    sql += " ORDER BY sl_no, emp_cd"

    headers = _fetchall(sql, params)
    if not headers:
        raise FpBillAbstractReportError(f"No family pension lines on bill {bill.bill_no}.")

    rows = [_build_row(h, bill, billpass=billpass) for h in headers]

    if billpass and len(rows) == 1:
        earn = _dec(billpass.get("bill_amt"))
        dedn = _dec(billpass.get("deduct_amt"))
        rows[0].update(_amount_fields(earn, dedn))
        _sync_beneficiary_amounts(rows[0])

    total_passed = sum(_dec(r["amount_passed"]) for r in rows)
    total_deduction = sum(_dec(r["deduction"]) for r in rows)
    total_net = total_passed - total_deduction

    if billpass and len(rows) == 1:
        total_passed = _dec(billpass.get("bill_amt"))
        total_deduction = _dec(billpass.get("deduct_amt"))
        total_net = _dec(billpass.get("net_amt")) or (total_passed - total_deduction)

    abstract_no = bill.bill_abstract_no or ""
    abstract_dt = bill.abstract_date
    if billpass:
        abstract_no = abstract_no or _clip(billpass.get("abstract_no"), 22)
        if not abstract_dt and billpass.get("abstract_dt"):
            abstract_dt = billpass["abstract_dt"]
            if hasattr(abstract_dt, "date"):
                abstract_dt = abstract_dt.date()

    return {
        "report_kind": "bill_abstract",
        "bill_scheme": "family_pension",
        "org_name": "SYAMA PRASAD MOOKERJEE PORT, KOLKATA",
        "report_title": "ABSTRACT FORM FOR PENSION BILLS",
        "header": {
            "abstract_no": abstract_no,
            "abstract_dt": _format_dd_mm_yy(abstract_dt),
            "bill_cd": _clip(billpass.get("bill_cd") if billpass else bill.bill_no, 22),
        },
        "bill_no": bill.bill_no,
        "clmca_id": headers[0].get("clmca_id") or _clip(clmca_id, 20),
        "emp_cd": headers[0].get("emp_cd") or _emp_key(emp_cd),
        "rows": rows,
        "totals": {
            "amount_passed_display": _format_amount(total_passed),
            "deduction_display": _format_amount(total_deduction),
            "net_payable_display": _format_amount(total_net),
            "amt_parties_display": _format_amount(total_net),
            "amt_treasurer_display": "",
        },
        "amount_words": {
            "passed_for": rupees_amount_in_words(total_passed),
            "net_payable": rupees_amount_in_words(total_net),
        },
        "footer": {
            "left_signatory": "Senior A/c's Officer Pension Section",
            "center_signatory": "For Financial Advisor & Chief Accounts Officer",
            "certification": "Certified that the above cheques have been correctly drawn.",
            "right_signatory": "Dy. Chief Accounts Officer Cash & Pay Section",
            "treasurer_heading": (
                "Total Payment Cheque and cash with Treasurer for unpaid items transferred -"
            ),
            "unpaid_misc": "a. Unpaid Misc. Regr. Folio -",
            "unpaid_abstract": "b. Unpaid Abstract Regr. Folio -",
            "grand_total": "GRAND TOTAL",
        },
        "row_count": len(rows),
    }
