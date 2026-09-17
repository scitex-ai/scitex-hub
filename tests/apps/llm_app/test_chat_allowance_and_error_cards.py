#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chat allowance and provider-error cards: what the user is SHOWN.

Card: hub-chat-free-daily-message-allowance-20260917 (operator decision 7971-7972).
SSOT: docs/product/PRIVATE_BETA_LOGIN_TO_WOW.md §6 — every email-verified real
user gets 10 SciTeX-funded messages/day; "Show selected model, remaining
messages, and reset time before sending"; "At the limit, preserve the draft and
offer BYOK/provider setup or paid usage"; "Never render raw LiteLLM/provider
exceptions", each state saying who must act and offering one primary action.

Boundary: the atomic quota, the spend caps, the kill switch and the classifier
that decides WHICH category a provider failure is are backend (scitex-hub). This
surface consumes `{category, remaining, reset_at, model}` and renders it — so
these tests pin rendering, redaction and the honest unknown state, and never the
accounting.

No database needed.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.template.loader import render_to_string

ALLOWANCE = "chat/partials/chat_allowance.html"
ERROR_CARD = "chat/partials/chat_error_card.html"

# A provider failure as it actually arrives from the library, credentials and all.
RAW_PROVIDER_TEXT = (
    "litellm.AuthenticationError: Incorrect API key provided: sk-live-DEADBEEF1234. "
    "You can find your API key at https://dashboard.example.com/keys"
)


# ---------------------------------------------------------------------------
# the allowance line, before the user sends anything
# ---------------------------------------------------------------------------


def test_an_available_allowance_shows_model_remaining_and_utc_reset():
    html = render_to_string(
        ALLOWANCE,
        {"allowance": {"state": "available", "model": "deepseek-chat",
                       "remaining": 10, "total": 10,
                       "reset_at": "2026-09-18T00:00:00Z", "reset_label": "2026-09-18 00:00 UTC"}},
    )

    assert 'data-chat-allowance="true"' in html
    assert 'data-allowance-state="available"' in html
    assert 'data-model="deepseek-chat"' in html
    assert 'data-remaining="10"' in html
    assert 'data-reset-at="2026-09-18T00:00:00Z"' in html

    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    assert "deepseek-chat" in text, "the selected model is not shown before sending"
    assert "10" in text
    assert "UTC" in text, "the reset time is not stated in UTC"


def test_an_exhausted_allowance_preserves_the_draft_and_offers_a_way_forward():
    html = render_to_string(
        ALLOWANCE,
        {"allowance": {"state": "exhausted", "model": "deepseek-chat",
                       "remaining": 0, "total": 10,
                       "reset_at": "2026-09-18T00:00:00Z", "reset_label": "2026-09-18 00:00 UTC"}},
    )

    assert 'data-allowance-state="exhausted"' in html
    # The surface must not clear or discard what the user typed.
    assert 'data-preserve-draft="true"' in html
    # Two ways forward, both explicit.
    assert 'data-chat-allowance-action="byok"' in html
    assert 'data-chat-allowance-action="paid"' in html


def test_an_unknown_allowance_invents_no_numbers():
    """With no backend payload the surface says so — it does not guess 10 of 10."""
    html = render_to_string(ALLOWANCE, {})

    assert 'data-allowance-state="unknown"' in html
    assert 'data-remaining="' not in html.replace('data-remaining=""', ""), (
        "an unknown allowance must not carry a remaining count"
    )
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    assert not re.search(r"\b10\b", text), (
        f"the unknown state invented an allowance: {text!r}"
    )


# ---------------------------------------------------------------------------
# provider failures become actionable cards, never raw text
# ---------------------------------------------------------------------------

# category -> (who must act, primary action marker)
EXPECTED_CATEGORIES = {
    "insufficient_balance": "scitex",
    "quota_reached": "user",
    "provider_auth": "scitex",
    "rate_limit": "provider",
    "model_unavailable": "user",
    "timeout": "provider",
    "provider_outage": "provider",
}


