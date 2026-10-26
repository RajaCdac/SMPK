"""Admin report: consolidations by the user who saved them, by date."""

from datetime import datetime, time

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from M2_oldage_arrear.models import M2OldageArrearConsolidation
from methodology2.models import Methodology2Consolidation

_SOURCES = (
    (Methodology2Consolidation, "Methodology-2"),
    (M2OldageArrearConsolidation, "Old age"),
)

_ROW_FIELDS = (
    "emp_cd",
    "name",
    "pensioner_name",
    "case_no",
    "roll_no",
    "category",
    "consolidated_by",
    "updated_at",
)


def _parse_date(value, field):
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD") from exc


def _fmt_date(value):
    if value is None:
        return ""
    return value.strftime("%d-%m-%Y")


def _fmt_dt(value):
    if value is None:
        return ""
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime("%d-%m-%Y %H:%M:%S")


def _local_date(value):
    if value is None:
        return None
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.date()


def _apply_filters(qs, *, username, q, from_date, to_date):
    if from_date is not None:
        start = timezone.make_aware(datetime.combine(from_date, time.min))
        qs = qs.filter(updated_at__gte=start)
    if to_date is not None:
        end = timezone.make_aware(datetime.combine(to_date, time.max))
        qs = qs.filter(updated_at__lte=end)
    if username == "__none__":
        qs = qs.filter(Q(consolidated_by__isnull=True) | Q(consolidated_by=""))
    elif username:
        qs = qs.filter(consolidated_by__iexact=username)
    if q:
        qs = qs.filter(
            Q(emp_cd__icontains=q)
            | Q(case_no__icontains=q)
            | Q(name__icontains=q)
            | Q(pensioner_name__icontains=q)
        )
    return qs


def _account_usernames():
    User = get_user_model()
    return list(
        User.objects.order_by("username").values_list("username", flat=True)
    )


def build_admin_consolidation_report(
    *,
    username="",
    q="",
    from_date=None,
    to_date=None,
):
    """
    users: one row per login, with how many consolidations they saved.
    dates: day totals for the chosen user.
    rows: the consolidations (chosen user, or a search across every user).
    """
    username = str(username or "").strip()
    q = str(q or "").strip()

    user_bucket = {}

    def bucket_for(actor):
        key = actor.casefold()
        row = user_bucket.get(key)
        if row is None:
            row = {
                "username": actor or "Not recorded",
                "filter_key": actor or "__none__",
                "methodology2": 0,
                "old_age": 0,
                "total": 0,
                "last_date": "",
                "last_iso": "",
            }
            user_bucket[key] = row
        return row

    for model, source in _SOURCES:
        light = _apply_filters(
            model.objects.all(),
            username="",
            q="",
            from_date=from_date,
            to_date=to_date,
        ).values("consolidated_by", "updated_at")
        for item in light.iterator():
            actor = str(item["consolidated_by"] or "").strip()
            row = bucket_for(actor)
            if source == "Methodology-2":
                row["methodology2"] += 1
            else:
                row["old_age"] += 1
            row["total"] += 1
            day = _local_date(item["updated_at"])
            iso = day.isoformat() if day else ""
            if iso >= row["last_iso"]:
                row["last_iso"] = iso
                row["last_date"] = _fmt_date(day)

    known = {name.casefold(): name for name in _account_usernames()}
    for key, canon in known.items():
        if key not in user_bucket:
            user_bucket[key] = {
                "username": canon,
                "filter_key": canon,
                "methodology2": 0,
                "old_age": 0,
                "total": 0,
                "last_date": "",
                "last_iso": "",
            }
        else:
            user_bucket[key]["username"] = canon

    users = sorted(
        user_bucket.values(),
        key=lambda row: (-row["total"], row["username"].casefold()),
    )

    show_rows = bool(username or q)
    rows = []
    date_bucket = {}
    if show_rows:
        # A search is across every user, so the creator can be seen.
        row_user = "" if q else username
        for model, source in _SOURCES:
            found = _apply_filters(
                model.objects.all(),
                username=row_user,
                q=q,
                from_date=from_date,
                to_date=to_date,
            ).values(*_ROW_FIELDS)
            for item in found.iterator():
                day = _local_date(item["updated_at"])
                iso = day.isoformat() if day else ""
                actor = str(item["consolidated_by"] or "").strip()
                if not q:
                    slot = date_bucket.setdefault(
                        iso,
                        {
                            "date": _fmt_date(day),
                            "date_iso": iso,
                            "methodology2": 0,
                            "old_age": 0,
                            "total": 0,
                        },
                    )
                    if source == "Methodology-2":
                        slot["methodology2"] += 1
                    else:
                        slot["old_age"] += 1
                    slot["total"] += 1
                name = str(item["name"] or item["pensioner_name"] or "").strip()
                rows.append(
                    {
                        "date": _fmt_date(day),
                        "date_iso": iso,
                        "saved_at": _fmt_dt(item["updated_at"]),
                        "emp_cd": item["emp_cd"] or "",
                        "name": name,
                        "case_no": item["case_no"] or "",
                        "roll_no": item["roll_no"] or "",
                        "category": item["category"] or "",
                        "source": source,
                        "consolidated_by": actor or "Not recorded",
                    }
                )
        rows.sort(key=lambda row: (row["saved_at"], row["emp_cd"]), reverse=True)

    dates = sorted(date_bucket.values(), key=lambda row: row["date_iso"], reverse=True)
    return {
        "users": users,
        "dates": dates,
        "rows": rows,
        "username": username,
        "q": q,
    }
