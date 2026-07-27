"""Server-side allowlist validator for outbound Slack webhook URLs.

Closes a full server-side request forgery (CodeQL ``py/full-ssrf``): an
authenticated user supplies ``webhook_url`` via the ``slack_configure`` view,
which flows unvalidated into ``requests.post(webhook.webhook_url, ...)`` inside
``SlackService._send_webhook``. Because ``SlackWebhook.objects.create(...)``
bypasses the model's ``URLField`` validation, the scheme and host are fully
attacker-controlled, so the server can be coerced into POSTing to arbitrary
internal targets (cloud metadata ``169.254.169.254``, ``localhost`` services,
internal Gitea/SLURM) and leaking the response body into a user-readable log.

This module is deliberately PURE and dependency-light (only ``urllib.parse``
plus Django's ``ValidationError`` type) so it can be unit-tested WITHOUT a
Django database. It is the single source of truth for "is this a real Slack
webhook URL?" and is enforced fail-closed at both the create and the send
boundary.

Allowlist rule (exact-host, https-only):
  * scheme MUST be exactly ``https`` (never ``http`` — no cleartext, and http
    would also admit internal-IP targets).
  * hostname (lower-cased) MUST be EXACTLY ``hooks.slack.com``.

Exact equality — never a substring/``startswith``/suffix check — is what makes
this safe. It rejects, by construction:
  * suffix spoof   ``hooks.slack.com.evil.com``
  * userinfo spoof ``hooks.slack.com@evil.com`` (urlparse.hostname == evil.com)
  * every internal-IP / localhost / metadata target.
"""

from __future__ import annotations

from urllib.parse import urlparse

from django.core.exceptions import ValidationError

# The ONE legitimate host for Slack incoming webhooks. Real webhooks are always
# https://hooks.slack.com/services/T.../B.../XXXX, so legitimate use is unaffected.
_ALLOWED_HOST = "hooks.slack.com"
_ALLOWED_SCHEME = "https"


def validate_slack_webhook_url(url: str) -> str:
    """Return ``url`` unchanged iff it is an https://hooks.slack.com/... URL.

    Args:
        url: The user-supplied webhook URL to check.

    Returns:
        The same ``url`` on success (so callers can inline the check).

    Raises:
        ValidationError: If ``url`` is empty/not-a-string, is not ``https``, or
            its host is not EXACTLY ``hooks.slack.com``. Never falls back to
            sending — the caller must treat a raise as "do not post".
    """
    if not url or not isinstance(url, str):
        raise ValidationError("Slack webhook URL is required.")

    try:
        parsed = urlparse(url)
    except (ValueError, TypeError) as exc:
        raise ValidationError("Slack webhook URL could not be parsed.") from exc

    if parsed.scheme != _ALLOWED_SCHEME:
        raise ValidationError(
            "Slack webhook URL must use https (got "
            f"'{parsed.scheme or 'no scheme'}')."
        )

    # ``hostname`` is the parsed authority host, lower-cased and with any
    # ``user:pass@`` userinfo and ``:port`` stripped — so the userinfo spoof
    # ``hooks.slack.com@evil.com`` correctly resolves to ``evil.com`` here.
    host = (parsed.hostname or "").lower()
    if host != _ALLOWED_HOST:
        raise ValidationError(
            f"Slack webhook host must be exactly '{_ALLOWED_HOST}' (got "
            f"'{host or 'no host'}'). This blocks SSRF to internal targets."
        )

    return url