def _card_html(category: str, **extra) -> str:
    context = {"category": category}
    context.update(extra)
    return render_to_string(ERROR_CARD, context)


def _has_actionable_primary(html: str) -> bool:
    """The primary control is a link OR a named action button.

    Forcing a link would be wrong for "Retry" and "Choose another model", which
    act in place rather than navigate.
    """
    if re.search(r'data-error-action-primary="true"[^>]*data-error-action="[^"]+"', html):
        return True
    return bool(re.search(r'href="[^"#]+"[^>]*data-error-action-primary="true"', html)) or bool(
        re.search(r'data-error-action-primary="true"[^>]*href="[^"#]+"', html)
    )


def test_every_known_category_renders_who_acts_and_one_primary_action():
    for category, actor in EXPECTED_CATEGORIES.items():
        html = _card_html(category)

        assert f'data-error-category="{category}"' in html, category
        assert f'data-error-actor="{actor}"' in html, (
            f"{category} does not say who has to act"
        )
        primary = re.findall(r'data-error-action-primary="true"', html)
        assert len(primary) == 1, (
            f"{category} must offer exactly one primary action, found {len(primary)}"
        )
        assert _has_actionable_primary(html), f"{category} has no actionable control"


def test_no_category_ever_renders_the_raw_provider_message():
    for category in list(EXPECTED_CATEGORIES) + ["something_new_from_the_provider"]:
        html = _card_html(category, provider_message=RAW_PROVIDER_TEXT)

        assert "litellm" not in html.lower(), f"{category} leaked the library name"
        assert "sk-live-DEADBEEF1234" not in html, f"{category} leaked a credential"
        assert "dashboard.example.com" not in html, (
            f"{category} leaked the provider's raw message"
        )
        assert "Incorrect API key provided" not in html


def test_an_unrecognised_category_falls_back_to_a_generic_card():
    html = _card_html("some_new_provider_failure", provider_message=RAW_PROVIDER_TEXT)

    assert 'data-error-category="unknown"' in html
    assert 'data-error-actor=' in html
    assert _has_actionable_primary(html)


def test_a_rate_limited_card_states_when_to_retry():
    html = _card_html("rate_limit", retry_after="60 seconds")

    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    assert "60 seconds" in text, "a rate limit must say when retrying is possible"


# ---------------------------------------------------------------------------
# the stylesheets these surfaces depend on must actually be LOADED
# ---------------------------------------------------------------------------

SHELL_STYLES_ENTRY = "static/shared/ts/head-styles-shell.ts"
ALLOWANCE_CSS = "static/shared/css/components/chat-allowance.css"


def test_the_allowance_stylesheet_is_imported_by_the_shell_styles_entry():
    """A rule in a stylesheet nobody loads is a rule no browser ever sees.

    Same trap as the landing hero, where new rules went into a file no page
    referenced. The shell bundles its styles through head-styles-shell.ts, so the
    import has to be there.
    """
    repo = Path(__file__).resolve().parents[3]
    entry = repo / SHELL_STYLES_ENTRY
    assert entry.is_file(), f"{SHELL_STYLES_ENTRY} moved — update this guard"

    assert ALLOWANCE_CSS in entry.read_text(), (
        f"{ALLOWANCE_CSS} is not imported by {SHELL_STYLES_ENTRY}; its rules "
        "would never reach a browser"
    )
    assert (repo / ALLOWANCE_CSS).is_file()


def test_the_two_surfaces_are_included_by_the_chat_pane():
    """Rendered only if the pane includes them — otherwise they are dead markup."""
    repo = Path(__file__).resolve().parents[3]
    pane = repo / "templates/global_base_partials/workspace_chat_pane.html"
    pane_html = pane.read_text()

    assert 'include "chat/partials/chat_allowance.html"' in pane_html, (
        "the allowance line is not rendered by the chat pane"
    )


# EOF
