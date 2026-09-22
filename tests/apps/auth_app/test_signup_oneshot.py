#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot signup (account + card, one page): token, JSON exit, verify-skip.

Uses no Stripe network: the intent mint is exercised only as far as the
``open: False`` closedown path (no keys in test env).
"""
import json

import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.mark.django_db
def test_signup_card_token_roundtrip():
    from apps.infra.auth_app.signup_card import (
        resolve_signup_card_token,
    )
    from apps.infra.auth_app.signup_card import (
        mint_signup_card_token,
    )

    user = User.objects.create_user(username="tok-probe", email="t@example.invalid")
    token = mint_signup_card_token(user, "seti_123")
    found, intent = resolve_signup_card_token(token)
    assert found is not None and found.pk == user.pk and intent == "seti_123"
    # Tampered token, wrong intent binding, and garbage all refuse.
    bad_user, _ = resolve_signup_card_token(token + "x")
    assert bad_user is None
    found2, intent2 = resolve_signup_card_token(
        mint_signup_card_token(user, "seti_999")
    )
    assert intent2 == "seti_999" and found2 is not None
    assert resolve_signup_card_token("garbage")[0] is None
    assert resolve_signup_card_token("")[0] is None


@pytest.mark.django_db
def test_signup_ajax_exit_is_json_with_card_key():
    from apps.infra.auth_app.views.authentication import _signup_done

    class Req:
        headers = {"X-Requested-With": "XMLHttpRequest"}

    user = User.objects.create_user(username="exit-probe", email="e@example.invalid")
    resp = _signup_done(Req(), "e@example.invalid", user=user)
    assert resp.status_code == 200
    data = json.loads(resp.content.decode())
    assert data["ok"] is True
    assert data["verify_url"].startswith("/auth/verify-email/")
    # No Stripe keys in test env: closedown path, account-only.
    assert data["card"] == {"open": False}


@pytest.mark.django_db
def test_signup_ajax_collision_has_no_card_payload():
    from apps.infra.auth_app.views.authentication import _signup_done

    class Req:
        headers = {"X-Requested-With": "XMLHttpRequest"}

    resp = _signup_done(Req(), "someone@example.invalid")
    data = json.loads(resp.content.decode())
    assert data["ok"] is True and "card" not in data


@pytest.mark.django_db
def test_mark_verified_without_card_stays_at_payment():
    from apps.infra.auth_app.onboarding import mark_verified, step_for

    user = User.objects.create_user(username="nopay-probe", email="n@example.invalid")
    row = mark_verified(user, source="email")
    assert row is not None and step_for(user) == "payment"


@pytest.mark.django_db
def test_confirm_card_anonymous_without_token_refused():
    c = Client()
    r = c.post(
        "/billing/confirm-card/",
        data=json.dumps({"setup_intent_id": "seti_nope"}),
        content_type="application/json",
    )
    assert r.status_code == 403


# EOF


@pytest.mark.django_db
def test_sender_down_json_names_contact():
    from apps.infra.auth_app.views.authentication import _sender_down

    class Req:
        headers = {"X-Requested-With": "XMLHttpRequest"}

    resp = _sender_down(Req())
    assert resp.status_code == 502
    data = json.loads(resp.content.decode())
    assert data["ok"] is False
    assert "info@scitex.ai" in data["error"]
    assert "check your inbox" not in data["error"].lower()


@pytest.mark.django_db
def test_sender_down_banner_names_contact():
    from apps.infra.auth_app.views.authentication import _sender_down

    class Req:
        headers = {}
        method = "POST"

    from django.contrib.messages.storage.cookie import CookieStorage

    req = Req()
    req.COOKIES = {}
    req._messages = CookieStorage(req)
    resp = _sender_down(req)
    assert resp.status_code == 200
    assert b"info@scitex.ai" in resp.content
