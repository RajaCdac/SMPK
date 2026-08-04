"""
Methodology 1 CPI revision chain (class 3/4), ported from the frontend
`methodology1PayRules.js` so the API matches the on-screen cards exactly.

Starting-scale pay (607 slab / 30%) is rounded up before the next CPI.
Pay-protect minimums apply to final notional after fitment, not starting pay.
"""

import math

from methodology1.services.parallel_cpi_service import (
    CPI_1030_REVISION,
    PRE_607_SCALE_REVISIONS,
    get_607_equivalent_pay,
    is_pre_607_scale_revision,
    resolve_pre_1988_607_base_pay,
)
from methodology1.services.revision_resolver import (
    get_calculation_start_revision,
    get_revision_column,
    is_1030_direct_607_period,
    is_pre_1988_separation,
)

CPI_607_REVISION = "1988(607 CPI)"
CPI_1708_REVISION = "1997(1708 CPI)"
CPI_277_REVISION = "2017(277 CPI)"
CPI_359_REVISION = "2022(359 CPI)"

MIN_PAY_PROTECT = {
    "1997(1708 CPI)": 1850,
    "2007(126 CPI)": 3900,
    "2012(198 CPI)": 6750,
    "2017(277 CPI)": 10450,
    "2022(359 CPI)": 14750,
}

MIN_PAY_30 = 375
MIN_PAY_20 = 450
MIN_PAY_15 = 600


def _round2(value):
    return round(float(value) + 1e-9, 2)


def _round_up_whole_rupee(value):
    return math.ceil(float(value))


def _protect_notional(raw_notional, revision_key):
    minimum = MIN_PAY_PROTECT.get(revision_key)
    if minimum is None or raw_notional is None:
        return raw_notional
    return max(float(raw_notional), minimum)


def _map_scale_to_card(scale_revision):
    return scale_revision


def _base_pay_for_607_rules(last_pay, scale_revision, scales=None, separation_date=None):
    if (
        scale_revision == CPI_1030_REVISION
        and scales
        and separation_date
        and not is_1030_direct_607_period(separation_date)
    ):
        mapped = get_607_equivalent_pay(last_pay, scales)
        if mapped is not None:
            return mapped
    return float(last_pay)


# --- 607 ----------------------------------------------------------------
def get_607_pay(last_pay):
    pay = float(last_pay)
    if pay <= 0:
        return None
    if pay <= 1499:
        return max(_round2(pay * 0.30), MIN_PAY_30)
    if 1500 < pay <= 3000:
        return max(_round2(pay * 0.20), MIN_PAY_20)
    if pay > 3001:
        return max(_round2(pay * 0.15), MIN_PAY_15)
    return pay


def get_607_chain_pay(last_pay):
    pay = get_607_pay(last_pay)
    if pay is None:
        return None
    return _round_up_whole_rupee(pay)


def get_607_direct_1030_chain_pay(last_pay, scales=None):
    """
    1995–1996: first map 1030 stage → equivalent 607 stage when possible,
    then take flat 30% (no 607 slab bands or minimums).
    """
    pay = float(last_pay)
    mapped = get_607_equivalent_pay(last_pay, scales)
    if mapped is not None:
        pay = float(mapped)
    if pay <= 0:
        return None
    return _round_up_whole_rupee(_round2(pay * 0.30))


def _resolve_607_chain_pay(
    last_pay, scale_revision, scales=None, separation_date=None
):
    if (
        scale_revision == CPI_1030_REVISION
        and separation_date
        and is_1030_direct_607_period(separation_date)
    ):
        return get_607_direct_1030_chain_pay(last_pay, scales)
    if (
        separation_date
        and is_pre_1988_separation(separation_date)
        and is_pre_607_scale_revision(scale_revision)
        and scales
    ):
        initial_pay = resolve_pre_1988_607_base_pay(separation_date, scales)
        if initial_pay is not None:
            return get_607_chain_pay(initial_pay)
    base = _base_pay_for_607_rules(
        last_pay, scale_revision, scales, separation_date
    )
    return get_607_chain_pay(base)


