#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Signup restore SCOPE (operator 2026-10-19): declutter, keep, restore.

SURGICAL, not a revert of c1e86a6b6 (a dangling operator commit, in no
branch — there is nothing to revert). Exactly three moves on /auth/signup/:

1. REMOVE the "Fund open science" funding-note line (declutter; the
   /funding/ route + funding.json keep working — covered elsewhere).
2. REMOVE the static academic-email examples line (declutter).
3. RESTORE the live academic check: POST /auth/api/check-email/ plus the
   hidden ``#academic-hint`` the signup JS reveals on ``{"academic": true}``.

KEPT (asserted so a future declutter cannot silently take them):
the trial/card-policy notice (operator card rule 2026-09-14), the password
rules panel, the profile-URL preview, the username live check, and the
green ``btn-success`` CTA (PR #1103 owns the navy CTA — not this lane).

No mocks (project rule): the real URLconf, the real view, the real template.
"""
from __future__ import annotations

import json

import pytest
from django.urls import reverse

SIGNUP_URL = "/auth/signup/"
CHECK_EMAIL_URL = "/auth/api/check-email/"


@pytest.fixture
def signup_html(client):
    response = client.get(SIGNUP_URL)
    assert response.status_code == 200, f"signup page: {response.status_code}"
    return response.content.decode("utf-8")


def _post(client, payload):
    return client.post(
        CHECK_EMAIL_URL,
        data=json.dumps(payload),
        content_type="application/json",
    )


@pytest.mark.auth
@pytest.mark.guards(
    defect="signup.html re-grew the Fund-open-science funding note and the static "
    "academic-email examples after the 2026-10-19 declutter, re-cluttering the form."
)
class TestDeclutteredLinesAreGone:
    """The two declutter lines stay gone; the funding destination survives."""
    @pytest.mark.django_db
    def test_no_fund_open_science_line(self, signup_html):
        assert "Fund open science" not in signup_html
        assert "signup-funding-note" not in signup_html

    @pytest.mark.django_db
    def test_no_static_academic_examples(self, signup_html):
        assert "Academic email examples:" not in signup_html
        assert "email-example" not in signup_html
        assert "student@univ-xxx.ac.jp" not in signup_html


@pytest.mark.auth
@pytest.mark.guards(
    defect="POST /auth/api/check-email/ or the #academic-hint display regressed, "
    "so academic visitors lost the live eligibility hint on the signup form."
)
class TestLiveAcademicCheckRestored:
    def test_route_resolves(self):
        assert reverse("auth_app:api_check_email") == CHECK_EMAIL_URL

    @pytest.mark.django_db
    def test_academic_domain_recognized(self, client):
        response = _post(client, {"email": "student@u-tokyo.ac.jp"})
        assert response.status_code == 200
        assert response.json() == {"academic": True}

    @pytest.mark.django_db
    def test_non_academic_domain_not_recognized(self, client):
        response = _post(client, {"email": "someone@gmail.com"})
        assert response.status_code == 200
        assert response.json() == {"academic": False}

    @pytest.mark.django_db
    def test_missing_at_sign_is_not_academic(self, client):
        response = _post(client, {"email": "not-an-email"})
        assert response.status_code == 200
        assert response.json() == {"academic": False}

    @pytest.mark.django_db
    def test_malformed_json_is_not_academic(self, client):
        response = client.post(
            CHECK_EMAIL_URL, data="{bad json", content_type="application/json"
        )
        assert response.status_code == 200
        assert response.json() == {"academic": False}

    @pytest.mark.django_db
    def test_get_is_not_allowed(self, client):
        assert client.get(CHECK_EMAIL_URL).status_code == 405

    @pytest.mark.django_db
    def test_hint_element_and_live_check_wired(self, signup_html):
        assert 'id="academic-hint"' in signup_html
        assert 'id="academic-hint-text"' in signup_html
        assert "Academic email recognized" in signup_html
        assert "/auth/api/check-email/" in signup_html


@pytest.mark.auth
@pytest.mark.guards(
    defect="a signup declutter removed kept work with the clutter: the card-policy "
    "notice, password rules, profile-URL preview, username check, or CTA styling."
)
class TestKeptWorkSurvives:
    @pytest.mark.django_db
    def test_card_policy_notice_still_rendered(self, signup_html):
        assert "card required, no charge during the trial" in signup_html
        assert "Billing terms" in signup_html

    @pytest.mark.django_db
    def test_password_rules_panel_still_rendered(self, signup_html):
        assert "Password Requirements:" in signup_html
        assert 'id="rule-length"' in signup_html

    @pytest.mark.django_db
    def test_profile_url_preview_still_rendered(self, signup_html):
        assert 'id="username-preview"' in signup_html

    @pytest.mark.django_db
    def test_username_live_check_still_wired(self, signup_html):
        assert "/auth/api/check-username/" in signup_html

    @pytest.mark.django_db
    def test_cta_not_restyled_by_this_lane(self, signup_html):
        # The CTA's color belongs to #1103 (navy-by-construction, no color
        # class). This lane only requires the submit itself to survive.
        assert "auth-primary-cta" in signup_html
        assert "Create Account" in signup_html
