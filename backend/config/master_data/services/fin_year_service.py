"""Financial year lookup helpers (MySQL mirror may return datetime for date columns)."""

from datetime import date, datetime

from master_data.models import FiXxXxMHFinCtrl


def as_calendar_date(value):
    if isinstance(value, datetime):
        return value.date()
    return value


def fin_year_for_date(ref_date, *, fin_stat=0):
    """Return FIN_YR whose YR_ST_DT..YR_END_DT contains ref_date."""
    target = as_calendar_date(ref_date)
    if not target:
        return None
    for fy in FiXxXxMHFinCtrl.objects.filter(fin_stat=fin_stat).order_by("-fin_yr"):
        start = as_calendar_date(fy.yr_st_dt)
        end = as_calendar_date(fy.yr_end_dt)
        if start and end and start <= target <= end:
            return fy.fin_yr
    return None


def fin_year_for_month(month, year, *, fin_stat=0):
    """Return FIN_YR for a calendar month (uses first day of month)."""
    return fin_year_for_date(date(int(year), int(month), 1), fin_stat=fin_stat)