def separation_scale_chain_pay(
    last_pay, scale_revision, scales=None, separation_date=None
):
    card = _map_scale_to_card(scale_revision)
    if card == CPI_1030_REVISION:
        return None
    if card == CPI_607_REVISION:
        base = _base_pay_for_607_rules(
            last_pay, scale_revision, scales, separation_date
        )
        return get_607_chain_pay(base)
    if card in MIN_PAY_PROTECT:
        return _round_up_whole_rupee(_round2(float(last_pay) * 0.30))
    return None


# --- 1708 ---------------------------------------------------------------
def _da_relief_1708(pay):
    rate = 2.7525 if pay <= 758 else 1.8138
    return min(_round2(pay * rate), 1377)


def compute_1708_notional(
    last_pay, scale_revision, start_revision, scales=None, separation_date=None
):
    scale_card = _map_scale_to_card(scale_revision)
    if scale_card == CPI_1708_REVISION:
        return _round_up_whole_rupee(_round2(float(last_pay) * 0.30))
    if scale_card not in (CPI_607_REVISION, CPI_1030_REVISION):
        if not (
            separation_date
            and is_pre_1988_separation(separation_date)
            and scale_card in PRE_607_SCALE_REVISIONS
            and scales
        ):
            return None

    pay = _resolve_607_chain_pay(
        last_pay, scale_revision, scales, separation_date
    )
    if pay is None:
        return None
    da = _da_relief_1708(pay)
    fitment = _round2(pay * 0.43)
    notional = _round_up_whole_rupee(pay + da + fitment)
    return _protect_notional(notional, CPI_1708_REVISION)


def first_chain_stage_pay(
    last_pay, scale_revision, start_revision, scales=None, separation_date=None
):
    if (
        separation_date
        and is_pre_1988_separation(separation_date)
        and start_revision == CPI_607_REVISION
        and is_pre_607_scale_revision(scale_revision)
        and scales
    ):
        return _resolve_607_chain_pay(
            last_pay, scale_revision, scales, separation_date
        )
    return separation_scale_chain_pay(
        last_pay, scale_revision, scales, separation_date
    )


# --- 126 ----------------------------------------------------------------
def get_126_pay(
    last_pay, scale_revision, start_revision, scales=None, separation_date=None
):
    if start_revision == "2007(126 CPI)":
        return first_chain_stage_pay(
            last_pay, scale_revision, start_revision, scales, separation_date
        )
    return compute_1708_notional(
        last_pay, scale_revision, start_revision, scales, separation_date
    )


def compute_126_notional(
    last_pay, scale_revision, start_revision, scales=None, separation_date=None
):
    pay = get_126_pay(
        last_pay, scale_revision, start_revision, scales, separation_date
    )
    if pay is None:
        return None
    da = _round2(pay * 0.782)
    fitment = _round2((pay + da) * 0.23)
    notional = _round_up_whole_rupee(pay + da + fitment)
    return _protect_notional(notional, "2007(126 CPI)")


# --- 198 ----------------------------------------------------------------
def get_198_pay(
    last_pay, scale_revision, start_revision, scales=None, separation_date=None
):
    if start_revision == "2012(198 CPI)":
        return first_chain_stage_pay(
            last_pay, scale_revision, start_revision, scales, separation_date
        )
    return compute_126_notional(
        last_pay, scale_revision, start_revision, scales, separation_date
    )


def compute_198_notional(
    last_pay, scale_revision, start_revision, scales=None, separation_date=None
):
    pay = get_198_pay(
        last_pay, scale_revision, start_revision, scales, separation_date
    )
    if pay is None:
        return None
    da = _round2(pay * 0.5714)
    fitment = _round2((pay + da) * 0.105)
    notional = _round_up_whole_rupee(pay + da + fitment)
    return _protect_notional(notional, "2012(198 CPI)")


# --- 277 ----------------------------------------------------------------
def get_277_pay(
    last_pay, scale_revision, start_revision, scales=None, separation_date=None
):
    # Already at/after 359 stage — do not rebuild a prior 277 notional.
    if scale_revision == CPI_359_REVISION or start_revision == CPI_359_REVISION:
        return None
    if start_revision == CPI_277_REVISION:
        return first_chain_stage_pay(
            last_pay, scale_revision, start_revision, scales, separation_date
        )
    return compute_198_notional(
        last_pay, scale_revision, start_revision, scales, separation_date
    )


