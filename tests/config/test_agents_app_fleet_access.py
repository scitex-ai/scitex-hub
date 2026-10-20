"""Who may ACT on the fleet — now through the generic audience gate.

Reads are login-only since 2026-09-26: the leaf scopes every read by
identity (upstream ``resolve_identity`` + ``scope_rows``), so an ordinary
signed-in user only ever sees their own agents. Control stays gated
upstream (``can_control``). What these tests pin is the HUB side of that
contract, generically — no test names the agents views, which no longer
exist:

- ``plugin_access_allowed`` with a staff-audience policy refuses ordinary
  accounts and admits staff, superusers, and listed operators (the CONTROL
  boundary the old ``_fleet_access_required`` decorator held);
- an open (login-only) policy admits ordinary signed-in users — the hub
  must not re-gate reads the leaf scopes itself;
- the operator allowlist lives in ``SCITEX_HUB_PLUGIN_OPERATORS``, which
  defaults to the fleet-operator env var so the operator's account keeps
  working without Django staff.

DB-free: stub users, ``override_settings``, no ORM.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import override_settings

from apps.workspace.apps_app.services.plugin_guards import plugin_access_allowed

#: The control boundary, as a leaf-declared policy: restricted audience.
FLEET_CONTROL_POLICY = {"audience": "staff", "login_required": True}

#: The read boundary, as a leaf-declared policy: login only.
FLEET_READ_POLICY = {"login_required": True}


def _user(**flags):
    base = {
        "is_authenticated": True,
        "is_staff": False,
        "is_superuser": False,
        "username": "alice",
    }
    base.update(flags)
    return SimpleNamespace(**base)


@pytest.fixture
def operators_setting():
    with override_settings(SCITEX_HUB_PLUGIN_OPERATORS=["bob", "carol"]):
        yield


@pytest.fixture
def no_operators_setting():
    with override_settings(SCITEX_HUB_PLUGIN_OPERATORS=[]):
        yield


def test_ordinary_signed_in_user_is_refused_control(no_operators_setting):
    # Arrange
    user = _user()

    # Act
    allowed = plugin_access_allowed(user, FLEET_CONTROL_POLICY)

    # Assert
    assert allowed is False


def test_staff_user_passes_control(no_operators_setting):
    # Arrange
    user = _user(is_staff=True)

    # Act
    allowed = plugin_access_allowed(user, FLEET_CONTROL_POLICY)

    # Assert
    assert allowed is True


def test_superuser_passes_control(no_operators_setting):
    # Arrange
    user = _user(is_superuser=True)

    # Act
    allowed = plugin_access_allowed(user, FLEET_CONTROL_POLICY)

    # Assert
    assert allowed is True


def test_configured_operator_passes_control_without_staff(operators_setting):
    # Arrange
    user = _user(username="carol")

    # Act
    allowed = plugin_access_allowed(user, FLEET_CONTROL_POLICY)

    # Assert
    assert allowed is True


def test_unlisted_user_is_refused_control_even_when_operators_set(
    operators_setting,
):
    # Arrange
    user = _user(username="mallory")

    # Act
    allowed = plugin_access_allowed(user, FLEET_CONTROL_POLICY)

    # Assert
    assert allowed is False


def test_anonymous_is_refused_control(operators_setting):
    # Arrange
    user = AnonymousUser()

    # Act
    allowed = plugin_access_allowed(user, FLEET_CONTROL_POLICY)

    # Assert
    assert allowed is False


def test_ordinary_signed_in_user_passes_the_read_boundary(no_operators_setting):
    # Reads are login-only: the hub must not re-gate what the leaf scopes
    # by identity. A refusal here would mean the hub re-gated reads.
    # Arrange
    user = _user()

    # Act
    allowed = plugin_access_allowed(user, FLEET_READ_POLICY)

    # Assert
    assert allowed is True


def test_operator_allowlist_defaults_to_the_fleet_operator_env():
    # The operator's account opens restricted mounts without Django staff.
    # The default is deployment DATA (an env var read in settings), so pin
    # the wiring as file content — importing settings twice to observe an
    # env default would fork the whole Django setup.
    # Arrange
    from pathlib import Path

    # Act
    text = (
        Path(__file__).resolve().parents[2]
        / "config/settings/settings_shared.py"
    ).read_text()

    # Assert
    assert "SCITEX_HUB_PLUGIN_OPERATORS" in text
    assert "SCITEX_AGENT_CONTAINER_LIFECYCLE_OPERATORS" in text
