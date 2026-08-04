"""Audit Django models vs MySQL mirror tables for missing id column."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.apps import apps
from django.db import connection


def mysql_columns(table):
    with connection.cursor() as c:
        c.execute("SHOW TABLES LIKE %s", [table])
        if not c.fetchone():
            return None
        c.execute(f"SHOW COLUMNS FROM `{table}`")
        return [row[0].lower() for row in c.fetchall()]


def django_pk_fields(model):
    for field in model._meta.local_fields:
        if field.name == "pk" and getattr(field, "composite", False):
            return list(field.fields)
    pks = [f.name for f in model._meta.local_fields if f.primary_key]
    return pks


def expects_surrogate_id(model):
    for field in model._meta.local_fields:
        if field.name == "pk" and getattr(field, "composite", False):
            return False
    pks = [f.name for f in model._meta.local_fields if f.primary_key]
    if pks == ["id"]:
        return True
    if not pks:
        return True
    return False


def suggest_pk(cols, model):
    for constraint in model._meta.constraints:
        fields = [f.lower() for f in getattr(constraint, "fields", [])]
        if fields and all(name in cols for name in fields):
            return list(constraint.fields)
    for names in [
        ["emp_cd", "sal_mth", "sal_yr", "earndedn_cd"],
        ["emp_cd", "sal_mth", "sal_yr"],
        ["sepcom_id", "earn_dedn_cd", "earn_dedn_type"],
        ["wef_dt", "emp_type", "emp_class_grp"],
        ["wef_dt", "emp_type", "base_cpi_no"],
        ["wef_dt", "gratuity_type", "ret_dt_from"],
        ["wef_dt", "gratuity_type"],
        ["wef_dt", "gratuity_type", "tqs_start_yrs"],
        ["interval_srl", "wef_dt"],
        ["jrnal_srl_no", "wef_dt"],
        ["earndedn_cd", "earndedn_type"],
        ["fin_yr", "doc_abv"],
        ["bill_type", "bill_mth", "bill_yr"],
        ["voucher_no", "sl_no"],
        ["fmpen_id", "earn_dedn_cd", "earn_dedn_type"],
        ["age_yrs", "wef_dt"],
    ]:
        if all(name in cols for name in names):
            return names
    return cols[:4]


apps_to_scan = ["first_pension", "master_data", "employee"]
issues = []
missing_table = []
duplicate_models = {}

for app_label in apps_to_scan:
    try:
        app_config = apps.get_app_config(app_label)
    except LookupError:
        continue
    for model in app_config.get_models():
        table = model._meta.db_table
        if not table or not table.lower().startswith("fi_"):
            continue
        key = table.lower()
        duplicate_models.setdefault(key, []).append(
            f"{app_label}.{model.__name__}"
        )
        cols = mysql_columns(table)
        if cols is None:
            missing_table.append((f"{app_label}.{model.__name__}", table))
            continue
        has_id = "id" in cols
        wants_id = expects_surrogate_id(model)
        pk_fields = django_pk_fields(model)
        if wants_id and not has_id:
            issues.append(
                {
                    "model": f"{app_label}.{model.__name__}",
                    "table": table,
                    "django_pk": pk_fields,
                    "suggested_pk": suggest_pk(cols, model),
                }
            )

print("=== MODELS EXPECTING id BUT MYSQL HAS NO id ===")
for row in sorted(issues, key=lambda x: x["table"]):
    print(f"{row['model']:50} {row['table']}")
    print(f"  django_pk={row['django_pk']}")
    print(f"  suggested_pk={row['suggested_pk']}")

print(f"\nTotal issues: {len(issues)}")

print("\n=== DUPLICATE MODELS ON SAME TABLE ===")
for table, models in sorted(duplicate_models.items()):
    if len(models) > 1:
        print(f"{table}: {', '.join(models)}")

print("\n=== MYSQL TABLE MISSING ===")
for m, t in missing_table:
    print(f"{m} -> {t}")
