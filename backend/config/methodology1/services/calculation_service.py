"""
Methodology I row-wise calculation (M2_34), keyed by retirement revision.
Rounding: ROUNDUP to next 10 (rows 51, 55, 2012 basic carry);
          nearest rupee on row 59 (Notional Pay as on 01.01.2017);
          row 60 from 2017 matrix fitment on row 59 (2012 scale column).
"""

from methodology1.services.matrix_service import (
    fix_pay_in_matrix_2017,
    fix_pay_in_matrix_2022,
)
from methodology1.services.rounding_helpers import (
    round2,
    round_nearest_rupee,
    round_up_to_10,
    round_up_whole_rupee,
)
from methodology1.services.scale_parser import (
    align_pay_with_increment,
    align_pay_without_increment,
    fix_pay_in_scale,
)
from methodology1.services.cpi_chain_service import (
    compute_277,
    get_607_chain_pay,
    separation_scale_chain_pay,
)
from methodology1.services.sda_service import (
    get_fixed_da_1988,
    get_special_da,
    get_special_da_1980,
)

try:
    from methodology1.services.excel_loader import load_da_1992_table
except Exception:
    load_da_1992_table = None

CPI_607_REVISION = "1988(607 CPI)"
CPI_607_LOW_PAY_CAP = 1499
CPI_607_LOW_PAY_FACTOR = 0.30
CPI_607_LOW_PAY_MIN = 375
CPI_607_MID_PAY_LOWER = 1500
CPI_607_MID_PAY_MAX = 3000
CPI_607_MID_PAY_FACTOR = 0.20
CPI_607_MIN_20 = 450
CPI_607_HIGH_PAY_LOWER = 3001
CPI_607_MIN_15 = 600


def _apply_607_factor(pay, factor, minimum):
    return max(round2(pay * factor), minimum)


def _resolve_starting_last_pay(current_revision, last_pay):
    """
    Methodology I at 607 CPI:
    - pay <= 1499           -> max(pay * 30%, 375)
    - 1500 < pay <= 3000    -> max(pay * 20%, 450)
    - pay > 3001            -> max(pay * 15%, 600)
    - otherwise             -> last pay as-is
    """
    pay = float(last_pay)
    if current_revision != CPI_607_REVISION:
        return pay, None

    if pay <= CPI_607_LOW_PAY_CAP:
        effective = _apply_607_factor(
            pay, CPI_607_LOW_PAY_FACTOR, CPI_607_LOW_PAY_MIN
        )
        return effective, {
            "rule": "607_cpi_30",
            "factor": CPI_607_LOW_PAY_FACTOR,
            "minimum": CPI_607_LOW_PAY_MIN,
            "description": "pay ≤ 1499 at 30% (min 375)",
        }

    if CPI_607_MID_PAY_LOWER < pay <= CPI_607_MID_PAY_MAX:
        effective = _apply_607_factor(
            pay, CPI_607_MID_PAY_FACTOR, CPI_607_MIN_20
        )
        return effective, {
            "rule": "607_cpi_20",
            "factor": CPI_607_MID_PAY_FACTOR,
            "minimum": CPI_607_MIN_20,
            "description": "1500 < pay ≤ 3000 at 20% (min 450)",
        }

    if pay > CPI_607_HIGH_PAY_LOWER:
        effective = _apply_607_factor(pay, 0.15, CPI_607_MIN_15)
        return effective, {
            "rule": "607_cpi_15_high",
            "factor": 0.15,
            "minimum": CPI_607_MIN_15,
            "description": "pay > 3001 at 15% (min 600)",
        }

    return pay, None


def _da_relief_from_pay(pay):
    """DA relief based on pay from 607 CPI (1030 CPI step skipped in Methodology I)."""
    value = float(pay)
    if not value:
        return 0
    rate = 2.7525 if value <= 758 else 1.8138
    return min(round2(value * rate), 1377)


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

START_ROW = {
    "1979(REVISED PAY SCALE)": 27,
    "1984(REVISED PAY SCALE)": 31,
    "1988(607 CPI)": 36,
    "1993(1030 CPI)": 42,
    "1997(1708 CPI)": 48,
    "2007(126 CPI)": 52,
    "2012(198 CPI)": 56,
    "2017(277 CPI)": 60,
    "2022(359 CPI)": 64,
}

