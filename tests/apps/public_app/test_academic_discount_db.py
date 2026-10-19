#!/usr/bin/env python3
# -*- coding: utf-8 -*--
"""Academic discount lane (operator CCT4555): database halves.

Runs on the CI pytest matrix (postgres), NOT in containers without one —
cf. tests/apps/auth_app/test_pending_signup_lifecycle.py. The pure halves
(checker, funnel_plan rule, grant logic) run everywhere in
test_academic_discount.py.

Covered here, against the real ORM:
* the grant persists the 1:1 row, exactly once, for an academic address;
* general addresses grant nothing;
* ``mark_verified`` (email signup) and ``begin_social_signup`` grant from
  the proven address — and never touch the funnel's plan choice;
* a revoked grant is never resurrected by re-verification.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from apps.infra.auth_app.models import PendingSignup
from apps.infra.auth_app.onboarding import (
    begin_social_signup,
    mark_verified,
)
from apps.infra.public_app.billing_models import UserDiscount
from apps.infra.public_app.services.academic_discount import (
    grant_academic_discount,
    user_has_academic_discount,
)

pytestmark = pytest.mark.django_db


def _user(email: str, active: bool = False) -> User:
    return User.objects.create_user(
        username=email.split("@")[0].replace(".", "_") + "_acad",
        email=email,
        password="Gx7-quiet-harbour-42",
        is_active=active,
    )


def test_grant_persists_one_row_for_academic_email():
    user = _user("taro@u-tokyo.ac.jp")
    row = grant_academic_discount(user, "taro@u-tokyo.ac.jp")
    assert row is not None
    assert row.code == "ACADEMIC50"
    assert row.verified_email == "taro@u-tokyo.ac.jp"
    assert row.basis_domain == "u-tokyo.ac.jp"
    assert row.is_active is True
    assert UserDiscount.objects.filter(user=user).count() == 1
    assert user_has_academic_discount(user) is True


def test_grant_is_idempotent():
    user = _user("staff@riken.jp")
    first = grant_academic_discount(user, "staff@riken.jp")
    second = grant_academic_discount(user, "staff@riken.jp")
    assert first is not None and second is not None
    assert first.pk == second.pk
    assert UserDiscount.objects.filter(user=user).count() == 1


def test_grant_returns_none_for_general_email():
    user = _user("taro@gmail.com")
    assert grant_academic_discount(user, "taro@gmail.com") is None
    assert UserDiscount.objects.filter(user=user).count() == 0
    assert user_has_academic_discount(user) is False


def test_mark_verified_grants_without_touching_the_plan():
    user = _user("hanako@keio.ac.jp")
    PendingSignup.objects.create(
        user=user, email=user.email, plan="subscription-free"
    )
    row = mark_verified(user, source="email")
    assert row.pricing_id == "subscription-free"  # the funnel decides later
    grant = UserDiscount.objects.filter(user=user).first()
    assert grant is not None and grant.is_active is True


def test_mark_verified_skips_general_addresses():
    user = _user("taro@gmail.com")
    PendingSignup.objects.create(
        user=user, email=user.email, plan="subscription-free"
    )
    mark_verified(user, source="email")
    assert UserDiscount.objects.filter(user=user).count() == 0


def test_reverification_never_resurrects_a_revocation():
    user = _user("taro@u-tokyo.ac.jp")
    grant = grant_academic_discount(user, "taro@u-tokyo.ac.jp")
    assert grant is not None
    grant.status = UserDiscount.Status.REVOKED
    grant.save(update_fields=["status", "updated_at"])
    PendingSignup.objects.create(
        user=user, email=user.email, plan="subscription-free"
    )
    mark_verified(user, source="email")
    grant.refresh_from_db()
    assert grant.status == UserDiscount.Status.REVOKED
    assert user_has_academic_discount(user) is False


def test_begin_social_signup_grants_for_academic_address():
    user = _user("prof@tohoku.ac.jp", active=True)
    begin_social_signup(user, provider="google")
    grant = UserDiscount.objects.filter(user=user).first()
    assert grant is not None and grant.is_active is True
