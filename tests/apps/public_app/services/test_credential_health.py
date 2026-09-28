from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from apps.infra.gitea_app.exceptions import GiteaAPIError
from apps.infra.public_app.services.credential_health import (
    ALLOWED_STATUSES,
    credential_inventory,
    run_credential_preflight,
)


class _Client:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = 0

    def get_current_user(self):
        self.calls += 1
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def _settings(**overrides):
    values = {
        "SECRET_KEY": "configured-secret",
        "DATABASES": {"default": {"PASSWORD": "configured-db-password"}},
        "GITEA_TOKEN": "configured-gitea-token",
        "REDIS_URL": "redis://redis:6379/1",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _run(settings_obj=None, client=None, **kwargs):
    return run_credential_preflight(
        settings_obj=settings_obj or _settings(),
        gitea_client_factory=lambda: client or _Client({"login": "service"}),
        database_probe=lambda: None,
        redis_probe=lambda: None,
        **kwargs,
    )


def _by_id(report):
    return {item["id"]: item for item in report["credentials"]}


def test_inventory_is_structural_and_contains_no_values():
    inventory = credential_inventory()

    assert {item["id"] for item in inventory} == {
        "django_secret_key",
        "database",
        "gitea",
        "redis",
    }
    assert all("value" not in item for item in inventory)
    assert all(item["call_sites"] for item in inventory)
    assert all(item["environment_variables"] for item in inventory)
    assert next(item for item in inventory if item["id"] == "gitea")[
        "required_in_production"
    ]


@pytest.mark.parametrize(
    ("credential_id", "settings_obj"),
    [
        ("django_secret_key", _settings(SECRET_KEY="")),
        ("database", _settings(DATABASES={"default": {"PASSWORD": ""}})),
        ("gitea", _settings(GITEA_TOKEN="")),
    ],
)
def test_mandatory_absent_credentials_are_reported(credential_id, settings_obj):
    report = _run(settings_obj=settings_obj)

    assert _by_id(report)[credential_id]["status"] == "absent"
    assert report["overall"] == "unhealthy"


@pytest.mark.parametrize(
    ("credential_id", "settings_obj"),
    [
        ("django_secret_key", _settings(SECRET_KEY="CHANGE_ME")),
        (
            "database",
            _settings(
                DATABASES={
                    "default": {"PASSWORD": "CHANGE-THIS-DATABASE-PASSWORD-FOR-PROD"}
                }
            ),
        ),
        ("gitea", _settings(GITEA_TOKEN="replace-me")),
    ],
)
def test_placeholders_are_rejected_without_probing(credential_id, settings_obj):
    client = _Client({"login": "service"})

    report = _run(settings_obj=settings_obj, client=client)

    assert _by_id(report)[credential_id]["status"] == "placeholder"
    if credential_id == "gitea":
        assert client.calls == 0


def test_gitea_401_is_rejected_not_unreachable():
    report = _run(client=_Client(GiteaAPIError("ignored", status_code=401)))

    assert _by_id(report)["gitea"]["status"] == "rejected"


def test_gitea_transport_failure_is_unreachable_and_exception_is_not_exposed():
    secret_in_exception = "configured-gitea-token"

    report = _run(client=_Client(GiteaAPIError(secret_in_exception)))

    assert _by_id(report)["gitea"]["status"] == "unreachable"
    assert secret_in_exception not in str(report)
    assert "error" not in _by_id(report)["gitea"]


def test_expired_metadata_is_reported_as_rejected():
    expiry = datetime.now(timezone.utc) - timedelta(minutes=1)

    report = _run(
        client=_Client({"expires_at": expiry.isoformat()}),
        now=datetime.now(timezone.utc),
    )

    assert _by_id(report)["gitea"]["status"] == "rejected"


def test_expiring_metadata_is_reported_without_returning_response_data():
    expiry = datetime.now(timezone.utc) + timedelta(days=3)
    response = {"login": "service", "expires_at": expiry.isoformat(), "token": "never"}

    report = _run(client=_Client(response), now=datetime.now(timezone.utc))

    assert _by_id(report)["gitea"]["status"] == "expiring_soon"
    assert "never" not in str(report)
    assert "expires_at" not in _by_id(report)["gitea"]


def test_healthy_probes_report_healthy():
    report = _run()

    assert report["overall"] == "healthy"
    assert {item["status"] for item in report["credentials"]} == {"healthy"}


@pytest.mark.parametrize("forced", sorted(ALLOWED_STATUSES))
def test_every_status_can_be_forced_without_reading_or_network(forced):
    def explode():
        raise AssertionError("probe should not run")

    report = run_credential_preflight(
        settings_obj=SimpleNamespace(),
        gitea_client_factory=explode,
        database_probe=explode,
        redis_probe=explode,
        forced_statuses={item["id"]: forced for item in credential_inventory()},
    )

    assert {item["status"] for item in report["credentials"]} == {forced}


def test_invalid_forced_status_fails_closed():
    with pytest.raises(ValueError, match="Unsupported credential status"):
        _run(forced_statuses={"gitea": "green-enough"})
