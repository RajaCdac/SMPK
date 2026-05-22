from methodology2.services.excel_loader import (
    load_Matrix_2017_table,
    load_Matrix_2022_table,
)


def normalize_scale_for_matrix(scale_string):
    """PayScale uses stages (14900-10-34600); matrix uses span (14900-34600)."""
    if not scale_string:
        return ""
    parts = [
        int(x)
        for x in str(scale_string).replace(" ", "").split("-")
        if str(x).isdigit()
    ]
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[-1]}"
    return str(scale_string).strip()


def _match_matrix_column(first_row, pre_revised_scale):
    target = normalize_scale_for_matrix(pre_revised_scale)
    for column in first_row.index:
        cell_value = normalize_scale_for_matrix(first_row[column])
        if cell_value == target:
            return column
    return None


def get_matrix_column_2017(pre_revised_scale):
    df = load_Matrix_2017_table()
    return _match_matrix_column(df.iloc[0], pre_revised_scale)

def get_next_matrix_pay_2017(pre_revised_scale,current_pay):
    df = load_Matrix_2017_table()
    column = get_matrix_column_2017(
        pre_revised_scale
    )
    if column is None:
        return None
    matrix_values = df[
        column
    ].iloc[3:].dropna().tolist()
    matrix_values = [
        int(value)
        for value in matrix_values
    ]
    for value in matrix_values:
        if value >= current_pay:
            return value
    return matrix_values[-1]

def get_matrix_column_2022(pre_revised_scale):
    df = load_Matrix_2022_table()
    return _match_matrix_column(df.iloc[0], pre_revised_scale)

def get_next_matrix_pay_2022(pre_revised_scale,current_pay):
    df = load_Matrix_2022_table()
    column = get_matrix_column_2022(
        pre_revised_scale
    )
    if column is None:
        return None
    matrix_values = df[
        column
    ].iloc[3:].dropna().tolist()
    matrix_values = [
        int(value)
        for value in matrix_values
    ]
    for value in matrix_values:
        if value >= current_pay:
            return value
    return matrix_values[-1]

def fix_pay_in_matrix_2022(pre_revised_scale, current_pay):
    revised_pay = get_next_matrix_pay_2022(
        pre_revised_scale,
        current_pay
    )
    return revised_pay

def fix_pay_in_matrix_2017(pre_revised_scale, current_pay):
    revised_pay = get_next_matrix_pay_2017(
        pre_revised_scale,
        current_pay
    )
    return revised_pay




