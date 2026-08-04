from master_data.models import FiPnMhEarndedn


def lookup_earndedn_by_code(code):
    key = str(code or "").strip()
    if not key:
        return None
    try:
        return FiPnMhEarndedn.objects.get(earndedn_cd=key)
    except FiPnMhEarndedn.DoesNotExist:
        if key.isdigit():
            padded = key.zfill(3)
            try:
                return FiPnMhEarndedn.objects.get(earndedn_cd=padded)
            except FiPnMhEarndedn.DoesNotExist:
                pass
    return None


def serialize_earndedn_master(obj):
    type_map = {"E": "EARN", "D": "DEDN"}
    ed_type = str(obj.earndedn_type or "E").strip().upper()
    return {
        "code": obj.earndedn_cd,
        "type": type_map.get(ed_type, "EARN"),
        "desc": obj.earndedn_desc or "",
        "earndedn_type": ed_type,
    }


def list_earndedn_from_mysql(*, ed_type=None):
    qs = FiPnMhEarndedn.objects.all().order_by("earndedn_cd")
    if ed_type:
        qs = qs.filter(earndedn_type=str(ed_type).strip().upper()[:1])
    return [serialize_earndedn_master(row) for row in qs]
