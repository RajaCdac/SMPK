"""Import journal voucher master data from Oracle into MySQL (read Oracle, write MySQL only)."""

from django.db import transaction

from master_data.models import FiPnMdJrnltype, FiPnMhEarndedn, FiPnMhJrnltype


def _int_val(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clip_str(value, max_len, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return text[:max_len]


def sync_jrnl_types_from_oracle():
    from employee.services.oracle_service import get_oracle_connection

    with get_oracle_connection().cursor() as cursor:
        cursor.execute("SELECT * FROM FINANCE.FI_PN_MH_JRNLTYPE ORDER BY JRNAL_SRL_NO")
        mh_cols = [d[0] for d in cursor.description]
        mh_rows = cursor.fetchall()

        cursor.execute("SELECT * FROM FINANCE.FI_PN_MD_JRNLTYPE ORDER BY JRNAL_SRL_NO, ZONAL_CD, ALOC_CD1")
        md_cols = [d[0] for d in cursor.description]
        md_rows = cursor.fetchall()

        cursor.execute(
            """
            SELECT EARNDEDN_CD, ZONAL_CD, ALLOC_CD
            FROM FINANCE.FI_PN_MH_EARNDEDN
            WHERE ZONAL_CD IS NOT NULL
            """
        )
        earn_rows = cursor.fetchall()

    mh_inserted = md_inserted = earn_updated = 0

    with transaction.atomic():
        FiPnMhJrnltype.objects.all().delete()
        for row in mh_rows:
            data = dict(zip(mh_cols, row))
            FiPnMhJrnltype.objects.create(
                jrnal_srl_no=_int_val(data.get("JRNAL_SRL_NO")),
                type=_clip_str(data.get("TYPE"), 6),
                jrnal_desc=_clip_str(data.get("JRNAL_DESC"), 30),
                date_created=data.get("DATE_CREATED"),
                date_modified=data.get("DATE_MODIFIED"),
                created_by=_clip_str(data.get("CREATED_BY"), 5),
                modified_by=_clip_str(data.get("MODIFIED_BY"), 5),
            )
            mh_inserted += 1

        FiPnMdJrnltype.objects.all().delete()
        for row in md_rows:
            data = dict(zip(md_cols, row))
            FiPnMdJrnltype.objects.create(
                jrnal_srl_no=_int_val(data.get("JRNAL_SRL_NO")),
                zonal_cd=_int_val(data.get("ZONAL_CD")) or 0,
                dr_cr_flg=_clip_str(data.get("DR_CR_FLG"), 1),
                aloc_cd1=_clip_str(data.get("ALOC_CD1"), 4),
                aloc_cd2=_clip_str(data.get("ALOC_CD2"), 4),
                aloc_cd3=_clip_str(data.get("ALOC_CD3"), 7),
                map_cd=_clip_str(data.get("MAP_CD"), 15),
                date_created=data.get("DATE_CREATED"),
                date_modified=data.get("DATE_MODIFIED"),
                created_by=_clip_str(data.get("CREATED_BY"), 5),
                modified_by=_clip_str(data.get("MODIFIED_BY"), 5),
            )
            md_inserted += 1

        for earn_cd, zonal_cd, alloc_cd in earn_rows:
            code = _clip_str(earn_cd, 3)
            if not code:
                continue
            updated = FiPnMhEarndedn.objects.filter(earndedn_cd=code).update(
                zonal_cd=_int_val(zonal_cd),
                alloc_cd=_clip_str(alloc_cd, 4),
            )
            if updated:
                earn_updated += 1

    return {
        "mh_jrnltype": mh_inserted,
        "md_jrnltype": md_inserted,
        "earndedn_zonal": earn_updated,
    }
