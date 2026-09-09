"""
Nominee master for pension / gratuity (Oracle FI_XX_MD_NOMIN_PN_E → FI_XX_MD_NOMINEE).
MySQL table: fi_xx_md_nominee.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db import connection
from django.utils import timezone

from employee.oracle_mirror import FiXxMhEmpPer

NOMIN_TYPE_CHOICES = [
    {"value": "PN", "label": "Pension"},
    {"value": "GR", "label": "Gratuity"},
    {"value": "PF", "label": "PF"},
    {"value": "CM", "label": "Commutation"},
]


class NomineeError(Exception):
    pass


def _clip(value, max_len, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return text[:max_len]


def _emp_key(emp_cd):
    return _clip(emp_cd, 5).upper()


def _fmt_date(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def _full_name(per: FiXxMhEmpPer | None) -> str:
    if not per:
        return ""
    parts = [per.title, per.first_name, per.middle_name, per.last_name]
    return " ".join(str(p).strip() for p in parts if p and str(p).strip()).strip()


def _as_decimal(value, field="amount"):
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise NomineeError(f"Invalid {field}") from exc


def get_employee(emp_cd: str) -> dict:
    key = _emp_key(emp_cd)
    if not key:
        raise NomineeError("Employee code is required")
    per = FiXxMhEmpPer.objects.filter(emp_cd=key).first()
    if not per:
        # Try zero-padded 5-digit style used in ESR
        per = FiXxMhEmpPer.objects.filter(emp_cd=key.zfill(5)[:5]).first()
        if per:
            key = per.emp_cd
        else:
            raise NomineeError(f"Employee {key} not found in employee master")
    return {
        "emp_cd": key,
        "emp_name": _full_name(per),
    }


def list_nominees(emp_cd: str) -> list[dict]:
    key = _emp_key(emp_cd)
    if not key:
        raise NomineeError("Employee code is required")

    sql = """
        SELECT
            n.EMP_CD,
            n.NOMIN_TYPE,
            n.SL_NO,
            n.NOMINEE_NAME,
            n.RELATION_CD,
            COALESCE(r.RELATION_DESC, '') AS RELATION_DESC,
            n.SHARE_PCT,
            n.BIRTH_DT,
            n.MARITAL_STATUS,
            n.EMPLOYED_FLG,
            n.HANDICAP_FLG,
            n.BANK_CD,
            COALESCE(b.BANK_DESC, '') AS BANK_DESC,
            n.BANK_AC_NO,
            n.ADDR1,
            n.ADDR2,
            n.CITY,
            n.STATE,
            n.PIN,
            n.CONTACT1,
            n.EMAIL_ID,
            n.DATE_CREATED,
            n.DATE_MODIFIED
        FROM fi_xx_md_nominee n
        LEFT JOIN fi_pm_mh_relation r
          ON r.RELATION_CD = n.RELATION_CD
        LEFT JOIN fi_pm_mh_bank b
          ON b.BANK_CD = n.BANK_CD
        WHERE n.EMP_CD = %s
        ORDER BY n.NOMIN_TYPE, n.SL_NO
    """
    # Fallback without bank/relation join if masters missing
    simple_sql = """
        SELECT
            EMP_CD, NOMIN_TYPE, SL_NO, NOMINEE_NAME, RELATION_CD,
            '' AS RELATION_DESC, SHARE_PCT, BIRTH_DT, MARITAL_STATUS,
            EMPLOYED_FLG, HANDICAP_FLG, BANK_CD, '' AS BANK_DESC, BANK_AC_NO,
            ADDR1, ADDR2, CITY, STATE, PIN, CONTACT1, EMAIL_ID,
            DATE_CREATED, DATE_MODIFIED
        FROM fi_xx_md_nominee
        WHERE EMP_CD = %s
        ORDER BY NOMIN_TYPE, SL_NO
    """
    with connection.cursor() as cur:
        try:
            cur.execute(sql, [key])
        except Exception:
            cur.execute(simple_sql, [key])
        cols = [c[0].lower() for c in cur.description]
        rows = []
        for raw in cur.fetchall():
            row = dict(zip(cols, raw))
            type_cd = str(row.get("nomin_type") or "").strip().upper()
            label = next(
                (t["label"] for t in NOMIN_TYPE_CHOICES if t["value"] == type_cd),
                type_cd,
            )
            share = row.get("share_pct")
            rows.append(
                {
                    "emp_cd": str(row.get("emp_cd") or "").strip(),
                    "nomin_type": type_cd,
                    "nomin_type_label": label,
                    "sl_no": int(row.get("sl_no") or 0),
                    "nominee_name": str(row.get("nominee_name") or "").strip(),
                    "relation_cd": row.get("relation_cd"),
                    "relation_desc": str(row.get("relation_desc") or "").strip(),
                    "share_pct": float(share) if share is not None else None,
                    "birth_dt": _fmt_date(row.get("birth_dt")),
                    "marital_status": str(row.get("marital_status") or "").strip(),
                    "employed_flg": row.get("employed_flg"),
                    "handicap_flg": row.get("handicap_flg"),
                    "bank_cd": str(row.get("bank_cd") or "").strip(),
                    "bank_desc": str(row.get("bank_desc") or "").strip(),
                    "bank_ac_no": str(row.get("bank_ac_no") or "").strip(),
                    "addr1": str(row.get("addr1") or "").strip(),
                    "addr2": str(row.get("addr2") or "").strip(),
                    "city": str(row.get("city") or "").strip(),
                    "state": str(row.get("state") or "").strip(),
                    "pin": row.get("pin"),
                    "contact1": str(row.get("contact1") or "").strip(),
                    "email_id": str(row.get("email_id") or "").strip(),
                    "date_created": _fmt_date(row.get("date_created")),
                    "date_modified": _fmt_date(row.get("date_modified")),
                }
            )
        return rows


def _share_total(emp_cd: str, nomin_type: str, exclude_sl: int | None = None) -> Decimal:
    sql = """
        SELECT COALESCE(SUM(SHARE_PCT), 0)
        FROM fi_xx_md_nominee
        WHERE EMP_CD = %s AND NOMIN_TYPE = %s
    """
    params = [emp_cd, nomin_type]
    if exclude_sl is not None:
        sql += " AND SL_NO <> %s"
        params.append(exclude_sl)
    with connection.cursor() as cur:
        cur.execute(sql, params)
        val = cur.fetchone()[0]
    return Decimal(str(val or 0))


def _next_sl_no(emp_cd: str, nomin_type: str) -> int:
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(MAX(SL_NO), 0) + 1
            FROM fi_xx_md_nominee
            WHERE EMP_CD = %s AND NOMIN_TYPE = %s
            """,
            [emp_cd, nomin_type],
        )
        return int(cur.fetchone()[0] or 1)


