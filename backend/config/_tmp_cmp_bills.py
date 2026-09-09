"""Compare First FP vs Monthly print lines for 47529 and 17663."""
import os
from datetime import date, datetime
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connections
from family_pension.services.first_fp_bill_service import load_first_fp_bill_print


def mq(sql, params=None):
    cur = connections["default"].cursor()
    cur.execute(sql, params or [])
    cols = [d[0].lower() for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def dump(title, rows):
    print(f"\n=== {title} ({len(rows)}) ===")
    for r in rows:
        out = {}
        for k, v in r.items():
            if isinstance(v, (datetime, date)):
                out[k] = v.isoformat()
            elif isinstance(v, Decimal):
                out[k] = float(v)
            else:
                out[k] = v
        print(out)


for emp in ("47529", "17663"):
    dump(
        f"{emp} TH",
        mq(
            """
            SELECT FAM_FMPEN_ID, CLMCA_ID, FPENSION_TYPE, FPENSION_MONTH, FPENSION_YEAR,
                   FPENSION_AMT, RELIEF, GRATUITY_AMT, BILL_NO
            FROM fi_pn_th_first_month_fpension
            WHERE EMP_CD=%s
            ORDER BY FPENSION_TYPE, FPENSION_YEAR, FPENSION_MONTH
            """,
            [emp],
        ),
    )
    th = mq(
        "SELECT FAM_FMPEN_ID FROM fi_pn_th_first_month_fpension WHERE EMP_CD=%s",
        [emp],
    )
    ids = [r["fam_fmpen_id"] for r in th]
    if ids:
        ph = ",".join(["%s"] * len(ids))
        dump(
            f"{emp} TD",
            mq(
                f"""
                SELECT FAM_FMPEN_ID, EARN_DEDN_TYPE, EARN_DEDN_CD,
                       AMOUNT, ORIGINAL_AMT, AREAR_AMT
                FROM fi_pn_td_first_month_fpension
                WHERE FAM_FMPEN_ID IN ({ph})
                ORDER BY FAM_FMPEN_ID, EARN_DEDN_CD
                """,
                ids,
            ),
        )

for emp, cid, bt, m, y in (
    ("47529", None, "M", 8, 2026),
    ("47529", None, "N", None, None),
    ("17663", "CM/18915", "M", 7, 2026),
    ("17663", "CM/18915", "N", 12, 2024),
):
    try:
        claim = cid or mq(
            "SELECT CLMCA_ID FROM fi_pn_mh_fpen_caclaim WHERE EMP_CD=%s LIMIT 1",
            [emp],
        )
        clm = cid or (claim[0]["clmca_id"] if claim else None)
        r = load_first_fp_bill_print(
            emp_cd=emp,
            clmca_id=clm,
            bill_type=bt,
            month=m,
            year=y,
        )
        p = r.get("print") or {}
        print(f"\n=== PRINT {emp} type={bt} {m}/{y} bill={r.get('bill_no')} ===")
        print("title", p.get("report_title"))
        print("type", r.get("bill_type"), p.get("fpension_type"))
        print("lines", p.get("detail_lines"))
        print(
            "gross/dedn/net",
            p.get("gross_earn"),
            p.get("gross_dedn"),
            p.get("net_earn"),
            p.get("hold_up_disp"),
        )
    except Exception as exc:
        print(f"\n=== PRINT {emp} {bt} FAIL {exc} ===")
