#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: ./tests/config/test_secret_key_fallbacks.py

"""A leaked signing key must be rotatable WITHOUT logging every user out.

WHY THIS FILE EXISTS
--------------------
Django signs sessions, password-reset links and signed URLs with
``SECRET_KEY``. Replacing it invalidates every signature made with the old
one, so the naive rotation logs out every user and breaks the reset mails
already sitting in inboxes.

That gives the safe action a visible cost and the unsafe action none, which is
exactly why a key known to be exposed can sit un-rotated for days. It is not
an oversight; it is the incentive the code creates.

``SECRET_KEY_FALLBACKS`` (Django >= 4.1) removes the cost: Django signs only
with ``SECRET_KEY`` but VERIFIES against the fallbacks too, so a retired key
keeps validating existing signatures for one rotation window.

Occasioned by hub-dev-preview-internet-reachable-with-debug-true-and-no-auth
-20260902, where hub's SECRET_KEY was publicly readable for four days. Hiding
the page does not undo the exposure; only rotation does — and rotation needs
to be cheap or it does not happen.

WHAT THIS FILE DOES NOT CHECK (declared, not overlooked)
--------------------------------------------------------
1. It does not verify that Django ITSELF honours the fallbacks. That is
   Django's own contract and its own test suite; asserting it here would be
   testing the framework.
2. It does not check that any particular deployment has a rotation in flight.
   The steady state is an empty list, and an empty list is correct.
3. It does not enforce the third step of the rotation contract — REMOVING the
   retired key once the window closes. Nothing here can see that, and a
   fallback left in place indefinitely keeps an exposed key valid. That is a
   real gap and it belongs to whoever runs the rotation.
"""

from __future__ import annotations

import os

import pytest
from django.conf import settings as django_settings

from config.settings.settings_secret_key import (
    SECRET_KEY_FALLBACKS_ENV,
    parse_secret_key_fallbacks,
    resolve_secret_key_fallbacks,
)


@pytest.fixture
def rotation_in_flight():
    """Put two retired keys in the REAL environment, then restore it.

    A yield fixture over ``os.environ`` rather than ``monkeypatch``: the
    resolver reads the process environment in production, so the test reads
    the process environment too. Nothing about the production code path is
    rewritten for the test's benefit.
    """
    previous = os.environ.get(SECRET_KEY_FALLBACKS_ENV)
    os.environ[SECRET_KEY_FALLBACKS_ENV] = "retired-key-a,retired-key-b"
    try:
        yield ["retired-key-a", "retired-key-b"]
    finally:
        if previous is None:
            os.environ.pop(SECRET_KEY_FALLBACKS_ENV, None)
        else:
            os.environ[SECRET_KEY_FALLBACKS_ENV] = previous


@pytest.fixture
def no_rotation_in_flight():
    """Remove the variable entirely, then restore whatever was there."""
    previous = os.environ.get(SECRET_KEY_FALLBACKS_ENV)
    os.environ.pop(SECRET_KEY_FALLBACKS_ENV, None)
    try:
        yield
    finally:
        if previous is not None:
            os.environ[SECRET_KEY_FALLBACKS_ENV] = previous


def test_an_unset_value_yields_an_empty_list_not_none():
    """Django indexes the setting directly; None would fail mid-request."""
    # Arrange
    unset = None

    # Act
    parsed = parse_secret_key_fallbacks(unset)

    # Assert
    assert parsed == []


def test_an_empty_string_yields_an_empty_list():
    """The steady state — no rotation in flight — must not be an error."""
    # Arrange
    empty = ""

    # Act
    parsed = parse_secret_key_fallbacks(empty)

    # Assert
    assert parsed == []


def test_a_single_key_is_returned_verbatim():
    """The common case during a rotation: exactly one retired key."""
    # Arrange
    raw = "old-signing-key-value"

    # Act
    parsed = parse_secret_key_fallbacks(raw)

    # Assert
    assert parsed == ["old-signing-key-value"]


def test_surrounding_whitespace_is_stripped_from_each_key():
    """A key pasted with spaces must not be silently wrong.

    An un-stripped key does not raise — it simply never matches, so every old
    session is rejected and the rotation appears to have logged everyone out
    anyway. The failure would look like the bug this setting prevents.
    """
    # Arrange
    raw = " first-key , second-key "

    # Act
    parsed = parse_secret_key_fallbacks(raw)

    # Assert
    assert parsed == ["first-key", "second-key"]


def test_blank_entries_are_dropped_so_no_empty_key_is_verified_against():
    """A trailing comma must not become an empty-string 'key'."""
    # Arrange
    raw = "only-key,,   ,"

    # Act
    parsed = parse_secret_key_fallbacks(raw)

    # Assert
    assert parsed == ["only-key"]


def test_the_resolver_reads_the_documented_environment_variable(rotation_in_flight):
    """The env name is a deployment contract, so pin it by using it."""
    # Arrange
    expected = rotation_in_flight

    # Act
    resolved = resolve_secret_key_fallbacks()

    # Assert
    assert resolved == expected


def test_the_resolver_is_empty_when_no_rotation_is_in_flight(no_rotation_in_flight):
    """CONTROL: the previous test must not pass by reading a stale value.

    Without this, a variable left set by any earlier test — or by the
    developer's own shell — would make the positive case pass for a reason
    that has nothing to do with the resolver.
    """
    # Arrange
    expected = []

    # Act
    resolved = resolve_secret_key_fallbacks()

    # Assert
    assert resolved == expected


def test_the_setting_is_exposed_to_django():
    """The wiring, not the parser — a helper nothing reads is not a feature."""
    # Arrange
    expected_type = list

    # Act
    configured = django_settings.SECRET_KEY_FALLBACKS

    # Assert
    assert isinstance(configured, expected_type)


# EOF
