from datetime import datetime

REVISION_ORDER = [
    "1979(REVISED PAY SCALE)",
    "1984(REVISED PAY SCALE)",
    "1988(607 CPI)",
    "1993(1030 CPI)",
    "1997(1708 CPI)",
    "2007(126 CPI)",
    "2012(198 CPI)",
    "2017(277 CPI)",
    "2022(359 CPI)",
]

# CPI effective dates — last pay at separation already includes these.
CPI_EFFECTIVE_DATE = {
    "1979(REVISED PAY SCALE)": datetime(1979, 1, 1),
    "1984(REVISED PAY SCALE)": datetime(1984, 1, 1),
    "1988(607 CPI)": datetime(1988, 1, 1),
    "1993(1030 CPI)": datetime(1994, 1, 1),
    "1997(1708 CPI)": datetime(1997, 1, 1),
    "2007(126 CPI)": datetime(2007, 1, 1),
    "2012(198 CPI)": datetime(2012, 1, 1),
    "2017(277 CPI)": datetime(2017, 1, 1),
    "2022(359 CPI)": datetime(2022, 1, 1),
}


def _parse_date(value):
    if isinstance(value, str):
        return datetime.strptime(value[:10], "%Y-%m-%d")
    return value


def is_1030_direct_607_period(separation_date):
    """
    Separation 01/01/1995–31/12/1996: last pay → 607 CPI at flat 30%
    (no parallel mapping, no 607 slab bands).
    """
    dt = _parse_date(separation_date)
    return datetime(1995, 1, 1) <= dt <= datetime(1996, 12, 31)


def is_pre_1988_separation(separation_date):
    """Separation before 01/01/1988 (1979 / 1984 revised pay scales)."""
    return _parse_date(separation_date) < datetime(1988, 1, 1)


def get_revision_column(retirement_date):
    """Which pay-scale column applies (for scale lookup in Excel)."""
    retirement_date = _parse_date(retirement_date)

    if retirement_date <= datetime(1983, 12, 31):
        return "1979(REVISED PAY SCALE)"
    if retirement_date <= datetime(1987, 12, 31):
        return "1984(REVISED PAY SCALE)"
    if retirement_date <= datetime(1992, 12, 31):
        return "1988(607 CPI)"
    if retirement_date <= datetime(1996, 12, 31):
        return "1993(1030 CPI)"
    if retirement_date <= datetime(2006, 12, 31):
        return "1997(1708 CPI)"
    if retirement_date <= datetime(2011, 12, 31):
        return "2007(126 CPI)"
    if retirement_date <= datetime(2016, 12, 31):
        return "2012(198 CPI)"
    if retirement_date <= datetime(2021, 12, 31):
        return "2017(277 CPI)"
    return "2022(359 CPI)"


def get_calculation_start_revision(separation_date):
    """
    First CPI stage to apply fitment on last pay.

    Last pay already reflects every CPI whose effective date is on or before
    separation date, so those stages are skipped (e.g. sep 2018 → 359 only;
    sep 2001 → 126 onward, not 1708).
    """
    dt = _parse_date(separation_date)
    revision = get_revision_column(dt)
    idx = REVISION_ORDER.index(revision)

    while idx < len(REVISION_ORDER) - 1:
        effective = CPI_EFFECTIVE_DATE.get(REVISION_ORDER[idx])
        if effective and dt >= effective:
            idx += 1
        else:
            break

    return REVISION_ORDER[idx]


def revision_index(revision):
    return REVISION_ORDER.index(revision)