def compute_277(
    last_pay, scale_revision, start_revision, scales=None, separation_date=None
):
    if scale_revision == CPI_359_REVISION or start_revision == CPI_359_REVISION:
        return None
    pay = get_277_pay(
        last_pay, scale_revision, start_revision, scales, separation_date
    )
    if pay is None:
        return None
    da = _round2(pay * 0.40)
    fitment = _round2((pay + da) * 0.106)
    raw_notional = _round_up_whole_rupee(pay + da + fitment)
    notional = _protect_notional(raw_notional, CPI_277_REVISION)
    return {
        "pay": pay,
        "da": da,
        "fitment": fitment,
        "notional": notional,
    }


def _already_on_359_scale(scale_revision, separation_date=None):
    """True when last pay is already under 359 CPI (no further fitment)."""
    if scale_revision == CPI_359_REVISION:
        return True
    if separation_date:
        try:
            return get_revision_column(separation_date) == CPI_359_REVISION
        except Exception:
            return False
    return False


# --- 359 ----------------------------------------------------------------
def compute_359(
    last_pay, scale_revision, start_revision, scales=None, separation_date=None
):
    # Separation already under 359 CPI: stage pay is 30% of last pay only —
    # no further CPI fitment.
    if _already_on_359_scale(scale_revision, separation_date):
        pay = first_chain_stage_pay(
            last_pay, scale_revision, start_revision, scales, separation_date
        )
        if pay is None:
            return None
        notional = _protect_notional(pay, CPI_359_REVISION)
        return {
            "pay": pay,
            "da": 0,
            "fitment": 0,
            "notional": notional,
        }

    if start_revision == CPI_359_REVISION:
        # Last pay still on an earlier CPI (e.g. 277); apply 359 fitment
        # on 30% of last pay.
        pay = first_chain_stage_pay(
            last_pay, scale_revision, start_revision, scales, separation_date
        )
    else:
        cpi_277 = compute_277(
            last_pay, scale_revision, start_revision, scales, separation_date
        )
        if cpi_277 is None:
            return None
        pay = cpi_277["notional"]
    if pay is None:
        return None
    da = _round2(pay * 0.30)
    fitment = _round2((pay + da) * 0.085)
    raw_notional = _round_up_whole_rupee(pay + da + fitment)
    notional = _protect_notional(raw_notional, CPI_359_REVISION)
    return {
        "pay": pay,
        "da": da,
        "fitment": fitment,
        "notional": notional,
    }


def calculate_277_359(separation_date, last_pay, scales=None):
    """Return 277 and 359 CPI values from separation date + last pay."""
    if last_pay in (None, "") or float(last_pay) <= 0:
        return {"error": "last_pay must be a positive number"}

    scale_revision = get_revision_column(separation_date)
    start_revision = get_calculation_start_revision(separation_date)
    cpi_277 = compute_277(
        last_pay, scale_revision, start_revision, scales, separation_date
    )
    cpi_359 = compute_359(
        last_pay, scale_revision, start_revision, scales, separation_date
    )

    if cpi_359 is None:
        return {"error": "Could not compute revision chain for given inputs"}

    # Already on 359 CPI: only 30% of last pay (no 277 stage).
    if _already_on_359_scale(scale_revision, separation_date):
        return {
            "separation_date": separation_date,
            "last_pay": float(last_pay),
            "scale_revision": scale_revision,
            "start_revision": start_revision,
            "cpi_277": None,
            "cpi_359": cpi_359,
            "value_277_cpi": None,
            "value_359_cpi": cpi_359["notional"],
        }

    # Start at 359 from an earlier scale (e.g. sep 2018): 359 only.
    if start_revision == CPI_359_REVISION:
        return {
            "separation_date": separation_date,
            "last_pay": float(last_pay),
            "scale_revision": scale_revision,
            "start_revision": start_revision,
            "cpi_277": None,
            "cpi_359": cpi_359,
            "value_277_cpi": None,
            "value_359_cpi": cpi_359["notional"],
        }

    if cpi_277 is None:
        return {"error": "Could not compute revision chain for given inputs"}

    return {
        "separation_date": separation_date,
        "last_pay": float(last_pay),
        "scale_revision": scale_revision,
        "start_revision": start_revision,
        "cpi_277": cpi_277,
        "cpi_359": cpi_359,
        "value_277_cpi": cpi_277["notional"],
        "value_359_cpi": cpi_359["notional"],
    }
