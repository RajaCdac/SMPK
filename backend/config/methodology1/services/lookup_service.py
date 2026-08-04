from methodology1.services.excel_loader import (
    load_pay_scale_table
)


def get_scale_by_code(scale_code):

    df = load_pay_scale_table()

    result = df[
        df['Scale'] == scale_code
    ]

    if result.empty:
        return None

    return result.iloc[0].to_dict()