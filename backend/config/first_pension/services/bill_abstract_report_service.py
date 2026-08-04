"""
Bill Abstract report — port of FI_PN_BILL_ABSTRACT.rdf / FI_PN_BILL_ABSTRACT_RPT.fmb (PPN).
Uses MySQL mirror data; reads Oracle FI_PN_TH_BILLPASS for authoritative abstract amounts.
"""

from decimal import Decimal

from master_data.models import FiPmMhBank, FiPmMhBankAbbr, FiPnMhEarndedn

from employee.oracle_mirror import FiXxMhEmpFin

from ..models import PensionCase
from ..oracle_mirror import (
    FiPnMhPensioner,
    FiPnTdFirstMonthPension,
    FiPnThFirstMonthPension,
    FiPnThPensionBill,
)
from ..utils.amount_words import rupees_amount_in_words

# gen_lic_tag L — Oracle bill abstract excludes monthly pension / held-up lines.
LIC_ABSTRACT_EXCLUDED_EARN = frozenset({"200", "208"})


class BillAbstractReportError(Exception):
    pass


_BANK_NARRATIVE = {
    "21": "Monthly Pension of U.B.I ({tag}) U.B.I Royal Exchange Br. Kol - 1. A/C No - 27181.",
    "16": "Monthly Pension of I.O.B ({tag}) I.O.B Strand Road Kol - 1. A/C No - 1106.",
    "32": "Monthly Pension of Canara Bank ({tag}) Canara Bank Hare Street Br. Kol - 1. A/C No - 2213.",
    "01": "Monthly Pension of S.B.I ({tag}) S.B.I Main Br. Kol - 1. A/C No - 01000/046136.",
    "22": "Monthly Pension of UCO Bank ({tag}) UCO Bank, 10, B.T.M.S. Kol - 1. A/C No - 201281.",
}


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


