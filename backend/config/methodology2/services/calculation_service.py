"""
Methodology 2 row-wise calculation (M2_34), keyed by retirement revision.
Rounding: ROUNDUP to next 10 (rows 51, 55, 2012 basic carry);
          nearest rupee on row 59 (Notional Pay as on 01.01.2017);
          row 60 from 2017 matrix fitment on row 59 (2012 scale column).
"""

from methodology2.services.matrix_service import (
    fix_pay_in_matrix_2017,
    fix_pay_in_matrix_2022,
)
from methodology2.services.rounding_helpers import (
    round2,
    round_nearest_rupee,
    round_up_to_10,
    round_up_whole_rupee,
)
from methodology2.services.scale_parser import (
    align_pay_with_increment,
    align_pay_without_increment,
    fix_pay_in_scale,
)
from methodology2.services.scale_service import get_next_revision
from methodology2.services.sda_service import (
    get_fixed_da_1988,
    get_special_da,
    get_special_da_1980,
)

try:
    from methodology2.services.excel_loader import load_da_1992_table
except Exception:
    load_da_1992_table = None

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
    37: "V.D.A from 607 to 1030 points",
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
    59: "Notional Pay (Located in the level of the pay matrix given at Appendix-III)",
    60: "Basic Pay Over 277 CPI Points as on 01.01.2017",
    61: "DA@30% On Basic",
    62: "Fitment @ 8.5%",
    63: "Notional Pay (2017)",
    64: "Basic Pay as on 01.01.2022",
    65: "Pension reference (2022 basic)",
}


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
        vda = round2(basic * 0.5541)
        return max(vda, 1218)
    if basic <= 6500:
        vda = round2(basic * 0.4156)
        return max(vda, 1939)
    if basic <= 9500:
        vda = round2(basic * 0.3324)
        return max(vda, 2701)
    vda = round2(basic * 0.2770)
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


def _block_1994_to_1997(state, scales, basic_1994):
    state[42] = float(basic_1994)
    if state[42] <= 3000:
        state[43] = round2(state[42] * 0.02)
    else:
        state[43] = round2(state[42] * 0.04)
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


def _block_1988_to_1994(state, scales, basic_1988, pay_for_sda, sda_override=0):
    state[36] = float(basic_1988)
    state[37] = 778.45 if state[36] else 0
    state[38] = float(sda_override) if sda_override else 0
    state[39] = _safe_sda(get_fixed_da_1988, state[36])
    state[40] = round2(state[36] * 0.125) if state[36] else 0
    state[41] = round2(
        state[36] + state[37] + state[38] + state[39] + state[40]
    )

    scale_1993 = scales.get("1993(1030 CPI)")
    basic_1994 = align_pay_without_increment(state[41], scale_1993)
    _block_1994_to_1997(state, scales, basic_1994)


def _block_1984_to_1988(state, scales, basic_1984, sda_override=0):
    state[31] = float(basic_1984)
    state[32] = 237.85 if state[31] else 0
    state[33] = _fda_1984(state[31]) if state[31] else 0
    state[34] = _safe_sda(get_special_da, state[31] + state[32] + state[33])
    state[35] = state[31] + state[32] + state[33] + state[34]

    scale_1988 = scales.get("1988(607 CPI)")
    pay_1988 = align_pay_with_increment(state[35], scale_1988, 1)
    _block_1988_to_1994(state, scales, pay_1988, state[31], sda_override)


def _compute_from_1979(state, scales, last_pay, sda_override=0):
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
    _block_1988_to_1994(state, scales, pay_1988, pay_after_two, sda_override)


def _compute_from_1984(state, scales, last_pay, sda_override=0):
    _block_1984_to_1988(state, scales, last_pay, sda_override)


def _compute_from_1988(state, scales, last_pay, sda_override=0):
    _block_1988_to_1994(state, scales, last_pay, last_pay, sda_override)


def _compute_from_1993(state, scales, last_pay, sda_override=0):
    scale_1993 = scales.get("1993(1030 CPI)")
    basic_1994 = align_pay_without_increment(float(last_pay), scale_1993)
    _block_1994_to_1997(state, scales, basic_1994)


def _compute_from_1997(state, scales, last_pay, sda_override=0):
    _tail_from_1997(state, last_pay, scales)


def _compute_from_2007(state, scales, last_pay, sda_override=0):
    _tail_from_2007(state, last_pay, scales)


