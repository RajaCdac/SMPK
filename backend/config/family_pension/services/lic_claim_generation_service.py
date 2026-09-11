"""
LIC Claim Generation — Family pension (PENSION_TYPE = F).

Oracle FI_PN_LIC_BILL_GEN_E family path: claim from fi_pn_mh_fpen_caclaim,
address from APPLICANT_ADDRESS, print FI_PN_LIC_FAMILY_PEN_DTLS (+ P_DA).
"""

from __future__ import annotations

from datetime import datetime

from django.db import connection, transaction
from django.db.utils import DatabaseError, ProgrammingError


class FamilyLicClaimError(Exception):
    pass


def _emp_key(emp_id) -> str:
    return str(emp_id or "").strip()[:6]


def _user_cd(user) -> str:
    return str(getattr(user, "username", None) or "A0001").strip()[:5].upper() or "A0001"


def _as_str(value, maxlen=None):
    text = "" if value is None else str(value).strip()
    if maxlen is not None:
        return text[:maxlen]
    return text


def _safe_one(cursor, sql, params=None):
    try:
        cursor.execute(sql, params or [])
        return cursor.fetchone()
    except (ProgrammingError, DatabaseError):
        try:
            connection.rollback()
        except Exception:
            pass
        return None


def _safe_all(cursor, sql, params=None):
    try:
        cursor.execute(sql, params or [])
        return cursor.fetchall()
    except (ProgrammingError, DatabaseError):
        try:
            connection.rollback()
        except Exception:
            pass
        return []


