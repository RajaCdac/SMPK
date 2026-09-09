"""
Dry-run: recalculate class 3/4 family pension + death gratuity for employees
already having rows in fi_pn_mh_familypensioner and compare to stored Oracle/legacy values.

Usage:
  python manage.py verify_family_pension_oracle
  python manage.py verify_family_pension_oracle --limit 15
  python manage.py verify_family_pension_oracle --emp 23409,17934,40436
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand
from django.db import connection

from family_pension.services.dcr_gratuity_service import (
    DcrGratuityError,
    ffunc_dcr_gratuity,
)
from family_pension.services.double_fpension_service import (
    DoubleFamilyPensionError,
    compute_double_family_pension,
)
from family_pension.services.first_fpension_service import (
    _as_date,
    _emp_key,
    _load_adm,
    _load_claim,
    _load_emp_dob,
    _load_fin,
    _load_pensioner,
    _money,
    _m1_amount_and_cpi,
    _num,
    _resolve_category,
    _resolve_last_pay,
    _resolve_separation_date,
    _scale_desc,
    _wef_date,
    _bill_month_year,
)
from methodology1.services.family_pension_calculation_service import (
    calculate_family_pension,
)


def _near(a, b, tol=1.0):
    """Amounts match within tol rupees (default 1)."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        return abs(float(a) - float(b)) <= float(tol)
    except (TypeError, ValueError):
        return False


def _pick_class34_samples(limit=12, emp_filter=None):
    emps = None
    if emp_filter:
        emps = [_emp_key(e) for e in emp_filter if str(e).strip()]

    sql = """
        SELECT
            f.EMP_CD, f.CLMCA_ID, f.APP_CLASS,
            f.ORIGINAL_FAMILY_PENSION_AMT,
            f.ORIGINAL_SINGLE_FPENSION_AMT,
            f.ORIGINAL_DOUBLE_FPENSION_AMT,
            f.GRATUITY_AMT, f.TQS, f.TCCS, f.PERIOD_OF_SERVICE,
            f.TQS_YR, f.TQS_MONTH, f.TQS_DAYS, f.BASE_CPI,
            f.PENSION_OPTION, f.INCENTIVE_HOLDER_FLAG
        FROM fi_pn_mh_familypensioner f
        LEFT JOIN fi_xx_mh_emp_fin fin ON fin.EMP_CD = f.EMP_CD
        WHERE (f.APP_CLASS IN (3, 4) OR fin.EMP_CLASS IN (3, 4, '3', '4'))
          AND f.ORIGINAL_FAMILY_PENSION_AMT IS NOT NULL
          AND f.ORIGINAL_FAMILY_PENSION_AMT > 0
    """
    params = []
    if emps:
        placeholders = ",".join(["%s"] * len(emps))
        sql += f" AND f.EMP_CD IN ({placeholders})"
        params.extend(emps)
    sql += """
        ORDER BY
          CASE WHEN f.GRATUITY_AMT > 0 THEN 0 ELSE 1 END,
          COALESCE(f.DATE_CREATED, '1900-01-01') DESC
        LIMIT %s
    """
    params.append(int(limit) * 3)  # over-fetch; de-dupe emp later

    with connection.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0].lower() for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    seen = set()
    out = []
    for r in rows:
        emp = _emp_key(r.get("emp_cd"))
        if emp in seen:
            continue
        seen.add(emp)
        out.append(r)
        if len(out) >= int(limit):
            break
    return out


