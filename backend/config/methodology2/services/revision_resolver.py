from datetime import datetime


def get_revision_column(retirement_date):

    if isinstance(retirement_date, str):

        retirement_date = datetime.strptime(
            retirement_date,
            '%Y-%m-%d'
        )

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