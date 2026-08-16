#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""An alarm that cannot deliver must SAY so (fix/alarms-must-not-fail-silently).

THE BUG THESE GUARD. All three alarm sends in
``apps/infra/public_app/tasks/health.py`` shipped with ``fail_silently=True``.
That instructs Django's mail backend to swallow send failures, so the
surrounding ``except Exception`` never fires and its ``logger.error`` is dead
code for the one failure it exists to report.

Composed with credentials that have gone stale -- which the operator suspected
on 2026-08-10 -- the result is an alarm that is silent about being silent:
configured, believed live, incapable of saying otherwise, and indistinguishable
from an alarm with nothing to report.

Note the asymmetry that made this easy to miss: every USER-FACING send in this
repo already uses ``fail_silently=False`` (password reset, contact form,
project mail). Only the alarms discarded their errors. A password reset that
cannot send raises; a "your site is down" alert that cannot send vanished.

No mocks (STX-NM001/NM002): the failing path uses a REAL Django email backend
written below that raises the way a real SMTP auth failure does, selected via
Django's own ``override_settings``. Nothing is patched.
"""

import logging

import pytest
from django.core.mail.backends.base import BaseEmailBackend
from django.test import override_settings

from apps.infra.public_app.tasks.health import (
    _send_alert_notification,
    _send_recovery_notification,
)

HEALTH_LOGGER = "apps.infra.public_app.tasks.health"
FAILING_BACKEND = f"{__name__}._RefusingEmailBackend"
COLLECTING_BACKEND = f"{__name__}._CollectingEmailBackend"


class _RefusingEmailBackend(BaseEmailBackend):
    """A real backend that refuses, standing in for dead SMTP credentials.

    IT HONOURS ``fail_silently``, AND THAT IS THE WHOLE POINT. Django puts that
    contract on the BACKEND, not on ``send_mail``: every real backend ends its
    error path with ``if not self.fail_silently: raise``. A fake that raised
    unconditionally would swallow the distinction under test -- the guards
    below would then pass against the very ``fail_silently=True`` code they
    exist to forbid, and read as protection while protecting nothing.

    So this reproduces the real behaviour: raise when the caller asked to hear
    about failures, stay quiet when it asked not to. Run these tests against
    the pre-fix ``fail_silently=True`` and they fail, which is the only reason
    to trust them passing now.
    """

    def send_messages(self, email_messages):
        if not self.fail_silently:
            raise OSError("SMTPAuthenticationError(535, 'authentication failed')")
        return 0


class _CollectingEmailBackend(BaseEmailBackend):
    """A real backend that accepts, to prove the failing one is not the norm."""

    sent: list = []

    def send_messages(self, email_messages):
        _CollectingEmailBackend.sent.extend(email_messages)
        return len(email_messages)


@pytest.fixture
def collected():
    """Messages accepted by the collecting backend during one test."""
    _CollectingEmailBackend.sent = []
    yield _CollectingEmailBackend.sent
    _CollectingEmailBackend.sent = []


@override_settings(EMAIL_BACKEND=COLLECTING_BACKEND)
def test_a_deliverable_alert_is_actually_sent(collected):
    """POSITIVE CONTROL: without it, the tests below pass vacuously.

    If the send were broken for an unrelated reason, "an error was logged"
    would be satisfied for the wrong reason and would read as a working guard.
    """
    # Arrange
    recipient, sender = "ops@example.com", "no-reply@example.com"
    # Act
    _send_alert_notification("https://example.com", "boom", 3, recipient, sender)
    # Assert
    assert len(collected) == 1


@override_settings(EMAIL_BACKEND=FAILING_BACKEND)
def test_an_undeliverable_alert_is_reported(caplog):
    """THE BUG: with fail_silently=True this logged nothing at all."""
    # Arrange
    caplog.set_level(logging.ERROR, logger=HEALTH_LOGGER)
    # Act
    _send_alert_notification("https://example.com", "boom", 3, "ops@x.com", "n@x.com")
    # Assert
    assert "ALARM DELIVERY FAILED" in caplog.text


@override_settings(EMAIL_BACKEND=FAILING_BACKEND)
def test_an_undeliverable_alert_does_not_crash_the_health_task(caplog):
    """Loud, but not fatal: the probe must keep running and keep detecting.

    This is why the original author reached for fail_silently, and the concern
    was right -- a health CHECK must not die on a mail error. The conclusion
    was what inverted it: the task survives because the caller catches, not
    because the error is discarded.
    """
    # Arrange
    caplog.set_level(logging.ERROR, logger=HEALTH_LOGGER)
    # Act
    observed = _send_alert_notification("https://e.com", "boom", 3, "o@x.com", "n@x.com")
    # Assert
    assert observed is None


@override_settings(EMAIL_BACKEND=FAILING_BACKEND)
def test_an_undeliverable_recovery_notice_is_reported(caplog):
    """The recovery path carried the same defect and needs the same guard."""
    # Arrange
    caplog.set_level(logging.ERROR, logger=HEALTH_LOGGER)
    # Act
    _send_recovery_notification("https://example.com", 0.12, "ops@x.com", "n@x.com")
    # Assert
    assert "ALARM DELIVERY FAILED" in caplog.text


@override_settings(EMAIL_BACKEND=FAILING_BACKEND)
def test_the_failure_report_names_the_recipient(caplog):
    """An error that only says what broke is half-written.

    The operator has to know WHICH address failed to be able to act, so the
    message carries it alongside the credential hint.
    """
    # Arrange
    caplog.set_level(logging.ERROR, logger=HEALTH_LOGGER)
    # Act
    _send_alert_notification("https://e.com", "boom", 3, "ops@example.com", "n@x.com")
    # Assert
    assert "ops@example.com" in caplog.text