def _recalc_one(stored: dict) -> dict:
    clmca_id = (stored.get("clmca_id") or "").strip()
    emp = _emp_key(stored.get("emp_cd"))
    result = {
        "emp_cd": emp,
        "clmca_id": clmca_id,
        "ok": False,
        "error": None,
        "inputs": {},
        "stored": {},
        "calc": {},
        "match": {},
    }

    try:
        claim = _load_claim(clmca_id) if clmca_id else {}
    except Exception as exc:
        result["error"] = f"claim load: {exc}"
        return result

    adm = _load_adm(emp)
    fin = _load_fin(emp)
    pensioner = _load_pensioner(emp)

    last_pay = _resolve_last_pay(claim, pensioner)
    sep_dt = _resolve_separation_date(claim, adm, pensioner)
    category = _resolve_category(claim, fin, pensioner)
    scale = _scale_desc(claim.get("scale_cd")) or (fin.get("scale_sl") or "").strip() or None

    if category not in {"3", "4"}:
        # force 3/4 if sample was selected as class 3/4 from APP_CLASS
        ac = stored.get("app_class")
        if ac is not None and str(ac).strip() in {"3", "4"}:
            category = str(int(ac))

    result["inputs"] = {
        "category": category,
        "last_pay": last_pay,
        "scale": scale,
        "sep_dt": sep_dt.isoformat() if sep_dt else None,
        "pension_opt": (claim.get("pension_opt") or stored.get("pension_option") or "G"),
        "incentive": (
            claim.get("incentive_holder_flg")
            or stored.get("incentive_holder_flag")
            or "N"
        ),
    }

    stored_fp = _num(stored.get("original_family_pension_amt"))
    stored_single = _num(stored.get("original_single_fpension_amt"))
    stored_double = _num(stored.get("original_double_fpension_amt"))
    stored_grat = _num(stored.get("gratuity_amt"))
    result["stored"] = {
        "fp": stored_fp,
        "single": stored_single,
        "double": stored_double,
        "gratuity": stored_grat,
        "tqs": _num(stored.get("tqs")),
        "tccs": _num(stored.get("tccs")),
        "tqs_yr": stored.get("tqs_yr"),
        "tqs_month": stored.get("tqs_month"),
        "tqs_days": stored.get("tqs_days"),
        "base_cpi": _num(stored.get("base_cpi")),
    }

    if not last_pay:
        result["error"] = "No last pay (claim LAST_BASIC_AT_RET / pensioner emoluments)"
        return result
    if not sep_dt:
        result["error"] = "No separation / retirement date"
        return result

    m1 = calculate_family_pension(
        separation_date=sep_dt.isoformat(),
        category=category,
        pay=last_pay,
        scale=scale,
    )
    if m1.get("error"):
        result["error"] = f"M1: {m1['error']}"
        result["calc"]["m1"] = m1
        return result

    try:
        preferred_cpi = _num(claim.get("retirement_cpi")) or _num(
            pensioner.get("base_cpi")
        )
        fp_amt, cpi_tag = _m1_amount_and_cpi(m1, preferred_cpi=preferred_cpi)
    except Exception as exc:
        result["error"] = str(exc)
        result["calc"]["m1"] = m1
        return result

    single_rate_dec = _money(fp_amt)
    wef = _wef_date(claim) if claim else (
        (_as_date(claim.get("dod_emp_pensioner")) + timedelta(days=1))
        if claim.get("dod_emp_pensioner")
        else sep_dt
    )
    bill_m, bill_y = _bill_month_year(claim, wef, None, None) if claim else (
        sep_dt.month,
        sep_dt.year,
    )
    emp_dob = _load_emp_dob(emp)
    dod = _as_date(claim.get("dod_emp_pensioner")) if claim else None
    ret_dt = (
        _as_date(adm.get("separation_dt"))
        or _as_date(pensioner.get("emp_ret_dt"))
        or sep_dt
    )

    dbl_err = None
    try:
        dbl = compute_double_family_pension(
            claim=claim or {
                "double_fpen_eligibility": 0,
                "double_fpen_upto": None,
            },
            emp_dob=emp_dob,
            single_fp_rate=float(single_rate_dec),
            last_basic=last_pay,
            dod=dod,
            retirement_dt=ret_dt,
            original_pension_amt=_num(pensioner.get("original_pension_amt")),
            wef=wef,
            bill_month=bill_m,
            bill_year=bill_y,
        )
        calc_single = float(_money(dbl.single_rate))
        calc_double = float(_money(dbl.double_rate))
        calc_payable = float(_money(dbl.payable_fp_amt))
    except DoubleFamilyPensionError as exc:
        dbl_err = str(exc)
        calc_single = float(single_rate_dec)
        calc_double = 0.0
        calc_payable = calc_single

    pension_opt = result["inputs"]["pension_opt"]
    incentive = result["inputs"]["incentive"]
    dcr = None
    dcr_err = None
    prior_service_gratuity = _num(pensioner.get("gratuity")) or 0
    death_after_retirement = bool(dod and ret_dt and dod > ret_dt)
    # Oracle: DCR only when dod <= retirement; else 0 (death after ret not a death-case)
    skip_death_gratuity = death_after_retirement or not (dod and ret_dt and dod <= ret_dt)
    if not dod:
        skip_death_gratuity = True
    try:
        if skip_death_gratuity:
            dcr = {
                "gratuity_amt": 0,
                "tqs": 0,
                "tccs": 0,
                "tqs_yr": 0,
                "tqs_month": 0,
                "tqs_days": 0,
                "note": "Death after retirement — DCR N/A (Oracle form)",
            }
            calc_grat = 0.0
        else:
            dcr = ffunc_dcr_gratuity(
                emp,
                pension_option=str(pension_opt or "G")[:1],
                gratuity_option=2,
                incentive_holder=str(incentive or "N")[:1],
                last_basic_fallback=last_pay,
                emp_class=category,
                retirement_dt=ret_dt,
            )
            calc_grat = float(_money(dcr.get("gratuity_amt")))
    except DcrGratuityError as exc:
        dcr_err = str(exc)
        calc_grat = None

    result["calc"] = {
        "m1_raw": {
            "FP_277_cpi": m1.get("FP_277_cpi"),
            "FP_359_cpi": m1.get("FP_359_cpi"),
        },
        "cpi_tag": float(cpi_tag),
        "fp_m1_rounded": float(single_rate_dec),
        "single": calc_single,
        "double": calc_double,
        "payable_fp": calc_payable,
        "gratuity": calc_grat,
        "tqs": _num((dcr or {}).get("tqs")),
        "tccs": _num((dcr or {}).get("tccs")),
        "tqs_yr": (dcr or {}).get("tqs_yr"),
        "tqs_month": (dcr or {}).get("tqs_month"),
        "tqs_days": (dcr or {}).get("tqs_days"),
        "multi_factor": (dcr or {}).get("multi_factor"),
        "death_chart_note": (dcr or {}).get("death_chart_note"),
        "double_error": dbl_err,
        "dcr_error": dcr_err,
    }

    # Primary FP mimic: ORIGINAL_SINGLE_FPENSION_AMT (Oracle single rate).
    # ORIGINAL_FAMILY_PENSION_AMT is often the same, but some CA rows store a
    # different payable / first-month figure — do not treat that as M1 target.
    stored_rate = (
        result["stored"]["single"]
        if result["stored"]["single"] not in (None, 0, 0.0)
        else result["stored"]["fp"]
    )
    fp_match = _near(stored_rate, calc_single, tol=2.0)
    fp_family_col = _near(result["stored"]["fp"], calc_single, tol=2.0)
    fp_m1_match = _near(stored_rate, result["calc"]["fp_m1_rounded"], tol=2.0)
    single_match = (
        _near(result["stored"]["single"], calc_single, tol=2.0)
        if result["stored"]["single"] not in (None,)
        else None
    )
    double_match = (
        _near(result["stored"]["double"] or 0, calc_double, tol=2.0)
    )
    # Gratuity: only score when DB has amount > 0
    if result["stored"]["gratuity"] and result["stored"]["gratuity"] > 0:
        grat_match = (
            _near(result["stored"]["gratuity"], calc_grat, tol=5.0)
            if calc_grat is not None
            else False
        )
        tqs_match = _near(result["stored"]["tqs"], result["calc"]["tqs"], tol=0.51)
    else:
        grat_match = None
        tqs_match = None

    result["match"] = {
        "fp": fp_match or fp_m1_match,
        "fp_family_col": fp_family_col,
        "fp_vs_m1": fp_m1_match,
        "single": single_match,
        "double": double_match,
        "gratuity": grat_match,
        "tqs": tqs_match,
        "stored_rate_used": stored_rate,
    }
    result["ok"] = True
    return result


