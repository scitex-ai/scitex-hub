"""Exploit-regression barrier for the Slack-webhook full-SSRF (CodeQL py/full-ssrf).

An authenticated user's ``webhook_url`` flows from the ``slack_configure`` view
into ``requests.post(webhook.webhook_url, ...)`` inside
``SlackService._send_webhook``. ``SlackWebhook.objects.create(...)`` bypasses the
model's ``URLField`` validation, so scheme + host were fully attacker-controlled
— the server could be coerced into POSTing to internal targets (cloud metadata
``169.254.169.254``, ``localhost`` services, internal Gitea/SLURM) and leaking
the response body into a user-readable log.

The fix is a PURE, https-only, EXACT-host allowlist in
``apps.infra.integrations_app.services.webhook_security.validate_slack_webhook_url``,
enforced fail-closed at both create-time and send-time. These tests exercise the
pure validator directly, so they need NO Django database and prove the guard
both ways (accept real Slack URLs, reject every SSRF vector). Exact-host equality
is what defeats the suffix (``hooks.slack.com.evil.com``) and userinfo
(``hooks.slack.com@evil.com``) spoofs, so both are asserted explicitly.
"""
from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from apps.infra.integrations_app.services.webhook_security import (
    validate_slack_webhook_url,
)

pytestmark = pytest.mark.security


# Every one of these must be REJECTED. Each maps to a concrete SSRF/spoof vector.
REJECTED_URLS = [
    "http://hooks.slack.com/services/x",          # cleartext http (not https)
    "https://evil.com/x",                          # wrong host entirely
    "http://169.254.169.254/latest/meta-data/",    # cloud metadata endpoint
    "http://localhost:6379/",                      # internal service (redis)
    "http://127.0.0.1:8000/admin/",                # loopback service
    "https://hooks.slack.com.evil.com/x",          # suffix spoof
    "https://hooks.slack.com@evil.com/x",          # userinfo spoof -> host=evil.com
    "https://HOOKS.SLACK.COM.evil.com/x",          # case-mixed suffix spoof
    "file:///etc/passwd",                          # non-http scheme, local file
    "gopher://127.0.0.1:6379/_INFO",               # gopher SSRF vector
    "",                                            # empty
    None,                                          # missing / not a string
]


@pytest.mark.parametrize("bad_url", REJECTED_URLS)
def test_rejects_non_slack_and_ssrf_urls(bad_url):
    """Every SSRF vector and non-Slack host raises ValidationError (fail-closed)."""
    # Arrange
    validator = validate_slack_webhook_url
    # Act
    raises = pytest.raises(ValidationError)
    # Assert
    with raises:
        validator(bad_url)


def test_accepts_real_slack_incoming_webhook():
    """A legitimate Slack incoming webhook passes and is returned unchanged."""
    # Arrange
    url = "https://hooks.slack.com/services/T000/B000/XXXXXXXX"
    # Act
    result = validate_slack_webhook_url(url)
    # Assert
    assert result == url


def test_accepts_exact_host_case_insensitively():
    """Host comparison is case-insensitive for the REAL host (not the spoof)."""
    # Arrange
    url = "https://Hooks.Slack.Com/services/T000/B000/XXXXXXXX"
    # Act
    result = validate_slack_webhook_url(url)
    # Assert
    assert result == url
