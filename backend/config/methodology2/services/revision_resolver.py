from datetime import date, datetime, timedelta


def methodology2_calc_as_of_date(reference_date):
    """
    Day before separation/retirement for Methodology 2 scale & revision calc.

    Pay-revision WEF dates (e.g. 01-Jan-2017) open a new scale set. An employee
    who separates on that day still holds the previous scale through the prior
    calendar day. Frontend keeps the real separation date; only calculation uses
    this as-of date (e.g. sep 01-01-2017 → calc as on 31-12-2016 → 2012 column).
    """
    if reference_date is None or reference_date == "":
        return None

    if isinstance(reference_date, datetime):
        d = reference_date.date()
    elif isinstance(reference_date, date):
        d = reference_date
    else:
        text = str(reference_date).strip()[:10]
        d = datetime.strptime(text, "%Y-%m-%d").date()

    return datetime.combine(d - timedelta(days=1), datetime.min.time())


def get_revision_column(retirement_date):
    retirement_date = methodology2_calc_as_of_date(retirement_date)
    if retirement_date is None:
        raise ValueError("retirement_date is required")

    if retirement_date <= datetime(1983, 12, 31):
        return '1979(REVISED PAY SCALE)'
    elif retirement_date <= datetime(1987, 12, 31):
        return '1984(REVISED PAY SCALE)'
    elif retirement_date <= datetime(1992, 12, 31):
        return '1988(607 CPI)'
    elif retirement_date <= datetime(1996, 12, 31):
        return '1993(1030 CPI)'
    elif retirement_date <= datetime(2006, 12, 31):
        return '1997(1708 CPI)'
    elif retirement_date <= datetime(2011, 12, 31):
        return '2007(126 CPI)'
    elif retirement_date <= datetime(2016, 12, 31):
        return '2012(198 CPI)'
    elif retirement_date <= datetime(2021, 12, 31):
        return '2017(277 CPI)'
    else:
        return '2022(359 CPI)'