class Command(BaseCommand):
    help = (
        "Recalculate Methodology-1 FP + death gratuity for class 3/4 family "
        "pensioners already in DB and compare."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Number of distinct employees to check (default 10)",
        )
        parser.add_argument(
            "--emp",
            type=str,
            default="",
            help="Comma-separated EMP_CD list (optional)",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        emp_raw = (options.get("emp") or "").strip()
        emp_filter = [e.strip() for e in emp_raw.split(",") if e.strip()] or None

        samples = _pick_class34_samples(limit=limit, emp_filter=emp_filter)
        if not samples:
            self.stdout.write(self.style.WARNING("No class 3/4 familypensioner samples found"))
            return

        self.stdout.write(
            self.style.NOTICE(
                f"Verifying {len(samples)} class 3/4 family pensioner(s) "
                "(recalc vs fi_pn_mh_familypensioner)"
            )
        )
        self.stdout.write("-" * 100)

        n_fp_ok = n_fp = 0
        n_g_ok = n_g = 0
        rows_out = []

        for stored in samples:
            r = _recalc_one(stored)
            rows_out.append(r)
            emp = r["emp_cd"]
            claim = r["clmca_id"]
            if r.get("error") and not r.get("ok"):
                self.stdout.write(
                    self.style.ERROR(f"{emp} ({claim}): ERROR — {r['error']}")
                )
                continue

            st = r["stored"]
            ca = r["calc"]
            m = r["match"]
            inp = r["inputs"]

            n_fp += 1
            if m.get("fp"):
                n_fp_ok += 1

            if m.get("gratuity") is not None:
                n_g += 1
                if m["gratuity"]:
                    n_g_ok += 1

            def flag(v):
                if v is True:
                    return "MATCH"
                if v is False:
                    return "DIFF "
                return "n/a  "

            self.stdout.write(
                f"EMP {emp}  claim {claim}  class {inp.get('category')}  "
                f"pay={inp.get('last_pay')}  scale={inp.get('scale')}  sep={inp.get('sep_dt')}"
            )
            self.stdout.write(
                f"  FP rate  DB(single/family)={st.get('single')}/{st.get('fp')}  "
                f"CALC={ca.get('single')} (M1={ca.get('fp_m1_rounded')} cpi={ca.get('cpi_tag')})  "
                f"[{flag(m.get('fp'))}]"
            )
            self.stdout.write(
                f"  Double   DB={st.get('double')}  CALC={ca.get('double')}  [{flag(m.get('double'))}]"
            )
            self.stdout.write(
                f"  Grat     DB={st.get('gratuity')}  CALC={ca.get('gratuity')}  "
                f"TQS DB={st.get('tqs')} CALC={ca.get('tqs')}  "
                f"[{flag(m.get('gratuity'))}]"
            )
            if ca.get("dcr_error"):
                self.stdout.write(self.style.WARNING(f"  DCR err: {ca['dcr_error']}"))
            if ca.get("death_chart_note"):
                self.stdout.write(f"  note: {ca['death_chart_note']}")
            if ca.get("m1_raw"):
                self.stdout.write(
                    f"  M1 raw: 277={ca['m1_raw'].get('FP_277_cpi')}  "
                    f"359={ca['m1_raw'].get('FP_359_cpi')}"
                )
            self.stdout.write("")

        self.stdout.write("=" * 100)
        self.stdout.write(
            self.style.SUCCESS(
                f"Family pension single rate (vs ORIGINAL_SINGLE_FPENSION_AMT): "
                f"{n_fp_ok}/{n_fp} within ±2"
            )
        )
        if n_g:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Death gratuity (where DB>0): {n_g_ok}/{n_g} within ±5"
                )
            )
        else:
            self.stdout.write("Death gratuity: no sample with GRATUITY_AMT>0 in this set")

        if n_fp and n_fp_ok < n_fp:
            self.stdout.write(
                self.style.WARNING(
                    "Some rates differ — check claim last basic / scale / join dates "
                    "vs what Oracle used when the row was first generated."
                )
            )