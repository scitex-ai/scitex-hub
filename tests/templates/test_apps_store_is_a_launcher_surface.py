#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""/apps/store/ is a launcher surface, so it shows the legal footer like `/` does.

The operator asked on 2026-08-10 for the apps home to carry the footer, and
said why: 「フッターがないとですね。あの特商法の表示がとか法律がとか後は連絡先が
とかってわかりにくいんで」 — the footer is the route to the 特定商取引法 disclosure,
the policy pages and contact. PR #578 fixed the signed-in launcher at `/` by
giving it `.app-home`, the class every footer rule treats as "a launcher
surface": workspace-layout.css excludes it from the hide rule, global-base.css
releases its viewport pin so the footer sits below the shell instead of eating
it, footer-collapse.css keeps the shell from collapsing, and footer.css still
hides the footer on phones where the mobile menu carries the legal routes.

But /apps/ REDIRECTS to /apps/store/, whose body carried `workspace-page
store-page` and nothing else — so the page the operator actually lands on kept
hiding the footer at every width. Measured on production 2026-09-05 01:46Z at
1905 px: footer display none, height 0, the 特定商取引法 link present in the DOM
and visible: false. Twenty-six days after the request.

The fix is one manifest field: the store declares `app-home` in its body_class
and inherits the whole launcher-surface bundle. No CSS rule changes, so the
guards that already model the cascade (test_footer_visible_by_default.py) and
the viewport pin (test_app_home_launcher_not_starved_by_footer.py) apply to
the store's classes unchanged — these tests run them against the store.

WHAT EACH TEST IS FOR
  store_manifest_declares_the_launcher_marker   the one line that is the fix.
  store_classes_do_not_hide_the_footer          the cascade model says visible.
  store_classes_do_not_pin_the_viewport         and the shell is released, so
                                                the footer cannot starve the grid.
  control_store_without_the_marker_hides_it     the pre-fix classes ARE hidden by
                                                the same model — the detector sees
                                                the defect it exists to catch.
  inventory_of_launcher_surfaces                exactly which module manifests
                                                claim the marker. Adding one is a
                                                decision someone writes down here.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest
from django.conf import settings

REPO = Path(settings.BASE_DIR)
STORE_MANIFEST = REPO / "apps" / "workspace" / "apps_app" / "manifest.json"
GLOBAL_BASE = REPO / "templates" / "global_base.html"
HERE = Path(__file__).resolve().parent

STORE_CLASSES_AFTER = frozenset({"workspace-page", "store-page", "app-home", "no-transition"})
STORE_CLASSES_BEFORE = frozenset({"workspace-page", "store-page", "no-transition"})


def _load(name: str):
    """Load a sibling test module by path — the helpers live there on purpose."""
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(name="footer_model", scope="module")
def _footer_model():
    return _load("test_footer_visible_by_default")


@pytest.fixture(name="viewport_model", scope="module")
def _viewport_model():
    return _load("test_app_home_launcher_not_starved_by_footer")


def _body_classes(manifest: Path) -> list[str]:
    return json.loads(manifest.read_text(encoding="utf-8")).get("body_class", "").split()


def test_store_manifest_declares_the_launcher_marker() -> None:
    # Arrange
    classes = _body_classes(STORE_MANIFEST)
    # Act
    declared = "app-home" in classes
    # Assert
    assert declared, classes


def test_store_classes_do_not_hide_the_footer(footer_model) -> None:
    # Arrange — the body classes /apps/store/ renders after the fix.
    classes = STORE_CLASSES_AFTER
    # Act
    hidden = footer_model._footer_hidden_for(classes)
    # Assert
    assert not hidden, sorted(classes)


def test_store_classes_do_not_pin_the_viewport(viewport_model) -> None:
    # Arrange — a visible footer on a pinned body starves the grid (2026-08-11).
    classes = STORE_CLASSES_AFTER
    # Act
    locked = viewport_model._is_viewport_locked(classes)
    # Assert
    assert not locked, sorted(classes)


def test_the_control_a_store_page_without_the_marker_hides_the_footer(footer_model) -> None:
    # Arrange — the classes production rendered before this fix.
    classes = STORE_CLASSES_BEFORE
    # Act
    hidden = footer_model._footer_hidden_for(classes)
    # Assert
    assert hidden, "the cascade model no longer sees the defect this file fixes"


def test_the_inventory_of_launcher_surfaces_is_exactly_the_store() -> None:
    # Arrange — every module manifest that claims the launcher-surface marker.
    manifests = sorted((REPO / "apps").rglob("manifest.json"))
    # Act
    claiming = sorted(
        m.parent.name for m in manifests if "app-home" in _body_classes(m)
    )
    # Assert — `/` gets the marker from global_base.html, not a manifest; the
    # store is the only module that is a launcher rather than a workspace.
    assert claiming == ["apps_app"], claiming


def test_the_signed_in_root_still_sets_the_marker_in_the_template() -> None:
    # Arrange — the other launcher surface, so the inventory above is complete.
    html = GLOBAL_BASE.read_text(encoding="utf-8")
    # Act
    hits = re.findall(r"no-transition app-home", html)
    # Assert
    assert len(hits) == 1, hits
