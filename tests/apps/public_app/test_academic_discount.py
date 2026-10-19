#!/usr/bin/env python3
# -*- coding: utf-8 -*--
"""Academic discount lane (operator CCT4555): email→academic→50%-off.

Runs WITHOUT a database and WITHOUT Django apps (this container has no
postgres — cf. tests/apps/auth_app/test_pending_signup_lifecycle.py). The
DB-backed halves (grant persistence, mark_verified wiring, the migration)
live in test_academic_discount_db.py and run on the CI matrix.

Covered here:
* the canonical checker (accounts-owned, stdlib-only) over a truth table,
  including lookalike domains that must NOT match;
* the single-definition guard: exactly one ``JAPANESE_ACADEMIC_DOMAINS = [``
  in the tree (a second copy is how the flags drifted apart before);
* ``funnel_plan`` rule 2: a grant-holding account still on the funnel
  default resolves the academic row; every explicit or recorded choice wins;
* grant logic against a stubbed row store (create / reuse / revoked-stays-
  revoked / non-academic-never).
"""

from __future__ import annotations

import re
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ACCOUNTS_ACADEMIC = PROJECT_ROOT / "apps/infra/accounts_app/academic.py"
ACCOUNTS_PROFILE = PROJECT_ROOT / "apps/infra/accounts_app/models/profile.py"
AUTH_MODELS = PROJECT_ROOT / "apps/infra/auth_app/models.py"

sys.path.insert(0, str(PROJECT_ROOT))

from apps.infra.accounts_app.academic import (  # noqa: E402
    JAPANESE_ACADEMIC_DOMAINS,
    is_japanese_academic_email,
)


# ---------------------------------------------------------------------------
# the checker
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "email",
    [
        "taro@u-tokyo.ac.jp",
        "hanako@dept.kyoto-u.ac.jp",
        "staff@riken.jp",
        "x@aist.go.jp",
        "x@jaxa.jp",
        "x@waseda.jp",
        "x@keio.ac.jp",
        "x@sophia.ac.jp",  # any .ac.jp, not just the named ones
        "UPPER@RIKEN.JP",
    ],
)
def test_academic_addresses_pass(email):
    assert is_japanese_academic_email(email) is True


@pytest.mark.parametrize(
    "email",
    [
        "taro@gmail.com",
        "taro@yahoo.co.jp",
        "taro@example.ac.jp.evil.com",  # academic string, wrong side of the dot
        "taro@fakexac.jp",  # endswith without the dot boundary
        "taro@ac-jp.example.com",
        "not-an-email",
        "",
        None,
    ],
)
def test_non_academic_addresses_fail(email):
    assert is_japanese_academic_email(email) is False


# ---------------------------------------------------------------------------
# single definition (the drift guard)
# ---------------------------------------------------------------------------


def _occurrences(path: Path, needle: str) -> int:
    return path.read_text(encoding="utf-8").count(needle)


def test_exactly_one_domain_list_definition():
    total = sum(
        _occurrences(p, "JAPANESE_ACADEMIC_DOMAINS = [")
        for p in (ACCOUNTS_ACADEMIC, ACCOUNTS_PROFILE, AUTH_MODELS)
    )
    assert total == 1, "a second checker copy is how the flags drifted before"


def test_both_profiles_reexport_the_canonical_checker():
    for path in (ACCOUNTS_PROFILE, AUTH_MODELS):
        text = path.read_text(encoding="utf-8")
        assert "apps.infra.accounts_app.academic import" in text.replace(
            "from .academic import", "apps.infra.accounts_app.academic import"
        ), path


# ---------------------------------------------------------------------------
# funnel_plan rule 2 (Django-free: stub the onboarding authority read)
# ---------------------------------------------------------------------------

PRICE_IDS = {
    "subscription-student": "price_student",
    "subscription-general": "price_general",
}


def _academic_user():
    return SimpleNamespace(
        pk=7, discount=SimpleNamespace(is_active=True)
    )


def _plain_user():
    return SimpleNamespace(pk=8, discount=SimpleNamespace(is_active=False))


@pytest.fixture()
def funnel_plan(monkeypatch):
    """Real funnel_plan with only the DB-backed authority read stubbed."""
    from apps.infra.accounts_app import payment_step

    state = {"pricing_id": ""}

    def fake_state_for(user):
        return SimpleNamespace(pricing_id=state["pricing_id"])

    stub = types.ModuleType("apps.infra.auth_app.onboarding")
    stub.state_for = fake_state_for
    monkeypatch.setitem(
        sys.modules, "apps.infra.auth_app.onboarding", stub
    )
    return payment_step.funnel_plan, state


