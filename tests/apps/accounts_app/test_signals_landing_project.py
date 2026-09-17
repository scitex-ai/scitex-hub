#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/accounts_app/test_signals_landing_project.py
"""The dotfiles project is provisioned, but it is never the user's project.

The home project holds bashrc, gitconfig and screenrc. It is a real feature for
a signed-in user and the wrong first screen for anyone else: landing there shows
a stranger our shell dotfiles and nothing about research.

History, because this file has now pinned two opposite rules:

* Measured on production 2026-08-16: the visitor was landed on the shell
  project, so ``/apps/writer/`` rendered "dotfiles · Writer", 0 words and a
  blank manuscript while a seeded demo sat unopened beside it. The first
  version of this file therefore forced the pointer onto any NON-home project.
* That fix still *chose for the user*, and for a brand-new account owning
  nothing else it still chose the shell project. Card
  ``hub-first-login-project-workspace-onboarding-20260917`` closes the class:
  ONLY an explicit choice may become active, so the pointer stays empty and the
  first-login welcome asks. See ``accounts_app.onboarding``.

These tests pin the second rule. They need the database gate, like before.
"""

import pytest
from django.contrib.auth import get_user_model

from apps.infra.accounts_app.signals import ensure_home_project
from apps.infra.project_app.models import Project

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    """A user whose profile has no landing project yet."""
    User = get_user_model()
    created = User.objects.create_user(username="visitor-999", password="x")
    created.profile.last_active_repository = None
    created.profile.save()
    return created


@pytest.fixture
def user_with_demo(user):
    """The same user, plus a non-home project standing in for the demo."""
    Project.objects.create(
        name="Handwritten Digits (Example)",
        slug="default-project",
        owner=user,
        visibility="private",
        is_home=False,
    )
    return user


def test_home_project_is_still_created(user_with_demo):
    """Provisioning is unchanged: the dotfiles project still exists."""
    ensure_home_project(user_with_demo)
    homes = Project.objects.filter(owner=user_with_demo, is_home=True).count()
    assert homes == 1


def test_no_project_is_adopted_when_the_profile_has_no_choice(user_with_demo):
    """The demo is there and remains unopened — the user chooses, not the code."""
    ensure_home_project(user_with_demo)
    user_with_demo.profile.refresh_from_db()
    assert user_with_demo.profile.last_active_repository is None, (
        "a project became active without the user choosing it"
    )


def test_the_home_project_is_not_adopted_either(user):
    """With nothing else on disk, the shell project is still not the workspace."""
    ensure_home_project(user)
    user.profile.refresh_from_db()
    assert user.profile.last_active_repository is None


def test_an_existing_choice_is_not_overwritten(user_with_demo):
    """last_active_repository means 'where they were'; do not rewrite a choice."""
    chosen = Project.objects.get(owner=user_with_demo, slug="default-project")
    user_with_demo.profile.last_active_repository = chosen
    user_with_demo.profile.save()
    ensure_home_project(user_with_demo)
    user_with_demo.profile.refresh_from_db()
    assert user_with_demo.profile.last_active_repository_id == chosen.pk


def test_get_active_project_returns_the_explicit_choice(user_with_demo):
    chosen = Project.objects.get(owner=user_with_demo, slug="default-project")
    user_with_demo.profile.last_active_repository = chosen
    user_with_demo.profile.save()

    assert user_with_demo.profile.get_active_project().pk == chosen.pk


def test_get_active_project_does_not_invent_one(user_with_demo):
    """It used to pick and persist the first owned project on read."""
    user_with_demo.profile.last_active_repository = None
    user_with_demo.profile.save()

    assert user_with_demo.profile.get_active_project() is None
    user_with_demo.profile.refresh_from_db()
    assert user_with_demo.profile.last_active_repository is None


def test_get_active_project_drops_a_reference_the_user_does_not_own(user_with_demo):
    """A stale cross-user pointer is cleared, never substituted."""
    User = get_user_model()
    other = User.objects.create_user(username="visitor-998", password="x")
    foreign = Project.objects.create(
        name="Not Yours", slug="not-yours", owner=other, visibility="private"
    )
    user_with_demo.profile.last_active_repository = foreign
    user_with_demo.profile.save()

    assert user_with_demo.profile.get_active_project() is None
    user_with_demo.profile.refresh_from_db()
    assert user_with_demo.profile.last_active_repository_id is None


# EOF