def _compute_from_2012(state, scales, last_pay, sda_override=0):
    _tail_from_2012(state, last_pay, scales)


def _compute_from_2017(state, scales, last_pay, sda_override=0):
    state[60] = float(last_pay)
    state[61] = round2(state[60] * 0.30)
    state[62] = round2(state[60] * 1.3 * 0.085)
    state[63] = round2(state[60] + state[61] + state[62])
    scale_2017 = scales.get("2017(277 CPI)")
    state[64] = _matrix_2022(scale_2017, state[63])
    state[65] = state[64]


def _compute_from_2022(state, scales, last_pay, sda_override=0):
    scale_2017 = scales.get("2017(277 CPI)")
    state[64] = _matrix_2022(scale_2017, float(last_pay))
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
    return expand_detailed_cpi_breakdown(rows)


def expand_detailed_cpi_breakdown(rows):
    """
    Expand 2007 / 2012 / 2017 / 2022 into A–E/F detailed breakdown rows
    for UI and print.

    Raw engine rows 52–65 are replaced by display rows 200701–202201.
    """
    by_row = {}
    for row in rows:
        if isinstance(row, dict) and row.get("row") is not None:
            by_row[int(row["row"])] = row

    def v(row_num):
        return float(by_row.get(row_num, {}).get("value") or 0)

    def has_value(row_num):
        return row_num in by_row and v(row_num) != 0

    out = [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("row") is not None
        and int(row["row"]) < 52
        and v(int(row["row"])) != 0
    ]

    def letter_row(row_num, letter, description, value):
        return {
            "row": row_num,
            "code": letter,
            "description": description,
            "value": value,
        }

    if has_value(52):
        a, b, c = v(52), v(53), v(54)
        d = round2(a + b + c)
        e = v(55) if has_value(55) else round_up_to_10(d)
        out.extend([
            letter_row(
                200701,
                "A",
                "Basic Pay Over 126 CPI Points as on 01.01.2007",
                a,
            ),
            letter_row(200702, "B", "Variable D.A of 57.14%", b),
            letter_row(200703, "C", "Fitment @ 10.5% on basic pay+DA", c),
            letter_row(200704, "D", "Aggregate of A+B+C", d),
            letter_row(
                200705,
                "E",
                "Notional Pay (Rounded of to the next 10 Rupees)",
                e,
            ),
        ])

    if has_value(56):
        a, b, c = v(56), v(57), v(58)
        d = round2(a + b + c)
        e = v(59) if has_value(59) else round_nearest_rupee(d)
        f = v(60)
        out.extend([
            letter_row(
                201201,
                "A",
                "Basic Pay Over 198 CPI Points as on 01.01.2012",
                a,
            ),
            letter_row(201202, "B", "DA @ 40% On basic pay", b),
            letter_row(201203, "C", "Fitment @ 10.6% on basic pay+DA", c),
            letter_row(201204, "D", "Aggregate of A+B+C", d),
            letter_row(201205, "E", "Rounded off to the nearest rupee", e),
            letter_row(
                201206,
                "F",
                (
                    "Notional Pay (Located in the level of the pay matrix "
                    "given at Appendix-III)"
                ),
                f,
            ),
        ])

    if has_value(60):
        a, b, c = v(60), v(61), v(62)
        d = v(63) if has_value(63) else round2(a + b + c)
        e = round_up_to_10(d)
        f = v(64)
        out.extend([
            letter_row(
                201701,
                "A",
                "Basic Pay Over 277 CPI Points as on 01.01.2017",
                a,
            ),
            letter_row(201702, "B", "DA @ 30% on basic pay", b),
            letter_row(201703, "C", "Fitment @ 8.5% on basic pay + DA", c),
            letter_row(201704, "D", "Aggregate of A+B+C", d),
            letter_row(201705, "E", "Rounded off to the next 10 Rupees", e),
            letter_row(
                201706,
                "F",
                (
                    "Notional Pay (Located in the level of the pay matrix "
                    "given at Appendix-IV)"
                ),
                f,
            ),
        ])

    if has_value(64):
        out.append(
            letter_row(202201, "A", "Basic Pay as on 01.01.2022", v(64))
        )

    return out


def calculate_revision(scales, current_revision, last_pay, sda_override=0):
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

    handler(state, scales, last_pay, sda_override)
    start_row = START_ROW[current_revision]
    return {
        "rows": _format_rows(state, start_row),
        "pension": _pension_from_state(state),
    }
