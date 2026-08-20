#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_hub/account/conftest.py
"""Shared fixtures for ``scitex_hub.account`` tests.

The ecosystem-wide rule forbids ``monkeypatch`` (STX-NM002) — every
test that needs an env-var twist must use a real ``yield``-based
fixture that sets the var on the live ``os.environ`` and restores
the prior state on teardown.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest


@pytest.fixture
def env_token() -> Iterator[str]:
    """Set ``SCITEX_HUB_TOKEN`` for the duration of the test."""
    prior = os.environ.get("SCITEX_HUB_TOKEN")
    os.environ["SCITEX_HUB_TOKEN"] = "scitex_test_token"
    try:
        yield "scitex_test_token"
    finally:
        if prior is None:
            os.environ.pop("SCITEX_HUB_TOKEN", None)
        else:
            os.environ["SCITEX_HUB_TOKEN"] = prior


@pytest.fixture
def env_url() -> Iterator[str]:
    """Set ``SCITEX_HUB_URL`` to a known test host."""
    prior = os.environ.get("SCITEX_HUB_URL")
    os.environ["SCITEX_HUB_URL"] = "https://hub.test.example"
    try:
        yield "https://hub.test.example"
    finally:
        if prior is None:
            os.environ.pop("SCITEX_HUB_URL", None)
        else:
            os.environ["SCITEX_HUB_URL"] = prior


@pytest.fixture
def env_no_token_and_homeless(tmp_path) -> Iterator[None]:
    """Clear ``SCITEX_HUB_TOKEN`` AND point ``HOME`` at an empty tmpdir.

    Combined: guarantees ``resolve_bearer`` can find neither an env
    token nor a cached ``token.json`` — so the "not logged in" path is
    exercised against the real resolver, not a mocked one.
    """
    prior_token = os.environ.get("SCITEX_HUB_TOKEN")
    prior_home = os.environ.get("HOME")
    os.environ.pop("SCITEX_HUB_TOKEN", None)
    os.environ["HOME"] = str(tmp_path)
    try:
        yield
    finally:
        if prior_token is None:
            os.environ.pop("SCITEX_HUB_TOKEN", None)
        else:
            os.environ["SCITEX_HUB_TOKEN"] = prior_token
        if prior_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = prior_home


# EOF
