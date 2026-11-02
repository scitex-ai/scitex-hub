"""Request-scoped backend credentials retain the generic mount authorization gates."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

ROOT = Path(__file__).resolve().parents[3]
urlpatterns = []


@pytest.fixture
def binding_runtime():
    """Use real Django requests, settings, middleware and responses without a database."""
    if not settings.configured:
        settings.configure(
            SECRET_KEY="binding-test-only",
            DEFAULT_CHARSET="utf-8",
            ROOT_URLCONF=__name__,
            LOGIN_URL="/login/",
            INSTALLED_APPS=[],
        )
    from apps.workspace.apps_app.services import plugin_guards

    spec = importlib.util.spec_from_file_location(
        "binding_optional_apps", ROOT / "config/settings/_optional_apps.py"
    )
    optional = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(optional)
    return plugin_guards, optional


@pytest.mark.parametrize(
    "path,bound",
    [
        ("/apps/cards/dm/thread/peer", True),
        ("/apps/cards/dm-other/thread/peer", False),
        ("/apps/cards/", False),
        ("/apps/other/dm/thread/peer", False),
    ],
)
def test_backend_binding_is_limited_to_the_configured_mount_and_subroute(
    binding_runtime, path, bound
):
    # Arrange
    guards, _ = binding_runtime
    ds = "postgresql://dm@db:55432/store"
    policy = {"audience": "staff", "tenant_attribute": "scitex_store"}
    request = RequestFactory().get(path, {"store": "postgresql://attacker/db"})
    request.user = SimpleNamespace(
        is_authenticated=True, is_staff=True, is_superuser=False
    )
    seen = []
    middleware = guards.PluginMountGuardMiddleware(
        lambda req: (
            seen.append(getattr(req, "scitex_store", None)) or HttpResponse("ok")
        )
    )
    # Act
    with override_settings(
        PLUGIN_MOUNT_TABLE_OVERRIDE=[("/apps/cards/", "Cards", policy)],
        PLUGIN_STORE_ROUTE_SECRET_BINDINGS={"/apps/cards/": {"dm/": ds}},
    ):
        response = middleware(request)
    # Assert
    assert (response.status_code, seen) == (200, [ds if bound else None])


@pytest.mark.parametrize(
    "authenticated,staff,status", [(False, False, 302), (True, False, 403)]
)
def test_binding_never_bypasses_login_or_leaf_audience(
    binding_runtime, authenticated, staff, status
):
    # Arrange
    guards, _ = binding_runtime
    request = RequestFactory().get(
        "/apps/cards/dm/thread/peer", HTTP_ACCEPT="application/json"
    )
    request.user = SimpleNamespace(
        is_authenticated=authenticated,
        is_staff=staff,
        is_superuser=False,
        username="visitor",
    )
    # Act
    with override_settings(
        PLUGIN_MOUNT_TABLE_OVERRIDE=[
            (
                "/apps/cards/",
                "Cards",
                {"audience": "staff", "tenant_attribute": "scitex_store"},
            )
        ],
        PLUGIN_STORE_ROUTE_SECRET_BINDINGS={
            "/apps/cards/": {"dm/": "postgresql://dm@db/store"}
        },
        SCITEX_HUB_PLUGIN_OPERATORS=[],
    ):
        response = guards.PluginMountGuardMiddleware(
            lambda req: HttpResponse("unexpected")
        )(request)
    # Assert
    assert (response.status_code, hasattr(request, "scitex_store")) == (status, False)


def test_optional_dm_credential_preserves_the_ambient_store(binding_runtime):
    # Arrange
    _, optional = binding_runtime
    reader = "postgresql://reader@db:55432/store"
    writer = "postgresql://dm@db:55432/store"
    env = {"SCITEX_STORE_DSN": reader, "SCITEX_HUB_CARDS_DM_STORE": writer}
    # Act
    bindings = optional.plugin_store_route_bindings(env)
    # Assert
    assert (bindings, env["SCITEX_STORE_DSN"]) == (
        {"/apps/cards/": {"dm/": writer}},
        reader,
    )


@pytest.mark.parametrize(
    "writer",
    [
        "postgresql://dm@elsewhere:55432/store",
        "postgresql://dm@db:55432/other",
        "file:///tmp/cards",
    ],
)
def test_dm_credential_cannot_silently_choose_another_database(binding_runtime, writer):
    # Arrange
    _, optional = binding_runtime
    env = {
        "SCITEX_STORE_DSN": "postgresql://reader@db:55432/store",
        "SCITEX_HUB_CARDS_DM_STORE": writer,
    }
    # Act
    with pytest.raises(RuntimeError) as error:
        optional.plugin_store_route_bindings(env)
    # Assert
    assert writer not in str(error.value)


def test_private_dm_credential_file_uses_the_same_scoped_binding(
    binding_runtime, tmp_path
):
    # Arrange
    _, optional = binding_runtime
    secret = tmp_path / "dm-dsn"
    secret.write_text("postgresql://dm@db:55432/store\n")
    env = {
        "SCITEX_STORE_DSN": "postgresql://reader@db:55432/store",
        "SCITEX_HUB_CARDS_DM_STORE_FILE": str(secret),
    }
    # Act
    bindings = optional.plugin_store_route_bindings(env)
    # Assert
    assert bindings == {"/apps/cards/": {"dm/": "postgresql://dm@db:55432/store"}}


def test_unavailable_private_dm_file_fails_without_exposing_its_path(
    binding_runtime, tmp_path
):
    # Arrange
    _, optional = binding_runtime
    secret = tmp_path / "unavailable-credential"
    # Act
    with pytest.raises(RuntimeError) as error:
        optional.plugin_store_route_bindings(
            {"SCITEX_HUB_CARDS_DM_STORE_FILE": str(secret)}
        )
    # Assert
    assert str(secret) not in str(error.value)


def test_dm_binding_is_redacted_by_django_settings_error_reports(binding_runtime):
    # Arrange
    from django.views.debug import SafeExceptionReporterFilter

    binding = {"/apps/cards/": {"dm/": "postgresql://writer:private@db/store"}}
    # Act
    result = SafeExceptionReporterFilter().cleanse_setting(
        "PLUGIN_STORE_ROUTE_SECRET_BINDINGS", binding
    )
    # Assert
    assert result == "********************"
