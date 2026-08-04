"""Map 1030 CPI stage pay to equivalent 607 CPI pay (parallel CPI tables)."""

import json
import re
from functools import lru_cache
from pathlib import Path

from methodology1.services.scale_parser import generate_pay_stages

CPI_607_REVISION = "1988(607 CPI)"
CPI_1030_REVISION = "1993(1030 CPI)"

PRE_607_SCALE_REVISIONS = (
    "1979(REVISED PAY SCALE)",
    "1984(REVISED PAY SCALE)",
)

_MAPPINGS_FILE = Path(__file__).resolve().parent / "parallel_cpi_mappings.json"


def _normalize_scale(scale_string):
    return re.sub(r"\s+", "", str(scale_string or "").strip())


def _mapping_key(scale_1030, scale_607):
    return f"{_normalize_scale(scale_1030)}|{_normalize_scale(scale_607)}"


@lru_cache(maxsize=1)
def _load_pdf_mapping_tables():
    """Pay_1030 -> pay_607 lookups keyed by normalized scale pair."""
    with _MAPPINGS_FILE.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    tables = {}
    for entry in payload.get("mappings", []):
        key = _mapping_key(entry.get("scale_1030"), entry.get("scale_607"))
        rows = {}
        for row in entry.get("rows", []):
            if isinstance(row, dict):
                pay_1030 = int(row["pay_1030"])
                pay_607 = int(row["pay_607"])
            else:
                pay_1030, pay_607 = int(row[0]), int(row[1])
            rows[pay_1030] = pay_607
        tables[key] = rows
    return tables


def lookup_pdf_mapping(scale_1030, scale_607, last_pay):
    tables = _load_pdf_mapping_tables()
    rows = tables.get(_mapping_key(scale_1030, scale_607))
    if not rows:
        return None
    pay = int(float(last_pay))
    return rows.get(pay)


def is_pre_607_scale_revision(scale_revision):
    return scale_revision in PRE_607_SCALE_REVISIONS


def get_scale_initial_pay(scale_string):
    """First pay stage (minimum) of a scale string."""
    stages = generate_pay_stages(str(scale_string or "").strip())
    if not stages:
        return None
    return float(stages[0])


def resolve_pre_1988_607_base_pay(separation_date, scales):
    """
    Before 01/01/1988: use the initial stage of the separation-scale column
    as last pay for 607 CPI slab rules (607 equivalent scale from same row).
    """
    from methodology1.services.revision_resolver import (
        get_revision_column,
        is_pre_1988_separation,
    )

    if not scales or not is_pre_1988_separation(separation_date):
        return None
    column = get_revision_column(separation_date)
    sep_scale = scales.get(column)
    if sep_scale is None or str(sep_scale).strip() in ("", "nan"):
        return None
    return get_scale_initial_pay(sep_scale)


def map_1030_pay_to_607_index(scale_1030, scale_607, last_pay):
    """
    Legacy stage-index mapping: same stage index in 1030 and 607 scales.
    Used only when no PDF table exists for the scale pair.
    """
    if not scale_1030 or not scale_607 or last_pay in (None, ""):
        return None

    stages_1030 = generate_pay_stages(str(scale_1030).strip())
    stages_607 = generate_pay_stages(str(scale_607).strip())
    if not stages_1030 or not stages_607:
        return None

    pay = int(float(last_pay))
    if pay not in stages_1030:
        return None

    stage_index = stages_1030.index(pay)
    if stage_index >= len(stages_607):
        return stages_607[-1]
    return stages_607[stage_index]


def map_1030_pay_to_607(scale_1030, scale_607, last_pay):
    """
    Map 1030 CPI last pay to equivalent 607 CPI pay.
    Uses digitized Scanned Parallel CPI.pdf tables when available.
    """
    if not scale_1030 or not scale_607 or last_pay in (None, ""):
        return None

    mapped = lookup_pdf_mapping(scale_1030, scale_607, last_pay)
    if mapped is not None:
        return mapped

    return map_1030_pay_to_607_index(scale_1030, scale_607, last_pay)


def get_607_equivalent_pay(last_pay, scales):
    """Return mapped 607 pay when scales dict has 1030 + 607 columns."""
    if not scales:
        return None
    scale_1030 = scales.get(CPI_1030_REVISION)
    scale_607 = scales.get(CPI_607_REVISION)
    if not scale_1030 or not scale_607:
        return None
    return map_1030_pay_to_607(scale_1030, scale_607, last_pay)
