"""DA percent lookup from fi_pr_mh_calc_da (MySQL mirror + optional Oracle)."""

from datetime import date, datetime
from decimal import Decimal

from employee.services.oracle_service import oracle_reads_enabled, try_oracle_connection

from ..oracle_mirror import FiPrMhCalcDa


def ada_quarter_start_month(wg_end_dt):
    month = wg_end_dt.month
    if month in (1, 2, 3):
        return 1
    if month in (4, 5, 6):
        return 4
    if month in (7, 8, 9):
        return 7
    return 10


def emp_class_grp(emp_class):
    """Map employee class to FI_PR_MH_CALC_DA.EMP_CLASS_GRP (I/II→1, III/IV→3)."""
    key = str(emp_class or "III").strip().upper()
    if key in ("1", "I", "2", "II"):
        return 1
    return 3


def _normalize_emp_type(emp_type):
    text = str(emp_type or "RE").strip().upper()
    return "RE" if text == "DL" else text


def _as_date(value):
    if value is None:
        return None
    if hasattr(value, "date") and callable(value.date):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    return value


def _quarter_wef_dt(reference_dt):
    ref = _as_date(reference_dt)
    if not ref:
        return None
    q_month = ada_quarter_start_month(ref)
    return date(ref.year, q_month, 1)


def _lookup_calc_da_mysql(wef_dt, emp_class, emp_type="RE"):
    grp = emp_class_grp(emp_class)
    emp_type = _normalize_emp_type(emp_type)
    wef_dt = _as_date(wef_dt)

    row = FiPrMhCalcDa.objects.filter(
        emp_type=emp_type,
        emp_class_grp=grp,
        wef_dt__date=wef_dt,
    ).first()
    if row and row.da_pct is not None:
        return Decimal(str(row.da_pct)), wef_dt

    row = (
        FiPrMhCalcDa.objects.filter(
            emp_type=emp_type,
            emp_class_grp=grp,
            wef_dt__date__lte=wef_dt,
        )
        .order_by("-wef_dt")
        .first()
    )
    if row and row.da_pct is not None:
        return Decimal(str(row.da_pct)), _as_date(row.wef_dt)
    return None, wef_dt


def _lookup_calc_da_oracle(cur, wef_dt, emp_class, emp_type="RE"):
    grp = emp_class_grp(emp_class)
    emp_type = _normalize_emp_type(emp_type)
    wef_dt = _as_date(wef_dt)
    cur.execute(
        """
        SELECT DA_PCT, WEF_DT FROM (
            SELECT DA_PCT, WEF_DT
            FROM FINANCE.FI_PR_MH_CALC_DA
            WHERE DECODE(EMP_TYPE, 'DL', 'RE') = :emp_type
              AND EMP_CLASS_GRP = :grp
              AND WEF_DT <= :wef
            ORDER BY WEF_DT DESC
        ) WHERE ROWNUM = 1
        """,
        {"emp_type": emp_type, "grp": grp, "wef": wef_dt},
    )
    row = cur.fetchone()
    if not row or row[0] is None:
        return None, wef_dt
    found_wef = row[1].date() if hasattr(row[1], "date") else row[1]
    return Decimal(str(row[0])), found_wef


def _cache_calc_da(wef_dt, emp_class, da_pct, emp_type="RE"):
    wef_dt = _as_date(wef_dt)
    emp_type = _normalize_emp_type(emp_type)
    grp = emp_class_grp(emp_class)
    row = FiPrMhCalcDa.objects.filter(
        emp_type=emp_type,
        emp_class_grp=grp,
        wef_dt__date=wef_dt,
    ).first()
    if row:
        row.da_pct = da_pct
        row.save(update_fields=["da_pct"])
        return
    FiPrMhCalcDa.objects.create(
        wef_dt=wef_dt,
        emp_type=emp_type,
        emp_class_grp=grp,
        da_pct=da_pct,
    )


