"""
Class 3 MACP into an Officers' scale.

Kept apart from calculation_service so the ordinary Class 3 path is unchanged.

These employees stay on the staff WRC fitment (2012, 2017, 2022). There is
no officers' pay matrix. For 01.01.2012–31.12.2016 every track uses the
highest Class 3 scale, 23600-56300.
"""

from __future__ import annotations

from methodology2.services.proportionate_pension import apply_proportionate_pension
from methodology2.services.revision_resolver import get_revision_column
from methodology2.services.rounding_helpers import (
    round2,
    round_nearest_rupee,
    round_up_to_10,
)
from methodology2.services.scale_parser import (
    expand_scale_increment_10,
    generate_pay_stages,
)

# Columns this path can start from. Earlier revisions have no Officers' MACP scale.
MACP_REVISIONS = (
    "2007(126 CPI)",
    "2012(198 CPI)",
    "2017(277 CPI)",
    "2022(359 CPI)",
)

REVISION_COLUMNS = (
    "2007(126 CPI)",
    "2012(198 CPI)",
    "2017(277 CPI)",
    "2022(359 CPI)",
)

# 2007 Officers' scale → later staff-revision scales.
# 2012 is the highest Class 3 scale for every track.
MACP_TRACKS = (
    {
        "key": "16400-40500",
        "2007(126 CPI)": "16400-40500",
        "2012(198 CPI)": "23600-56300",
        "2017(277 CPI)": "40000-140000",
        "2022(359 CPI)": "40000-140000",
    },
    {
        "key": "20600-46500",
        "2007(126 CPI)": "20600-46500",
        "2012(198 CPI)": "23600-56300",
        "2017(277 CPI)": "50000-160000",
        "2022(359 CPI)": "50000-160000",
    },
    {
        "key": "24900-50500",
        "2007(126 CPI)": "24900-50500",
        "2012(198 CPI)": "23600-56300",
        "2017(277 CPI)": "60000-180000",
        "2022(359 CPI)": "60000-180000",
    },
)

# A stage dropdown larger than this is not usable; the screen takes a typed basic.
_MAX_STAGE_OPTIONS = 4000


def _track_by_key(track_key: str) -> dict | None:
    key = str(track_key or "").strip()
    for track in MACP_TRACKS:
        if track["key"] == key:
            return track
    return None


def _track_label(track: dict) -> str:
    return (
        f"{track['2007(126 CPI)']}"
        f"  →  2012: {track['2012(198 CPI)']}"
        f"  →  2017/2022: {track['2017(277 CPI)']}"
    )


def _equivalent_from(track: dict, revision: str) -> dict:
    start = REVISION_COLUMNS.index(revision)
    return {col: track[col] for col in REVISION_COLUMNS[start:]}


def _pay_stages(scale_text: str) -> list[int]:
    stages = generate_pay_stages(expand_scale_increment_10(scale_text))
    if len(stages) > _MAX_STAGE_OPTIONS:
        return []
    return stages


def macp_options(retirement_date) -> dict:
    """Tracks offered for a separation date, with the scale in force on that date."""
    try:
        revision = get_revision_column(retirement_date)
    except (TypeError, ValueError) as exc:
        return {"error": str(exc), "revision": "", "tracks": []}

    if revision not in MACP_REVISIONS:
        return {
            "error": (
                "MACP Officers' scales apply from the 2007 revision. "
                "Use a separation date on or after 02.01.2007."
            ),
            "revision": revision,
            "tracks": [],
        }

    tracks = []
    for track in MACP_TRACKS:
        scale_now = track[revision]
        tracks.append(
            {
                "key": track["key"],
                "label": _track_label(track),
                "scale_at_retirement": scale_now,
                "pay_stages": _pay_stages(scale_now),
                "equivalent_scales": _equivalent_from(track, revision),
            }
        )
    return {"error": None, "revision": revision, "tracks": tracks}


def _apply_2017_fitment(state: dict) -> None:
    """Staff WRC 2017 fitment. Notional is the aggregate rounded up to 10, not a matrix cell."""
    state[61] = round2(state[60] * 0.30)
    state[62] = round2(state[60] * 1.3 * 0.085)
    state[63] = round2(state[60] + state[61] + state[62])
    state[64] = round_up_to_10(state[63])
    state[65] = state[64]


def _apply_2012_block(state: dict, basic) -> None:
    """Staff WRC 2012 fitment on the highest Class 3 scale. No 2017 pay matrix."""
    state[56] = round_up_to_10(float(basic))
    state[57] = round2(state[56] * 0.40)
    state[58] = round2((state[56] + state[57]) * 0.106)
    total = state[56] + state[57] + state[58]
    state[59] = round_nearest_rupee(total)
    state[60] = state[59]
    _apply_2017_fitment(state)


