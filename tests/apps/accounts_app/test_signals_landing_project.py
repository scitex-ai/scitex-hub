#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/accounts_app/test_signals_landing_project.py
"""A new profile lands on a real project, never on the shell-config one.

The home project holds bashrc, gitconfig and screenrc. It is a real feature
for a signed-in user and the wrong first screen for anyone else: landing there
shows a stranger our shell dotfiles and nothing about research.

Measured on production 2026-08-16 — every visitor workspace already held both
projects on disk, and the visitor was landed on the shell one, so
/apps/writer/ rendered "dotfiles · Writer", 0 words and a blank manuscript
while the seeded demo sat unopened beside it. The content was never missing;
the pointer was wrong. These tests pin the pointer.
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


def test_landing_project_is_not_the_home_project(user_with_demo):
    # Arrange: the demo exists alongside the home project
    ensure_home_project(user_with_demo)
    user_with_demo.profile.refresh_from_db()
    # Act
    landing = user_with_demo.profile.last_active_repository
    # Assert
    assert landing.is_home is False, (
        "the profile landed on the shell-config project; a visitor would see "
        "bashrc and gitconfig instead of the demo"
    )


def test_landing_project_is_the_demo(user_with_demo):
    # Arrange
    ensure_home_project(user_with_demo)
    user_with_demo.profile.refresh_from_db()
    # Act
    landing = user_with_demo.profile.last_active_repository
    # Assert
    assert landing.slug == "default-project"


def test_home_project_is_still_created(user_with_demo):
    """Preferring the demo must not stop the home project existing."""
    # Arrange
    ensure_home_project(user_with_demo)
    # Act
    homes = Project.objects.filter(owner=user_with_demo, is_home=True).count()
    # Assert
    assert homes == 1


def test_home_project_is_the_fallback_when_nothing_else_exists(user):
    """With no other project, the home one is better than none."""
    # Arrange: no demo project for this user
    ensure_home_project(user)
    user.profile.refresh_from_db()
    # Act
    landing = user.profile.last_active_repository
    # Assert
    assert landing is not None and landing.is_home is True


def test_an_existing_choice_is_not_overwritten(user_with_demo):
    """last_active_repository means 'where they were'; do not rewrite a choice."""
    # Arrange: the user is already sitting on the home project deliberately
    home = Project.objects.create(
        name="dotfiles",
        slug="dotfiles",
        owner=user_with_demo,
        visibility="private",
        is_home=True,
    )
    user_with_demo.profile.last_active_repository = home
    user_with_demo.profile.save()
    ensure_home_project(user_with_demo)
    user_with_demo.profile.refresh_from_db()
    # Act
    landing = user_with_demo.profile.last_active_repository
    # Assert
    assert landing.pk == home.pk


def test_repair_runs_even_when_the_home_project_already_exists(user_with_demo):
    """A profile provisioned before the demo existed is fixed on next login."""
    # Arrange: home project present, profile still pointing nowhere
    Project.objects.create(
        name="dotfiles",
        slug="dotfiles",
        owner=user_with_demo,
        visibility="private",
        is_home=True,
    )
    user_with_demo.profile.last_active_repository = None
    user_with_demo.profile.save()
    ensure_home_project(user_with_demo)
    user_with_demo.profile.refresh_from_db()
    # Act
    landing = user_with_demo.profile.last_active_repository
    # Assert
    assert landing is not None and landing.is_home is False


# EOF
