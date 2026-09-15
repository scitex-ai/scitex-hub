"""Secret-safe credential inventory and authenticated health probes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from django.conf import settings as django_settings

ALLOWED_STATUSES = frozenset(
    {"absent", "placeholder", "rejected", "unreachable", "expiring_soon", "healthy"}
)
_UNHEALTHY = ALLOWED_STATUSES - {"healthy"}
_PLACEHOLDERS = frozenset(
    {
        "change-me",
        "change_me",
        "changeme",
        "change_this_in_prod",
        "change-this-database-password-for-prod",
        "your-gitea-token-here",
        "replace-me",
        "secret",
    }
)


@dataclass(frozen=True)
class CredentialSpec:
    id: str
    environment_variables: tuple[str, ...]
    setting_names: tuple[str, ...]
    required_in_production: bool
    probe: str
    call_sites: tuple[str, ...]


_SPECS = (
    CredentialSpec(
        "django_secret_key",
        ("SCITEX_HUB_DJANGO_SECRET_KEY", "SCITEX_CLOUD_DJANGO_SECRET_KEY"),
        ("SECRET_KEY",),
        True,
        "configuration",
        (
            "config/settings/settings_prod.py",
            "apps/infra/integrations_app/models.py",
            "apps/infra/project_app/models/workflows/workflow_secret.py",
        ),
    ),
    CredentialSpec(
        "database",
        ("SCITEX_HUB_DB_PASSWORD", "SCITEX_HUB_POSTGRES_PASSWORD"),
        ("DATABASES.default.PASSWORD",),
        True,
        "django.db.connection",
        ("config/settings/settings_prod.py", "django.db.connection"),
    ),
    CredentialSpec(
        "gitea",
        ("SCITEX_HUB_GITEA_TOKEN", "SCITEX_CLOUD_GITEA_TOKEN"),
        ("GITEA_TOKEN",),
        True,
        "GiteaClient.get_current_user",
        (
            "config/settings/settings_prod.py",
            "apps/infra/gitea_app/api_client/base.py",
            "apps/infra/gitea_app/api_client/users.py",
        ),
    ),
    CredentialSpec(
        "redis",
        ("SCITEX_HUB_REDIS_URL", "SCITEX_CLOUD_REDIS_URL"),
        ("REDIS_URL",),
        False,
        "django.core.cache",
        ("config/settings/settings_shared.py", "django.core.cache"),
    ),
)


def credential_inventory() -> list[dict]:
    """Return structural consumers and names; never resolve credential values."""
    return [
        {
            "id": spec.id,
            "environment_variables": list(spec.environment_variables),
            "setting_names": list(spec.setting_names),
            "required_in_production": spec.required_in_production,
            "probe": spec.probe,
            "call_sites": list(spec.call_sites),
        }
        for spec in _SPECS
    ]


def _placeholder(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    return normalized in _PLACEHOLDERS or normalized.startswith(("example-", "placeholder-"))


def _value(settings_obj, credential_id: str):
    if credential_id == "django_secret_key":
        return getattr(settings_obj, "SECRET_KEY", "")
    if credential_id == "database":
        return getattr(settings_obj, "DATABASES", {}).get("default", {}).get("PASSWORD", "")
    if credential_id == "gitea":
        return getattr(settings_obj, "GITEA_TOKEN", "")
    return getattr(settings_obj, "REDIS_URL", "")


def _expiration_status(payload: object, now: datetime) -> str:
    if not isinstance(payload, dict):
        return "healthy"
    raw = payload.get("expires_at") or payload.get("token_expiration")
    if not isinstance(raw, str):
        return "healthy"
    try:
        expiry = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
    except ValueError:
        return "healthy"
    if expiry <= now:
        return "rejected"
    return "expiring_soon" if expiry <= now + timedelta(days=14) else "healthy"


def _default_database_probe() -> None:
    from django.db import connection

    connection.ensure_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")


def _default_redis_probe() -> None:
    from django.core.cache import cache

    cache.set("credential_health", "ok", 10)
    if cache.get("credential_health") != "ok":
        raise ConnectionError


def _default_gitea_factory():
    from apps.infra.gitea_app.api_client import GiteaClient

    return GiteaClient()


def _failure_status(exc: Exception) -> str:
    status_code = getattr(exc, "status_code", None)
    if status_code in (401, 403):
        return "rejected"
    sqlstate = getattr(exc, "pgcode", None) or getattr(exc, "sqlstate", None)
    if sqlstate == "28P01":
        return "rejected"
    name = type(exc).__name__.lower()
    if "authentication" in name or "invalidpassword" in name:
        return "rejected"
    return "unreachable"


def run_credential_preflight(
    *,
    settings_obj=None,
    gitea_client_factory: Callable = _default_gitea_factory,
    database_probe: Callable = _default_database_probe,
    redis_probe: Callable = _default_redis_probe,
    forced_statuses: dict[str, str] | None = None,
    now: datetime | None = None,
) -> dict:
    """Run probes and return a fixed-schema report containing no secret material."""
    settings_obj = settings_obj or django_settings
    forced_statuses = forced_statuses or {}
    unknown = set(forced_statuses) - {spec.id for spec in _SPECS}
    invalid = set(forced_statuses.values()) - ALLOWED_STATUSES
    if unknown or invalid:
        raise ValueError("Unsupported credential status or credential id")
    now = now or datetime.now(timezone.utc)
    results = []
    for spec in _SPECS:
        forced = forced_statuses.get(spec.id)
        if forced:
            status = forced
        else:
            value = _value(settings_obj, spec.id)
            if value is None or (isinstance(value, str) and not value.strip()):
                status = "absent"
            elif _placeholder(value):
                status = "placeholder"
            elif spec.id == "django_secret_key":
                status = "healthy"
            else:
                try:
                    if spec.id == "database":
                        payload = database_probe()
                    elif spec.id == "redis":
                        payload = redis_probe()
                    else:
                        payload = gitea_client_factory().get_current_user()
                    status = _expiration_status(payload, now)
                except Exception as exc:
                    status = _failure_status(exc)
        results.append(
            {
                "id": spec.id,
                "status": status,
                "required": spec.required_in_production,
                "probe": spec.probe,
            }
        )
    unhealthy = any(item["required"] and item["status"] in _UNHEALTHY for item in results)
    return {"schema_version": 1, "overall": "unhealthy" if unhealthy else "healthy", "credentials": results}
