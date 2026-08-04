from master_data.models import FiPnMhErndednmap

# Standard map codes from FI_PN_FIRST_PENSION_PROCESS.fmb
MAP_PENSION = 99
MAP_COMMUTATION = 102
MAP_GRATUITY = 104
MAP_RELIEF = 110


def resolve_earndedn_cd(map_cd, e_d_type="E"):
    """Map logical code (99=pension, 102=commutation, etc.) to EARNDEDN_CD."""
    ed_type = str(e_d_type or "E").strip().upper()[:1]
    row = FiPnMhErndednmap.objects.filter(
        map_cd=int(map_cd),
        e_d_type=ed_type,
    ).first()
    if row:
        return row.earndedn_cd
    row = FiPnMhErndednmap.objects.filter(map_cd=int(map_cd)).first()
    return row.earndedn_cd if row else None
