"""
LIC Claim Generation — Oracle FI_PN_LIC_BILL_GEN_E (normal pension first).

Persists rows in fi_pn_lic_bill_gen. Pension type N = normal / first pension.
"""

from datetime import datetime

from django.db import connection, transaction
from django.db.utils import DatabaseError, ProgrammingError


class LicClaimGenerationError(Exception):
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
    """Run a lookup; return None if the table/column is missing in MySQL."""
    try:
        cursor.execute(sql, params or [])
        return cursor.fetchone()
    except (ProgrammingError, DatabaseError):
        try:
            connection.rollback()
        except Exception:
            pass
        return None


def _as_float(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        text = str(value).strip()
        return float(text) if text.isdigit() else None


def _as_lic_sl(value):
    """LIC SL No is a short serial; reject bank/Aadhaar-like annuity numbers."""
    n = _as_float(value)
    if n is None or n <= 0 or n > 99_999_999:
        return None
    return n

def _fetch_emp_name(cursor, emp: str) -> str:
    cursor.execute(
        """
        SELECT TRIM(CONCAT_WS(' ', TITLE, FIRST_NAME, MIDDLE_NAME, LAST_NAME))
        FROM fi_xx_mh_emp_per
        WHERE EMP_CD = %s
        LIMIT 1
        """,
        [emp],
    )
    row = cursor.fetchone()
    if row and str(row[0] or "").strip():
        return str(row[0]).strip()
    cursor.execute(
        """
        SELECT NAME FROM fi_pn_mh_pensioner
        WHERE EMP_CD = %s
        LIMIT 1
        """,
        [emp],
    )
    row = cursor.fetchone()
    return str(row[0] or "").strip() if row else ""


def _fetch_address_normal(cursor, emp: str) -> str:
    cursor.execute(
        """
        SELECT CONCAT_WS(
            ', ',
            NULLIF(TRIM(PERM_ADDR1), ''),
            NULLIF(TRIM(PERM_ADDR2), ''),
            NULLIF(TRIM(PERM_PS), ''),
            NULLIF(TRIM(PERM_CITY), ''),
            NULLIF(TRIM(PERM_DIST), ''),
            NULLIF(TRIM(PERM_STATE), ''),
            NULLIF(TRIM(PERM_PIN), '')
        )
        FROM fi_xx_mh_emp_per
        WHERE EMP_CD = %s
        LIMIT 1
        """,
        [emp],
    )
    row = cursor.fetchone()
    return str(row[0] or "").strip() if row else ""


def _fetch_normal_defaults(cursor, emp: str) -> dict:
    """
    Resolve Claim ID, Roll No, LIC SL No, Address from local finance schema.
    Prefer first_pension_pensionproposal for new cases.
    """
    claim_id = ""
    pen_roll = ""
    lic_sl = None
    address = _fetch_address_normal(cursor, emp)

    # App proposal (primary)
    row = _safe_one(
        cursor,
        """
        SELECT ca_number, pension_roll_no
        FROM first_pension_pensionproposal
        WHERE emp_cd = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        [emp],
    )
    if row:
        claim_id = _as_str(row[0], 10)
        pen_roll = _as_str(row[1], 20)

    # Legacy finance proposal — fill blanks
    if not claim_id or not pen_roll:
        row = _safe_one(
            cursor,
            """
            SELECT CA_NUMBER, PENSION_ROLL_NO
            FROM fi_pn_mh_pension_proposal
            WHERE EMP_CD = %s
            ORDER BY CA_NUMBER DESC
            LIMIT 1
            """,
            [emp],
        )
        if row:
            if not claim_id:
                claim_id = _as_str(row[0], 10)
            if not pen_roll:
                pen_roll = _as_str(row[1], 20)

    if not claim_id:
        row = _safe_one(
            cursor,
            """
            SELECT CA_NUMBER
            FROM fi_pn_mh_pensioner
            WHERE EMP_CD = %s
            ORDER BY CA_NUMBER DESC
            LIMIT 1
            """,
            [emp],
        )
        if row:
            claim_id = _as_str(row[0], 10)

    if not pen_roll:
        row = _safe_one(
            cursor,
            """
            SELECT PENSION_ROLL_NO
            FROM fi_pn_mh_pensioner
            WHERE EMP_CD = %s
              AND PENSION_ROLL_NO IS NOT NULL
              AND TRIM(PENSION_ROLL_NO) <> ''
            LIMIT 1
            """,
            [emp],
        )
        if row:
            pen_roll = _as_str(row[0], 20)

    # Existing LIC claim row (common path — already generated earlier).
    row = _safe_one(
        cursor,
        """
        SELECT LIC_SL_NO, PEN_ROLL_NO, CLAIM_ID, ADDRESS
        FROM fi_pn_lic_bill_gen
        WHERE EMP_CD = %s
          AND UPPER(COALESCE(PENSION_TYPE, '')) = 'N'
        ORDER BY CREATED_ON DESC, CLAIM_ID DESC
        LIMIT 1
        """,
        [emp],
    )
    if row:
        if lic_sl is None:
            lic_sl = _as_lic_sl(row[0])
        if not pen_roll:
            pen_roll = _as_str(row[1], 20)
        if not claim_id:
            claim_id = _as_str(row[2], 10)
        if not address:
            address = _as_str(row[3], 200)

    if not pen_roll:
        row = _safe_one(
            cursor,
            """
            SELECT ROLL_NO
            FROM fi_pn_mh_bill_print
            WHERE EMP_CD = %s
              AND ROLL_NO IS NOT NULL
              AND TRIM(ROLL_NO) <> ''
            ORDER BY DATE_CREATED DESC
            LIMIT 1
            """,
            [emp],
        )
        if row:
            pen_roll = _as_str(row[0], 20)

    if lic_sl is None:
        row = _safe_one(
            cursor,
            """
            SELECT ANNUITY_NO
            FROM fi_pn_mh_bill_print
            WHERE EMP_CD = %s
              AND ANNUITY_NO IS NOT NULL
              AND TRIM(ANNUITY_NO) <> ''
            ORDER BY DATE_CREATED DESC
            LIMIT 1
            """,
            [emp],
        )
        if row:
            lic_sl = _as_lic_sl(row[0])

    if not pen_roll:
        row = _safe_one(
            cursor,
            """
            SELECT PENSION_ROLL
            FROM fi_pn_lic_details_data
            WHERE EMP_CD = %s
              AND PENSION_ROLL IS NOT NULL
              AND TRIM(PENSION_ROLL) <> ''
            ORDER BY CREATED_ON DESC
            LIMIT 1
            """,
            [emp],
        )
        if row:
            pen_roll = _as_str(row[0], 20)

    if not pen_roll:
        row = _safe_one(
            cursor,
            """
            SELECT PENSION_ROLL_NO
            FROM fi_pn_lic_master
            WHERE SALARY_ROLL_NO = %s
              AND PENSION_ROLL_NO IS NOT NULL
              AND TRIM(PENSION_ROLL_NO) <> ''
            LIMIT 1
            """,
            [emp],
        )
        if row:
            pen_roll = _as_str(row[0], 20)

    if not pen_roll:
        row = _safe_one(
            cursor,
            """
            SELECT ROLL_NO
            FROM fi_pn_wage_2022_hdr_third
            WHERE EMP_CD = %s
              AND ROLL_NO IS NOT NULL
              AND TRIM(ROLL_NO) <> ''
            LIMIT 1
            """,
            [emp],
        )
        if row:
            pen_roll = _as_str(row[0], 20)

    if lic_sl is None:
        row = _safe_one(
            cursor,
            """
            SELECT LIC_SL_NO
            FROM fi_pn_lic_details_data
            WHERE EMP_CD = %s
              AND LIC_SL_NO IS NOT NULL
            ORDER BY CREATED_ON DESC
            LIMIT 1
            """,
            [emp],
        )
        if row:
            lic_sl = _as_lic_sl(row[0])

    if lic_sl is None:
        row = _safe_one(
            cursor,
            """
            SELECT ANNUITY_NO
            FROM fi_pn_lic_master
            WHERE SALARY_ROLL_NO = %s
              AND ANNUITY_NO IS NOT NULL
              AND TRIM(ANNUITY_NO) <> ''
            LIMIT 1
            """,
            [emp],
        )
        if row:
            lic_sl = _as_lic_sl(row[0])

    return {
        "claim_id": claim_id,
        "pen_roll_no": pen_roll,
        "lic_sl_no": lic_sl,
        "address": address,
    }


def _list_ca_numbers(cursor, emp: str) -> list:
    seen = set()
    out = []
    for sql in (
        """
        SELECT ca_number
        FROM first_pension_pensionproposal
        WHERE emp_cd = %s
          AND ca_number IS NOT NULL
          AND TRIM(ca_number) <> ''
        ORDER BY id DESC
        """,
        """
        SELECT CA_NUMBER
        FROM fi_pn_mh_pension_proposal
        WHERE EMP_CD = %s
          AND CA_NUMBER IS NOT NULL
          AND TRIM(CA_NUMBER) <> ''
        ORDER BY CA_NUMBER DESC
        """,
        """
        SELECT CA_NUMBER
        FROM fi_pn_mh_pensioner
        WHERE EMP_CD = %s
          AND CA_NUMBER IS NOT NULL
          AND TRIM(CA_NUMBER) <> ''
        ORDER BY CA_NUMBER DESC
        """,
    ):
        rows = []
        try:
            cursor.execute(sql, [emp])
            rows = cursor.fetchall()
        except (ProgrammingError, DatabaseError):
            try:
                connection.rollback()
            except Exception:
                pass
            rows = []
        for r in rows:
            if not r or not r[0]:
                continue
            val = _as_str(r[0], 10)
            if val and val not in seen:
                seen.add(val)
                out.append(val)
    return out


def _row_dict(row) -> dict:
    if not row:
        return {}
    return {
        "emp_cd": _as_str(row[0], 6),
        "lic_sl_no": float(row[1]) if row[1] is not None else None,
        "pen_roll_no": _as_str(row[2], 20),
        "pension_type": _as_str(row[3], 1).upper() or "N",
        "claim_id": _as_str(row[4], 10),
        "address": _as_str(row[5], 200),
        "created_by": _as_str(row[6], 5),
        "created_on": row[7].isoformat() if row[7] else None,
        "modified_by": _as_str(row[8], 5) if row[8] else "",
        "modified_on": row[9].isoformat() if row[9] else None,
    }


def list_normal_claims(emp_id) -> list:
    emp = _emp_key(emp_id)
    if not emp:
        return []
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EMP_CD, LIC_SL_NO, PEN_ROLL_NO, PENSION_TYPE, CLAIM_ID,
                   ADDRESS, CREATED_BY, CREATED_ON, MODIFIED_BY, MODIFIED_ON
            FROM fi_pn_lic_bill_gen
            WHERE EMP_CD = %s
              AND UPPER(COALESCE(PENSION_TYPE, '')) = 'N'
            ORDER BY CREATED_ON DESC, CLAIM_ID DESC
            """,
            [emp],
        )
        return [_row_dict(r) for r in cursor.fetchall()]


def load_normal_claim(emp_id, claim_id=None) -> dict:
    """
    Load existing normal LIC claim row, or defaults from proposal / emp master.
    """
    emp = _emp_key(emp_id)
    if not emp:
        raise LicClaimGenerationError("Employee code is required")

    with connection.cursor() as cursor:
        name = _fetch_emp_name(cursor, emp)
        if not name:
            # Still allow if local proposal / pensioner / emp exists
            found = False
            for sql in (
                "SELECT 1 FROM first_pension_pensionproposal WHERE emp_cd = %s LIMIT 1",
                "SELECT 1 FROM fi_pn_mh_pensioner WHERE EMP_CD = %s LIMIT 1",
                "SELECT 1 FROM fi_pn_mh_pension_proposal WHERE EMP_CD = %s LIMIT 1",
                "SELECT 1 FROM fi_xx_mh_emp_per WHERE EMP_CD = %s LIMIT 1",
            ):
                row = _safe_one(cursor, sql, [emp])
                if row:
                    found = True
                    break
            if not found:
                raise LicClaimGenerationError(f"Employee {emp} not found")

        ca_numbers = _list_ca_numbers(cursor, emp)
        defaults = _fetch_normal_defaults(cursor, emp)

        existing = None
        cid = _as_str(claim_id, 10)
        if cid:
            cursor.execute(
                """
                SELECT EMP_CD, LIC_SL_NO, PEN_ROLL_NO, PENSION_TYPE, CLAIM_ID,
                       ADDRESS, CREATED_BY, CREATED_ON, MODIFIED_BY, MODIFIED_ON
                FROM fi_pn_lic_bill_gen
                WHERE EMP_CD = %s
                  AND CLAIM_ID = %s
                  AND UPPER(COALESCE(PENSION_TYPE, '')) = 'N'
                LIMIT 1
                """,
                [emp, cid],
            )
            existing = _row_dict(cursor.fetchone())
        if not existing:
            cursor.execute(
                """
                SELECT EMP_CD, LIC_SL_NO, PEN_ROLL_NO, PENSION_TYPE, CLAIM_ID,
                       ADDRESS, CREATED_BY, CREATED_ON, MODIFIED_BY, MODIFIED_ON
                FROM fi_pn_lic_bill_gen
                WHERE EMP_CD = %s
                  AND UPPER(COALESCE(PENSION_TYPE, '')) = 'N'
                ORDER BY CREATED_ON DESC, CLAIM_ID DESC
                LIMIT 1
                """,
                [emp],
            )
            existing = _row_dict(cursor.fetchone())

        claims = list_normal_claims(emp)

        # Prefer saved claim row; fill any blank fields from master defaults.
        if existing:
            claim = {
                **existing,
                "lic_sl_no": (
                    existing.get("lic_sl_no")
                    if existing.get("lic_sl_no") is not None
                    else defaults.get("lic_sl_no")
                ),
                "pen_roll_no": existing.get("pen_roll_no")
                or defaults.get("pen_roll_no")
                or "",
                "claim_id": existing.get("claim_id")
                or defaults.get("claim_id")
                or "",
                "address": existing.get("address")
                or defaults.get("address")
                or "",
                "pension_type": "N",
            }
            exists = True
        else:
            claim = {
                "emp_cd": emp,
                "lic_sl_no": defaults.get("lic_sl_no"),
                "pen_roll_no": defaults.get("pen_roll_no") or "",
                "pension_type": "N",
                "claim_id": defaults.get("claim_id") or "",
                "address": defaults.get("address") or "",
            }
            exists = False

        return {
            "emp_cd": emp,
            "emp_name": name,
            "pension_type": "N",
            "exists": exists,
            "claim": claim,
            "claims": claims,
            "ca_numbers": ca_numbers,
            "defaults": defaults,
        }


def save_normal_claim(payload, user=None) -> dict:
    """Insert or update a normal (N) LIC claim generation row."""
    emp = _emp_key(payload.get("emp_cd") or payload.get("emp_id"))
    claim_id = _as_str(payload.get("claim_id"), 10)
    if not emp:
        raise LicClaimGenerationError("Employee code is required")
    if not claim_id:
        raise LicClaimGenerationError("Claim ID / CA Number is required")

    lic_sl_raw = payload.get("lic_sl_no")
    lic_sl_no = None
    if lic_sl_raw is not None and str(lic_sl_raw).strip() != "":
        try:
            lic_sl_no = float(lic_sl_raw)
        except (TypeError, ValueError) as exc:
            raise LicClaimGenerationError("LIC SL No must be numeric") from exc

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
                        PENSION_TYPE = 'N',
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
                    ) VALUES (%s, %s, %s, 'N', %s, %s, %s, %s)
                    """,
                    [emp, lic_sl_no, pen_roll_no, claim_id, user_cd, now, address],
                )

    return load_normal_claim(emp, claim_id=claim_id)
