"""Persist Oracle API results in MySQL for offline use."""

import logging

from django.conf import settings
from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError

from first_pension.models import (
    CachedEmployeeOracleDetail,
    CachedRetirementEmployee,
    DashboardMonthSnapshot,
)

logger = logging.getLogger(__name__)

_DB_UNAVAILABLE = (OperationalError, ProgrammingError)


def _safe_cache_op(label, fn, default=None):
    """Run a cache DB op; return default when first_pension tables are missing."""
    try:
        return fn()
    except _DB_UNAVAILABLE as exc:
        logger.debug("%s cache unavailable: %s", label, exc)
        return default


def cache_enabled():
    return getattr(settings, "ORACLE_LOCAL_CACHE_ENABLED", True)


def sync_dashboard_to_cache(month, year, payload):
    if not cache_enabled():
        return

    retirement_list = payload.get("retirement_list") or []

    def _write():
        with transaction.atomic():
            DashboardMonthSnapshot.objects.update_or_create(
                month=month,
                year=year,
                defaults={
                    "total_employees": payload.get("total_employees"),
                    "prev_month_count": payload.get("prev_month_count", 0),
                    "retirement_count": payload.get("retirement_count", 0),
                    "next_month_count": payload.get("next_month_count", 0),
                    "prev_month_label": payload.get("prev_month_label", ""),
                    "this_month_label": payload.get("this_month_label", ""),
                    "next_month_label": payload.get("next_month_label", ""),
                },
            )

            CachedRetirementEmployee.objects.filter(
                retirement_month=month,
                retirement_year=year,
            ).delete()

            rows = []
            for row in retirement_list:
                emp_code = str(row.get("emp_code", "")).strip()
                if not emp_code:
                    continue
                rows.append(
                    CachedRetirementEmployee(
                        emp_code=emp_code,
                        retirement_month=month,
                        retirement_year=year,
                        name=row.get("name") or "",
                        joining_date=row.get("joining_date") or "",
                        retirement_date=row.get("retirement_date") or "",
                        birth_date=row.get("birth_date") or "",
                        age_on_appointment=row.get("age_on_appointment"),
                        age_on_retirement=row.get("age_on_retirement"),
                        designation=row.get("designation") or "",
                        scale=row.get("scale") or "",
                        last_basic=row.get("last_basic"),
                        emp_class=row.get("class") or "",
                        row_payload=row,
                    )
                )
            if rows:
                CachedRetirementEmployee.objects.bulk_create(rows, batch_size=500)
        return True

    if not _safe_cache_op("sync_dashboard", _write, default=False):
        return

    logger.info(
        "Synced dashboard cache for %s/%s (%s employees)",
        month,
        year,
        len(retirement_list),
    )


def load_dashboard_from_cache(month, year):
    if not cache_enabled():
        return None

    def _load():
        snapshot = DashboardMonthSnapshot.objects.filter(
            month=month, year=year
        ).first()
        if snapshot is None:
            return None

        cached_rows = CachedRetirementEmployee.objects.filter(
            retirement_month=month,
            retirement_year=year,
        ).order_by("emp_code")

        retirement_list = []
        for row in cached_rows:
            if row.row_payload:
                retirement_list.append(row.row_payload)
            else:
                retirement_list.append({
                    "emp_code": row.emp_code,
                    "name": row.name,
                    "joining_date": row.joining_date or None,
                    "retirement_date": row.retirement_date or None,
                    "birth_date": row.birth_date or None,
                    "age_on_appointment": row.age_on_appointment,
                    "age_on_retirement": row.age_on_retirement,
                    "designation": row.designation,
                    "scale": row.scale,
                    "last_basic": (
                        float(row.last_basic)
                        if row.last_basic is not None
                        else None
                    ),
                    "class": row.emp_class,
                })

        return {
            "total_employees": snapshot.total_employees,
            "retirement_count": snapshot.retirement_count,
            "retirement_list": retirement_list,
            "prev_month_count": snapshot.prev_month_count,
            "next_month_count": snapshot.next_month_count,
            "prev_month_label": snapshot.prev_month_label,
            "this_month_label": snapshot.this_month_label,
            "next_month_label": snapshot.next_month_label,
            "retirement_month": month,
            "retirement_year": year,
            "synced_at": (
                snapshot.synced_at.isoformat() if snapshot.synced_at else None
            ),
        }

    return _safe_cache_op("load_dashboard", _load, default=None)


_EMPLOYEE_MYSQL_CONTEXT_KEYS = frozenset({
    "commutation_exists",
    "commutation_data",
    "no_pay_exists",
    "no_pay_data",
    "process_intake_completed",
    "process_intake_data",
    "proposal_exists",
    "proposal_data",
    "amount_exists",
    "amount_data",
})


def employee_oracle_cache_slice(employee_data):
    """Store Oracle fields only; MySQL workflow data is refreshed on each read."""
    return {
        k: v
        for k, v in employee_data.items()
        if k not in _EMPLOYEE_MYSQL_CONTEXT_KEYS
    }


def sync_employee_search_to_cache(emp_key, employee_data):
    if not cache_enabled():
        return

    emp_code = str(emp_key).strip()
    if not emp_code:
        return

    def _write():
        CachedEmployeeOracleDetail.objects.update_or_create(
            emp_code=emp_code,
            defaults={"payload": employee_oracle_cache_slice(employee_data)},
        )
        return True

    if not _safe_cache_op("sync_employee", _write, default=False):
        return
    logger.info("Synced employee Oracle cache for %s", emp_code)


def load_employee_from_cache(emp_key):
    if not cache_enabled():
        return None

    emp_code = str(emp_key).strip()

    def _load():
        row = CachedEmployeeOracleDetail.objects.filter(emp_code=emp_code).first()
        if row is None:
            return None
        return dict(row.payload)

    return _safe_cache_op("load_employee", _load, default=None)


def merge_cached_employee_with_db(cached_oracle, db_context, *, merge_proposal_bank):
    """Combine cached Oracle row with current MySQL pension-case context."""
    merged = {**cached_oracle, **db_context}
    proposal_data = db_context.get("proposal_data")
    if proposal_data:
        merged["proposal_data"] = merge_proposal_bank(
            proposal_data,
            cached_oracle.get("proposal_defaults") or {},
        )
    merged["partial"] = False
    merged["data_source"] = "cache"
    return merged
