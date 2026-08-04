from django.db.models import Q

from master_data.models import FiPmMhBank, FiPmMhBankAbbr


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
    qs = FiPmMhBankAbbr.objects.all().order_by("bank_name", "bank_type")
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