def lookup_latest_calc_da_percent(emp_class, *, emp_type="RE"):
    grp = emp_class_grp(emp_class)
    emp_type = _normalize_emp_type(emp_type)
    row = (
        FiPrMhCalcDa.objects.filter(emp_type=emp_type, emp_class_grp=grp)
        .order_by("-wef_dt")
        .first()
    )
    if row and row.da_pct is not None:
        return Decimal(str(row.da_pct))

    if oracle_reads_enabled():
        conn = try_oracle_connection()
        if conn is not None:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    SELECT DA_PCT, WEF_DT FROM (
                        SELECT DA_PCT, WEF_DT
                        FROM FINANCE.FI_PR_MH_CALC_DA
                        WHERE DECODE(EMP_TYPE, 'DL', 'RE') = :emp_type
                          AND EMP_CLASS_GRP = :grp
                        ORDER BY WEF_DT DESC
                    ) WHERE ROWNUM = 1
                    """,
                    {"emp_type": emp_type, "grp": grp},
                )
                row = cur.fetchone()
                if row and row[0] is not None:
                    found_wef = row[1].date() if hasattr(row[1], "date") else row[1]
                    pct = Decimal(str(row[0]))
                    _cache_calc_da(found_wef, emp_class, pct, emp_type)
                    return pct
            finally:
                cur.close()
                conn.close()

    raise ValueError(
        f"No DA% in fi_pr_mh_calc_da for class {emp_class} (grp {grp})"
    )


def lookup_calc_da_percent(reference_dt, emp_class, *, emp_type="RE"):
    """DA% from fi_pr_mh_calc_da for the quarter containing reference_dt."""
    if not reference_dt:
        return lookup_latest_calc_da_percent(emp_class, emp_type=emp_type)

    wef_dt = _quarter_wef_dt(reference_dt)
    pct, _ = _lookup_calc_da_mysql(wef_dt, emp_class, emp_type)
    if pct is not None:
        return pct

    if oracle_reads_enabled():
        conn = try_oracle_connection()
        if conn is not None:
            cur = conn.cursor()
            try:
                pct, found_wef = _lookup_calc_da_oracle(
                    cur, wef_dt, emp_class, emp_type
                )
                if pct is not None:
                    _cache_calc_da(found_wef, emp_class, pct, emp_type)
                    return pct
            finally:
                cur.close()
                conn.close()

    raise ValueError(
        f"No DA% in fi_pr_mh_calc_da for class {emp_class} "
        f"(grp {emp_class_grp(emp_class)}) effective {wef_dt}"
    )


def flat_class_da_percent(emp_class, reference_dt=None):
    """Class DA% from fi_pr_mh_calc_da (as-of quarter or latest row)."""
    if reference_dt:
        return lookup_calc_da_percent(reference_dt, emp_class)
    return lookup_latest_calc_da_percent(emp_class)


def lookup_ada_da_percent(wg_end_dt, emp_class=None):
    """DA% for gratuity increment-month emoluments (fi_pr_mh_calc_da quarterly rate)."""
    if not wg_end_dt:
        return flat_class_da_percent(emp_class)
    return lookup_calc_da_percent(wg_end_dt, emp_class)


def sync_calc_da_rates_from_oracle():
    """Pull all RE rows from Oracle FI_PR_MH_CALC_DA into MySQL."""
    conn = try_oracle_connection()
    if conn is None:
        raise RuntimeError("Oracle connection is not available.")
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT WEF_DT, DECODE(EMP_TYPE, 'DL', 'RE'), EMP_CLASS_GRP, DA_PCT
            FROM FINANCE.FI_PR_MH_CALC_DA
            WHERE DECODE(EMP_TYPE, 'DL', 'RE') = 'RE'
            ORDER BY WEF_DT
            """
        )
        count = 0
        for wef_dt, emp_type, grp, da_pct in cur.fetchall():
            if wef_dt is None or da_pct is None:
                continue
            if hasattr(wef_dt, "date"):
                wef_dt = wef_dt.date()
            existing = FiPrMhCalcDa.objects.filter(
                emp_type=str(emp_type or "RE")[:2],
                emp_class_grp=int(grp),
                wef_dt__date=wef_dt,
            ).first()
            if existing:
                existing.da_pct = Decimal(str(da_pct))
                existing.save(update_fields=["da_pct"])
            else:
                FiPrMhCalcDa.objects.create(
                    wef_dt=wef_dt,
                    emp_type=str(emp_type or "RE")[:2],
                    emp_class_grp=int(grp),
                    da_pct=Decimal(str(da_pct)),
                )
            count += 1
        return count
    finally:
        cur.close()
        conn.close()


def sync_ada_rates_from_oracle():
    """Backward-compatible alias — sync fi_pr_mh_calc_da from Oracle."""
    return sync_calc_da_rates_from_oracle()
