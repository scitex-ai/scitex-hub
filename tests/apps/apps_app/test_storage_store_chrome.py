#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Storage tile/store chrome regressions — desktop polish sweep 2026-07-17.

Field findings (live prod, https://scitex.ai, 1440x900, dark + light):

- /apps/store/storage/ badge read "Other" while the storage manifest
  declares ``"category": "data"`` — ``seed_apps._CATEGORY_MAP`` had no
  "storage" row, so the store DB row silently fell back to "other".
- The anonymous "Login to install" CTA linked ``/accounts/login/`` which
  404s on prod (the real route is ``/auth/login/``) — dead link on the
  storage detail page, the browse cards, and the global auth modal.
- The storage tile had no per-app accent: ``accent_color`` was "" in the
  manifest and colors.css defined no ``--app-accent-storage`` token
  (every sibling launcher app has one, in BOTH theme blocks).

These are file-content guards (no DB — DB-backed store tests are CI's).
AAA; one assertion each.
"""

import json
from pathlib import Path

# `re` and `_COLORS_CSS` were dropped with the two accent tests below: nothing
# left in this file reads a stylesheet. Leaving an unused path constant behind
# would be worse than untidy here — it would name a file hub no longer ships,
# and the next reader would reasonably assume it still exists.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_STORAGE_MANIFEST = (
    _REPO_ROOT / "apps" / "workspace" / "storage_app" / "manifest.json"
)
_STORE_TEMPLATES = [
    _REPO_ROOT
    / "apps"
    / "workspace"
    / "apps_app"
    / "templates"
    / "apps_app"
    / "detail.html",
    _REPO_ROOT
    / "apps"
    / "workspace"
    / "apps_app"
    / "templates"
    / "apps_app"
    / "partials"
    / "module_card.html",
    _REPO_ROOT / "templates" / "global_base_partials" / "auth_required_modal.html",
]


# RETIRED 2026-08-18 — superseded by
# tests/apps/apps_app/test_every_app_accent_token_resolves.py.
#
# Two tests lived here: `test_colors_css_defines_storage_accent_in_light_and_dark`
# and `test_manifest_accent_has_matching_css_token`. Both read
# `static/shared/css/primitives/colors.css` by a HARDCODED PATH, and hub no
# longer ships that file — it imports scitex-ui's primitives instead.
#
# The successor's docstring called this exact retirement before it happened:
#
#     "The storage test hardcodes primitives/colors.css. That file is being
#      retired in favour of importing scitex-ui's copy, which would leave the
#      test either failing for the wrong reason or, worse, READING A FILE THAT
#      NO LONGER PARTICIPATES IN WHAT THE BROWSER LOADS."
#
# The second half is why these are deleted rather than repointed at
# variables.css. A path-following version would keep passing while asserting
# something about a file the page may not load — a green that means nothing.
# The successor resolves the real @import chain, so it answers the question
# these asked ("does the token reach a page?") rather than the question they
# could actually check ("is the token in this file?").
#
# COVERAGE IS NOT REDUCED. The successor asserts the same contract for storage
# AND for the other eleven apps that declare an accent, parametrised per app, so
# storage-specific coverage is strictly greater than it was here.
#
# The remaining tests in this file are unaffected: they guard the store category
# mapping and the login-CTA hrefs, neither of which touches colors.css.


def test_seed_category_matches_storage_manifest():
    """seed_apps must not let the storage store row drift from the manifest."""
    # Arrange
    from apps.workspace.apps_app.management.commands.seed_apps import (
        _CATEGORY_MAP,
    )

    manifest = json.loads(_STORAGE_MANIFEST.read_text())

    # Act
    seeded_category = _CATEGORY_MAP.get("storage")

    # Assert — "data" per the manifest, never the "other" fallback.
    assert seeded_category == manifest["category"], (
        "seed_apps._CATEGORY_MAP['storage'] must match the manifest "
        f"category '{manifest['category']}', got '{seeded_category}'"
    )


def test_seed_description_defined_for_storage():
    """The generic "<Label> workspace module." fallback is the guarded regression."""
    # Arrange
    from apps.workspace.apps_app.management.commands.seed_apps import (
        _DESCRIPTIONS,
    )

    # Act
    description = _DESCRIPTIONS.get("storage", "")

    # Assert
    assert description, (
        "seed_apps._DESCRIPTIONS must carry a real storage description "
        "(the store detail page renders it verbatim)"
    )


def test_store_templates_use_auth_login_route():
    """The store chrome must never link /accounts/login/ (404s; real: /auth/login/)."""
    # Arrange
    contents = {p.name: p.read_text() for p in _STORE_TEMPLATES}

    # Act — an offender is any template still linking the dead route.
    offenders = [
        name
        for name, text in contents.items()
        if 'href="/accounts/login/' in text
    ]

    # Assert
    assert offenders == [], (
        f"dead /accounts/login/ link (404 on prod) in: {offenders}"
    )


# EOF
