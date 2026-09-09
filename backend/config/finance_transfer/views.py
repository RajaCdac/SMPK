from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole

from .engine import (
    MYSQL_DEFAULTS,
    ORACLE_SCHEMA,
    list_oracle_finance_tables,
    mysql_table_status_map,
    public_mysql_config,
    resolve_mysql_config,
    test_mysql_connection,
)
from .job_runner import get_status, run_apply_pending_fks, start_transfer_job
from .smpk_sync_engine import (
    SALARY_TABLES,
    default_source_config,
    default_target_config,
    list_smpk_sync_tables,
    resolve_source_config,
    resolve_target_config,
)
from .smpk_sync_job_runner import get_status as get_smpk_sync_status
from .smpk_sync_job_runner import start_smpk_sync_job


def _extract_mysql_config(source) -> dict | None:
    """Pull mysql connection fields from query params or JSON body."""
    if source is None:
        return None
    if hasattr(source, "get"):
        # QueryDict or dict
        nested = source.get("mysql") if not hasattr(source, "getlist") else None
        if isinstance(nested, dict):
            source = nested
        keys = ("host", "port", "user", "password", "database")
        raw = {}
        for key in keys:
            # support mysql_host style and host
            val = source.get(key)
            if val is None or val == "":
                val = source.get(f"mysql_{key}")
            if val is not None and val != "":
                raw[key] = val
        if not raw:
            return None
        return raw
    return None


class FinanceTransferDefaultsView(APIView):
    """Default MySQL connection template for the admin form."""

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        return Response(
            {
                "oracle_schema": ORACLE_SCHEMA,
                "mysql_defaults": public_mysql_config(MYSQL_DEFAULTS),
                # empty password placeholder so UI can override
                "mysql_password_default": "",
            }
        )


