"""
Family Pension Recovery / Deduction entry
(Oracle: fi_pn_ded_fam_form.fmb → FI_PN_TD_FIRST_MONTH_FPENSION).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db import connection, transaction


class RecoveryDeductionError(Exception):
    pass


def _clip(value, max_len=None, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    if max_len:
        return text[:max_len]
    return text


def _emp_key(emp_cd):
    """Normalize emp code to 5-char Oracle style (zero-pad numeric codes)."""
    text = _clip(emp_cd, 10)
    if not text:
        return ""
    if text.isdigit():
        return text.zfill(5)[-5:]
    return text[:5]


def _emp_match_variants(emp_cd):
    """Return lookup variants so 1231 and 01231 both match."""
    raw = _clip(emp_cd, 10)
    key = _emp_key(emp_cd)
    variants = []
    for v in (key, raw, raw.lstrip("0") or "0"):
        if v and v not in variants:
            variants.append(v)
        if v and v.isdigit():
            padded = v.zfill(5)[-5:]
            if padded not in variants:
                variants.append(padded)
    return variants


def _num(value):
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError, InvalidOperation):
        return None


def _dictfetchall(cur):
    cols = [c[0].lower() if isinstance(c[0], str) else c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _lookup_name(cur, emp_cd, clmca_id=None):
    if clmca_id:
        cur.execute(
            """
            SELECT APPLICANT_NAME
            FROM fi_pn_mh_fpen_caclaim
            WHERE CLMCA_ID = %s
            LIMIT 1
            """,
            [_clip(clmca_id, 20)],
        )
        row = cur.fetchone()
        if row and row[0]:
            return _clip(row[0], 100)

    emp = _emp_key(emp_cd)
    if not emp:
        return ""
    for sql in (
        """
        SELECT TRIM(CONCAT_WS(' ',
            NULLIF(TRIM(TITLE), ''),
            NULLIF(TRIM(FNAME), ''),
            NULLIF(TRIM(MNAME), ''),
            NULLIF(TRIM(LNAME), '')
        ))
        FROM fi_xx_mh_emp_per WHERE EMP_CD = %s LIMIT 1
        """,
        """
        SELECT EMP_NAME FROM fi_pn_mh_pensioner WHERE EMP_CD = %s LIMIT 1
        """,
        """
        SELECT EMP_NAME FROM fi_pn_mh_familypensioner WHERE EMP_CD = %s LIMIT 1
        """,
    ):
        try:
            cur.execute(sql, [emp])
            row = cur.fetchone()
            if row and row[0]:
                return _clip(row[0], 100)
        except Exception:
            continue
    return ""


def _lookup_case_no(cur, clmca_id, emp_cd):
    cid = _clip(clmca_id, 20)
    if cid:
        cur.execute(
            """
            SELECT CA_NO FROM fi_pn_mh_fpen_caclaim
            WHERE CLMCA_ID = %s LIMIT 1
            """,
            [cid],
        )
        row = cur.fetchone()
        if row and row[0]:
            return _clip(row[0], 22)
    emp = _emp_key(emp_cd)
    if emp:
        cur.execute(
            """
            SELECT CA_NUMBER FROM fi_pn_mh_pensioner
            WHERE EMP_CD = %s LIMIT 1
            """,
            [emp],
        )
        row = cur.fetchone()
        if row and row[0]:
            return _clip(row[0], 22)
    return ""


def list_earndedn_codes(*, earn_type: str = "") -> list[dict]:
    """Codes from FI_PN_MH_EARNDEDN, optionally filtered by E/D."""
    et = _clip(earn_type, 1).upper()
    with connection.cursor() as cur:
        if et in ("E", "D"):
            cur.execute(
                """
                SELECT EARNDEDN_CD AS code,
                       EARNDEDN_TYPE AS type,
                       EARNDEDN_DESC AS description
                FROM fi_pn_mh_earndedn
                WHERE UPPER(TRIM(EARNDEDN_TYPE)) = %s
                ORDER BY EARNDEDN_CD
                """,
                [et],
            )
        else:
            cur.execute(
                """
                SELECT EARNDEDN_CD AS code,
                       EARNDEDN_TYPE AS type,
                       EARNDEDN_DESC AS description
                FROM fi_pn_mh_earndedn
                ORDER BY EARNDEDN_TYPE, EARNDEDN_CD
                """
            )
        return _dictfetchall(cur)


def get_earndedn_description(code: str, earn_type: str = "") -> dict | None:
    cd = _clip(code, 10)
    if not cd:
        return None
    et = _clip(earn_type, 1).upper()
    with connection.cursor() as cur:
        if et in ("E", "D"):
            cur.execute(
                """
                SELECT EARNDEDN_CD AS code,
                       EARNDEDN_TYPE AS type,
                       EARNDEDN_DESC AS description
                FROM fi_pn_mh_earndedn
                WHERE EARNDEDN_CD = %s
                  AND UPPER(TRIM(EARNDEDN_TYPE)) = %s
                LIMIT 1
                """,
                [cd, et],
            )
        else:
            cur.execute(
                """
                SELECT EARNDEDN_CD AS code,
                       EARNDEDN_TYPE AS type,
                       EARNDEDN_DESC AS description
                FROM fi_pn_mh_earndedn
                WHERE EARNDEDN_CD = %s
                LIMIT 1
                """,
                [cd],
            )
        rows = _dictfetchall(cur)
        return rows[0] if rows else None


def _list_lines(cur, fam_id: str) -> list[dict]:
    cur.execute(
        """
        SELECT
            td.EARN_DEDN_TYPE AS earn_dedn_type,
            td.EARN_DEDN_CD AS earn_dedn_cd,
            td.AMOUNT AS amount,
            td.ORIGINAL_AMT AS original_amt,
            td.AREAR_AMT AS arear_amt,
            ed.EARNDEDN_DESC AS description
        FROM fi_pn_td_first_month_fpension td
        LEFT JOIN fi_pn_mh_earndedn ed
          ON ed.EARNDEDN_CD = td.EARN_DEDN_CD
         AND UPPER(TRIM(ed.EARNDEDN_TYPE)) = UPPER(TRIM(td.EARN_DEDN_TYPE))
        WHERE td.FAM_FMPEN_ID = %s
        ORDER BY
          CASE WHEN UPPER(COALESCE(td.EARN_DEDN_TYPE,'E')) = 'E' THEN 0 ELSE 1 END,
          td.EARN_DEDN_CD
        """,
        [fam_id],
    )
    rows = _dictfetchall(cur)
    for r in rows:
        for key in ("amount", "original_amt", "arear_amt"):
            if r.get(key) is not None:
                r[key] = float(r[key])
    return rows


def lookup_recovery_context(*, month, year, emp_cd) -> dict:
    """
    Oracle KEY-NEXT-ITEM on EMP_CD:
      find FAM_FMPEN_ID on TH for emp + month + year
      (FPEN/M or FPEN/N, BILL_NO present).
    """
    emp = _emp_key(emp_cd)
    try:
        m = int(month)
        y = int(year)
    except (TypeError, ValueError):
        raise RecoveryDeductionError("Month and Year are required.") from None
    if not emp:
        raise RecoveryDeductionError("Enter the employee number.")
    if m < 1 or m > 12:
        raise RecoveryDeductionError("Month must be 1–12.")
    if y < 1900 or y > 2100:
        raise RecoveryDeductionError("Year is invalid.")

    with connection.cursor() as cur:
        variants = _emp_match_variants(emp_cd)
        placeholders = ", ".join(["%s"] * len(variants))
        cur.execute(
            f"""
            SELECT
                FAM_FMPEN_ID,
                EMP_CD,
                CLMCA_ID,
                FPENSION_MONTH,
                FPENSION_YEAR,
                BILL_NO,
                FPENSION_TYPE,
                FPENSION_AMT,
                RELIEF
            FROM fi_pn_th_first_month_fpension
            WHERE EMP_CD IN ({placeholders})
              AND FPENSION_MONTH = %s
              AND FPENSION_YEAR = %s
              AND (FAM_FMPEN_ID LIKE 'FPEN/M%%' OR FAM_FMPEN_ID LIKE 'FPEN/N%%')
              AND BILL_NO IS NOT NULL
              AND TRIM(BILL_NO) <> ''
            ORDER BY
              CASE WHEN FAM_FMPEN_ID LIKE 'FPEN/M%%' THEN 0 ELSE 1 END,
              FAM_FMPEN_ID DESC
            LIMIT 1
            """,
            [*variants, m, y],
        )
        row = cur.fetchone()
        if not row:
            # Helpful hint: show months that do have a billed header for this emp.
            cur.execute(
                f"""
                SELECT DISTINCT FPENSION_MONTH, FPENSION_YEAR, BILL_NO, FAM_FMPEN_ID
                FROM fi_pn_th_first_month_fpension
                WHERE EMP_CD IN ({placeholders})
                  AND (FAM_FMPEN_ID LIKE 'FPEN/M%%' OR FAM_FMPEN_ID LIKE 'FPEN/N%%')
                  AND BILL_NO IS NOT NULL
                  AND TRIM(BILL_NO) <> ''
                ORDER BY FPENSION_YEAR DESC, FPENSION_MONTH DESC
                LIMIT 5
                """,
                variants,
            )
            hints = cur.fetchall()
            if hints:
                parts = [
                    f"{int(h[0]):02d}/{int(h[1])} ({h[3]})"
                    for h in hints
                ]
                raise RecoveryDeductionError(
                    "No billed family pension for this month/year. "
                    "Try: " + "; ".join(parts)
                )
            raise RecoveryDeductionError(
                "No Entry — family pension bill not found for this "
                "employee / month / year."
            )

        fam_id = _clip(row[0], 30)
        emp_found = _emp_key(row[1]) or emp
        clmca_id = _clip(row[2], 20)
        case_no = _lookup_case_no(cur, clmca_id, emp_found)
        name = _lookup_name(cur, emp_found, clmca_id)
        lines = _list_lines(cur, fam_id)

    return {
        "found": True,
        "fam_fmpen_id": fam_id,
        "emp_cd": emp_found,
        "clmca_id": clmca_id,
        "case_no": case_no,
        "name": name,
        "month": int(row[3]) if row[3] is not None else m,
        "year": int(row[4]) if row[4] is not None else y,
        "bill_no": _clip(row[5], 30),
        "fpension_type": _clip(row[6], 5),
        "fpension_amt": float(row[7]) if row[7] is not None else None,
        "relief": float(row[8]) if row[8] is not None else None,
        "lines": lines,
    }


def save_recovery_line(
    *,
    fam_fmpen_id: str,
    earn_dedn_type: str,
    earn_dedn_cd: str,
    amount,
    user_id: str = "SMPK",
) -> dict:
    """
    Upsert one TD line (PK: FAM_FMPEN_ID + TYPE + CD).
    PRE-INSERT behaviour: ORIGINAL_AMT = AMOUNT on insert.
    """
    fam = _clip(fam_fmpen_id, 30)
    et = _clip(earn_dedn_type, 1).upper()
    cd = _clip(earn_dedn_cd, 10)
    amt = _num(amount)
    user = _clip(user_id, 5) or "SMPK"

    if not fam:
        raise RecoveryDeductionError("FAM_FMPEN_ID is required.")
    if et not in ("E", "D"):
        raise RecoveryDeductionError("Type must be E (Earning) or D (Deduction).")
    if not cd:
        raise RecoveryDeductionError("Earn/Dedn code is required.")
    if amt is None:
        raise RecoveryDeductionError("Amount is required.")

    master = get_earndedn_description(cd, et)
    if not master:
        raise RecoveryDeductionError(
            f"Code {cd} not found in earn/dedn master for type {et}."
        )

    with transaction.atomic():
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM fi_pn_th_first_month_fpension
                WHERE FAM_FMPEN_ID = %s LIMIT 1
                """,
                [fam],
            )
            if not cur.fetchone():
                raise RecoveryDeductionError("Header bill not found for this FMPEN ID.")

            cur.execute(
                """
                SELECT AMOUNT, ORIGINAL_AMT
                FROM fi_pn_td_first_month_fpension
                WHERE FAM_FMPEN_ID = %s
                  AND EARN_DEDN_TYPE = %s
                  AND EARN_DEDN_CD = %s
                LIMIT 1
                """,
                [fam, et, cd],
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    """
                    UPDATE fi_pn_td_first_month_fpension
                    SET AMOUNT = %s,
                        DATE_MODIFIED = NOW(),
                        MODIFIED_BY = %s
                    WHERE FAM_FMPEN_ID = %s
                      AND EARN_DEDN_TYPE = %s
                      AND EARN_DEDN_CD = %s
                    """,
                    [amt, user, fam, et, cd],
                )
                action = "updated"
            else:
                cur.execute(
                    """
                    INSERT INTO fi_pn_td_first_month_fpension (
                        EARN_DEDN_TYPE, EARN_DEDN_CD, AMOUNT,
                        DATE_CREATED, CREATED_BY,
                        FAM_FMPEN_ID, ORIGINAL_AMT, AREAR_AMT
                    ) VALUES (
                        %s, %s, %s,
                        NOW(), %s,
                        %s, %s, NULL
                    )
                    """,
                    [et, cd, amt, user, fam, amt],
                )
                action = "inserted"

            lines = _list_lines(cur, fam)

    return {
        "ok": True,
        "action": action,
        "fam_fmpen_id": fam,
        "earn_dedn_type": et,
        "earn_dedn_cd": cd,
        "description": master.get("description") or "",
        "amount": amt,
        "lines": lines,
    }


def delete_recovery_line(
    *,
    fam_fmpen_id: str,
    earn_dedn_type: str,
    earn_dedn_cd: str,
) -> dict:
    fam = _clip(fam_fmpen_id, 30)
    et = _clip(earn_dedn_type, 1).upper()
    cd = _clip(earn_dedn_cd, 10)
    if not fam or et not in ("E", "D") or not cd:
        raise RecoveryDeductionError("fam_fmpen_id, type and code are required.")

    with transaction.atomic():
        with connection.cursor() as cur:
            cur.execute(
                """
                DELETE FROM fi_pn_td_first_month_fpension
                WHERE FAM_FMPEN_ID = %s
                  AND EARN_DEDN_TYPE = %s
                  AND EARN_DEDN_CD = %s
                """,
                [fam, et, cd],
            )
            deleted = cur.rowcount
            lines = _list_lines(cur, fam)

    if not deleted:
        raise RecoveryDeductionError("Line not found.")
    return {"ok": True, "deleted": deleted, "lines": lines}
