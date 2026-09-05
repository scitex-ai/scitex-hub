#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/apps_app/test_projects_app_icon_reads_as_projects.py
"""The Projects app's icon says "projects", not "home".

OPERATOR, Telegram 4794, 2026-09-05: the project app uses a HOUSE icon, which
reads wrong; he wants a project/file icon.

He is describing a real mismatch, not a preference: the module is LABELLED
"Projects" and carries ``fas fa-home``. A house is where the app used to be
conceptually ("Hub"), and the label moved on without the icon.

WHY THE MANIFEST IS THE ONLY PLACE THIS CHANGES
-----------------------------------------------
``public_app.templatetags.module_icons.build_module_icon_html`` calls
``registry.get_module(name)`` and its own docstring calls itself "the single
source of truth for module icon rendering". Every surface goes through the
``{% module_icon %}`` tag, which delegates there. So the manifest decides.

There WAS a second-looking place — repo_app/views/index.py put
``"module_icon": "fa-home"`` in its context — and it was a decoy: no template
renders ``{{ module_icon }}`` (checked with a positive control that the search
does find ``{{ `` in those same templates). It is removed in this change, so
the next person editing the icon finds one place instead of two that disagree.

That decoy is worth naming, because the same shape cost real time today: the
launcher's app ORDER also had two sources, the manifests and a hardcoded
DEFAULT_LAUNCHER_ORDER, and the manifest edit was a no-op on every surface a
user sees.
"""

import json
from pathlib import Path

from apps.infra.workspace_app.registry import get_all_modules, get_module

PROJECTS_MODULE = "home"

# tests/apps/apps_app/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST = _REPO_ROOT / "apps" / "workspace" / "repo_app" / "manifest.json"


def test_the_projects_manifest_is_on_disk():
    """Control: a missing file would make the assertions below vacuous."""
    # Arrange
    path = _MANIFEST
    # Act
    present = path.is_file()
    # Assert
    assert present is True, f"no manifest at {path}"


def test_the_module_is_still_labelled_projects():
    """Control for the real assertion: the icon is only 'wrong' relative to
    the label. If the label changed to Home, the house would be correct."""
    # Arrange
    manifest = json.loads(_MANIFEST.read_text())
    # Act
    label = manifest.get("label")
    # Assert
    assert label == "Projects"


def test_the_projects_icon_is_not_a_house():
    # Arrange
    manifest = json.loads(_MANIFEST.read_text())
    # Act
    icon = manifest.get("icon", "")
    # Assert
    assert "fa-home" not in icon, (
        f"the module labelled 'Projects' carries {icon!r} (operator, "
        "Telegram 4794, 2026-09-05)"
    )


def test_the_projects_icon_reads_as_files_or_projects():
    # Arrange
    manifest = json.loads(_MANIFEST.read_text())
    acceptable = ("fa-folder-open", "fa-folder", "fa-diagram-project")
    # Act
    icon = manifest.get("icon", "")
    # Assert
    assert any(candidate in icon for candidate in acceptable), (
        f"{icon!r} is not one of {acceptable}"
    )


def test_the_registry_serves_that_icon():
    """The manifest is only worth asserting if the registry reads it — this is
    the layer that every rendering surface actually consults."""
    # Arrange
    declared = json.loads(_MANIFEST.read_text()).get("icon", "")
    # Act
    module = get_module(PROJECTS_MODULE)
    # Assert
    assert module is not None and module.icon_fa == declared


def test_no_other_module_claims_the_projects_icon():
    """Two tiles with the same glyph are indistinguishable at a glance, which
    is the complaint this change exists to fix, one step removed."""
    # Arrange
    projects = get_module(PROJECTS_MODULE)
    # Act
    clashes = [
        m.name
        for m in get_all_modules()
        if m.name != PROJECTS_MODULE and m.icon_fa and m.icon_fa == projects.icon_fa
    ]
    # Assert
    assert clashes == [], f"{clashes} also use {projects.icon_fa!r}"


# EOF