def test_academic_grant_on_default_resolves_student_row(funnel_plan):
    plan, _ = funnel_plan
    row = plan(_academic_user(), price_ids=dict(PRICE_IDS))
    assert row is not None and row["id"] == "subscription-student"


def test_recorded_general_plan_wins_over_grant(funnel_plan):
    plan, state = funnel_plan
    state["pricing_id"] = "subscription-general"
    row = plan(_academic_user(), price_ids=dict(PRICE_IDS))
    assert row is not None and row["id"] == "subscription-general"


def test_explicit_request_wins_over_grant(funnel_plan):
    plan, _ = funnel_plan
    row = plan(
        _academic_user(),
        requested_id="subscription-general",
        price_ids=dict(PRICE_IDS),
    )
    assert row is not None and row["id"] == "subscription-general"


def test_no_grant_no_guess_on_multi_row_allowlist(funnel_plan):
    plan, _ = funnel_plan
    assert plan(_plain_user(), price_ids=dict(PRICE_IDS)) is None


def test_student_unchargeable_falls_back_to_single_row(funnel_plan):
    plan, _ = funnel_plan
    row = plan(
        _academic_user(), price_ids={"subscription-general": "price_general"}
    )
    assert row is not None and row["id"] == "subscription-general"


# ---------------------------------------------------------------------------
# grant logic (stubbed row store — persistence itself is a DB test)
# ---------------------------------------------------------------------------


def _grant_module(stub_row=None, created=True):
    """The real grant module with only the Django model stubbed."""
    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        from apps.infra.public_app.services import academic_discount as ad

        store = types.SimpleNamespace(get_or_create_calls=[])

        class FakeManager:
            def get_or_create(self, user, defaults):
                store.get_or_create_calls.append((user, defaults))
                if stub_row is not None:
                    return stub_row, False
                row = SimpleNamespace(
                    is_active=True,
                    code=defaults["code"],
                    verified_email=defaults["verified_email"],
                    basis_domain=defaults.get("basis_domain", ""),
                )
                return row, created

        stub_models = types.ModuleType(
            "apps.infra.public_app.billing_models"
        )

        class FakeUserDiscount:
            objects = FakeManager()

        stub_models.UserDiscount = FakeUserDiscount
        with mock.patch.dict(
            sys.modules,
            {"apps.infra.public_app.billing_models": stub_models},
        ):
            yield ad, store

    return _ctx()


def test_grant_creates_row_for_academic_email():
    with _grant_module() as (ad, store):
        user = SimpleNamespace(pk=11)
        row = ad.grant_academic_discount(user, "taro@u-tokyo.ac.jp")
        assert row is not None
        assert row.code == "ACADEMIC50"
        assert row.basis_domain == "u-tokyo.ac.jp"
        assert len(store.get_or_create_calls) == 1


def test_grant_returns_none_for_general_email():
    with _grant_module() as (ad, store):
        assert (
            ad.grant_academic_discount(
                SimpleNamespace(pk=12), "taro@gmail.com"
            )
            is None
        )
        assert store.get_or_create_calls == []


def test_grant_never_resurrects_a_revoked_row():
    revoked = SimpleNamespace(is_active=False)
    with _grant_module(stub_row=revoked) as (ad, _):
        assert (
            ad.grant_academic_discount(
                SimpleNamespace(pk=13), "staff@riken.jp"
            )
            is None
        )


def test_eligibility_read_is_safe_for_nobody():
    from apps.infra.public_app.services import academic_discount as ad

    assert ad.user_has_academic_discount(None) is False
    assert ad.user_has_academic_discount(SimpleNamespace(pk=None)) is False
    assert (
        ad.user_has_academic_discount(SimpleNamespace(pk=1)) is False
    )  # no .discount


# ---------------------------------------------------------------------------
# payment-step surface (source-level: the template needs a Django render env)
# ---------------------------------------------------------------------------


def test_payment_step_names_the_grant_when_present():
    template = (
        PROJECT_ROOT
        / "apps/infra/accounts_app/templates/accounts_app/payment_step.html"
    ).read_text(encoding="utf-8")
    assert "academic_discount" in template
    assert 'data-payment-disclosure="academic-discount"' in template
    # display-only: the flag must not smuggle a second plan decision in
    assert template.count("academic_discount") <= 3
