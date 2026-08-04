from methodology1.services.excel_loader import (load_pay_scale_table)
from methodology1.services.revision_resolver import (get_revision_column)
from methodology1.services.scale_parser import generate_pay_stages

def _normalize_scale_text(value):
    return "".join(str(value or "").split())


def format_scale_label(scale_string):
    stages = generate_pay_stages(scale_string)
    if len(stages) >= 2:
        return f"{stages[0]} - {stages[-1]}"
    return str(scale_string or "").strip()


def get_available_scales(retirement_date):
    revision_column = get_revision_column(retirement_date)
    df = load_pay_scale_table()
    scales = df[revision_column].dropna().tolist()
    return scales


def get_available_scale_options(retirement_date):
    return [
        {
            "scale": str(scale).strip(),
            "label": format_scale_label(scale),
        }
        for scale in get_available_scales(retirement_date)
    ]


def resolve_full_scale(retirement_date, selected_scale):
    """
    Resolve a dropdown label or short min-max form to the full PayScale string.
    Accepts e.g. ``2010-2830`` and returns ``2010-35-2290-45-2830``.
    """
    if not selected_scale:
        return None

    text = str(selected_scale).strip()
    if get_equivalent_scales_by_scale(retirement_date, text):
        return text

    target = _normalize_scale_text(text)
    for scale in get_available_scales(retirement_date):
        if _normalize_scale_text(scale) == target:
            return str(scale).strip()

    parts = [part.strip() for part in text.split("-") if part.strip()]
    if len(parts) == 2:
        try:
            minimum, maximum = int(parts[0]), int(parts[1])
        except ValueError:
            return text

        matches = []
        for scale in get_available_scales(retirement_date):
            stages = generate_pay_stages(scale)
            if stages and stages[0] == minimum and stages[-1] == maximum:
                matches.append(str(scale).strip())

        if len(matches) == 1:
            return matches[0]

    return text


def get_equivalent_scales_by_scale(
    retirement_date,
    selected_scale
):

    revision_column = get_revision_column(retirement_date)
    df = load_pay_scale_table()
    target = _normalize_scale_text(selected_scale)
    column_norm = df[revision_column].astype(str).map(_normalize_scale_text)
    result = df[column_norm == target]

    if result.empty and revision_column != "1993(1030 CPI)":
        alt_norm = df["1993(1030 CPI)"].astype(str).map(_normalize_scale_text)
        result = df[alt_norm == target]

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
    min_index = min(
        start_index,
        revision_columns.index("1988(607 CPI)"),
    )

    filtered_data = {}

    for column in revision_columns[min_index:]:

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