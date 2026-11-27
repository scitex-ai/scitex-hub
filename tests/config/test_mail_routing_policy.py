#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_mail_routing_policy.py
"""Outgoing mail follows the operator's per-purpose routing (2026-11-27).

  system/ops alerts   From no-reply@  To dev@
  user-facing mail    From no-reply@  To the user

The settings module is RE-EXECUTED with the environment really set or really
unset (a yield fixture around ``os.environ``), so what is measured is the
committed default and the committed override path -- not this machine's env.
"""

from __future__ import annotations

import importlib
import os

import pytest

from config import branding

ROUTING_KEYS = (
    "SCITEX_HUB_ADMINS",
    "SCITEX_HUB_MANAGERS",
    "SCITEX_HUB_SERVER_EMAIL",
    "SCITEX_HUB_DEFAULT_FROM_EMAIL",
    "SCITEX_HUB_HEALTH_NOTIFICATION_RECIPIENT",
)


def _settings_email():
    import config.settings.settings_email as module

    return importlib.reload(module)


@pytest.fixture
def routing_env():
    """Unset every routing override; let a test set some; restore afterwards."""
    saved = {key: os.environ.pop(key) for key in ROUTING_KEYS if key in os.environ}
    try:
        yield os.environ
    finally:
        for key in ROUTING_KEYS:
            os.environ.pop(key, None)
        os.environ.update(saved)
        _settings_email()  # leave the module as the real env defines it


class TestDefaults:
    def test_django_error_mail_goes_to_the_ops_address(self, routing_env):
        # Arrange
        # Act
        admins = _settings_email().ADMINS
        # Assert
        assert admins == [("dev@scitex.ai", "dev@scitex.ai")]

    def test_django_error_mail_never_defaults_to_the_operators_inbox(self, routing_env):
        # Arrange
        # Act
        addresses = [address for _name, address in _settings_email().ADMINS]
        # Assert
        assert "ywatanabe@scitex.ai" not in addresses

    def test_managers_follow_admins(self, routing_env):
        # Arrange
        # Act
        module = _settings_email()
        # Assert
        assert module.MANAGERS == module.ADMINS

    def test_error_mail_is_sent_from_no_reply(self, routing_env):
        # Arrange
        # Act
        server_email = _settings_email().SERVER_EMAIL
        # Assert
        assert server_email == "no-reply@scitex.ai"

    def test_user_mail_is_sent_from_no_reply(self, routing_env):
        # Arrange
        # Act
        default_from = _settings_email().DEFAULT_FROM_EMAIL
        # Assert
        assert default_from == "no-reply@scitex.ai"

    def test_the_sender_is_not_implicitly_the_smtp_login(self, routing_env):
        # Arrange
        routing_env["SCITEX_HUB_EMAIL_HOST_USER"] = "some-login@example.org"
        try:
            # Act
            server_email = _settings_email().SERVER_EMAIL
        finally:
            routing_env.pop("SCITEX_HUB_EMAIL_HOST_USER", None)
        # Assert
        assert server_email == "no-reply@scitex.ai"

    def test_the_site_down_alarm_goes_to_the_ops_address(self, routing_env):
        # Arrange
        from apps.infra.public_app.tasks import health

        # Act
        _url, _site, recipient, _sender = health._get_health_config()
        # Assert
        assert recipient == branding.OPS_ALERT_EMAIL


class TestOverrides:
    def test_admins_can_be_set_per_deployment(self, routing_env):
        # Arrange
        routing_env["SCITEX_HUB_ADMINS"] = "Ops <ops@example.org>, b@example.org"
        # Act
        admins = _settings_email().ADMINS
        # Assert
        assert admins == [
            ("Ops", "ops@example.org"),
            ("b@example.org", "b@example.org"),
        ]

    def test_a_malformed_admins_value_fails_settings_import(self, routing_env):
        # Arrange
        routing_env["SCITEX_HUB_ADMINS"] = "not-an-address"
        # Act
        # Assert
        with pytest.raises(ValueError, match="SCITEX_HUB_ADMINS"):
            _settings_email()

    def test_the_server_sender_can_be_set_per_deployment(self, routing_env):
        # Arrange
        routing_env["SCITEX_HUB_SERVER_EMAIL"] = "alerts@example.org"
        # Act
        server_email = _settings_email().SERVER_EMAIL
        # Assert
        assert server_email == "alerts@example.org"

    def test_the_site_down_recipient_can_be_set_per_deployment(self, routing_env):
        # Arrange
        from apps.infra.public_app.tasks import health

        routing_env["SCITEX_HUB_HEALTH_NOTIFICATION_RECIPIENT"] = "oncall@example.org"
        # Act
        _url, _site, recipient, _sender = health._get_health_config()
        # Assert
        assert recipient == "oncall@example.org"


class TestBrandingAddresses:
    def test_the_no_reply_address_is_the_mailbox_that_exists(self):
        # Arrange
        # Act
        address = branding.NOREPLY_EMAIL
        # Assert
        assert address == "no-reply@scitex.ai"

    def test_the_ops_alert_address_is_dev(self):
        # Arrange
        # Act
        address = branding.OPS_ALERT_EMAIL
        # Assert
        assert address == "dev@scitex.ai"


# EOF