def _apply_2007_block(state: dict, basic) -> None:
    state[52] = float(basic)
    state[53] = round2(state[52] * 0.5714)
    state[54] = round2((state[52] + state[53]) * 0.105)
    state[55] = round_up_to_10(state[52] + state[53] + state[54])
    _apply_2012_block(state, state[55])


def _pension_from_state(state: dict) -> dict:
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


def _letter(row_num, letter, description, value):
    return {
        "row": row_num,
        "code": letter,
        "description": description,
        "value": value,
    }


def _format_macp_rows(state: dict, revision: str) -> list:
    """
    Same lettered Class 3 blocks as the ordinary print, without the
    pay-matrix lines (2012 F / 2017 F).
    """
    out = []
    start = REVISION_COLUMNS.index(revision)

    if start <= 0 and state.get(52) is not None:
        a, b, c = state[52], state[53], state[54]
        agg = round2(a + b + c)
        out.extend(
            [
                _letter(200701, "A", "Basic Pay Over 126 CPI Points as on 01.01.2007", a),
                _letter(200702, "B", "Variable D.A of 57.14% on Basic Pay", b),
                _letter(200703, "C", "Fitment @ 10.5% on (Basic+DA)", c),
                _letter(200704, "D", "Aggregate of A+B+C", agg),
                _letter(
                    200705,
                    "E",
                    "Notional Pay (Rounded to the next 10 Rupees)",
                    state.get(55) if state.get(55) is not None else round_up_to_10(agg),
                ),
            ]
        )

    if start <= 1 and state.get(56) is not None:
        a, b, c = state[56], state[57], state[58]
        agg = round2(a + b + c)
        nearest = state.get(59) if state.get(59) is not None else round_nearest_rupee(agg)
        out.extend(
            [
                _letter(201201, "A", "Basic Pay Over 198 CPI Points as on 01.01.2012", a),
                _letter(201202, "B", "DA @ 40% On basic pay", b),
                _letter(201203, "C", "Fitment @ 10.6% on (Basic+DA)", c),
                _letter(201204, "D", "Aggregate of A+B+C", agg),
                _letter(201205, "E", "Rounded off to the nearest rupee", nearest),
            ]
        )

    if start <= 2 and state.get(60) is not None:
        a = state[60]
        b = state.get(61) or 0
        c = state.get(62) or 0
        agg = state.get(63) if state.get(63) is not None else round2(a + b + c)
        notional = round_up_to_10(agg)
        out.extend(
            [
                _letter(201701, "A", "Basic Pay Over 277 CPI Points as on 01.01.2017", a),
                _letter(201702, "B", "DA @ 30% on basic pay", b),
                _letter(201703, "C", "Fitment @ 8.5% on (Basic+DA)", c),
                _letter(201704, "D", "Aggregate of A+B+C", agg),
                _letter(
                    201705,
                    "E",
                    "Notional Pay (Rounded to the next 10 Rupees)",
                    notional,
                ),
            ]
        )

    if state.get(64) is not None and (start <= 3):
        out.append(_letter(202201, "A", "Basic Pay as on 01.01.2022", state[64]))

    return out


def calculate_macp(
    retirement_date,
    track_key,
    last_pay,
    *,
    tqs_yr=None,
    tqs_month=None,
    tqs_days=None,
) -> dict:
    options = macp_options(retirement_date)
    if options.get("error"):
        return {"error": options["error"]}

    track = _track_by_key(track_key)
    if not track:
        return {"error": "Select one of the three MACP Officers' scales."}

    try:
        pay = float(last_pay)
    except (TypeError, ValueError):
        return {"error": "Last pay is required."}
    if pay <= 0:
        return {"error": "Last pay is required."}

    revision = options["revision"]
    state: dict = {}
    if revision == "2007(126 CPI)":
        _apply_2007_block(state, pay)
    elif revision == "2012(198 CPI)":
        _apply_2012_block(state, pay)
    elif revision == "2017(277 CPI)":
        state[60] = float(pay)
        _apply_2017_fitment(state)
    else:
        state[64] = float(pay)
        state[65] = state[64]

    pension = apply_proportionate_pension(
        _pension_from_state(state),
        retirement_date=retirement_date,
        tqs_yr=tqs_yr,
        tqs_month=tqs_month,
        tqs_days=tqs_days,
    )
    scales = _equivalent_from(track, revision)
    return {
        "rows": _format_macp_rows(state, revision),
        "pension": pension,
        "start_revision": revision,
        "equivalent_scales": scales,
        "category": "3",
        "scale": f"MACP {track['key']}",
        "scale_at_retirement": track[revision],
        "macp": True,
        "track": track["key"],
    }