ROW_LABELS = {
    27: "Basic Pay in the existing scale",
    28: "Fixed DA",
    29: "Fixed Special Allowance",
    30: "Notional Pay (as on 01.01.1984)",
    31: "Basic Pay in the existing scale as on 01-01-1984",
    32: "V.D.A from 455 to 607 points",
    33: "F.D.A (Revision Order)",
    34: "Fitment",
    35: "Notional Pay (as on 01.01.1988)",
    36: "Basic Pay in the existing scale as on 01-01-1988",
    37: "DA relief",
    38: "S.D.A (Revision Order)",
    39: "F.D.A (Revision Order)",
    40: "Fitment @ 12.5% (on Basic pay)",
    41: "Notional Pay (as on 01.01.1993)",
    42: "Basic Pay in the existing scale as on 01-01-1994",
    43: "Special allowance (1994)",
    44: "V.D.A (As per slab)",
    45: "CPI difference @ Rs.138",
    46: "Fitment @27.5% on Basic Pay",
    47: "Notional basic pay over 1708 CPI",
    48: "Basic Pay in the existing scale as on 01-01-1997",
    49: "DA @ 78.2% on Basic",
    50: "Fitment @ 23% on (Basic + DA)",
    51: "Notional Pay (as on 01.01.1997)",
    52: "Basic Pay Over 126 CPI Points as on 01.01.2007",
    53: "Variable D.A OF 57.14%",
    54: "Fitment of 10.5% of (Basic+DA)",
    55: "Notional Pay (as on 01.01.2007)",
    56: "Basic Pay Over 198 CPI Points as on 01.01.2012",
    57: "DA@40% On Basic",
    58: "Fitment @ 10.6% on Basic + DA",
    59: "Notional Pay (as on 01.01.2017)",
    60: "Basic Pay Over 277 CPI Points as on 01.01.2017",
    61: "DA@30% On Basic",
    62: "Fitment @ 8.5%",
    63: "Notional Pay (2017)",
    64: "Basic Pay as on 01.01.2022",
    65: "Pension reference (2022 basic)",
}


def _tail_from_1997(state, basic_1997, scales):
    """Rows 48–65 from 1997 basic (last pay at retirement)."""
    state[48] = float(basic_1997)
    state[49] = round2(state[48] * 0.782)
    state[50] = round2((state[48] + state[49]) * 0.23)
    state[51] = round_up_to_10(state[48] + state[49] + state[50])

    state[52] = state[51]
    state[53] = round2(state[52] * 0.5714)
    state[54] = round2((state[52] + state[53]) * 0.105)
    state[55] = round_up_to_10(state[52] + state[53] + state[54])

    state[56] = state[55]
    state[57] = round2(state[56] * 0.40)
    state[58] = round2((state[56] + state[57]) * 0.106)
    _set_notional_pay_2017_row(state, scales)
    state[61] = round2(state[60] * 0.30)
    state[62] = round2(state[60] * 1.3 * 0.085)
    state[63] = round2(state[60] + state[61] + state[62])

    scale_2017 = scales.get("2017(277 CPI)")
    state[64] = _matrix_2022(scale_2017, state[63])
    state[65] = state[64]


def _tail_from_2007(state, basic_2007, scales):
    state[52] = float(basic_2007)
    state[53] = round2(state[52] * 0.5714)
    state[54] = round2((state[52] + state[53]) * 0.105)
    state[55] = round_up_to_10(state[52] + state[53] + state[54])

    state[56] = state[55]
    state[57] = round2(state[56] * 0.40)
    state[58] = round2((state[56] + state[57]) * 0.106)
    _set_notional_pay_2017_row(state, scales)
    state[61] = round2(state[60] * 0.30)
    state[62] = round2(state[60] * 1.3 * 0.085)
    state[63] = round2(state[60] + state[61] + state[62])

    scale_2017 = scales.get("2017(277 CPI)")
    state[64] = _matrix_2022(scale_2017, state[63])
    state[65] = state[64]


def _tail_from_2012(state, basic_2012, scales):
    state[56] = round_up_to_10(float(basic_2012))
    state[57] = round2(state[56] * 0.40)
    state[58] = round2((state[56] + state[57]) * 0.106)
    _set_notional_pay_2017_row(state, scales)
    state[61] = round2(state[60] * 0.30)
    state[62] = round2(state[60] * 1.3 * 0.085)
    state[63] = round2(state[60] + state[61] + state[62])

    scale_2017 = scales.get("2017(277 CPI)")
    state[64] = _matrix_2022(scale_2017, state[63])
    state[65] = state[64]


def _fda_1984(pay):
    pay = float(pay)
    if pay <= 619:
        return 212.40
    if pay <= 769:
        return 217.40
    if pay <= 869:
        return 222.40
    return 227.40


def _vda_1994(basic_pay_1994):
    basic = float(basic_pay_1994)
    if load_da_1992_table:
        df = load_da_1992_table()
        for _, row in df.iterrows():
            low, high = float(row["Min"]), float(row["Max"])
            if low <= basic <= high:
                rate = float(row["Rate"])
                slab = float(row["Slab"])
                return max(round2(basic * rate), slab)
    if basic <= 3500:
        vda = round2(basic * 0.554)
        return max(vda, 1218)
    if basic <= 6500:
        vda = round2(basic * 0.415)
        return max(vda, 1939)
    if basic <= 9500:
        vda = round2(basic * 0.332)
        return max(vda, 2701)
    vda = round2(basic * 0.277)
    return max(vda, 3158)


