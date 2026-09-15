#!/usr/bin/env python3
"""Non-DB tests for the password-reset on-screen feedback helper.

The helper (apps/infra/auth_app/views/password_reset.py::_reset_feedback) is
the piece the operator asked for (2026-09-13): in DEBUG (this dev server) the
real outcome is shown so a mail-delivery problem is visible, not silent; in
production (DEBUG=False) the single indistinguishable generic message is kept
so a caller cannot probe whether an address is registered or whether a send
succeeded (the enumeration-oracle guard).

The helper calls ``messages.success/warning/error(request, text)``, which
writes into ``request._messages``. A tiny recording stub for ``_messages``
keeps this deterministic and free of any session / DB dependency, so it runs
locally (no Postgres) as well as in CI. The full view path (real User lookup,
real send) is covered by the django_db suite
test_password_reset_non_enumerating.py.
"""

import pytest
from django.contrib.messages.constants import DEBUG, ERROR, INFO, SUCCESS, WARNING
from django.test import RequestFactory


class _Recording:
    """Stands in for request._messages.

    Django's messages API (``messages.success(request, text)``) calls
    ``request._messages.add(level, message, extra_tags)`` — so the storage
    interface is ``add``, not ``success``. Records (level, text) pairs."""

    def __init__(self):
        self.queued = []

    def add(self, level, message, extra_tags=()):
        self.queued.append((level, message))


def _request():
    req = RequestFactory().post("/auth/forgot-password/", {"email": "x"})
    req._messages = _Recording()
    return req


LEVEL_TAG = {
    DEBUG: "debug",
    INFO: "info",
    SUCCESS: "success",
    WARNING: "warning",
    ERROR: "error",
}


@pytest.mark.parametrize(
    "debug,registered,sent,level_tag,needle",
    [
        # PRODUCTION: one generic message for every outcome (oracle guard).
        (False, True, True, "success", "If an account with this email exists"),
        (False, True, False, "success", "If an account with this email exists"),
        (False, False, False, "success", "If an account with this email exists"),
        # DEBUG: the real outcome, levelled, so mail problems are visible.
        (True, True, True, "success", "sent to ywatanabe@scitex.ai"),
        (True, True, False, "error", "Send FAILED for ywatanabe@scitex.ai"),
        (True, False, False, "warning", "No account for ywatanabe@scitex.ai"),
    ],
)
def test_reset_feedback_debug_vs_production(settings, debug, registered, sent, level_tag, needle):
    from apps.infra.auth_app.views.password_reset import _reset_feedback

    settings.DEBUG = debug
    request = _request()
    _reset_feedback(request, "ywatanabe@scitex.ai", registered=registered, sent=sent)

    queued = request._messages.queued
    assert len(queued) == 1
    assert LEVEL_TAG[queued[0][0]] == level_tag
    assert needle in queued[0][1]


def test_production_never_names_the_address_or_outcome(settings):
    """The generic production message must not reveal the address or outcome."""
    from apps.infra.auth_app.views.password_reset import _reset_feedback

    settings.DEBUG = False
    for registered, sent in [(True, True), (True, False), (False, False)]:
        request = _request()
        _reset_feedback(request, "secret@scitex.ai", registered=registered, sent=sent)
        text = request._messages.queued[0][1]
        assert "secret@scitex.ai" not in text
        assert "sent to" not in text.lower()
        assert "no account" not in text.lower()
