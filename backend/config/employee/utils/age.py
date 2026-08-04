from dateutil.relativedelta import relativedelta


def calculate_age(dob, other_date):
    """Return {years, months, days} between dob and other_date (date/datetime)."""
    if dob is None or other_date is None:
        return None
    if other_date < dob:
        return None
    diff = relativedelta(other_date, dob)
    return {"years": diff.years, "months": diff.months, "days": diff.days}
