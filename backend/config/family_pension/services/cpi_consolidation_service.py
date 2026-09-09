"""
Persist Methodology-I CPI notional basics into fi_pn_cpi_consolidation.

One row per (CLAIM_ID, CPI). Used later by 277/359 arrear so each era
(126 / 198 / 277 / 359) has a stored basic instead of only generated/upgraded.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from decimal import Decimal

from django.db import connection


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
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y"):
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


def _int_basic(value) -> int | None:
    n = _num(value)
    if n is None:
        return None
    return int(math.ceil(float(n)))


def _emp_class_int(value) -> int | None:
    n = _num(value)
    if n is None:
        return None
    return int(n)


# CPI codes stored in fi_pn_cpi_consolidation (class-dependent subset)
CPI_CLASS_34 = (607, 1708, 126, 198, 277, 359)
CPI_CLASS_12 = (1708, 126, 277)  # officer path — no 359


def compute_cpi_basics(
    *,
    separation_date,
    category,
    pay,
    scale=None,
    m1_result: dict | None = None,
    equiv_pay_at_base_cpi=None,
) -> dict[int, int]:
    """
    Build {cpi: notional_basic} for fi_pn_cpi_consolidation.

    Class 3/4 (Methodology I): 607, 1708, 126, 198, 277, 359
      — only steps that the chain can resolve for the separation date.

    Class 1/2 (officer last-pay chain): 1708, 126, 277
      — never stores 359 (no separate 359 FP band for officers).
    """
    from methodology1.services.cpi_chain_service import (
        CPI_277_REVISION,
        CPI_359_REVISION,
        CPI_607_REVISION,
        CPI_1708_REVISION,
        _resolve_607_chain_pay,
        compute_126_notional,
        compute_1708_notional,
        compute_198_notional,
        compute_277,
        compute_359,
    )
    from methodology1.services.revision_resolver import (
        get_calculation_start_revision,
        get_revision_column,
        is_1030_direct_607_period,
        is_pre_1988_separation,
    )
    from methodology1.services.scale_service import (
        get_equivalent_scales_by_scale,
        resolve_full_scale,
    )
    from methodology1.services.family_pension_calculation_service import (
        _normalize_category,
        _normalize_scale,
        _parse_pay,
        calculate_family_pension,
    )
    from methodology1.services.parallel_cpi_service import CPI_1030_REVISION

    out: dict[int, int] = {}
    cat = _normalize_category(category) or "3"
    last_pay = _parse_pay(pay)
    equiv_pay = _parse_pay(equiv_pay_at_base_cpi)
    sep = _as_date(separation_date)
    if not last_pay:
        last_pay = equiv_pay
    if not last_pay or not sep:
        return out

    sep_iso = sep.isoformat()

    # ── Class 1 / 2: officer chain — 1708 / 126 / 277 only (no 359) ─────────
    if cat in ("1", "2"):
        return _compute_class12_cpi_basics(
            separation_date=sep,
            pay=last_pay,
            scale=scale,
            m1_result=m1_result,
        )

    # ── Class 3 / 4: full Methodology-I ladder ──────────────────────────────
    scale_value = _normalize_scale(scale)
    if scale_value:
        scale_value = resolve_full_scale(sep_iso, scale_value)

    scale_revision = get_revision_column(sep_iso)
    start_revision = get_calculation_start_revision(sep_iso)
    equivalent_scales = None

    needs_scale_map = is_pre_1988_separation(sep_iso) or (
        scale_revision == CPI_1030_REVISION
        and not is_1030_direct_607_period(sep_iso)
    )
    if needs_scale_map and scale_value:
        equivalent_scales = get_equivalent_scales_by_scale(sep_iso, scale_value)
    elif needs_scale_map and not scale_value and equiv_pay:
        last_pay = equiv_pay

    def _put(cpi_code: int, value) -> None:
        basic = _int_basic(value)
        if basic is not None and basic > 0:
            out[cpi_code] = basic

    # 607 — only when separation is at/before 607/1030 era (or pre-1988)
    if (
        is_pre_1988_separation(sep_iso)
        or scale_revision in (CPI_607_REVISION, CPI_1030_REVISION)
        or start_revision == CPI_607_REVISION
    ):
        try:
            n607 = _resolve_607_chain_pay(
                last_pay, scale_revision, equivalent_scales, sep_iso
            )
            _put(607, n607)
        except Exception:
            pass

    # Pre-1988 / early scale without Excel scale map: 1708+ chain cannot start
    # from 1979/1984 revision. Continue from 607 rules using original last pay
    # (matches Oracle minimum ladder 1850 → 4055 → 10904 → 15381).
    chain_scale_rev = scale_revision
    chain_scales = equivalent_scales
    if needs_scale_map and not equivalent_scales and 607 in out:
        chain_scale_rev = CPI_607_REVISION
        chain_scales = None

    # 1708 / 126 / 198 / 277 / 359
    try:
        _put(
            1708,
            compute_1708_notional(
                last_pay, chain_scale_rev, start_revision, chain_scales, sep_iso
            ),
        )
    except Exception:
        pass

    if start_revision not in (CPI_277_REVISION, CPI_359_REVISION):
        try:
            _put(
                126,
                compute_126_notional(
                    last_pay, chain_scale_rev, start_revision, chain_scales, sep_iso
                ),
            )
        except Exception:
            pass
        try:
            _put(
                198,
                compute_198_notional(
                    last_pay, chain_scale_rev, start_revision, chain_scales, sep_iso
                ),
            )
        except Exception:
            pass

    m1 = m1_result
    if not m1 or m1.get("error"):
        try:
            m1 = calculate_family_pension(
                separation_date=sep_iso,
                category=cat,
                pay=last_pay,
                scale=scale_value,
                equiv_pay_at_base_cpi=equiv_pay,
            )
        except Exception:
            m1 = {}

    if start_revision != CPI_359_REVISION:
        try:
            c277 = compute_277(
                last_pay, chain_scale_rev, start_revision, chain_scales, sep_iso
            )
            if c277 and c277.get("notional") is not None:
                _put(277, c277["notional"])
            else:
                _put(277, (m1 or {}).get("FP_277_cpi"))
        except Exception:
            _put(277, (m1 or {}).get("FP_277_cpi"))

    try:
        c359 = compute_359(
            last_pay, chain_scale_rev, start_revision, chain_scales, sep_iso
        )
        if c359 and c359.get("notional") is not None:
            _put(359, c359["notional"])
        else:
            _put(359, (m1 or {}).get("FP_359_cpi"))
    except Exception:
        _put(359, (m1 or {}).get("FP_359_cpi"))

    return {
        cpi: basic
        for cpi, basic in out.items()
        if basic is not None and basic > 0 and cpi in CPI_CLASS_34
    }


def _compute_class12_cpi_basics(
    *,
    separation_date: date,
    pay: float,
    scale=None,
    m1_result: dict | None = None,
) -> dict[int, int]:
    """
    Officer (class 1/2) CPI ladder — never includes 359.

    Stores family-pension rate at each stage (30% of officer basic), matching
    fi_pn_family_277_upgrade GENERATED/UPGRADED basics used by arrear:

      1997 last-pay era → CPI 1708
      2007 fitment       → CPI 126
      2017 fitment       → CPI 277
    """
    from family_pension.services.class12_fp_service import (
        Class12FamilyPensionError,
        REVISION_ORDER,
        _block_2007,
        _block_2017,
        _round2,
        calculate_class12_family_pension_for_fp,
        get_class12_start_revision,
    )

    def _fp_at(stage_basic: float) -> int | None:
        return _int_basic(_round2(float(stage_basic) * 0.30))

    out: dict[int, int] = {}
    sep_iso = separation_date.isoformat()
    src = m1_result if m1_result and not m1_result.get("error") else None

    if not src:
        try:
            src = calculate_class12_family_pension_for_fp(
                separation_date=sep_iso,
                last_pay=pay,
                scale=scale,
            )
        except Class12FamilyPensionError:
            src = {}
        except Exception:
            src = {}

    start = (src or {}).get("start_revision") or get_class12_start_revision(sep_iso)
    try:
        start_idx = REVISION_ORDER.index(start)
    except ValueError:
        start_idx = REVISION_ORDER.index("1997")

    basic = float(pay)
    rows: list = []

    if start_idx <= REVISION_ORDER.index("1997"):
        out[1708] = _fp_at(basic)
        basic = _block_2007(basic, rows)
        out[126] = _fp_at(basic)
        if start != "2017":
            basic = _block_2017(basic, rows)
        out[277] = _fp_at(basic)
    elif start_idx <= REVISION_ORDER.index("2007") and start != "2017":
        out[126] = _fp_at(basic)
        basic = _block_2017(basic, rows)
        out[277] = _fp_at(basic)
    else:
        b2017 = _int_basic((src or {}).get("basic_pay_2017")) or _int_basic(basic)
        out[277] = _fp_at(b2017)

    # Prefer explicit FP_277 / basic_pay_2017 from officer result when present
    fp277 = _int_basic((src or {}).get("FP_277_cpi"))
    if fp277 is not None:
        out[277] = fp277
    else:
        b2017 = _int_basic((src or {}).get("basic_pay_2017"))
        if b2017 is not None:
            out[277] = _fp_at(b2017)

    out.pop(359, None)

    return {
        cpi: basic
        for cpi, basic in out.items()
        if basic is not None and basic > 0 and cpi in CPI_CLASS_12
    }


def upsert_cpi_consolidation(
    *,
    claim_id: str,
    emp_cd: str,
    case_no=None,
    emp_class=None,
    cpi_basics: dict[int, int],
    last_pay=None,
    separation_dt=None,
    user_id: str = "SMPK",
) -> list[dict]:
    """
    Insert / update fi_pn_cpi_consolidation for each CPI basic.
    Class 1/2: only 1708/126/277 (drops 359 and any other).
    Class 3/4: 607/1708/126/198/277/359.
    Returns the list of stored rows for this claim.
    """
    cid = _clip(claim_id, 22)
    emp = _emp_key(emp_cd)
    if not cid or not emp or not cpi_basics:
        return []

    user = _clip(user_id, 5) or "SMPK"
    cls = _emp_class_int(emp_class)
    allowed = CPI_CLASS_12 if cls in (1, 2) else CPI_CLASS_34
    # Never keep 359 for class 1/2
    filtered = {
        int(cpi): int(basic)
        for cpi, basic in cpi_basics.items()
        if int(cpi) in allowed and _int_basic(basic)
    }
    if not filtered:
        return []

    sep = _as_date(separation_dt)
    pay = _num(last_pay)
    case_val = None
    if case_no not in (None, ""):
        try:
            case_val = int(float(str(case_no).strip()))
        except (TypeError, ValueError):
            case_val = None

    with connection.cursor() as cur:
        # Drop CPI rows not allowed for this class (e.g. stale 359 on class 1/2)
        placeholders = ", ".join(["%s"] * len(allowed))
        cur.execute(
            f"""
            DELETE FROM fi_pn_cpi_consolidation
             WHERE CLAIM_ID = %s
               AND CPI NOT IN ({placeholders})
            """,
            [cid, *allowed],
        )

        for cpi_i, basic_i in sorted(filtered.items()):
            cur.execute(
                """
                SELECT 1 FROM fi_pn_cpi_consolidation
                WHERE CLAIM_ID = %s AND CPI = %s
                LIMIT 1
                """,
                [cid, cpi_i],
            )
            exists = cur.fetchone() is not None
            if exists:
                cur.execute(
                    """
                    UPDATE fi_pn_cpi_consolidation
                       SET EMP_CD = %s,
                           CASE_NO = COALESCE(%s, CASE_NO),
                           EMP_CLASS = COALESCE(%s, EMP_CLASS),
                           BASIC = %s,
                           LAST_PAY = COALESCE(%s, LAST_PAY),
                           SEPARATION_DT = COALESCE(%s, SEPARATION_DT),
                           DATE_MODIFIED = NOW(),
                           MODIFIED_BY = %s
                     WHERE CLAIM_ID = %s AND CPI = %s
                    """,
                    [
                        emp,
                        case_val,
                        cls,
                        basic_i,
                        pay,
                        sep,
                        user,
                        cid,
                        cpi_i,
                    ],
                )
            else:
                cur.execute(
                    """
                    INSERT INTO fi_pn_cpi_consolidation (
                        CLAIM_ID, EMP_CD, CASE_NO, EMP_CLASS,
                        CPI, BASIC, LAST_PAY, SEPARATION_DT,
                        DATE_CREATED, CREATED_BY
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        NOW(), %s
                    )
                    """,
                    [
                        cid,
                        emp,
                        case_val,
                        cls,
                        cpi_i,
                        basic_i,
                        pay,
                        sep,
                        user,
                    ],
                )

    return load_cpi_consolidation(claim_id=cid)


def load_cpi_consolidation(
    *,
    claim_id: str = None,
    emp_cd: str = None,
) -> list[dict]:
    """Load consolidation rows ordered by CPI."""
    cid = _clip(claim_id, 22) if claim_id else ""
    emp = _emp_key(emp_cd) if emp_cd else ""
    sql = """
        SELECT CLAIM_ID, EMP_CD, CASE_NO, EMP_CLASS, CPI, BASIC,
               LAST_PAY, SEPARATION_DT, DATE_CREATED, CREATED_BY,
               DATE_MODIFIED, MODIFIED_BY
        FROM fi_pn_cpi_consolidation
    """
    params = []
    if cid:
        sql += " WHERE CLAIM_ID = %s"
        params.append(cid)
    elif emp:
        sql += " WHERE EMP_CD = %s"
        params.append(emp)
    else:
        return []
    sql += " ORDER BY CPI"

    with connection.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0].lower() for d in cur.description]
        rows = []
        for r in cur.fetchall():
            row = dict(zip(cols, r))
            for k, v in list(row.items()):
                if isinstance(v, datetime):
                    row[k] = v.date().isoformat()
                elif isinstance(v, date):
                    row[k] = v.isoformat()
                elif isinstance(v, Decimal):
                    row[k] = float(v)
            rows.append(row)
        return rows


def save_cpi_basics_from_methodology(
    *,
    claim_id: str,
    emp_cd: str,
    case_no=None,
    emp_class=None,
    separation_date=None,
    category=None,
    pay=None,
    scale=None,
    m1_result: dict | None = None,
    user_id: str = "SMPK",
    equiv_pay_at_base_cpi=None,
) -> list[dict]:
    """
    Compute CPI basics (Methodology I / class 1-2) and upsert consolidation rows.
    """
    basics = compute_cpi_basics(
        separation_date=separation_date,
        category=category if category is not None else emp_class,
        pay=pay,
        scale=scale,
        m1_result=m1_result,
        equiv_pay_at_base_cpi=equiv_pay_at_base_cpi,
    )
    if not basics:
        return []
    return upsert_cpi_consolidation(
        claim_id=claim_id,
        emp_cd=emp_cd,
        case_no=case_no,
        emp_class=emp_class if emp_class is not None else category,
        cpi_basics=basics,
        last_pay=pay,
        separation_dt=separation_date,
        user_id=user_id,
    )


class CpiUpgradeError(Exception):
    pass


def _fetchone_dict(sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params or [])
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0].lower() for d in cur.description]
        return dict(zip(cols, row))


def _party_names_for_cpi(claim_id: str, emp_cd: str) -> dict:
    emp = _emp_key(emp_cd)
    cid = _clip(claim_id, 22)
    emp_name = ""
    if emp:
        row = _fetchone_dict(
            "SELECT NAME FROM fi_pn_mh_pensioner WHERE EMP_CD = %s LIMIT 1",
            [emp],
        )
        if row and row.get("name"):
            emp_name = str(row["name"]).strip()
        if not emp_name:
            row = _fetchone_dict(
                """
                SELECT TRIM(CONCAT_WS(' ',
                    NULLIF(TITLE,''), NULLIF(FIRST_NAME,''),
                    NULLIF(MIDDLE_NAME,''), NULLIF(LAST_NAME,''))) AS name
                FROM fi_xx_mh_emp_per WHERE EMP_CD = %s LIMIT 1
                """,
                [emp],
            )
            if row and row.get("name"):
                emp_name = str(row["name"]).strip()
    applicant = ""
    if cid:
        row = _fetchone_dict(
            """
            SELECT NAME FROM fi_pn_md_fpen_appcn
            WHERE CLMCA_ID = %s AND FPEN_ACTIVE = 1
            ORDER BY SL_NO LIMIT 1
            """,
            [cid],
        )
        if row and row.get("name"):
            applicant = str(row["name"]).strip()
    return {"emp_name": emp_name, "applicant_name": applicant}


def get_cpi_upgrade_status(*, claim_id: str = None, emp_cd: str = None) -> dict:
    """Load existing consolidation + claim context for the CPI-Upgrade screen."""
    rows = load_cpi_consolidation(claim_id=claim_id, emp_cd=emp_cd)
    cid = _clip(claim_id, 22) if claim_id else ""
    emp = _emp_key(emp_cd) if emp_cd else ""
    if rows:
        cid = _clip(rows[0].get("claim_id"), 22) or cid
        emp = _emp_key(rows[0].get("emp_cd")) or emp

    claim = None
    if cid:
        claim = _fetchone_dict(
            """
            SELECT CLMCA_ID, CA_NO, EMP_CD, CLASS, DOD_EMP_PENSIONER,
                   RETIREMENT_CPI, LAST_BASIC_AT_RET, SCALE_CD
            FROM fi_pn_mh_fpen_caclaim WHERE CLMCA_ID = %s LIMIT 1
            """,
            [cid],
        )
    elif emp:
        claim = _fetchone_dict(
            """
            SELECT CLMCA_ID, CA_NO, EMP_CD, CLASS, DOD_EMP_PENSIONER,
                   RETIREMENT_CPI, LAST_BASIC_AT_RET, SCALE_CD
            FROM fi_pn_mh_fpen_caclaim
            WHERE EMP_CD = %s
            ORDER BY DATE_CREATED DESC LIMIT 1
            """,
            [emp],
        )

    if claim:
        cid = _clip(claim.get("clmca_id"), 22)
        emp = _emp_key(claim.get("emp_cd") or emp)

    names = _party_names_for_cpi(cid, emp) if (cid or emp) else {}
    return {
        "found": bool(rows),
        "claim_id": cid or None,
        "emp_cd": emp or None,
        "case_no": (rows[0].get("case_no") if rows else None)
        or (claim.get("ca_no") if claim else None),
        "emp_class": (rows[0].get("emp_class") if rows else None)
        or (claim.get("class") if claim else None),
        "emp_name": names.get("emp_name") or "",
        "applicant_name": names.get("applicant_name") or "",
        "last_pay": (rows[0].get("last_pay") if rows else None)
        or (_num(claim.get("last_basic_at_ret")) if claim else None),
        "separation_dt": (rows[0].get("separation_dt") if rows else None),
        "rows": rows,
        "message": (
            None
            if rows
            else "No CPI consolidation yet — click Generate CPI Basics."
        ),
    }


def generate_cpi_upgrade_for_employee(
    *,
    claim_id: str = None,
    emp_cd: str = None,
    user_id: str = "SMPK",
) -> dict:
    """
    Manual CPI-Upgrade menu: resolve claim + pay/class/sep, run Methodology,
    upsert fi_pn_cpi_consolidation for older employees before arrear.
    """
    from family_pension.services.class12_fp_service import (
        load_familypensioner_app_class,
    )

    cid = _clip(claim_id, 22) if claim_id else ""
    emp = _emp_key(emp_cd) if emp_cd else ""

    if cid:
        claim = _fetchone_dict(
            """
            SELECT CLMCA_ID, CA_NO, EMP_CD, CLASS, DOD_EMP_PENSIONER,
                   RETIREMENT_CPI, LAST_BASIC_AT_RET, SCALE_CD
            FROM fi_pn_mh_fpen_caclaim WHERE CLMCA_ID = %s LIMIT 1
            """,
            [cid],
        )
    elif emp:
        claim = _fetchone_dict(
            """
            SELECT CLMCA_ID, CA_NO, EMP_CD, CLASS, DOD_EMP_PENSIONER,
                   RETIREMENT_CPI, LAST_BASIC_AT_RET, SCALE_CD
            FROM fi_pn_mh_fpen_caclaim
            WHERE EMP_CD = %s
            ORDER BY DATE_CREATED DESC LIMIT 1
            """,
            [emp],
        )
    else:
        raise CpiUpgradeError("emp_cd or claim_id is required")

    if not claim:
        raise CpiUpgradeError(
            "No family-pension claim found for this employee. "
            "Save the claim first, then generate CPI basics."
        )

    cid = _clip(claim.get("clmca_id"), 22)
    emp = _emp_key(claim.get("emp_cd") or emp)
    case_no = claim.get("ca_no")

    fp_class = load_familypensioner_app_class(emp)
    emp_class = fp_class if fp_class is not None else claim.get("class")
    if emp_class is None:
        fin = _fetchone_dict(
            "SELECT EMP_CLASS FROM fi_xx_mh_emp_fin WHERE EMP_CD = %s LIMIT 1",
            [emp],
        ) or {}
        emp_class = fin.get("emp_class") or 3

    pensioner = _fetchone_dict(
        """
        SELECT EMP_RET_DT, PENSION_EMOLUMENTS, ORIGINAL_PENSION_AMT
        FROM fi_pn_mh_pensioner WHERE EMP_CD = %s LIMIT 1
        """,
        [emp],
    ) or {}
    adm = _fetchone_dict(
        """
        SELECT SEPARATION_DT FROM fi_xx_mh_emp_adm
        WHERE EMP_CD = %s LIMIT 1
        """,
        [emp],
    ) or {}

    sep_dt = _as_date(adm.get("separation_dt")) or _as_date(
        pensioner.get("emp_ret_dt")
    )
    last_pay = _num(claim.get("last_basic_at_ret")) or _num(
        pensioner.get("pension_emoluments")
    )
    scale = _clip(claim.get("scale_cd"), 20) or None

    if not sep_dt:
        raise CpiUpgradeError(
            f"Separation / retirement date missing for employee {emp}."
        )
    if not last_pay:
        raise CpiUpgradeError(
            f"Last basic pay missing on claim / pensioner for employee {emp}."
        )

    cat = str(int(float(emp_class)))
    rows = save_cpi_basics_from_methodology(
        claim_id=cid,
        emp_cd=emp,
        case_no=case_no,
        emp_class=emp_class,
        separation_date=sep_dt,
        category=cat,
        pay=last_pay,
        scale=scale,
        user_id=user_id,
    )
    if not rows:
        raise CpiUpgradeError(
            "Methodology could not produce CPI basics for this employee "
            "(check class, last pay, scale, and separation date)."
        )

    names = _party_names_for_cpi(cid, emp)
    return {
        "ok": True,
        "message": "CPI basics generated and saved to fi_pn_cpi_consolidation.",
        "claim_id": cid,
        "emp_cd": emp,
        "case_no": case_no,
        "emp_class": _emp_class_int(emp_class),
        "emp_name": names.get("emp_name") or "",
        "applicant_name": names.get("applicant_name") or "",
        "last_pay": last_pay,
        "separation_dt": sep_dt.isoformat(),
        "scale": scale,
        "rows": rows,
    }