def _format_dd_mm_yy(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%y")
    return str(value)[:10]


def _format_dd_mm_yyyy(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    return str(value)[:10]


def _format_amount(value):
    return f"{float(_dec(value)):.2f}"


def _branch_abbrev(branch_desc):
    text = str(branch_desc or "").strip()
    if "(" in text and ")" in text:
        inner = text[text.find("(") + 1 : text.find(")")]
        if inner:
            return inner.strip().upper()
    clean = "".join(ch for ch in text.upper() if ch.isalpha())
    if not clean:
        return ""
    if len(clean) <= 3:
        return clean
    # KIDDERPORE -> KDP (matches Oracle branch short codes)
    picks = [clean[0]]
    if len(clean) > 3:
        picks.append(clean[3])
    if len(clean) > 6:
        picks.append(clean[6])
    while len(picks) < 3 and len(picks) < len(clean):
        picks.append(clean[len(picks)])
    return "".join(picks[:3])


def _bill_tag_label(headers):
    tags = {str(h.sys_man_tag or "S").strip().upper() or "S" for h in headers}
    if tags == {"T"}:
        return "Transfer Bill"
    return "Normal Bill"


def _rendered_narrative(party_cd, headers):
    tag = _bill_tag_label(headers)
    template = _BANK_NARRATIVE.get(_clip(party_cd, 2))
    if template:
        return template.format(tag=tag)
    return ""


def _fetch_billpass_from_oracle(bill_no):
    try:
        from employee.services.oracle_service import get_oracle_connection
    except Exception:
        return None

    try:
        conn = get_oracle_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT bill_cd, dbill_reg_no, dbill_reg_dt, abstract_no, abstract_dt,
                   bill_amt, deduct_amt, net_amt
            FROM finance.fi_pn_th_billpass
            WHERE dbill_reg_no = :bill
            """,
            {"bill": _clip(bill_no, 22)},
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
    except Exception:
        return None

    if not row:
        return None

    cols = [
        "bill_cd",
        "dbill_reg_no",
        "dbill_reg_dt",
        "abstract_no",
        "abstract_dt",
        "bill_amt",
        "deduct_amt",
        "net_amt",
    ]
    return dict(zip(cols, row))


def _sync_bill_from_billpass(bill, billpass):
    """Back-fill MySQL bill header when wave3 sync left totals/abstract empty."""
    if not billpass:
        return
    changed = []
    abstract_no = _clip(billpass.get("abstract_no"), 22)
    abstract_dt = billpass.get("abstract_dt")
    bill_amt = _dec(billpass.get("bill_amt"))
    deduct_amt = _dec(billpass.get("deduct_amt"))

    if abstract_no and bill.bill_abstract_no != abstract_no:
        bill.bill_abstract_no = abstract_no
        changed.append("bill_abstract_no")
    if abstract_dt and not bill.abstract_date:
        bill.abstract_date = abstract_dt.date() if hasattr(abstract_dt, "date") else abstract_dt
        changed.append("abstract_date")
    if not _dec(bill.total_amt_earned) and bill_amt:
        bill.total_amt_earned = bill_amt
        changed.append("total_amt_earned")
    if not _dec(bill.total_amt_deducted) and deduct_amt is not None:
        bill.total_amt_deducted = deduct_amt
        changed.append("total_amt_deducted")
    if changed:
        bill.save(update_fields=changed)


def _fetch_ifsc_from_oracle(emp_cd):
    try:
        from employee.services.oracle_service import get_oracle_connection

        conn = get_oracle_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ifsc FROM finance.fi_xx_mh_emp_aadhar
            WHERE emp_cd = :emp AND ifsc IS NOT NULL
            """,
            {"emp": _clip(emp_cd, 5)},
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and row[0]:
            return _clip(row[0], 11)
    except Exception:
        pass
    return ""


def _display_ifsc(branch_rbi_cd, emp_cd):
    ifsc = _fetch_ifsc_from_oracle(emp_cd)
    if ifsc:
        return ifsc
    rbi = _clip(branch_rbi_cd, 11)
    if len(rbi) == 11 and rbi[:4].isalpha():
        return rbi
    return rbi


def _bank_details(bank_cd):
    bank_cd = _clip(bank_cd, 6)
    branch = FiPmMhBank.objects.filter(bank_cd=bank_cd).first() if bank_cd else None
    abbr = (
        FiPmMhBankAbbr.objects.filter(bank_type=bank_cd[:2]).first()
        if len(bank_cd) >= 2
        else None
    )
    bank_name = (abbr.bank_name if abbr else "") or ""
    branch_desc = (branch.bank_desc if branch else "") or ""
    short = _branch_abbrev(branch_desc)
    if bank_name and branch_desc:
        label = f"{bank_name} - {branch_desc}"
        if short and f"({short})" not in label.upper():
            label = f"{label} ({short})"
    else:
        label = bank_name or branch_desc or bank_cd
    address_parts = []
    if branch:
        address_parts = [
            p
            for p in [branch.addr1, branch.addr2, branch.ps, branch.city, branch.dist]
            if p and str(p).strip()
        ]
    return {
        "bank": label,
        "address": ", ".join(address_parts),
        "rbi_cd": _clip(branch.rbi_cd if branch else "", 11),
    }


def _retirement_date(emp_cd, pensioner):
    case = PensionCase.objects.filter(emp_code=_clip(emp_cd, 5)).first()
    if case and case.retirement_date:
        return case.retirement_date
    if pensioner and pensioner.emp_ret_dt:
        return pensioner.emp_ret_dt
    return None


def _line_totals_for_abstract(fmpen_id, *, gen_lic_tag=None, lic_bank_cd=None):
    earn = Decimal("0")
    dedn = Decimal("0")
    exclude_earn = (
        str(gen_lic_tag or "").upper() in ("G", "L")
        or bool(str(lic_bank_cd or "").strip())
    )
    earn_codes = set(
        FiPnMhEarndedn.objects.filter(earndedn_type="E").values_list("earndedn_cd", flat=True)
    )
    dedn_codes = set(
        FiPnMhEarndedn.objects.filter(earndedn_type="D").values_list("earndedn_cd", flat=True)
    )
    for line in FiPnTdFirstMonthPension.objects.filter(fmpen_id=fmpen_id):
        if exclude_earn and line.earn_dedn_type == "E" and line.earn_dedn_cd in LIC_ABSTRACT_EXCLUDED_EARN:
            continue
        amt = _dec(line.amount)
        if line.earn_dedn_cd in earn_codes or line.earn_dedn_type == "E":
            earn += amt
        elif line.earn_dedn_cd in dedn_codes or line.earn_dedn_type == "D":
            dedn += amt
    return earn, dedn


def _employee_bank_source(emp_cd, header, pensioner):
    """Oracle bill abstract uses FI_XX_MH_EMP_FIN for payee bank details."""
    fin = FiXxMhEmpFin.objects.filter(emp_cd=_clip(emp_cd, 5)).first()
    bank_cd = ""
    account_no = ""
    if fin and str(fin.bank_cd or "").strip():
        bank_cd = _clip(fin.bank_cd, 6)
        account_no = _clip(fin.bank_ac_no, 20)
    if not bank_cd:
        bank_cd = _clip(header.bank_cd or (pensioner.bank_cd if pensioner else ""), 6)
    if not account_no:
        account_no = _clip(pensioner.account_no if pensioner else "", 20)
    return bank_cd, account_no


def _employee_block(header):
    pensioner = FiPnMhPensioner.objects.filter(emp_cd=header.emp_cd).first()
    retirement_dt = _retirement_date(header.emp_cd, pensioner)
    bank_cd, account_no = _employee_bank_source(header.emp_cd, header, pensioner)
    bank_info = _bank_details(bank_cd)
    return {
        "emp_cd": header.emp_cd,
        "payee_name": _clip(pensioner.name if pensioner else "", 62),
        "retirement_dt": _format_dd_mm_yyyy(retirement_dt),
        "bank": bank_info["bank"],
        "address": bank_info["address"],
        "ifsc": _display_ifsc(bank_info["rbi_cd"], header.emp_cd),
        "account_no": account_no,
        "payment_not_before": _format_dd_mm_yyyy(retirement_dt),
    }


def _amount_fields(earn, dedn):
    net = earn - dedn
    return {
        "amount_passed": float(earn),
        "deduction": float(dedn),
        "net_payable": float(net),
        "amount_passed_display": _format_amount(earn),
        "deduction_display": _format_amount(dedn),
        "net_payable_display": _format_amount(net),
        "amt_parties_display": _format_amount(net),
        "amt_treasurer_display": "",
    }


def _build_row(header, bill, *, billpass=None, amounts=None):
    if amounts is None:
        earn, dedn = _line_totals_for_abstract(
            header.fmpen_id,
            gen_lic_tag=bill.gen_lic_tag,
            lic_bank_cd=header.lic_bank_cd,
        )
    else:
        earn, dedn = amounts

    bill_reg_dt = bill.date_created
    if billpass and billpass.get("dbill_reg_dt"):
        bill_reg_dt = billpass["dbill_reg_dt"]

    return {
        "bill_reg_no": bill.bill_no,
        "bill_reg_dt": _format_dd_mm_yy(bill_reg_dt),
        "rendered": _rendered_narrative(_clip(header.bank_cd, 2), [header]),
        "cheque_no": str(bill.cheque_no or ""),
        **_amount_fields(earn, dedn),
        "employee": _employee_block(header),
    }


def build_bill_abstract_report(bill_no, *, emp_codes=None):
    bill_key = _clip(bill_no, 22)
    bill = FiPnThPensionBill.objects.filter(bill_no=bill_key).first()
    if not bill:
        raise BillAbstractReportError(f"Bill {bill_no} not found.")
    if not bill_key.startswith("PPN"):
        raise BillAbstractReportError(
            "Bill abstract is supported for PPN (first pension) bills only."
        )

    billpass = _fetch_billpass_from_oracle(bill.bill_no)
    _sync_bill_from_billpass(bill, billpass)

    headers_qs = FiPnThFirstMonthPension.objects.filter(bill_no=bill.bill_no)
    if emp_codes:
        codes = {_clip(c, 5) for c in emp_codes}
        headers_qs = headers_qs.filter(emp_cd__in=codes)
    headers = list(headers_qs.order_by("emp_cd"))
    if not headers:
        raise BillAbstractReportError(f"No pensioners on bill {bill.bill_no}.")

    rows = []
    for header in headers:
        earn, dedn = _line_totals_for_abstract(
            header.fmpen_id,
            gen_lic_tag=bill.gen_lic_tag,
            lic_bank_cd=header.lic_bank_cd,
        )
        rows.append(_build_row(header, bill, billpass=billpass, amounts=(earn, dedn)))

    if billpass and len(rows) == 1:
        earn = _dec(billpass.get("bill_amt"))
        dedn = _dec(billpass.get("deduct_amt"))
        rows[0].update(_amount_fields(earn, dedn))

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
        "org_name": "SYAMA PRASAD MOOKERJEE PORT, KOLKATA",
        "report_title": "ABSTRACT FORM FOR PENSION BILLS",
        "header": {
            "abstract_no": abstract_no,
            "abstract_dt": _format_dd_mm_yy(abstract_dt),
            "bill_cd": _clip(billpass.get("bill_cd") if billpass else bill.bill_no, 22),
        },
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
