from methodology2.services.excel_loader import (load_special_allowance_table,load_special_da_table,load_fixed_da_table)


def get_special_da(pay):
    df = load_special_da_table()
    result = df[
        (df['Lower'] <= pay) &
        (df['Upper'] >= pay)
    ]
    if result.empty:
        return None
    return float(
        result.iloc[0]['S.D.A']
    )


def get_special_da_options():
    """Distinct S.D.A values from the SpecialDA worksheet, ascending."""
    df = load_special_da_table()
    values = sorted({float(v) for v in df['S.D.A'].dropna().tolist()})
    return values


def get_special_da_1980(pay):
    df = load_special_allowance_table()
    result = df[
        (df['Lower'] <= pay) &
        (df['Upper'] >= pay)
    ]
    if result.empty:
        return None
    return float(
        result.iloc[0]['S.D.A']
    )

def get_fixed_da_1988(revised_pay):
    df = load_fixed_da_table()
    result = df[
        (df['Lower'] <= revised_pay) &
        (df['Upper'] >= revised_pay)
    ]
    if result.empty:
        return None
    return float(
        result.iloc[0]['FDA']
    )