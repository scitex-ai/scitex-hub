"""Regression coverage for Hub's optional, authenticated SAC mount."""

from importlib import import_module
from importlib.util import find_spec
from unittest.mock import patch

import pytest
from django.apps import apps
from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.test import RequestFactory
from django.urls import resolve

from apps.workspace.agents_app import views
from config.settings._optional_apps import optional_upstream_apps

try:
    _SAC_INSTALLED = find_spec("scitex_agent_container._django") is not None
except ModuleNotFoundError:
    _SAC_INSTALLED = False
_LEAF_CONFIG = (
    "scitex_agent_container._django.apps.AgentContainerDashboardConfig"
)


def test_hub_adapter_urlconf_is_committed_and_importable() -> None:
    module = import_module("apps.workspace.agents_app.urls")

    assert module.app_name == "scitex_agent_container"
    assert len(module.urlpatterns) == 5


@pytest.mark.skipif(not _SAC_INSTALLED, reason="SAC leaf is not installed")
def test_root_urlconf_imports_when_sac_is_installed() -> None:
    match = resolve("/apps/agents/")
    assert match.view_name == "scitex_agent_container:index"


@pytest.mark.skipif(not _SAC_INSTALLED, reason="SAC leaf is not installed")
def test_development_system_check_succeeds_with_sac() -> None:
    call_command("check", verbosity=0)


def test_optional_apps_registers_sac_leaf() -> None:
    def installed(module_path: str):
        return object() if module_path == "scitex_agent_container._django" else None

    with patch("config.settings._optional_apps._installed", side_effect=installed):
        entries = optional_upstream_apps()

    assert entries == [_LEAF_CONFIG]


@pytest.mark.skipif(not _SAC_INSTALLED, reason="SAC leaf is not installed")
def test_sac_leaf_is_present_in_django_registry() -> None:
    assert apps.is_installed("scitex_agent_container._django")


@pytest.mark.parametrize(
    ("path", "view"),
    [
        ("/apps/agents/", views.index),
        ("/apps/agents/api/fleet", views.fleet_api),
        ("/apps/agents/healthz", views.healthz),
    ],
)
def test_read_surfaces_require_login(path, view) -> None:
    request = RequestFactory().get(path)
    request.user = AnonymousUser()

    response = view(request)

    assert response.status_code == 302
    assert response.url.startswith("/auth/login/")
    assert f"next={path}" in response.url


def test_detail_requires_login() -> None:
    request = RequestFactory().get("/apps/agents/scitex-scholar/")
    request.user = AnonymousUser()

    response = views.detail(request, "scitex-scholar")

    assert response.status_code == 302


@pytest.mark.parametrize(
    ("path", "view", "args"),
    [
        ("/apps/agents/", views.index, ()),
        ("/apps/agents/api/fleet", views.fleet_api, ()),
        ("/apps/agents/healthz", views.healthz, ()),
        (
            "/apps/agents/scitex-scholar/",
            views.detail,
            ("scitex-scholar",),
        ),
    ],
)
def test_ordinary_authenticated_user_cannot_read_fleet(
    django_user_model, path, view, args
) -> None:
    request = RequestFactory().get(path)
    request.user = django_user_model(username="ordinary-user")

    response = view(request, *args)

    assert response.status_code == 403


@pytest.mark.skipif(not _SAC_INSTALLED, reason="SAC leaf is not installed")
def test_configured_operator_can_read_fleet(django_user_model, monkeypatch) -> None:
    request = RequestFactory().get("/apps/agents/")
    request.user = django_user_model(username="operator")
    monkeypatch.setenv(
        "SCITEX_AGENT_CONTAINER_LIFECYCLE_OPERATORS", "other, operator"
    )

    with patch(
        "scitex_agent_container._django.views.index", return_value="fleet"
    ) as upstream:
        response = views.index(request)

    assert response == "fleet"
    upstream.assert_called_once_with(request)


@pytest.mark.skipif(not _SAC_INSTALLED, reason="SAC leaf is not installed")
def test_staff_user_can_read_fleet(django_user_model) -> None:
    request = RequestFactory().get("/apps/agents/")
    request.user = django_user_model(username="staff", is_staff=True)

    with patch(
        "scitex_agent_container._django.views.index", return_value="fleet"
    ) as upstream:
        response = views.index(request)

    assert response == "fleet"
    upstream.assert_called_once_with(request)


@pytest.mark.skipif(not _SAC_INSTALLED, reason="SAC leaf is not installed")
def test_superuser_can_read_fleet(django_user_model) -> None:
    request = RequestFactory().get("/apps/agents/")
    request.user = django_user_model(username="admin", is_superuser=True)

    with patch(
        "scitex_agent_container._django.views.index", return_value="fleet"
    ) as upstream:
        response = views.index(request)

    assert response == "fleet"
    upstream.assert_called_once_with(request)


@pytest.mark.skipif(not _SAC_INSTALLED, reason="SAC leaf is not installed")
def test_authenticated_action_delegates(django_user_model) -> None:
    request = RequestFactory().post(
        "/apps/agents/scitex-scholar/action", {"action": "restart"}
    )
    request.user = django_user_model(username="operator")

    with patch(
        "scitex_agent_container._django.views.lifecycle_action",
        return_value="accepted",
    ) as upstream:
        response = views.lifecycle_action(request, "scitex-scholar")

    assert response == "accepted"
    upstream.assert_called_once_with(request, "scitex-scholar")
