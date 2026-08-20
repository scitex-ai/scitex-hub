"""The URL that is POSTed must be the URL the validator returned.

py/full-ssrf #9058 (critical) fires on slack_service.py:152. The fix landed
earlier: validate_slack_webhook_url enforces https + host EXACTLY
hooks.slack.com and raises otherwise, and _send_webhook calls it before
posting. The alert stayed open anyway, and the reason is the thing this file
pins down.

_send_webhook used to call the validator for its RAISE and then post
``webhook.webhook_url`` a second time:

    validate_slack_webhook_url(webhook.webhook_url)   # checked this read
    ...
    requests.post(webhook.webhook_url, ...)           # sent that read

Two separate reads of a mutable attribute. Safe today, and the same shape as
the external-API proxy bug fixed in #594: the expression that is checked and
the expression that is used are not the same expression. It also left no
dataflow from validator to sink, so no ReturnValue barrier could ever mark it
safe — the alert was structurally unclosable.

These tests assert the binding, not the validator (which has its own tests):
whatever comes back from the validator is what reaches requests.post.
"""

import pytest

django = pytest.importorskip("django")
from django.conf import settings  # noqa: E402

if not settings.configured:  # pragma: no cover - environment guard
    pytest.skip(
        "Django settings not configured in this environment; this test runs in "
        "CI, where pytest-matrix installs .[all,dev] and conftest completes "
        "Django setup.",
        allow_module_level=True,
    )

from django.core.exceptions import ValidationError  # noqa: E402

from apps.infra.integrations_app.services import slack_service as mod  # noqa: E402


class _Webhook:
    """Minimal stand-in for the ORM row _send_webhook reads."""

    def __init__(self, url):
        self.webhook_url = url
        self.channel = ""
        self.username = "scitex"
        self.icon_emoji = ":robot:"
        self.id = 1
        self.connection = None


VALID = "https://hooks.slack.com/services/T000/B000/XXXX"


def test_posted_url_is_the_validator_return_value(monkeypatch):
    """The sink receives the validator's OUTPUT, not a re-read of the row."""
    sentinel = "https://hooks.slack.com/services/SENTINEL"
    monkeypatch.setattr(mod, "validate_slack_webhook_url", lambda url: sentinel)

    posted = {}

    class _Resp:
        status_code = 200
        text = "ok"

    def _fake_post(url, **kwargs):
        posted["url"] = url
        return _Resp()

    monkeypatch.setattr(mod.requests, "post", _fake_post)

    svc = mod.SlackService.__new__(mod.SlackService)
    svc._build_message = lambda event_type, data: {}
    svc._log_error = lambda *a, **k: None

    svc._send_webhook(_Webhook(VALID), "event", {})

    assert posted["url"] == sentinel, (
        "requests.post received the row attribute, not the validated return "
        "value — the checked expression and the sent expression have drifted "
        "apart again"
    )


def test_a_rejected_url_never_reaches_requests_post(monkeypatch):
    """Fail closed: a raise must stop the post, not merely be logged."""

    def _reject(url):
        raise ValidationError("nope")

    monkeypatch.setattr(mod, "validate_slack_webhook_url", _reject)

    called = []
    monkeypatch.setattr(
        mod.requests, "post", lambda *a, **k: called.append(1)
    )

    svc = mod.SlackService.__new__(mod.SlackService)
    svc._build_message = lambda event_type, data: {}
    svc._log_error = lambda *a, **k: None

    result = svc._send_webhook(_Webhook("http://evil.example.net/x"), "event", {})

    assert called == [], "posted despite a rejected webhook URL"
    assert result["success"] is False