class FinanceTransferTestMysqlView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        try:
            cfg = resolve_mysql_config(_extract_mysql_config(request.data))
            result = test_mysql_connection(cfg)
            return Response(result)
        except Exception as exc:
            return Response(
                {"ok": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class FinanceTransferTablesView(APIView):
    """List Oracle FINANCE tables + MySQL presence (admin only)."""

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        return self._list(request, request.query_params)

    def post(self, request):
        # Prefer POST so MySQL password is not logged in the query string.
        data = request.data or {}
        # allow prefix on body
        params = dict(data)
        if "prefix" not in params and request.query_params.get("prefix"):
            params["prefix"] = request.query_params.get("prefix")
        return self._list(request, params)

    def _list(self, request, source):
        prefix = (source.get("prefix") or "").strip() if hasattr(source, "get") else ""
        prefixes = None
        if prefix:
            prefixes = [
                p.strip()
                for p in str(prefix).replace(";", ",").split(",")
                if p.strip()
            ]

        mysql_raw = None
        if hasattr(source, "get") and isinstance(source.get("mysql"), dict):
            mysql_raw = source.get("mysql")
        if not mysql_raw:
            mysql_raw = _extract_mysql_config(source)

        try:
            mysql_cfg = resolve_mysql_config(mysql_raw)
            tables = list_oracle_finance_tables(prefixes)
            mysql_map = mysql_table_status_map(mysql_cfg)
        except Exception as exc:
            hint_cfg = public_mysql_config(mysql_raw)
            return Response(
                {
                    "error": str(exc),
                    "hint": (
                        "Ensure Oracle is reachable and MySQL "
                        f"({hint_cfg['user']}@{hint_cfg['host']}:"
                        f"{hint_cfg['port']}/{hint_cfg['database']}) is up."
                    ),
                    "mysql": hint_cfg,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        items = []
        for item in tables:
            name = item["name"]
            mysql = mysql_map.get(name) or {"exists": False, "row_count": None}
            items.append(
                {
                    "name": name,
                    "oracle_num_rows": item.get("num_rows"),
                    "in_mysql": bool(mysql.get("exists")),
                    "mysql_row_count": mysql.get("row_count"),
                }
            )

        return Response(
            {
                "oracle_schema": ORACLE_SCHEMA,
                "mysql": public_mysql_config(mysql_cfg),
                "count": len(items),
                "tables": items,
            }
        )


class FinanceTransferStartView(APIView):
    """Start async transfer of selected tables."""

    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        data = request.data or {}
        tables = data.get("tables") or []
        if isinstance(tables, str):
            tables = [t.strip() for t in tables.split(",") if t.strip()]

        mysql_raw = data.get("mysql") if isinstance(data.get("mysql"), dict) else None
        if not mysql_raw:
            mysql_raw = _extract_mysql_config(data)

        try:
            state = start_transfer_job(
                tables,
                drop=bool(data.get("drop", True)),
                truncate=bool(data.get("truncate", False)),
                batch_size=int(data.get("batch_size") or 2000),
                skip_foreign_keys=bool(data.get("skip_foreign_keys", True)),
                constraints_only=bool(data.get("constraints_only", False)),
                stop_on_error=bool(data.get("stop_on_error", False)),
                mysql_config=mysql_raw,
            )
        except RuntimeError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(state, status=status.HTTP_202_ACCEPTED)


class FinanceTransferStatusView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        return Response(get_status())


class FinanceTransferApplyFksView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        data = request.data or {}
        mysql_raw = data.get("mysql") if isinstance(data.get("mysql"), dict) else None
        if not mysql_raw:
            mysql_raw = _extract_mysql_config(data)
        try:
            result = run_apply_pending_fks(mysql_config=mysql_raw)
        except RuntimeError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_409_CONFLICT)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(result)


SYNC_MODE_CHOICES = [
    {
        "id": "insert_ignore",
        "label": "Insert new rows only",
        "description": (
            "Keep all existing smpk_pension rows. Insert only brand-new PKs from finance."
        ),
        "destructive": False,
    },
    {
        "id": "append",
        "label": "Upsert (insert + update)",
        "description": (
            "Insert new PKs and refresh matching rows from finance. "
            "Never deletes local-only rows."
        ),
        "destructive": False,
    },
    {
        "id": "recreate",
        "label": "Full replace (drop & reload)",
        "description": (
            "DROP and recreate each selected table from finance, then reload all rows."
        ),
        "destructive": True,
    },
    {
        "id": "truncate",
        "label": "Truncate & reload",
        "description": (
            "Empty each selected smpk_pension table, then reload all rows from finance."
        ),
        "destructive": True,
    },
]


class SmpkSyncDefaultsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        return Response(
            {
                "source_defaults": default_source_config(),
                "target_defaults": default_target_config(),
                "salary_tables": list(SALARY_TABLES),
                "sync_modes": SYNC_MODE_CHOICES,
            }
        )


class SmpkSyncTestMysqlView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        data = request.data or {}
        role = (data.get("role") or "source").strip().lower()
        raw = data.get("mysql") if isinstance(data.get("mysql"), dict) else None
        if not raw:
            raw = _extract_mysql_config(data)
        try:
            if role == "target":
                cfg = resolve_target_config(raw)
            else:
                cfg = resolve_source_config(raw)
            result = test_mysql_connection(cfg)
            return Response(result)
        except Exception as exc:
            return Response(
                {"ok": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class SmpkSyncTablesView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        data = request.data or {}
        source_raw = data.get("source") if isinstance(data.get("source"), dict) else None
        target_raw = data.get("target") if isinstance(data.get("target"), dict) else None
        if not source_raw:
            source_raw = _extract_mysql_config(data.get("source_mysql") or data)
        if not target_raw:
            target_raw = _extract_mysql_config(data.get("target_mysql") or data)

        try:
            items = list_smpk_sync_tables(
                source_raw,
                target_raw,
                prefix=(data.get("prefix") or ""),
                include_payroll=bool(data.get("include_payroll")),
            )
            src_cfg = resolve_source_config(source_raw)
            tgt_cfg = resolve_target_config(target_raw)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "source": public_mysql_config(src_cfg),
                "target": public_mysql_config(tgt_cfg),
                "count": len(items),
                "tables": items,
            }
        )


class SmpkSyncStartView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        data = request.data or {}
        mode = (data.get("mode") or "insert_ignore").strip()
        preset = (data.get("preset") or "").strip().lower()

        tables = data.get("tables") or []
        if isinstance(tables, str):
            tables = [t.strip() for t in tables.split(",") if t.strip()]
        if preset == "salary":
            tables = list(SALARY_TABLES)
        elif preset == "all":
            tables = None

        source_raw = data.get("source") if isinstance(data.get("source"), dict) else None
        target_raw = data.get("target") if isinstance(data.get("target"), dict) else None

        try:
            state = start_smpk_sync_job(
                tables if tables else None,
                mode=mode,
                include_payroll=bool(data.get("include_payroll")),
                batch_size=int(data.get("batch_size") or 2000),
                stop_on_error=bool(data.get("stop_on_error")),
                source_config=source_raw,
                target_config=target_raw,
            )
        except RuntimeError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(state, status=status.HTTP_202_ACCEPTED)


class SmpkSyncStatusView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        return Response(get_smpk_sync_status())
