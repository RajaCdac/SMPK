"""
ESR — Employee Personal / Admin from
  smpk_pension.fi_xx_mh_emp_per
  smpk_pension.fi_xx_mh_emp_adm
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.db import connections

# fi_xx_mh_emp_per.STATUS — Personal Information Status (ESR / claim gate).
EMP_PERSONAL_STATUS_LABELS = {
    "RE": "RE — Regular Emp",
    "PE": "PE — Probationary Emp",
    "TE": "TE — Trainee Emp",
    "DW": "DW — Deputationist WB",
    "DC": "DC — Deputationist Central",
    "PN": "PN — Pensioner",
    "FP": "FP — Family Pensioner",
    "EG": "EG — Exgratia holder",
}

EMP_PERSONAL_STATUS_OPTIONS = [
    [code, label] for code, label in EMP_PERSONAL_STATUS_LABELS.items()
]

# Friendly labels for known columns (others title-case from DB name).
_LABELS = {
    # Personal
    "EMP_CD": "Employee Code",
    "TITLE": "Title",
    "FIRST_NAME": "First Name",
    "MIDDLE_NAME": "Middle Name",
    "LAST_NAME": "Last Name",
    "PERM_ADDR1": "Address Line 1",
    "PERM_ADDR2": "Address Line 2",
    "PERM_PS": "Police Station",
    "PERM_CITY": "City",
    "PERM_DIST": "District",
    "PERM_STATE": "State",
    "PERM_PIN": "PIN",
    "PERM_COUNTRY": "Country",
    "PERM_CONTACT1": "Contact 1",
    "PERM_CONTACT2": "Contact 2",
    "PERM_FAX_NO": "Fax",
    "PERM_EMAIL_ID": "Email",
    "PRES_ADDR1": "Address Line 1",
    "PRES_ADDR2": "Address Line 2",
    "PRES_PS": "Police Station",
    "PRES_CITY": "City",
    "PRES_DIST": "District",
    "PRES_STATE": "State",
    "PRES_PIN": "PIN",
    "PRES_COUNTRY": "Country",
    "PRES_CONTACT1": "Contact 1",
    "PRES_CONTACT2": "Contact 2",
    "PRES_FAX_NO": "Fax",
    "PRES_EMAIL_ID": "Email",
    "F_H_FLG": "Father / Husband Flag",
    "F_H_NAME": "Father / Husband Name",
    "F_H_ADDR": "Father / Husband Address",
    "BIRTH_DT": "Date of Birth",
    "DOB_EVIDENCE": "DOB Evidence",
    "SEX": "Sex",
    "EDU_QUAL": "Educational Qualification",
    "PROF_QUAL": "Professional Qualification",
    "OTHER_QUAL": "Other Qualification",
    "AWARDS": "Awards",
    "RELIGION": "Religion",
    "NATIONALITY": "Nationality",
    "HEIGHT_CM": "Height (cm)",
    "ID_MARKS": "Identification Marks",
    "CATEGORY": "Category",
    "HANDICAP_FLG": "Handicapped",
    "MARITAL_STATUS": "Marital Status",
    "DATE_CREATED": "Date Created",
    "DATE_MODIFIED": "Date Modified",
    "CREATED_BY": "Created By",
    "MODIFIED_BY": "Modified By",
    "STATUS": "Status",
    "DOCTOR_FLG": "Doctor Flag",
    "REMARKS": "Remarks",
    # Admin
    "MO_CERT_REF": "MO Certificate Ref",
    "JOIN_DT": "Join Date",
    "EMP_ORIGIN_TAG": "Origin Tag",
    "CONFIRM_DT": "Confirmation Date",
    "APP_QUOTA": "Appointment Quota",
    "SEPARATION_TYPE": "Separation Type",
    "SEPARATION_DT": "Separation Date",
    "TERMIN_REMARK": "Termination Remark",
    "EXP_RET_DT": "Expected Retirement",
    "PF_TYPE": "PF Type",
    "HINDI_FLG": "Hindi Known",
    "DLYPAID_YEARS": "Daily Paid Years",
    "VIG_CERT_NO": "Vigilance Cert No",
    "VIG_CERT_DT": "Vigilance Cert Date",
    "ORDER_NO": "Order No",
    "ORDER_DT": "Order Date",
    "ORDER_ISSUED_BY": "Order Issued By",
    "DESIG_CD": "Designation",
    "UNION_CD": "Union Code",
    "MC_REG_NO": "MC Reg No",
    "MC_REG_DT": "MC Reg Date",
    "KNOWN_FLG": "Known Flag",
    "KNOWN_DETAILS": "Known Details",
    "PAN_NO": "PAN No",
    # Finance
    "BANK_CD": "Bank Code",
    "PAYMODE_CD": "Pay Mode",
    "BANK_AC_NO": "Bank A/C No",
    "LAST_GI_DT": "Last GI Date",
    "NEXT_GI_DT": "Next GI Date",
    "SUSPEND_FLG": "Suspend Flag",
    "SUSPEND_WEF_DT": "Suspend WEF",
    "QTR_FLG": "Quarter Flag",
    "TRANSPORT_FLG": "Transport",
    "TEL_FLG": "Telephone",
    "PAST_SERV_DAYS": "Past Service Days",
    "DUES_CLR_FLG": "Dues Clear Flag",
    "PAY_PCT": "Pay %",
    "FINAL_STLMT_STATUS": "Final Settlement Status",
    "FA_NO": "FA No",
    "SCALE_SL": "Scale",
    "SCALE_WEF_DT": "Scale WEF",
    "SCALE_OPTFOR": "Scale Option For",
    "INLAND_CERT_CLASS": "Inland Cert Class",
    "EMP_CLASS": "Emp Class",
}

_PER_SECTION_ORDER = [
    ("identity", "Identity"),
    ("personal", "Personal details"),
    ("permanent", "Permanent address"),
    ("present", "Present address"),
    ("family", "Father / husband"),
    ("audit", "Record info"),
    ("other", "Other"),
]

_ADM_SECTION_ORDER = [
    ("identity", "Identity"),
    ("service", "Service"),
    ("separation", "Separation"),
    ("orders", "Orders & certificates"),
    ("post", "Post & registration"),
    ("other", "Other"),
    ("audit", "Record info"),
]

_FIN_SECTION_ORDER = [
    ("identity", "Identity"),
    ("bank", "Bank & pay"),
    ("flags", "Allowances & flags"),
    ("scale", "Scale"),
    ("settlement", "Settlement & status"),
    ("other", "Other"),
    ("audit", "Record info"),
]

_PER_ID_ORDER = [
    "TITLE",
    "FIRST_NAME",
    "MIDDLE_NAME",
    "LAST_NAME",
    "STATUS",
]

_ADM_ID_ORDER = [
    "DESIG_CD",
    "JOIN_DT",
    "CONFIRM_DT",
    "EXP_RET_DT",
    "SEPARATION_TYPE",
]

_FIN_ID_ORDER = [
    "SCALE_SL",
    "EMP_CLASS",
    "BANK_CD",
    "BANK_AC_NO",
    "PAYMODE_CD",
]


def _str(value):
    if value is None:
        return ""
    return str(value).strip()


# CREATED_BY / MODIFIED_BY codes → USER_NM from Oracle FINANCE.TR_XX_M_KPTUSERS
# (mirrored on MySQL `finance.tr_xx_m_kptusers`).
_user_nm_cache: dict | None = None


def _user_nm_map() -> dict:
    """USER_ID → USER_NM (lazy, once per process)."""
    global _user_nm_cache
    if _user_nm_cache is not None:
        return _user_nm_cache
    out: dict[str, str] = {}
    try:
        with connections["finance"].cursor() as cur:
            cur.execute(
                """
                SELECT USER_ID, MAX(USER_NM) AS USER_NM
                FROM tr_xx_m_kptusers
                WHERE USER_ID IS NOT NULL
                  AND USER_NM IS NOT NULL
                  AND TRIM(USER_NM) <> ''
                GROUP BY USER_ID
                """
            )
            for uid, nm in cur.fetchall():
                key = _str(uid).upper()
                name = _str(nm)
                if key and name:
                    out[key] = name
    except Exception:
        out = {}
    _user_nm_cache = out
    return out


def _fmt_user_id(code: str) -> str:
    text = _str(code)
    if not text:
        return ""
    name = _user_nm_map().get(text.upper())
    if name:
        return f"{text} — {name}"
    return text


def _fmt_value(key: str, value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()

    text = _str(value)
    ku = key.upper()
    if ku in ("CREATED_BY", "MODIFIED_BY", "L_MODIFIED_BY"):
        return _fmt_user_id(text)
    if ku == "SEX":
        return {"M": "Male", "F": "Female", "O": "Other"}.get(text.upper(), text)
    if ku == "STATUS":
        return EMP_PERSONAL_STATUS_LABELS.get(text.upper(), text)
    if ku == "MARITAL_STATUS":
        return {
            "S": "Single",
            "M": "Married",
            "W": "Widow(er)",
            "D": "Divorced",
        }.get(text.upper(), text)
    if ku == "F_H_FLG":
        return {"F": "Father", "H": "Husband"}.get(text.upper(), text)
    if ku in (
        "HANDICAP_FLG",
        "DOCTOR_FLG",
        "HINDI_FLG",
        "KNOWN_FLG",
        "QTR_FLG",
        "TRANSPORT_FLG",
        "TEL_FLG",
        "DUES_CLR_FLG",
    ):
        if text in ("1", "Y", "YES", "True", "true"):
            return "Yes"
        if text in ("0", "N", "NO", "False", "false"):
            return "No"
        return text
    if ku == "SUSPEND_FLG":
        return {
            "Y": "Yes",
            "N": "No",
            "S": "Suspended",
            "1": "Yes",
            "0": "No",
        }.get(text.upper(), text)
    return text


def _label(key: str) -> str:
    ku = key.upper()
    if ku in _LABELS:
        return _LABELS[ku]
    return ku.replace("_", " ").title()


def _section_for_per(key: str) -> str:
    ku = key.upper()
    if ku in ("TITLE", "FIRST_NAME", "MIDDLE_NAME", "LAST_NAME", "STATUS"):
        return "identity"
    if ku.startswith("PERM_"):
        return "permanent"
    if ku.startswith("PRES_"):
        return "present"
    if ku.startswith("F_H_"):
        return "family"
    if ku in (
        "DATE_CREATED",
        "DATE_MODIFIED",
        "CREATED_BY",
        "MODIFIED_BY",
    ):
        return "audit"
    if ku in (
        "BIRTH_DT",
        "DOB_EVIDENCE",
        "SEX",
        "EDU_QUAL",
        "PROF_QUAL",
        "OTHER_QUAL",
        "AWARDS",
        "RELIGION",
        "NATIONALITY",
        "HEIGHT_CM",
        "ID_MARKS",
        "CATEGORY",
        "HANDICAP_FLG",
        "MARITAL_STATUS",
        "DOCTOR_FLG",
        "REMARKS",
    ):
        return "personal"
    return "other"


def _section_for_adm(key: str) -> str:
    ku = key.upper()
    if ku in (
        "DESIG_CD",
        "JOIN_DT",
        "CONFIRM_DT",
        "EXP_RET_DT",
        "SEPARATION_TYPE",
    ):
        return "identity"
    if ku in (
        "EMP_ORIGIN_TAG",
        "APP_QUOTA",
        "PF_TYPE",
        "HINDI_FLG",
        "DLYPAID_YEARS",
        "MO_CERT_REF",
    ):
        return "service"
    if ku in ("SEPARATION_DT", "TERMIN_REMARK"):
        return "separation"
    if ku in (
        "VIG_CERT_NO",
        "VIG_CERT_DT",
        "ORDER_NO",
        "ORDER_DT",
        "ORDER_ISSUED_BY",
    ):
        return "orders"
    if ku in ("UNION_CD", "MC_REG_NO", "MC_REG_DT", "PAN_NO"):
        return "post"
    if ku in (
        "DATE_CREATED",
        "DATE_MODIFIED",
        "CREATED_BY",
        "MODIFIED_BY",
    ):
        return "audit"
    return "other"


def _section_for_fin(key: str) -> str:
    ku = key.upper()
    if ku in (
        "SCALE_SL",
        "EMP_CLASS",
        "BANK_CD",
        "BANK_AC_NO",
        "PAYMODE_CD",
    ):
        return "identity"
    if ku in ("LAST_GI_DT", "NEXT_GI_DT", "FA_NO", "PAY_PCT"):
        return "bank"
    if ku in (
        "SUSPEND_FLG",
        "SUSPEND_WEF_DT",
        "QTR_FLG",
        "TRANSPORT_FLG",
        "TEL_FLG",
        "PAST_SERV_DAYS",
        "DUES_CLR_FLG",
    ):
        return "flags"
    if ku in ("SCALE_WEF_DT", "SCALE_OPTFOR", "INLAND_CERT_CLASS"):
        return "scale"
    if ku in ("FINAL_STLMT_STATUS", "REMARKS"):
        return "settlement"
    if ku in (
        "DATE_CREATED",
        "DATE_MODIFIED",
        "CREATED_BY",
        "MODIFIED_BY",
    ):
        return "audit"
    return "other"


def _lookup_emp_name(cur, emp_cd: str) -> str:
    cur.execute(
        """
        SELECT TRIM(CONCAT_WS(' ',
            NULLIF(TRIM(TITLE), ''),
            NULLIF(TRIM(FIRST_NAME), ''),
            NULLIF(TRIM(MIDDLE_NAME), ''),
            NULLIF(TRIM(LAST_NAME), '')
        ))
        FROM fi_xx_mh_emp_per
        WHERE EMP_CD = %s
        LIMIT 1
        """,
        [emp_cd],
    )
    row = cur.fetchone()
    return _str(row[0]) if row and row[0] else ""


def _lookup_desig_desc(cur, desig_cd) -> str:
    if desig_cd in (None, ""):
        return ""
    try:
        code = int(desig_cd)
    except (TypeError, ValueError):
        return ""
    try:
        cur.execute(
            "SELECT DESIG_DESC FROM fi_xx_mh_desig WHERE DESIG_CD = %s LIMIT 1",
            [code],
        )
        row = cur.fetchone()
        return _str(row[0]) if row and row[0] else ""
    except Exception:
        return ""


def _order_fields(fields: list, order: list) -> list:
    if not fields:
        return fields
    by_key = {f["key"]: f for f in fields}
    ordered = [by_key[k] for k in order if k in by_key]
    ordered.extend(f for f in fields if f["key"] not in order)
    return ordered


def _build_from_row(
    *,
    cur,
    cols,
    row,
    section_order,
    section_fn,
    identity_order,
    code: str,
    enrich_fn=None,
    display_name: str = "",
):
    raw = {}
    buckets = {key: [] for key, _ in section_order}

    for col, val in zip(cols, row):
        ku = str(col).upper()
        if ku == "EMP_CD":
            continue
        display = _fmt_value(ku, val)
        raw[ku] = display
        buckets[section_fn(ku)].append(
            {
                "key": ku,
                "label": _label(ku),
                "value": display if display != "" else "—",
            }
        )

    if enrich_fn:
        enrich_fn(cur, buckets, raw)

    if "identity" in buckets:
        buckets["identity"] = _order_fields(buckets["identity"], identity_order)

    sections = []
    for sid, title in section_order:
        fields = buckets.get(sid) or []
        if fields:
            sections.append({"id": sid, "title": title, "fields": fields})

    return {
        "found": True,
        "emp_cd": code,
        "display_name": display_name,
        "sections": sections,
        "fields": raw,
    }


# Oracle FI_XX_MH_EMP_PER_E.fmb — field order for read-only entry screen.
_EMP_PER_FORM_GROUPS = [
    {
        "id": "personal",
        "legend": "Personal Information",
        "rows": [
            [("EMP_CD", "Employee Code", "sm")],
            [
                ("TITLE", "Title", "xs"),
                ("FIRST_NAME", "First Name", "md"),
                ("MIDDLE_NAME", "Middle Name", "md"),
                ("LAST_NAME", "Last Name", "md"),
            ],
            [
                ("BIRTH_DT", "Date of Birth", "sm"),
                ("DOB_EVIDENCE", "Evidence", "md"),
                ("SEX", "Sex", "xs"),
            ],
            [
                ("EDU_QUAL", "Educational", "grow"),
                ("PROF_QUAL", "Professional", "grow"),
            ],
            [
                ("OTHER_QUAL", "Other Qualification", "grow"),
                ("AWARDS", "Awards", "grow"),
            ],
            [
                ("RELIGION", "Religion", "sm"),
                ("NATIONALITY", "Nationality", "sm"),
                ("HEIGHT_CM", "Height (Cm)", "xs"),
                ("ID_MARKS", "Identification Marks", "grow"),
            ],
            [
                ("CATEGORY", "Category", "xs"),
                ("HANDICAP_FLG", "Handicapped", "xs"),
                ("MARITAL_STATUS", "Marital Status", "sm"),
            ],
            [
                ("F_H_FLG", "Father / Husband", "sm"),
                ("F_H_NAME", "Father/Husband's Name", "grow"),
            ],
            [("F_H_ADDR", "Father/Husband's Address", "full")],
            [
                ("STATUS", "Status", "md"),
                ("DOCTOR_FLG", "Doctor", "xs"),
            ],
            [("REMARKS", "Remarks", "full")],
        ],
    },
    {
        "id": "permanent",
        "legend": "Permanent Address",
        "rows": [
            [
                ("PERM_ADDR1", "Address Line 1", "half"),
                ("PERM_ADDR2", "Address Line 2", "half"),
            ],
            [
                ("PERM_PS", "Police Station", "md"),
                ("PERM_CITY", "City", "md"),
            ],
            [
                ("PERM_DIST", "District", "md"),
                ("PERM_STATE", "State", "sm"),
            ],
            [
                ("PERM_PIN", "Pin", "xs"),
                ("PERM_COUNTRY", "Country", "md"),
            ],
            [
                ("PERM_CONTACT1", "Tel #", "sm"),
                ("PERM_CONTACT2", "Tel # 2", "sm"),
                ("PERM_FAX_NO", "Fax", "sm"),
                ("PERM_EMAIL_ID", "Email id", "grow"),
            ],
        ],
    },
    {
        "id": "present",
        "legend": "Present Address",
        "rows": [
            [
                ("PRES_ADDR1", "Address Line 1", "half"),
                ("PRES_ADDR2", "Address Line 2", "half"),
            ],
            [
                ("PRES_PS", "Police Station", "md"),
                ("PRES_CITY", "City", "md"),
            ],
            [
                ("PRES_DIST", "District", "md"),
                ("PRES_STATE", "State", "sm"),
            ],
            [
                ("PRES_PIN", "Pin", "xs"),
                ("PRES_COUNTRY", "Country", "md"),
            ],
            [
                ("PRES_CONTACT1", "Tel #", "sm"),
                ("PRES_CONTACT2", "Tel # 2", "sm"),
                ("PRES_FAX_NO", "Fax", "sm"),
                ("PRES_EMAIL_ID", "Email id", "grow"),
            ],
        ],
    },
    {
        "id": "audit",
        "legend": "Record Info",
        "rows": [
            [
                ("DATE_CREATED", "Date Created", "sm"),
                ("CREATED_BY", "Created By", "md"),
            ],
            [
                ("DATE_MODIFIED", "Date Modified", "sm"),
                ("MODIFIED_BY", "Modified By", "md"),
            ],
        ],
    },
]


def _build_emp_per_form(raw: dict) -> list:
    """Oracle EMP_PER_E layout with prefilled display values."""
    groups = []
    for group in _EMP_PER_FORM_GROUPS:
        rows_out = []
        for row in group["rows"]:
            fields = []
            for key, label, width in row:
                display = raw.get(key, "")
                fields.append(
                    {
                        "key": key,
                        "label": label,
                        "width": width,
                        "value": display if display not in ("", "—") else "",
                    }
                )
            rows_out.append(fields)
        groups.append(
            {
                "id": group["id"],
                "legend": group["legend"],
                "rows": rows_out,
            }
        )
    return groups


def get_emp_personal(emp_cd: str) -> dict:
    """Load fi_xx_mh_emp_per by EMP_CD (SELECT *)."""
    code = _str(emp_cd)[:5]
    if not code:
        return {"error": "Employee Code is required"}

    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT *
            FROM fi_xx_mh_emp_per
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [code],
        )
        row = cur.fetchone()
        if not row:
            return {
                "found": False,
                "emp_cd": code,
                "error": f"No personal record found for employee {code}",
            }

        cols = [d[0] for d in cur.description]
        # provisional name from row
        tmp = {
            str(c).upper(): _fmt_value(str(c).upper(), v)
            for c, v in zip(cols, row)
        }
        full_name = " ".join(
            p
            for p in (
                tmp.get("TITLE") or "",
                tmp.get("FIRST_NAME") or "",
                tmp.get("MIDDLE_NAME") or "",
                tmp.get("LAST_NAME") or "",
            )
            if p
        ).strip()

        payload = _build_from_row(
            cur=cur,
            cols=cols,
            row=row,
            section_order=_PER_SECTION_ORDER,
            section_fn=_section_for_per,
            identity_order=_PER_ID_ORDER,
            code=code,
            display_name=full_name,
        )
        fields = dict(payload.get("fields") or {})
        fields["EMP_CD"] = code
        payload["fields"] = fields
        payload["form"] = {
            "title": "Personal Information",
            "source": "FI_XX_MH_EMP_PER_E",
            "emp_cd": code,
            "groups": _build_emp_per_form(fields),
        }
        return payload


def get_emp_personal_status(emp_cd: str) -> dict:
    """Personal Information Status for claim gate (fi_xx_mh_emp_per.STATUS)."""
    code = _str(emp_cd)[:5]
    if not code:
        return {"error": "Employee Code is required"}

    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT
                STATUS,
                {_PER_NAME_SQL} AS full_name
            FROM fi_xx_mh_emp_per
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [code],
        )
        row = cur.fetchone()
        if not row:
            return {
                "found": False,
                "emp_cd": code,
                "error": f"No personal record found for employee {code}",
            }

    status_cd = _str(row[0]).upper()[:2]
    return {
        "found": True,
        "emp_cd": code,
        "display_name": _str(row[1]),
        "status": status_cd,
        "status_label": _fmt_value("STATUS", status_cd) if status_cd else "",
        "status_options": EMP_PERSONAL_STATUS_OPTIONS,
        "suggest_pensioner": status_cd == "RE",
    }


def update_emp_personal_status(
    emp_cd: str, status_cd: str, *, user_id: str | None = None
) -> dict:
    """Update fi_xx_mh_emp_per.STATUS (Personal Information Status)."""
    code = _str(emp_cd)[:5]
    new_status = _str(status_cd).upper()[:2]
    if not code:
        return {"error": "Employee Code is required"}
    if not new_status:
        return {"error": "Status is required"}
    if new_status not in EMP_PERSONAL_STATUS_LABELS:
        return {
            "error": (
                f"Invalid status '{new_status}'. "
                f"Allowed: {', '.join(EMP_PERSONAL_STATUS_LABELS)}"
            )
        }

    user = (_str(user_id) or "SMPK")[:5]
    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT STATUS
            FROM fi_xx_mh_emp_per
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [code],
        )
        row = cur.fetchone()
        if not row:
            return {
                "found": False,
                "emp_cd": code,
                "error": f"No personal record found for employee {code}",
            }
        old_status = _str(row[0]).upper()[:2]

        cur.execute(
            """
            UPDATE fi_xx_mh_emp_per
            SET STATUS = %s,
                DATE_MODIFIED = NOW(),
                MODIFIED_BY = %s
            WHERE EMP_CD = %s
            """,
            [new_status, user, code],
        )
    conn.commit()

    result = get_emp_personal_status(code)
    result["old_status"] = old_status
    result["updated"] = old_status != new_status
    result["message"] = (
        f"Status updated {old_status or '—'} → {new_status}"
        if old_status != new_status
        else f"Status already {new_status}"
    )
    return result


def _enrich_admin(cur, buckets, raw):
    """Attach designation description onto DESIG_CD display."""
    desig_raw = raw.get("DESIG_CD")
    if not desig_raw or desig_raw == "—":
        return
    # raw may already be formatted number; use original code for lookup
    desc = _lookup_desig_desc(cur, desig_raw)
    if not desc:
        return
    display = f"{desig_raw} — {desc}"
    raw["DESIG_CD"] = display
    for field in buckets.get("identity") or []:
        if field["key"] == "DESIG_CD":
            field["value"] = display
            break


def _lookup_bank_label(cur, bank_cd: str) -> str:
    code = _str(bank_cd)
    if not code:
        return ""
    try:
        cur.execute(
            """
            SELECT
                COALESCE(NULLIF(TRIM(b.BANK_NAME), ''), '') AS bank_name,
                COALESCE(NULLIF(TRIM(a.BANK_DESC), ''), '') AS branch_desc
            FROM fi_pm_mh_bank a
            LEFT JOIN fi_pm_mh_bankabbr b
              ON b.BANK_TYPE = LEFT(%s, 2)
            WHERE a.BANK_CD = %s
            LIMIT 1
            """,
            [code, code],
        )
        row = cur.fetchone()
        if not row:
            return ""
        bank_name = _str(row[0])
        branch = _str(row[1])
        if bank_name and branch:
            return f"{bank_name} / {branch}"
        return bank_name or branch
    except Exception:
        return ""


def _enrich_finance(cur, buckets, raw):
    bank_cd = raw.get("BANK_CD")
    if not bank_cd or bank_cd == "—":
        return
    label = _lookup_bank_label(cur, bank_cd)
    if not label:
        return
    display = f"{bank_cd} — {label}"
    raw["BANK_CD"] = display
    for field in buckets.get("identity") or []:
        if field["key"] == "BANK_CD":
            field["value"] = display
            break


def get_emp_admin(emp_cd: str) -> dict:
    """Load fi_xx_mh_emp_adm by EMP_CD (SELECT *)."""
    code = _str(emp_cd)[:5]
    if not code:
        return {"error": "Employee Code is required"}

    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT *
            FROM fi_xx_mh_emp_adm
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [code],
        )
        row = cur.fetchone()
        if not row:
            return {
                "found": False,
                "emp_cd": code,
                "error": f"No admin record found for employee {code}",
            }

        cols = [d[0] for d in cur.description]
        name = _lookup_emp_name(cur, code)

        return _build_from_row(
            cur=cur,
            cols=cols,
            row=row,
            section_order=_ADM_SECTION_ORDER,
            section_fn=_section_for_adm,
            identity_order=_ADM_ID_ORDER,
            code=code,
            enrich_fn=_enrich_admin,
            display_name=name,
        )


def get_emp_finance(emp_cd: str) -> dict:
    """Load fi_xx_mh_emp_fin by EMP_CD (SELECT *)."""
    code = _str(emp_cd)[:5]
    if not code:
        return {"error": "Employee Code is required"}

    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT *
            FROM fi_xx_mh_emp_fin
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [code],
        )
        row = cur.fetchone()
        if not row:
            return {
                "found": False,
                "emp_cd": code,
                "error": f"No finance record found for employee {code}",
            }

        cols = [d[0] for d in cur.description]
        name = _lookup_emp_name(cur, code)

        return _build_from_row(
            cur=cur,
            cols=cols,
            row=row,
            section_order=_FIN_SECTION_ORDER,
            section_fn=_section_for_fin,
            identity_order=_FIN_ID_ORDER,
            code=code,
            enrich_fn=_enrich_finance,
            display_name=name,
        )


# ---------------------------------------------------------------------------
# ESR Personal — DataTables server-side list (fi_xx_mh_emp_per)
# ---------------------------------------------------------------------------

_PER_LIST_ORDER = [
    "EMP_CD",
    "NAME_EXPR",
    "SEX",
    "BIRTH_DT",
    "CATEGORY",
    "MARITAL_STATUS",
    "PERM_CITY",
    "PERM_CONTACT1",
    "STATUS",
]

# Display name expression (MySQL)
_PER_NAME_SQL = """
TRIM(CONCAT_WS(
    ' ',
    NULLIF(TRIM(TITLE), ''),
    NULLIF(TRIM(FIRST_NAME), ''),
    NULLIF(TRIM(MIDDLE_NAME), ''),
    NULLIF(TRIM(LAST_NAME), '')
))
""".strip()


def _parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def summary_emp_personal() -> dict:
    """Analytics for ESR Personal dashboard cards (fi_xx_mh_emp_per).

    STATUS codes:
      RE → Regular Emp
      PE → Probationary Emp
      TE → Trainee Emp
      DW → Deputationist WB
      DC → Deputationist Central
      PN → Pensioner
      FP → Family Pensioner
      EG → Exgratia holder
    """
    sql = """
        SELECT
            COUNT(*) AS total_rows,
            SUM(CASE WHEN UPPER(TRIM(COALESCE(SEX, ''))) = 'M' THEN 1 ELSE 0 END) AS male,
            SUM(CASE WHEN UPPER(TRIM(COALESCE(SEX, ''))) = 'F' THEN 1 ELSE 0 END) AS female,
            SUM(CASE WHEN UPPER(TRIM(COALESCE(STATUS, ''))) = 'RE' THEN 1 ELSE 0 END) AS regular_emp,
            SUM(CASE WHEN UPPER(TRIM(COALESCE(STATUS, ''))) = 'PE' THEN 1 ELSE 0 END) AS probationary,
            SUM(CASE WHEN UPPER(TRIM(COALESCE(STATUS, ''))) = 'TE' THEN 1 ELSE 0 END) AS trainee,
            SUM(CASE WHEN UPPER(TRIM(COALESCE(STATUS, ''))) = 'DW' THEN 1 ELSE 0 END) AS deputation_wb,
            SUM(CASE WHEN UPPER(TRIM(COALESCE(STATUS, ''))) = 'DC' THEN 1 ELSE 0 END) AS deputation_central,
            SUM(CASE WHEN UPPER(TRIM(COALESCE(STATUS, ''))) = 'PN' THEN 1 ELSE 0 END) AS pensioner,
            SUM(CASE WHEN UPPER(TRIM(COALESCE(STATUS, ''))) = 'FP' THEN 1 ELSE 0 END) AS family_pensioner,
            SUM(CASE WHEN UPPER(TRIM(COALESCE(STATUS, ''))) = 'EG' THEN 1 ELSE 0 END) AS exgratia,
            SUM(
                CASE
                    WHEN UPPER(TRIM(COALESCE(DOCTOR_FLG, ''))) IN (
                        '1', 'Y', 'YES'
                    )
                    THEN 1 ELSE 0
                END
            ) AS doctor
        FROM fi_xx_mh_emp_per
    """
    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone() or ()

    def _i(idx, default=0):
        try:
            v = row[idx]
            if v is None:
                return default
            return int(v)
        except (IndexError, TypeError, ValueError):
            return default

    return {
        "total_rows": _i(0),
        "male": _i(1),
        "female": _i(2),
        "regular_emp": _i(3),
        "probationary": _i(4),
        "trainee": _i(5),
        "deputation_wb": _i(6),
        "deputation_central": _i(7),
        "pensioner": _i(8),
        "family_pensioner": _i(9),
        "exgratia": _i(10),
        "doctor": _i(11),
    }


def datatable_emp_personal(params) -> dict:
    """
    DataTables server-side list of employees from fi_xx_mh_emp_per.

    Params: draw, start, length, search[value], order[0][column], order[0][dir]
    """
    draw = _parse_int(params.get("draw"), 1)
    start = max(0, _parse_int(params.get("start"), 0))
    length = _parse_int(params.get("length"), 25)
    if length < 0 or length > 500:
        length = 25

    search = (
        params.get("search[value]")
        or params.get("search.value")
        or ""
    )
    search = str(search).strip()

    order_col = _parse_int(
        params.get("order[0][column]") or params.get("order.0.column"),
        0,
    )
    order_dir = str(
        params.get("order[0][dir]") or params.get("order.0.dir") or "asc"
    ).lower()
    if order_dir not in ("asc", "desc"):
        order_dir = "asc"
    if order_col < 0 or order_col >= len(_PER_LIST_ORDER):
        order_col = 0
    order_key = _PER_LIST_ORDER[order_col]
    if order_key == "NAME_EXPR":
        order_sql = f"({_PER_NAME_SQL}) {order_dir.upper()}, EMP_CD ASC"
    else:
        order_sql = f"{order_key} {order_dir.upper()}, EMP_CD ASC"

    where_sql = ""
    where_params: list = []
    if search:
        like = f"%{search}%"
        where_sql = f"""
            WHERE EMP_CD LIKE %s
               OR FIRST_NAME LIKE %s
               OR MIDDLE_NAME LIKE %s
               OR LAST_NAME LIKE %s
               OR TITLE LIKE %s
               OR PERM_CITY LIKE %s
               OR PERM_CONTACT1 LIKE %s
               OR CATEGORY LIKE %s
               OR STATUS LIKE %s
               OR ({_PER_NAME_SQL}) LIKE %s
        """
        where_params = [like] * 10

    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM fi_xx_mh_emp_per")
        records_total = int(cur.fetchone()[0] or 0)

        if where_sql:
            cur.execute(
                f"SELECT COUNT(*) FROM fi_xx_mh_emp_per {where_sql}",
                where_params,
            )
            records_filtered = int(cur.fetchone()[0] or 0)
        else:
            records_filtered = records_total

        cur.execute(
            f"""
            SELECT
                EMP_CD,
                {_PER_NAME_SQL} AS full_name,
                SEX,
                BIRTH_DT,
                CATEGORY,
                MARITAL_STATUS,
                PERM_CITY,
                PERM_CONTACT1,
                STATUS
            FROM fi_xx_mh_emp_per
            {where_sql}
            ORDER BY {order_sql}
            LIMIT %s OFFSET %s
            """,
            [*where_params, length, start],
        )
        data = []
        for row in cur.fetchall():
            (
                emp,
                full_name,
                sex,
                birth_dt,
                category,
                marital,
                city,
                contact,
                status,
            ) = row
            data.append(
                {
                    "emp_cd": _str(emp),
                    "full_name": _str(full_name) or "—",
                    "sex": _fmt_value("SEX", sex) or "—",
                    "birth_dt": _fmt_value("BIRTH_DT", birth_dt) or "—",
                    "category": _str(category) or "—",
                    "marital_status": _fmt_value("MARITAL_STATUS", marital) or "—",
                    "city": _str(city) or "—",
                    "contact": _str(contact) or "—",
                    "status": _fmt_value("STATUS", status) or "—",
                }
            )

    return {
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data,
    }


# ---------------------------------------------------------------------------
# ESR Admin — DataTables server-side list (fi_xx_mh_emp_adm)
# ---------------------------------------------------------------------------

_ADM_LIST_ORDER = [
    "EMP_CD",
    "NAME_EXPR",
    "DESIG_CD",
    "JOIN_DT",
    "CONFIRM_DT",
    "SEPARATION_TYPE",
    "SEPARATION_DT",
    "EXP_RET_DT",
    "PF_TYPE",
    "PAN_NO",
]

_ADM_NAME_SQL = """
TRIM(CONCAT_WS(
    ' ',
    NULLIF(TRIM(p.TITLE), ''),
    NULLIF(TRIM(p.FIRST_NAME), ''),
    NULLIF(TRIM(p.MIDDLE_NAME), ''),
    NULLIF(TRIM(p.LAST_NAME), '')
))
""".strip()


def _fmt_sep_type(value) -> str:
    code = _str(value).upper()
    if not code:
        return ""
    labels = {
        "RT": "RT — Retirement",
        "DT": "DT — Death",
        "VR": "VR — Voluntary retirement",
        "TN": "TN — Termination",
        "TF": "TF — Transfer",
        "RG": "RG — Resignation",
        "CR": "CR — Compulsory retirement",
        "RI": "RI — Invalidation",
        "CO": "CO — Contract end",
        "RD": "RD — Redundancy",
        "WH": "WH — Without notice",
        "RR": "RR — Reversion",
        "SU": "SU — Superannuation",
        "SD": "SD — Superannuation",
    }
    return labels.get(code, code)


def summary_emp_admin() -> dict:
    """Analytics for ESR Admin dashboard cards (fi_xx_mh_emp_adm)."""
    sql = """
        SELECT
            COUNT(*) AS total_rows,
            SUM(CASE WHEN SEPARATION_DT IS NULL THEN 1 ELSE 0 END) AS in_service,
            SUM(CASE WHEN SEPARATION_DT IS NOT NULL THEN 1 ELSE 0 END) AS separated,
            SUM(
                CASE
                    WHEN UPPER(TRIM(COALESCE(SEPARATION_TYPE, ''))) = 'RT'
                    THEN 1 ELSE 0
                END
            ) AS retired,
            SUM(
                CASE
                    WHEN UPPER(TRIM(COALESCE(SEPARATION_TYPE, ''))) = 'DT'
                    THEN 1 ELSE 0
                END
            ) AS death,
            SUM(
                CASE
                    WHEN UPPER(TRIM(COALESCE(SEPARATION_TYPE, ''))) = 'VR'
                    THEN 1 ELSE 0
                END
            ) AS voluntary_ret,
            SUM(
                CASE
                    WHEN UPPER(TRIM(COALESCE(SEPARATION_TYPE, ''))) = 'TN'
                    THEN 1 ELSE 0
                END
            ) AS sep_terminated,
            SUM(
                CASE
                    WHEN HINDI_FLG IN (1)
                      OR UPPER(TRIM(CAST(COALESCE(HINDI_FLG, '') AS CHAR))) IN (
                          '1', 'Y', 'YES'
                      )
                    THEN 1 ELSE 0
                END
            ) AS hindi_known
        FROM fi_xx_mh_emp_adm
    """
    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone() or ()

    def _i(idx, default=0):
        try:
            v = row[idx]
            if v is None:
                return default
            return int(v)
        except (IndexError, TypeError, ValueError):
            return default

    return {
        "total_rows": _i(0),
        "in_service": _i(1),
        "separated": _i(2),
        "retired": _i(3),
        "death": _i(4),
        "voluntary_ret": _i(5),
        "terminated": _i(6),
        "hindi_known": _i(7),
    }


def datatable_emp_admin(params) -> dict:
    """
    DataTables server-side list of employees from fi_xx_mh_emp_adm
    (name joined from fi_xx_mh_emp_per).
    """
    draw = _parse_int(params.get("draw"), 1)
    start = max(0, _parse_int(params.get("start"), 0))
    length = _parse_int(params.get("length"), 25)
    if length < 0 or length > 500:
        length = 25

    search = (
        params.get("search[value]")
        or params.get("search.value")
        or ""
    )
    search = str(search).strip()

    order_col = _parse_int(
        params.get("order[0][column]") or params.get("order.0.column"),
        0,
    )
    order_dir = str(
        params.get("order[0][dir]") or params.get("order.0.dir") or "asc"
    ).lower()
    if order_dir not in ("asc", "desc"):
        order_dir = "asc"
    if order_col < 0 or order_col >= len(_ADM_LIST_ORDER):
        order_col = 0
    order_key = _ADM_LIST_ORDER[order_col]
    if order_key == "NAME_EXPR":
        order_sql = f"({_ADM_NAME_SQL}) {order_dir.upper()}, a.EMP_CD ASC"
    elif order_key == "EMP_CD":
        order_sql = f"a.EMP_CD {order_dir.upper()}"
    else:
        order_sql = f"a.{order_key} {order_dir.upper()}, a.EMP_CD ASC"

    from_join = """
        FROM fi_xx_mh_emp_adm a
        LEFT JOIN fi_xx_mh_emp_per p ON p.EMP_CD = a.EMP_CD
    """
    where_sql = ""
    where_params: list = []
    if search:
        like = f"%{search}%"
        where_sql = f"""
            WHERE a.EMP_CD LIKE %s
               OR CAST(a.DESIG_CD AS CHAR) LIKE %s
               OR a.SEPARATION_TYPE LIKE %s
               OR a.PAN_NO LIKE %s
               OR a.PF_TYPE LIKE %s
               OR p.FIRST_NAME LIKE %s
               OR p.LAST_NAME LIKE %s
               OR ({_ADM_NAME_SQL}) LIKE %s
        """
        where_params = [like] * 8

    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM fi_xx_mh_emp_adm")
        records_total = int(cur.fetchone()[0] or 0)

        if where_sql:
            cur.execute(
                f"SELECT COUNT(*) {from_join} {where_sql}",
                where_params,
            )
            records_filtered = int(cur.fetchone()[0] or 0)
        else:
            records_filtered = records_total

        cur.execute(
            f"""
            SELECT
                a.EMP_CD,
                {_ADM_NAME_SQL} AS full_name,
                a.DESIG_CD,
                a.JOIN_DT,
                a.CONFIRM_DT,
                a.SEPARATION_TYPE,
                a.SEPARATION_DT,
                a.EXP_RET_DT,
                a.PF_TYPE,
                a.PAN_NO
            {from_join}
            {where_sql}
            ORDER BY {order_sql}
            LIMIT %s OFFSET %s
            """,
            [*where_params, length, start],
        )
        data = []
        for row in cur.fetchall():
            (
                emp,
                full_name,
                desig,
                join_dt,
                confirm_dt,
                sep_type,
                sep_dt,
                exp_ret,
                pf_type,
                pan_no,
            ) = row
            data.append(
                {
                    "emp_cd": _str(emp),
                    "full_name": _str(full_name) or "—",
                    "desig_cd": _str(desig) or "—",
                    "join_dt": _fmt_value("JOIN_DT", join_dt) or "—",
                    "confirm_dt": _fmt_value("CONFIRM_DT", confirm_dt) or "—",
                    "separation_type": _fmt_sep_type(sep_type) or "—",
                    "separation_dt": _fmt_value("SEPARATION_DT", sep_dt) or "—",
                    "exp_ret_dt": _fmt_value("EXP_RET_DT", exp_ret) or "—",
                    "pf_type": _str(pf_type) or "—",
                    "pan_no": _str(pan_no) or "—",
                }
            )

    return {
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data,
    }


# ---------------------------------------------------------------------------
# ESR Finance — DataTables server-side list (fi_xx_mh_emp_fin)
# ---------------------------------------------------------------------------

_FIN_LIST_ORDER = [
    "EMP_CD",
    "NAME_EXPR",
    "EMP_CLASS",
    "BANK_CD",
    "PAYMODE_CD",
    "BANK_AC_NO",
    "SCALE_SL",
    "SCALE_WEF_DT",
    "SUSPEND_FLG",
    "FINAL_STLMT_STATUS",
]

_FIN_NAME_SQL = """
TRIM(CONCAT_WS(
    ' ',
    NULLIF(TRIM(p.TITLE), ''),
    NULLIF(TRIM(p.FIRST_NAME), ''),
    NULLIF(TRIM(p.MIDDLE_NAME), ''),
    NULLIF(TRIM(p.LAST_NAME), '')
))
""".strip()


def summary_emp_finance() -> dict:
    """Analytics for ESR Finance dashboard cards (fi_xx_mh_emp_fin)."""
    sql = """
        SELECT
            COUNT(*) AS total_rows,
            SUM(CASE WHEN EMP_CLASS = 1 THEN 1 ELSE 0 END) AS class_1,
            SUM(CASE WHEN EMP_CLASS = 2 THEN 1 ELSE 0 END) AS class_2,
            SUM(CASE WHEN EMP_CLASS = 3 THEN 1 ELSE 0 END) AS class_3,
            SUM(CASE WHEN EMP_CLASS = 4 THEN 1 ELSE 0 END) AS class_4,
            SUM(
                CASE
                    WHEN EMP_CLASS IS NULL OR EMP_CLASS NOT IN (1, 2, 3, 4)
                    THEN 1 ELSE 0
                END
            ) AS class_other,
            SUM(
                CASE
                    WHEN NULLIF(TRIM(COALESCE(BANK_CD, '')), '') IS NOT NULL
                    THEN 1 ELSE 0
                END
            ) AS with_bank,
            SUM(
                CASE
                    WHEN UPPER(TRIM(COALESCE(SUSPEND_FLG, ''))) IN (
                        'S', 'T', 'W', 'Y', '1'
                    )
                    THEN 1 ELSE 0
                END
            ) AS suspended,
            SUM(
                CASE
                    WHEN QTR_FLG IN (1)
                      OR UPPER(TRIM(CAST(COALESCE(QTR_FLG, '') AS CHAR))) IN (
                          '1', 'Y', 'YES'
                      )
                    THEN 1 ELSE 0
                END
            ) AS quarter_flag
        FROM fi_xx_mh_emp_fin
    """
    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone() or ()

    def _i(idx, default=0):
        try:
            v = row[idx]
            if v is None:
                return default
            return int(v)
        except (IndexError, TypeError, ValueError):
            return default

    return {
        "total_rows": _i(0),
        "class_1": _i(1),
        "class_2": _i(2),
        "class_3": _i(3),
        "class_4": _i(4),
        "class_other": _i(5),
        "with_bank": _i(6),
        "suspended": _i(7),
        "quarter_flag": _i(8),
    }


def datatable_emp_finance(params) -> dict:
    """
    DataTables server-side list of employees from fi_xx_mh_emp_fin
    (name joined from fi_xx_mh_emp_per).
    """
    draw = _parse_int(params.get("draw"), 1)
    start = max(0, _parse_int(params.get("start"), 0))
    length = _parse_int(params.get("length"), 25)
    if length < 0 or length > 500:
        length = 25

    search = (
        params.get("search[value]")
        or params.get("search.value")
        or ""
    )
    search = str(search).strip()

    order_col = _parse_int(
        params.get("order[0][column]") or params.get("order.0.column"),
        0,
    )
    order_dir = str(
        params.get("order[0][dir]") or params.get("order.0.dir") or "asc"
    ).lower()
    if order_dir not in ("asc", "desc"):
        order_dir = "asc"
    if order_col < 0 or order_col >= len(_FIN_LIST_ORDER):
        order_col = 0
    order_key = _FIN_LIST_ORDER[order_col]
    if order_key == "NAME_EXPR":
        order_sql = f"({_FIN_NAME_SQL}) {order_dir.upper()}, f.EMP_CD ASC"
    elif order_key == "EMP_CD":
        order_sql = f"f.EMP_CD {order_dir.upper()}"
    else:
        order_sql = f"f.{order_key} {order_dir.upper()}, f.EMP_CD ASC"

    from_join = """
        FROM fi_xx_mh_emp_fin f
        LEFT JOIN fi_xx_mh_emp_per p ON p.EMP_CD = f.EMP_CD
    """
    where_sql = ""
    where_params: list = []
    if search:
        like = f"%{search}%"
        where_sql = f"""
            WHERE f.EMP_CD LIKE %s
               OR f.BANK_CD LIKE %s
               OR f.BANK_AC_NO LIKE %s
               OR f.PAYMODE_CD LIKE %s
               OR f.SCALE_SL LIKE %s
               OR CAST(f.EMP_CLASS AS CHAR) LIKE %s
               OR p.FIRST_NAME LIKE %s
               OR p.LAST_NAME LIKE %s
               OR ({_FIN_NAME_SQL}) LIKE %s
        """
        where_params = [like] * 9

    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM fi_xx_mh_emp_fin")
        records_total = int(cur.fetchone()[0] or 0)

        if where_sql:
            cur.execute(
                f"SELECT COUNT(*) {from_join} {where_sql}",
                where_params,
            )
            records_filtered = int(cur.fetchone()[0] or 0)
        else:
            records_filtered = records_total

        cur.execute(
            f"""
            SELECT
                f.EMP_CD,
                {_FIN_NAME_SQL} AS full_name,
                f.EMP_CLASS,
                f.BANK_CD,
                f.PAYMODE_CD,
                f.BANK_AC_NO,
                f.SCALE_SL,
                f.SCALE_WEF_DT,
                f.SUSPEND_FLG,
                f.FINAL_STLMT_STATUS
            {from_join}
            {where_sql}
            ORDER BY {order_sql}
            LIMIT %s OFFSET %s
            """,
            [*where_params, length, start],
        )
        data = []
        for row in cur.fetchall():
            (
                emp,
                full_name,
                emp_class,
                bank_cd,
                paymode,
                bank_ac,
                scale_sl,
                scale_wef,
                suspend_flg,
                final_stl,
            ) = row
            data.append(
                {
                    "emp_cd": _str(emp),
                    "full_name": _str(full_name) or "—",
                    "emp_class": _str(emp_class) or "—",
                    "bank_cd": _str(bank_cd) or "—",
                    "paymode_cd": _str(paymode) or "—",
                    "bank_ac_no": _str(bank_ac) or "—",
                    "scale_sl": _str(scale_sl) or "—",
                    "scale_wef_dt": _fmt_value("SCALE_WEF_DT", scale_wef) or "—",
                    "suspend_flg": _fmt_value("SUSPEND_FLG", suspend_flg) or "—",
                    "final_stlmt_status": _str(final_stl) or "—",
                }
            )

    return {
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data,
    }
