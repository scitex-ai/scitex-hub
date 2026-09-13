#!/usr/bin/env python3
"""Release-channel entitlement for internal apps (card hub-cards-internal-entitlement).

Operator ruling 2026-09-13: "internal" visibility is a RELEASE-CHANNEL property,
not an admin-role property. On the development deployment every authenticated
team member sees internal apps; anonymous users stay redirected; production
keeps them hidden unless the deployment opts in. Staff always see them.

can_view_internal_app is a pure predicate over (user, settings flag), so these
tests need no database — they run locally (no Postgres) and in CI.
"""

import pytest
from django.contrib.auth.models import AnonymousUser


class _User:
    def __init__(self, is_authenticated, is_staff=False, is_superuser=False):
        self.is_authenticated = is_authenticated
        self.is_staff = is_staff
        self.is_superuser = is_superuser


def _gate():
    from apps.workspace.apps_app.views.helpers import can_view_internal_app

    return can_view_internal_app


@pytest.fixture
def dev_channel(settings):
    settings.SCITEX_HUB_INTERNAL_APPS_RELEASED = True
    yield


@pytest.fixture
def prod_channel(settings):
    settings.SCITEX_HUB_INTERNAL_APPS_RELEASED = False
    yield


def test_anonymous_never_sees_internal(settings):
    settings.SCITEX_HUB_INTERNAL_APPS_RELEASED = True
    assert _gate()(AnonymousUser()) is False


def test_dev_authenticated_nonstaff_sees_internal(dev_channel):
    assert _gate()(_User(True, is_staff=False, is_superuser=False)) is True


def test_dev_anonymous_despite_channel_stays_redirected(dev_channel):
    assert _gate()(AnonymousUser()) is False


def test_prod_authenticated_nonstaff_hidden(prod_channel):
    assert _gate()(_User(True, is_staff=False, is_superuser=False)) is False


def test_staff_sees_internal_on_any_channel(prod_channel):
    # Staff/operators are the explicit exception: they see internal apps even
    # where the deployment has not released them to everyone. (Django
    # superusers are is_staff by convention; the gate keys on is_staff, not a
    # separate superuser check — admin authority is the exception, the channel
    # is the rule.)
    assert _gate()(_User(True, is_staff=True)) is True


def test_superuser_only_is_not_a_promotion_gate(dev_channel):
    # The contract is "authenticated", not "is_staff" — a plain authenticated
    # user on dev must be enough (this is what lets ywatanabe, is_staff=False,
    # see the Cards tile without an admin promotion).
    assert _gate()(_User(True, is_staff=False, is_superuser=False)) is True