def _safe_sda(fn, pay, default=0):
    try:
        val = fn(pay)
        return float(val) if val is not None else default
    except Exception:
        return default


def _matrix_2017(scale_2012, amount):
    try:
        val = fix_pay_in_matrix_2017(scale_2012, amount)
        if val is not None:
            return int(val)
    except Exception:
        pass
    return fix_pay_in_scale(scale_2012, amount)


def _matrix_2022(scale_2022, amount):
    try:
        val = fix_pay_in_matrix_2022(scale_2022, amount)
        if val is not None:
            return int(val)
    except Exception:
        pass
    return fix_pay_in_scale(scale_2022, amount)


def _set_notional_pay_2017_row(state, scales):
    """Row 59: nearest rupee. Row 60: 2017 matrix fitment on row 59 (2012 scale)."""
    total = state[56] + state[57] + state[58]
    state[59] = round_nearest_rupee(total)
    scale_2012 = scales.get("2012(198 CPI)")
    state[60] = _matrix_2017(scale_2012, state[59])


def _block_1994_to_1997(state, scales, basic_1994):
    state[42] = float(basic_1994)
    if state[42] <= 3000:
        state[43] = round_up_whole_rupee(state[42] * 0.02)
    else:
        state[43] = round_up_whole_rupee(state[42] * 0.04)
    state[44] = _vda_1994(state[42])
    state[45] = 138 if state[42] else 0
    state[46] = round2(state[42] * 0.275) if state[42] else 0
    state[47] = round2(
        state[42] + state[43] + state[44] + state[45] + state[46]
    )

    scale_1997 = scales.get("1997(1708 CPI)")
    basic_1997 = align_pay_with_increment(
        state[47], scale_1997, 1
    )
    _tail_from_1997(state, basic_1997, scales)


def _block_1988_to_1994(state, scales, basic_1988, pay_for_sda):
    state[36] = float(basic_1988)
    state[37] = _da_relief_from_pay(state[36])
    state[38] = _safe_sda(get_special_da, pay_for_sda)
    state[39] = _safe_sda(get_fixed_da_1988, state[36])
    state[40] = round2(state[36] * 0.125) if state[36] else 0
    state[41] = round2(
        state[36] + state[37] + state[38] + state[39] + state[40]
    )

    scale_1993 = scales.get("1993(1030 CPI)")
    basic_1994 = align_pay_without_increment(state[41], scale_1993)
    _block_1994_to_1997(state, scales, basic_1994)


def _block_1984_to_1988(state, scales, basic_1984):
    state[31] = float(basic_1984)
    state[32] = 237.85 if state[31] else 0
    state[33] = _fda_1984(state[31]) if state[31] else 0
    state[34] = _safe_sda(get_special_da, state[31] + state[32] + state[33])
    state[35] = state[31] + state[32] + state[33] + state[34]

    scale_1988 = scales.get("1988(607 CPI)")
    pay_1988 = align_pay_with_increment(state[35], scale_1988, 1)
    _block_1988_to_1994(state, scales, pay_1988, state[31])


def _compute_from_1979(state, scales, last_pay):
    basic = float(last_pay)
    state[27] = basic
    state[28] = 150
    state[29] = _safe_sda(get_special_da_1980, basic)
    state[30] = round2(state[27] + state[28] + state[29])

    scale_1984 = scales.get("1984(REVISED PAY SCALE)")
    pay_after_two = align_pay_with_increment(state[30], scale_1984, 2)
    state[31] = pay_after_two
    state[32] = 237.85
    state[33] = _fda_1984(pay_after_two)
    state[34] = _safe_sda(get_special_da, pay_after_two + state[32] + state[33])
    state[35] = pay_after_two + state[32] + state[33] + state[34]

    scale_1988 = scales.get("1988(607 CPI)")
    pay_1988 = align_pay_with_increment(state[35], scale_1988, 1)
    _block_1988_to_1994(state, scales, pay_1988, pay_after_two)


def _compute_from_1984(state, scales, last_pay):
    _block_1984_to_1988(state, scales, last_pay)


def _compute_from_1988(state, scales, last_pay):
    _block_1988_to_1994(state, scales, last_pay, last_pay)


def _compute_from_1993(state, scales, last_pay):
    scale_1993 = scales.get("1993(1030 CPI)")
    basic_1994 = align_pay_without_increment(float(last_pay), scale_1993)
    _block_1994_to_1997(state, scales, basic_1994)


