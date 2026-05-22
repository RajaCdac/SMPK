from methodology2.services.excel_loader import (load_pay_scale_table)
from methodology2.services.revision_resolver import (get_revision_column)

def get_available_scales(retirement_date):
    revision_column = get_revision_column(retirement_date)
    df = load_pay_scale_table()
    scales = df[revision_column].dropna().tolist()
    return scales


def get_equivalent_scales_by_scale(
    retirement_date,
    selected_scale
):

    revision_column = get_revision_column(retirement_date)
    df = load_pay_scale_table()
    result = df[
        df[revision_column] == selected_scale
    ]

    if result.empty:
        return None

    data = result.iloc[0].to_dict()

    revision_columns = [
        '1979(REVISED PAY SCALE)',
        '1984(REVISED PAY SCALE)',
        '1988(607 CPI)',
        '1993(1030 CPI)',
        '1997(1708 CPI)',
        '2007(126 CPI)',
        '2012(198 CPI)',
        '2017(277 CPI)',
        '2022(359 CPI)'
    ]

    start_column = get_revision_column(
        retirement_date
    )

    start_index = revision_columns.index(
        start_column
    )

    filtered_data = {}

    for column in revision_columns[start_index:]:

        filtered_data[column] = data[column]

    return filtered_data

def get_next_revision(
    current_revision
):

    revision_columns = [
        '1979(REVISED PAY SCALE)',
        '1984(REVISED PAY SCALE)',
        '1988(607 CPI)',
        '1993(1030 CPI)',
        '1997(1708 CPI)',
        '2007(126 CPI)',
        '2012(198 CPI)',
        '2017(277 CPI)',
        '2022(359 CPI)'
    ]
    current_index = revision_columns.index(
        current_revision
    )
    return revision_columns[
        current_index + 1
    ]
# The following functions are for stage-based scales/
def is_stage_based_scale(revision_name):
    non_stage_revisions = [
        # '2007(126 CPI)',
        # '2012(198 CPI)'
        #  '2017(277 CPI)',
        #  '2022(359 CPI)'
    ]
    return revision_name not in non_stage_revisions