def _as_float(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        text = str(value).strip()
        return float(text) if text.isdigit() else None


def _as_lic_sl(value):
    n = _as_float(value)
    if n is None or n <= 0 or n > 99_999_999:
        return None
    return n


def _fetch_emp_name(cursor, emp: str) -> str:
    row = _safe_one(
        cursor,
        """
        SELECT TRIM(CONCAT_WS(' ', TITLE, FIRST_NAME, MIDDLE_NAME, LAST_NAME))
        FROM fi_xx_mh_emp_per
        WHERE EMP_CD = %s
        LIMIT 1
        """,
        [emp],
    )
    if row and str(row[0] or "").strip():
        return str(row[0]).strip()
    row = _safe_one(
        cursor,
        "SELECT NAME FROM fi_pn_mh_pensioner WHERE EMP_CD = %s LIMIT 1",
        [emp],
    )
    return str(row[0] or "").strip() if row else ""


def _list_fp_claims(cursor, emp: str) -> list:
    rows = _safe_all(
        cursor,
        """
        SELECT CLMCA_ID, APPLICANT_NAME, APPLICANT_ADDRESS, FPENSION_ROLL_NO
        FROM fi_pn_mh_fpen_caclaim
        WHERE EMP_CD = %s
        ORDER BY CLMCA_ID DESC
        """,
        [emp],
    )
    out = []
    for r in rows or []:
        cid = _as_str(r[0], 10)
        if not cid:
            continue
        out.append(
            {
                "claim_id": cid,
                "applicant_name": _as_str(r[1], 100),
                "address": _as_str(r[2], 200),
                "fpension_roll_no": _as_str(r[3], 20),
            }
        )
    return out


def _row_dict(row) -> dict:
    if not row:
        return {}
    return {
        "emp_cd": _as_str(row[0], 6),
        "lic_sl_no": float(row[1]) if row[1] is not None else None,
        "pen_roll_no": _as_str(row[2], 20),
        "pension_type": "F",
        "claim_id": _as_str(row[3], 10),
        "address": _as_str(row[4], 200),
        "created_by": _as_str(row[5], 5),
        "created_on": row[6].isoformat() if row[6] else None,
        "modified_by": _as_str(row[7], 5) if row[7] else "",
        "modified_on": row[8].isoformat() if row[8] else None,
    }


def _fetch_bill_gen(cursor, emp: str, claim_id=None) -> dict:
    cid = _as_str(claim_id, 10)
    if cid:
        row = _safe_one(
            cursor,
            """
            SELECT EMP_CD, LIC_SL_NO, PEN_ROLL_NO, CLAIM_ID, ADDRESS,
                   CREATED_BY, CREATED_ON, MODIFIED_BY, MODIFIED_ON
            FROM fi_pn_lic_bill_gen
            WHERE EMP_CD = %s
              AND CLAIM_ID = %s
              AND UPPER(COALESCE(PENSION_TYPE, '')) = 'F'
            LIMIT 1
            """,
            [emp, cid],
        )
        if row:
            return _row_dict(row)
    row = _safe_one(
        cursor,
        """
        SELECT EMP_CD, LIC_SL_NO, PEN_ROLL_NO, CLAIM_ID, ADDRESS,
               CREATED_BY, CREATED_ON, MODIFIED_BY, MODIFIED_ON
        FROM fi_pn_lic_bill_gen
        WHERE EMP_CD = %s
          AND UPPER(COALESCE(PENSION_TYPE, '')) = 'F'
        ORDER BY CREATED_ON DESC, CLAIM_ID DESC
        LIMIT 1
        """,
        [emp],
    )
    return _row_dict(row)


def _fpension_roll(cursor, emp: str, claim_id: str) -> str:
    row = _safe_one(
        cursor,
        """
        SELECT FPENSION_ROLL_NO
        FROM fi_pn_mh_familypensioner
        WHERE EMP_CD = %s
          AND (%s = '' OR CLMCA_ID = %s)
          AND FPENSION_ROLL_NO IS NOT NULL
          AND TRIM(FPENSION_ROLL_NO) <> ''
        LIMIT 1
        """,
        [emp, claim_id, claim_id],
    )
    if row:
        return _as_str(row[0], 20)
    row = _safe_one(
        cursor,
        """
        SELECT FPENSION_ROLL_NO
        FROM fi_pn_mh_fpen_caclaim
        WHERE EMP_CD = %s
          AND (%s = '' OR CLMCA_ID = %s)
          AND FPENSION_ROLL_NO IS NOT NULL
          AND TRIM(FPENSION_ROLL_NO) <> ''
        LIMIT 1
        """,
        [emp, claim_id, claim_id],
    )
    return _as_str(row[0], 20) if row else ""


def _default_da_pct(cursor, emp: str, claim_id: str) -> float | None:
    """Best-effort DA% for family print (form DA_PER)."""
    row = _safe_one(
        cursor,
        """
        SELECT COALESCE(f.APP_CLASS, c.CLASS), COALESCE(f.BASE_CPI, c.RETIREMENT_CPI)
        FROM fi_pn_mh_fpen_caclaim c
        LEFT JOIN fi_pn_mh_familypensioner f
          ON f.EMP_CD = c.EMP_CD AND f.CLMCA_ID = c.CLMCA_ID
        WHERE c.EMP_CD = %s
          AND (%s = '' OR c.CLMCA_ID = %s)
        LIMIT 1
        """,
        [emp, claim_id, claim_id],
    )
    emp_class = 1
    cpi = 277
    if row:
        if row[0] is not None and str(row[0]).strip() != "":
            try:
                emp_class = int(float(row[0]))
            except (TypeError, ValueError):
                emp_class = 1
        if row[1] is not None:
            try:
                cpi = int(float(row[1]))
            except (TypeError, ValueError):
                cpi = 277
    class_grp = 1 if emp_class in (1, 2) else 3
    da = _safe_one(
        cursor,
        """
        SELECT DA_PCT FROM fi_pr_mh_calc_da
        WHERE EMP_CLASS_GRP = %s
          AND WEF_DT <= CURDATE()
        ORDER BY WEF_DT DESC
        LIMIT 1
        """,
        [class_grp],
    )
    if da and da[0] is not None:
        return float(da[0])
    # unused cpi kept for future era-specific tables
    _ = cpi
    return None


def load_family_claim(emp_id, claim_id=None) -> dict:
    emp = _emp_key(emp_id)
    if not emp:
        raise FamilyLicClaimError("Employee code is required")

    with connection.cursor() as cursor:
        claims = _list_fp_claims(cursor, emp)
        existing_any = _fetch_bill_gen(cursor, emp, claim_id=None)

        # Resolve claim id: param → existing bill_gen → first FP claim
        cid = _as_str(claim_id, 10)
        if not cid and existing_any:
            cid = existing_any.get("claim_id") or ""
        if not cid and claims:
            cid = claims[0]["claim_id"]

        if not claims and not existing_any:
            # still allow if emp exists
            name = _fetch_emp_name(cursor, emp)
            if not name:
                row = _safe_one(
                    cursor,
                    "SELECT 1 FROM fi_xx_mh_emp_per WHERE EMP_CD = %s LIMIT 1",
                    [emp],
                )
                if not row:
                    raise FamilyLicClaimError(f"Employee {emp} not found")
            raise FamilyLicClaimError(
                f"No family pension claim found for employee {emp}"
            )

        claim_meta = next((c for c in claims if c["claim_id"] == cid), None)
        if not claim_meta and claims and not cid:
            claim_meta = claims[0]
            cid = claim_meta["claim_id"]
        if not claim_meta and cid:
            # claim may exist only on bill_gen
            claim_meta = {
                "claim_id": cid,
                "applicant_name": "",
                "address": "",
                "fpension_roll_no": "",
            }

        existing = _fetch_bill_gen(cursor, emp, claim_id=cid) if cid else {}
        emp_name = _fetch_emp_name(cursor, emp)
        applicant = (claim_meta or {}).get("applicant_name") or ""
        address = ""
        pen_roll = ""
        lic_sl = None

        if existing:
            lic_sl = existing.get("lic_sl_no")
            pen_roll = existing.get("pen_roll_no") or ""
            address = existing.get("address") or ""
            cid = existing.get("claim_id") or cid

        if not address:
            address = (claim_meta or {}).get("address") or ""
        if not pen_roll:
            pen_roll = (claim_meta or {}).get("fpension_roll_no") or ""
        if not pen_roll:
            pen_roll = _fpension_roll(cursor, emp, cid)

        da_pct = _default_da_pct(cursor, emp, cid)

        claim = {
            "emp_cd": emp,
            "lic_sl_no": lic_sl if lic_sl is not None else None,
            "pen_roll_no": pen_roll,
            "pension_type": "F",
            "claim_id": cid,
            "address": address,
            "applicant_name": applicant,
        }
        if existing:
            claim = {
                **existing,
                "lic_sl_no": (
                    existing.get("lic_sl_no")
                    if existing.get("lic_sl_no") is not None
                    else lic_sl
                ),
                "pen_roll_no": existing.get("pen_roll_no") or pen_roll,
                "claim_id": existing.get("claim_id") or cid,
                "address": existing.get("address") or address,
                "applicant_name": applicant,
                "pension_type": "F",
            }

        return {
            "emp_cd": emp,
            "emp_name": emp_name,
            "applicant_name": applicant,
            "pension_type": "F",
            "exists": bool(existing),
            "claim": claim,
            "claims": claims,
            "da_pct": da_pct,
        }


def save_family_claim(payload, user=None) -> dict:
    emp = _emp_key(payload.get("emp_cd") or payload.get("emp_id"))
    claim_id = _as_str(payload.get("claim_id"), 10)
    if not emp:
        raise FamilyLicClaimError("Employee code is required")
    if not claim_id:
        raise FamilyLicClaimError("Claim ID is required")

    lic_sl_raw = payload.get("lic_sl_no")
    lic_sl_no = None
    if lic_sl_raw is not None and str(lic_sl_raw).strip() != "":
        try:
            lic_sl_no = float(lic_sl_raw)
        except (TypeError, ValueError) as exc:
            raise FamilyLicClaimError("LIC SL No must be numeric") from exc

    pen_roll_no = _as_str(payload.get("pen_roll_no"), 20)
    address = _as_str(payload.get("address"), 200)
    user_cd = _user_cd(user)
    now = datetime.now()

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EMP_CD FROM fi_pn_lic_bill_gen
                WHERE EMP_CD = %s AND CLAIM_ID = %s
                LIMIT 1
                """,
                [emp, claim_id],
            )
            exists = bool(cursor.fetchone())
            if exists:
                cursor.execute(
                    """
                    UPDATE fi_pn_lic_bill_gen
                    SET LIC_SL_NO = %s,
                        PEN_ROLL_NO = %s,
                        PENSION_TYPE = 'F',
                        ADDRESS = %s,
                        MODIFIED_BY = %s,
                        MODIFIED_ON = %s
                    WHERE EMP_CD = %s AND CLAIM_ID = %s
                    """,
                    [lic_sl_no, pen_roll_no, address, user_cd, now, emp, claim_id],
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO fi_pn_lic_bill_gen (
                        EMP_CD, LIC_SL_NO, PEN_ROLL_NO, PENSION_TYPE, CLAIM_ID,
                        CREATED_BY, CREATED_ON, ADDRESS
                    ) VALUES (%s, %s, %s, 'F', %s, %s, %s, %s)
                    """,
                    [emp, lic_sl_no, pen_roll_no, claim_id, user_cd, now, address],
                )

    return load_family_claim(emp, claim_id=claim_id)