def _compute_from_1997(state, scales, last_pay):
    _tail_from_1997(state, last_pay, scales)


def _compute_from_2007(state, scales, last_pay, scale_revision=None, start_revision=None):
    if scale_revision and start_revision == "2007(126 CPI)":
        base = separation_scale_chain_pay(last_pay, scale_revision) or float(last_pay)
    else:
        base = float(last_pay)
    _tail_from_2007(state, base, scales)


def _compute_from_2012(state, scales, last_pay, scale_revision=None, start_revision=None):
    if scale_revision and start_revision == "2012(198 CPI)":
        base = separation_scale_chain_pay(last_pay, scale_revision) or float(last_pay)
    else:
        base = float(last_pay)
    _tail_from_2012(state, base, scales)


def _compute_from_2017(state, scales, last_pay, scale_revision=None, start_revision=None):
    if scale_revision and start_revision == "2017(277 CPI)":
        state[60] = separation_scale_chain_pay(last_pay, scale_revision) or float(last_pay)
    else:
        state[60] = float(last_pay)
    state[61] = round2(state[60] * 0.30)
    state[62] = round2(state[60] * 1.3 * 0.085)
    state[63] = round2(state[60] + state[61] + state[62])
    scale_2017 = scales.get("2017(277 CPI)")
    state[64] = _matrix_2022(scale_2017, state[63])
    state[65] = state[64]


def _compute_from_2022(state, scales, last_pay, scale_revision=None, start_revision=None):
    if scale_revision and start_revision == "2022(359 CPI)":
        state[60] = separation_scale_chain_pay(last_pay, scale_revision) or float(last_pay)
        state[61] = round2(state[60] * 0.30)
        state[62] = round2(state[60] * 1.3 * 0.085)
        state[63] = round2(state[60] + state[61] + state[62])
        chain_pay = state[63]
    else:
        chain_pay = float(last_pay)
    scale_2017 = scales.get("2017(277 CPI)")
    state[64] = _matrix_2022(scale_2017, chain_pay)
    state[65] = state[64]


def _pension_from_state(state):
    basic_2022 = state.get(64) or 0
    basic_2017 = state.get(60) or 0
    return {
        "basic_pay_2022": basic_2022,
        "basic_pay_2017": basic_2017,
        "pension_359_cpi": round2(basic_2022 / 2),
        "pension_277_cpi": round2(basic_2017 / 2),
        "family_pension_359_cpi": round2(basic_2022 * 0.3),
        "family_pension_277_cpi": round2(basic_2017 * 0.3),
    }


def _format_rows(state, start_row):
    rows = []
    for row_num in range(27, 66):
        value = state.get(row_num, 0) if row_num >= start_row else 0
        rows.append({
            "row": row_num,
            "description": ROW_LABELS.get(row_num, f"Row {row_num}"),
            "value": value,
        })
    return rows


def calculate_revision(scales, current_revision, last_pay, scale_revision=None):
    if not scales:
        return {"rows": [], "pension": {}}

    state = {}
    handlers = {
        "1979(REVISED PAY SCALE)": _compute_from_1979,
        "1984(REVISED PAY SCALE)": _compute_from_1984,
        "1988(607 CPI)": _compute_from_1988,
        "1993(1030 CPI)": _compute_from_1993,
        "1997(1708 CPI)": _compute_from_1997,
        "2007(126 CPI)": _compute_from_2007,
        "2012(198 CPI)": _compute_from_2012,
        "2017(277 CPI)": _compute_from_2017,
        "2022(359 CPI)": _compute_from_2022,
    }

    handler = handlers.get(current_revision)
    if not handler:
        return {"rows": [], "pension": {}}

    original_pay = float(last_pay)
    effective_pay, pay_adjustment = _resolve_starting_last_pay(
        current_revision, last_pay
    )
    if current_revision in (
        "2007(126 CPI)",
        "2012(198 CPI)",
        "2017(277 CPI)",
        "2022(359 CPI)",
    ):
        handler(state, scales, effective_pay, scale_revision, current_revision)
    else:
        handler(state, scales, effective_pay)
    start_row = START_ROW[current_revision]
    rows = _format_rows(state, start_row)
    if pay_adjustment and current_revision == CPI_607_REVISION:
        for row in rows:
            if row["row"] == 36:
                row["description"] = (
                    f"Pay amount (607 CPI — "
                    f"{int(pay_adjustment['factor'] * 100)}% of {original_pay})"
                )
                row["value"] = effective_pay
                break
    return {
        "rows": rows,
        "pension": _pension_from_state(state),
        "last_pay_adjusted": pay_adjustment is not None,
        "effective_last_pay": effective_pay,
        "original_last_pay": original_pay,
        "last_pay_adjustment": pay_adjustment,
    }