def _wife_count(emp_cd: str, nomin_type: str) -> int:
    """Oracle PRE-INSERT: max 4 wives via relation_desc = WIFE."""
    with connection.cursor() as cur:
        try:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM fi_xx_md_nominee n
                JOIN fi_pm_mh_relation r ON r.RELATION_CD = n.RELATION_CD
                WHERE n.EMP_CD = %s
                  AND n.NOMIN_TYPE = %s
                  AND UPPER(TRIM(r.RELATION_DESC)) = 'WIFE'
                """,
                [emp_cd, nomin_type],
            )
            return int(cur.fetchone()[0] or 0)
        except Exception:
            return 0


def _is_wife_relation(relation_cd) -> bool:
    if relation_cd is None or relation_cd == "":
        return False
    with connection.cursor() as cur:
        try:
            cur.execute(
                """
                SELECT UPPER(TRIM(RELATION_DESC))
                FROM fi_pm_mh_relation
                WHERE RELATION_CD = %s
                LIMIT 1
                """,
                [int(relation_cd)],
            )
            row = cur.fetchone()
            return bool(row and row[0] == "WIFE")
        except Exception:
            return False


def create_nominee(data: dict, *, user_code: str = "") -> dict:
    """Insert nominee with Oracle FI_XX_MD_NOMIN_PN_E rules."""
    emp = get_employee(data.get("emp_cd"))
    emp_cd = emp["emp_cd"]
    nomin_type = _clip(data.get("nomin_type"), 2).upper()
    if not nomin_type:
        raise NomineeError("Nominee type can't be left blank")
    if nomin_type not in {t["value"] for t in NOMIN_TYPE_CHOICES}:
        raise NomineeError(f"Invalid nominee type '{nomin_type}'")

    nominee_name = _clip(data.get("nominee_name"), 50)
    if not nominee_name:
        raise NomineeError("Nominee Name can't be left blank")

    relation_cd = data.get("relation_cd")
    if relation_cd in (None, ""):
        raise NomineeError("Nominee Relationship can't be left blank")
    try:
        relation_cd = int(relation_cd)
    except (TypeError, ValueError) as exc:
        raise NomineeError("Invalid relationship code") from exc

    share = _as_decimal(data.get("share_pct"), "share_pct")
    if share is None:
        raise NomineeError("Share % can't be left blank")
    if share <= 0:
        raise NomineeError("Share % must be greater than zero")

    existing = _share_total(emp_cd, nomin_type)
    if existing + share > Decimal("100"):
        raise NomineeError("Share percentage can't exceed 100%.")

    if _is_wife_relation(relation_cd) and _wife_count(emp_cd, nomin_type) >= 4:
        raise NomineeError("More than four wives is not allowed for nominee.")

    sl_no = _next_sl_no(emp_cd, nomin_type)
    marital = _clip(data.get("marital_status") or "M", 1).upper() or "M"
    employed = data.get("employed_flg")
    if employed in (None, ""):
        employed = 0
    handicap = data.get("handicap_flg")
    if handicap in (None, ""):
        handicap = 0
    try:
        employed = int(employed)
        handicap = int(handicap)
    except (TypeError, ValueError) as exc:
        raise NomineeError("Invalid employed/handicap flag") from exc

    bank_cd = _clip(data.get("bank_cd"), 6) or None
    bank_ac = _clip(data.get("bank_ac_no"), 15) or None
    birth_dt = (data.get("birth_dt") or "").strip() or None
    pin = data.get("pin")
    if pin in ("", None):
        pin = None
    elif pin is not None:
        try:
            pin = int(pin)
        except (TypeError, ValueError) as exc:
            raise NomineeError("Invalid PIN") from exc

    now = timezone.now()
    user = _clip(user_code, 5) or "SMPK"

    with connection.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fi_xx_md_nominee (
                EMP_CD, NOMIN_TYPE, SL_NO, NOMINEE_NAME, RELATION_CD,
                ADDR1, ADDR2, PS, CITY, DIST, STATE, PIN, COUNTRY,
                CONTACT1, CONTACT2, FAX_NO, EMAIL_ID, BIRTH_DT,
                SHARE_PCT, MARITAL_STATUS, EMPLOYED_FLG, HANDICAP_FLG,
                BANK_CD, BANK_AC_NO, DATE_CREATED, CREATED_BY
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            """,
            [
                emp_cd,
                nomin_type,
                sl_no,
                nominee_name,
                relation_cd,
                _clip(data.get("addr1"), 25) or None,
                _clip(data.get("addr2"), 25) or None,
                _clip(data.get("ps"), 30) or None,
                _clip(data.get("city"), 20) or None,
                _clip(data.get("dist"), 20) or None,
                _clip(data.get("state"), 20) or None,
                pin,
                _clip(data.get("country"), 20) or "INDIA",
                _clip(data.get("contact1"), 15) or None,
                _clip(data.get("contact2"), 15) or None,
                _clip(data.get("fax_no"), 15) or None,
                _clip(data.get("email_id"), 30) or None,
                birth_dt,
                share,
                marital,
                employed,
                handicap,
                bank_cd,
                bank_ac,
                now,
                user,
            ],
        )

    nominees = list_nominees(emp_cd)
    created = next(
        (
            n
            for n in nominees
            if n["nomin_type"] == nomin_type and n["sl_no"] == sl_no
        ),
        None,
    )
    return {
        "employee": emp,
        "nominee": created,
        "sl_no": sl_no,
        "message": f"The nominee serial number is {sl_no}.",
        "nominees": nominees,
    }


def get_nominee_bundle(emp_cd: str) -> dict:
    emp = get_employee(emp_cd)
    nominees = list_nominees(emp["emp_cd"])
    by_type = {}
    for n in nominees:
        t = n["nomin_type"]
        by_type.setdefault(t, Decimal("0"))
        by_type[t] += Decimal(str(n.get("share_pct") or 0))
    return {
        "employee": emp,
        "nominees": nominees,
        "share_totals": {k: float(v) for k, v in by_type.items()},
        "nomin_type_choices": NOMIN_TYPE_CHOICES,
    }
