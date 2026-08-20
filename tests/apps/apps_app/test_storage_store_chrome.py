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
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_COLORS_CSS = _REPO_ROOT / "static" / "shared" / "css" / "primitives" / "colors.css"
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


def test_colors_css_defines_storage_accent_in_light_and_dark():
    """The storage accent token must exist for BOTH themes (dark is first-class)."""
    # Arrange
    css = _COLORS_CSS.read_text()

    # Act — one definition in the :root (light) block + one in the dark block.
    definitions = re.findall(r"--app-accent-storage:", css)

    # Assert
    assert len(definitions) == 2, (
        "--app-accent-storage must be defined exactly twice in colors.css "
        f"(light + dark blocks), found {len(definitions)}"
    )


def test_manifest_accent_has_matching_css_token():
    """Same contract ModuleTestMixin.test_accent_color_css_exists enforces, sans DB."""
    # Arrange
    manifest = json.loads(_STORAGE_MANIFEST.read_text())
    css = _COLORS_CSS.read_text()

    # Act
    accent = manifest["accent_color"]

    # Assert
    assert f"--app-accent-{accent}:" in css, (
        f"manifest accent_color '{accent}' has no --app-accent-{accent} "
        "token in colors.css"
    )


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
