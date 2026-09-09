from django.db import transaction
from django.db.models import Q
from django.db.utils import OperationalError, ProgrammingError

from master_data.models import FiPmMhBank, FiPmMhBankAbbr, FiPmMhBankMax


def allocate_bank_cd(bank_type):
    """Oracle PRE-INSERT: BANK_CD = bank type || LPAD(next FI_PM_MH_BANK_MAX.MAX_NO, 4, 0)."""
    prefix = str(bank_type or "").strip().upper()[:2]
    if len(prefix) != 2:
        raise ValueError("Bank type is required.")

    def _max_existing_serial():
        max_n = 0
        for cd in FiPmMhBank.objects.filter(bank_cd__istartswith=prefix).values_list(
            "bank_cd", flat=True
        ):
            tail = str(cd or "")[2:]
            if tail.isdigit():
                max_n = max(max_n, int(tail))
        return max_n

    with transaction.atomic():
        max_n = _max_existing_serial()
        try:
            row = (
                FiPmMhBankMax.objects.select_for_update()
                .filter(bank_type=prefix)
                .first()
            )
            if row:
                try:
                    max_n = max(max_n, int(str(row.max_no or "0").strip() or "0"))
                except ValueError:
                    pass
                next_n = max_n + 1
                row.max_no = str(next_n)
                row.save(update_fields=["max_no"])
            else:
                next_n = max_n + 1
                FiPmMhBankMax.objects.create(bank_type=prefix, max_no=str(next_n))
        except (OperationalError, ProgrammingError):
            next_n = max_n + 1
        return f"{prefix}{next_n:04d}"


def _serialize_bank(obj):
    return {
        "bank_cd": obj.bank_cd,
        "bank_name": obj.bank_desc,
        "bank_desc": obj.bank_desc,
        "bank_id": obj.bank_id,
        "control_bank_cd": obj.control_bank_cd,
        "city": obj.city,
        "rbi_cd": obj.rbi_cd,
    }


def _serialize_bank_abbr(obj):
    return {
        "bank_type": obj.bank_type,
        "bank_name": obj.bank_name,
        "bank_short_name": obj.bank_short_name,
        "bank_id": obj.bank_id,
    }


def fetch_bank_master_list(*, search=None, limit=500):
    qs = FiPmMhBank.objects.all().order_by("bank_desc", "bank_cd")
    if search:
        term = str(search).strip()
        qs = qs.filter(
            Q(bank_cd__icontains=term)
            | Q(bank_desc__icontains=term)
            | Q(city__icontains=term)
            | Q(rbi_cd__icontains=term)
        )
    if limit:
        qs = qs[: int(limit)]
    return [_serialize_bank(row) for row in qs]


def fetch_bank_abbr_list(*, search=None, limit=500):
    qs = FiPmMhBankAbbr.objects.all().order_by("bank_type")
    if search:
        term = str(search).strip()
        qs = qs.filter(
            Q(bank_type__icontains=term)
            | Q(bank_name__icontains=term)
            | Q(bank_short_name__icontains=term)
        )
    if limit:
        qs = qs[: int(limit)]
    return [_serialize_bank_abbr(row) for row in qs]


def fetch_bank_by_code(bank_cd):
    code = str(bank_cd).strip()
    if not code:
        return None
    row = FiPmMhBank.objects.filter(bank_cd__iexact=code).first()
    if not row:
        return None
    return _serialize_bank(row)


def fetch_bank_abbr_by_type(bank_type):
    code = str(bank_type).strip()
    if not code:
        return None
    row = FiPmMhBankAbbr.objects.filter(bank_type__iexact=code).first()
    if not row:
        return None
    return _serialize_bank_abbr(row)


def lookup_bank_desc(bank_cd):
    row = fetch_bank_by_code(bank_cd)
    return row["bank_desc"] if row else ""
