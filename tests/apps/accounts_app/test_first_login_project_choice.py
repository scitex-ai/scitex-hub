#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""First verified login must ASK which project, never assume one.

Card: hub-first-login-project-workspace-onboarding-20260917 (Hub-only slice).
SSOT: docs/product/PRIVATE_BETA_LOGIN_TO_WOW.md — §3 ("The primary action is
Create project … The sample exists only after explicit selection") and the
non-negotiable rule "Real users never receive a silently created or selected
example project."

Today the inverse is true: apps/infra/accounts_app/signals.py creates a
`dotfiles` project on user creation and adopts it (or the oldest non-home
project) as `profile.last_active_repository`, so a newly verified user is put
inside a project they never chose — and for a user who owns nothing else, that
project is the shell-config one.

Contract under construction:
  A. the pure selection rule — only an explicitly chosen project may become active;
  B. the first-login surface — three explicit choices + the workspace facts;
  C. (database) a brand-new verified user owns no project and has no active
     project until they choose.

Sections A and B need no database; section C is marked for the database gate.
"""

from __future__ import annotations

import pytest
from django.template.loader import render_to_string
from django.test import TestCase

# Literal action keys: the surface contract is asserted as strings, so section B
# fails on the missing SURFACE rather than on a missing import.
CREATE_PROJECT = "create-project"
IMPORT_PROJECT_OR_FILES = "import-project"
GUIDED_SAMPLE = "guided-sample"
EXPECTED_ACTIONS = (CREATE_PROJECT, IMPORT_PROJECT_OR_FILES, GUIDED_SAMPLE)


def _onboarding():
    """The module this slice introduces (imported lazily so B can run without it)."""
    from apps.infra.accounts_app import onboarding

    return onboarding


# ---------------------------------------------------------------------------
# A. the pure selection rule (no database, runs anywhere)
# ---------------------------------------------------------------------------


class FakeProject:
    """Minimal stand-in for a Project row: the rule only reads these fields."""

    def __init__(self, pk: int, slug: str, *, is_home: bool = False, is_example: bool = False):
        self.pk = pk
        self.slug = slug
        self.is_home = is_home
        self.is_example = is_example


def test_an_explicitly_chosen_project_becomes_active():
    onboarding = _onboarding()
    chosen = FakeProject(7, "my-analysis")
    projects = [FakeProject(1, "dotfiles", is_home=True), chosen]

    assert onboarding.resolve_active_project(projects, chosen_project_id=7) is chosen


def test_no_choice_leaves_no_active_project_even_when_projects_exist():
    """"Never silently select": with no explicit choice there is NO active project.

    This is the exact behaviour that is broken today — the signal adopts the
    home/dotfiles project (or the oldest non-home project) instead.
    """
    onboarding = _onboarding()
    dotfiles = FakeProject(1, "dotfiles", is_home=True)
    example = FakeProject(2, "default-project", is_example=True)

    assert onboarding.resolve_active_project(
        [dotfiles, example], chosen_project_id=None
    ) is None


def test_an_example_project_is_never_adopted_without_being_chosen():
    onboarding = _onboarding()

    assert onboarding.resolve_active_project(
        [FakeProject(2, "default-project", is_example=True)], chosen_project_id=None
    ) is None


def test_a_choice_the_user_does_not_own_is_not_used():
    onboarding = _onboarding()
    owned = [FakeProject(1, "dotfiles", is_home=True)]

    assert onboarding.resolve_active_project(owned, chosen_project_id=99) is None


def test_a_user_with_no_explicit_choice_is_asked_to_choose():
    onboarding = _onboarding()

    assert onboarding.needs_project_choice(has_explicit_choice=False) is True
    assert onboarding.needs_project_choice(has_explicit_choice=True) is False


def test_the_declared_actions_match_the_surface_contract():
    onboarding = _onboarding()

    keys = tuple(a.key for a in onboarding.first_login_actions())
    assert keys == EXPECTED_ACTIONS


# ---------------------------------------------------------------------------
# B. the first-login surface: three explicit choices, no preselection
# ---------------------------------------------------------------------------


def test_first_login_offers_exactly_three_choices_with_one_primary():
    onboarding = _onboarding()
    actions = onboarding.first_login_actions()

    assert tuple(a.key for a in actions) == EXPECTED_ACTIONS
    primary = [a for a in actions if a.is_primary]
    assert len(primary) == 1, "exactly one primary action — Create project"
    assert primary[0].key == CREATE_PROJECT
    # Nothing is preselected, so nothing can run before the user clicks.
    assert all(a.is_preselected is False for a in actions)


def test_the_welcome_screen_states_the_workspace_facts_and_the_three_choices():
    """Renders the SHIPPED context against the SHIPPED template, so a drift
    between `first_login_context()` and the surface fails here."""
    onboarding = _onboarding()
    context = onboarding.first_login_context()
    context["linux_username"] = "researcher-01"

    html = render_to_string("onboarding/first_login_welcome.html", context)

    for key in EXPECTED_ACTIONS:
        assert f'data-action="{key}"' in html, f"missing explicit choice {key}"

    # The primary choice is the creating path, and it points at the real page.
    assert 'data-action="create-project"' in html
    assert "first-login-action--primary" in html

    # The workspace facts the user must be told before choosing.
    assert "NAS-02" in html
    assert "32" in html and "GB" in html
    assert "storage" in html.lower() and "not RAM" in html

    # No active project may be rendered for a user who has not chosen one.
    assert 'data-active-project="' not in html


# ---------------------------------------------------------------------------
# C. database: a brand-new verified user owns nothing until they choose
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNewVerifiedUserOwnsNothingYet(TestCase):
    """The card's own wording: no EXAMPLE project for a real new account, and no
    project — dotfiles included — may become ACTIVE on its own. The dotfiles
    project itself is a real feature (shell config) and may exist."""

    def _verified_user(self, username):
        from django.contrib.auth import get_user_model

        from apps.infra.auth_app.onboarding import mark_verified

        User = get_user_model()
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="TestPass123!",  # pragma: allowlist secret
        )
        # Verification is NOT a profile field: the authority is OnboardingState,
        # written by onboarding.mark_verified (email proven, payment still owed).
        # The old `user.profile.email_verified = True` never existed on the model
        # and failed with "E ... fields do not exist in this model ... email_verified".
        mark_verified(user)
        return user

    def test_creating_a_user_does_not_create_an_example_project(self):
        from apps.infra.project_app.models import Project

        user = self._verified_user("first-login-no-example")

        examples = Project.objects.filter(owner=user, slug="default-project")
        assert examples.count() == 0, (
            "an example/demo project was created for a user who never asked"
        )

    def test_creating_a_user_leaves_no_active_project(self):
        user = self._verified_user("first-login-no-active")

        user.profile.refresh_from_db()
        assert user.profile.last_active_repository is None, (
            "a project became active without the user choosing it"
        )

    def test_the_dotfiles_project_never_becomes_the_active_project(self):
        """It is shell configuration; owning it must not make it the workspace."""
        from apps.infra.project_app.models import Project

        user = self._verified_user("first-login-dotfiles")

        user.profile.refresh_from_db()
        assert Project.objects.filter(owner=user, is_home=True).exists(), (
            "precondition: the dotfiles project is provisioned"
        )
        assert user.profile.last_active_repository is None

    def test_the_root_route_asks_instead_of_landing_them_in_a_project(self):
        user = self._verified_user("first-login-root")
        self.client.force_login(user)

        response = self.client.get("/")

        assert response.status_code == 200
        assert b'data-first-login-welcome="true"' in response.content


# EOF
