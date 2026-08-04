import re

# Role codes treated as application administrator (sidebar: users, audit, workflow).
ADMIN_ROLE_CODES = frozenset({"ADMIN", "PENSION_ADMIN", "ADMINISTRATOR"})


def role_name_to_code(name):
    normalized = re.sub(r"[^a-z0-9]+", " ", (name or "").strip().lower()).strip()
    if normalized in {"admin", "administrator", "pension admin"}:
        return "ADMIN"
    if normalized in {"family pension user", "family pension"}:
        return "FAMILY_PENSION_USER"
    if normalized in {"first pension user", "first pension"}:
        return "FIRST_PENSION_USER"
    if normalized in {"bill generation user", "bill generation"}:
        return "BILL_GENERATION_USER"
    if normalized in {"lic section user", "lic section"}:
        return "LIC_SECTION_USER"
    if normalized in {
        "pension user",
        "pension",
        "user",
        "clerk",
        "pension clerk",
        "pension officer",
    }:
        return "PENSION_USER"
    slug = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_").upper()
    if slug in ADMIN_ROLE_CODES:
        return "ADMIN"
    if slug:
        return slug
    return "PENSION_USER"


def normalize_role_code(code, role_name=None):
    raw = (code or "").strip().upper()
    if raw in ADMIN_ROLE_CODES:
        return "ADMIN"
    if raw:
        return raw
    return role_name_to_code(role_name)
