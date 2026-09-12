"""SAC dashboard mounting and authentication contract.

``scitex-agent-container`` is an OPTIONAL upstream package: the hub mounts its
dashboard only when it is importable (see ``config/urls.py``) and it is NOT a
declared hub dependency, so it is absent from the ``.[all,dev]`` CI env. The
login-boundary tests hold either way (they never import the package); the two
delegation tests need the real upstream to patch, so they skip rather than
error where it is not installed.
"""

from importlib.util import find_spec
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.workspace.agents_app import views

_SAC_INSTALLED = find_spec("scitex_agent_container") is not None


def test_dashboard_requires_login() -> None:
    request = RequestFactory().get("/apps/agents/")
    request.user = AnonymousUser()

    response = views.index(request)

    assert response.status_code == 302
    assert response.url.startswith("/auth/login/")
    assert "next=/apps/agents/" in response.url


@pytest.mark.skipif(not _SAC_INSTALLED, reason="scitex-agent-container not installed")
def test_authenticated_dashboard_delegates(django_user_model) -> None:
    request = RequestFactory().get("/apps/agents/")
    request.user = django_user_model(username="operator")

    with patch(
        "scitex_agent_container._django.views.index", return_value="fleet"
    ) as upstream:
        response = views.index(request)

    assert response == "fleet"
    upstream.assert_called_once_with(request)


def test_detail_requires_login() -> None:
    request = RequestFactory().get("/apps/agents/scitex-scholar/")
    request.user = AnonymousUser()

    response = views.detail(request, "scitex-scholar")

    assert response.status_code == 302


@pytest.mark.skipif(not _SAC_INSTALLED, reason="scitex-agent-container not installed")
def test_authenticated_action_delegates(django_user_model) -> None:
    request = RequestFactory().post(
        "/apps/agents/scitex-scholar/action", {"action": "restart"}
    )
    request.user = django_user_model(username="ywatanabe")

    with patch(
        "scitex_agent_container._django.views.lifecycle_action",
        return_value="accepted",
    ) as upstream:
        response = views.lifecycle_action(request, "scitex-scholar")

    assert response == "accepted"
    upstream.assert_called_once_with(request, "scitex-scholar")
