#!/usr/bin/env python3
"""Hub-owned project continuity contracts for launcher-to-app navigation."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

from apps.infra.workspace_app.registry import _manifest_to_module_config

ROOT = Path(__file__).resolve().parents[3]


def test_launcher_identifies_the_active_project_in_its_dom_contract():
    # Arrange
    template = ROOT / "apps/workspace/apps_app/templates/apps_app/launcher.html"
    # Act
    source = template.read_text(encoding="utf-8")
    # Assert
    assert (
        'data-active-project-key="{{ current_project.owner.username }}/{{ current_project.slug }}"'
        in source
    )


def test_launcher_tile_exposes_manifest_scope_once():
    # Arrange
    template = (
        ROOT / "apps/workspace/apps_app/templates/apps_app/partials/launcher_tile.html"
    )
    # Act
    source = template.read_text(encoding="utf-8")
    # Assert
    assert source.count('data-scope="{{ tile.scope }}"') == 1


def test_host_shell_exposes_project_and_app_version_metadata_once():
    # Arrange
    shell = (ROOT / "templates/global_base.html").read_text(encoding="utf-8")
    head = (ROOT / "templates/global_base_partials/global_head_meta.html").read_text(
        encoding="utf-8"
    )
    # Act
    counts = (
        shell.count(
            'data-active-project-key="{{ current_project.owner.username }}/{{ current_project.slug }}"'
        ),
        shell.count('data-active-app-version="{{ active_module.version }}"'),
        head.count("{% hub_project_provider_meta %}"),
    )
    # Assert
    assert counts == (1, 1, 1)


def test_project_scoped_manifest_metadata_reaches_the_registry():
    # Arrange
    manifest = {
        "name": "example",
        "label": "Example",
        "app_name": "example_app",
        "scope": "project",
    }
    # Act
    module = _manifest_to_module_config(manifest)
    # Assert
    assert module.scope == "project"


def test_hub_scope_overlay_keeps_external_stats_in_the_active_project():
    # Arrange: the current Stats entry point predates manifest scope metadata.
    manifest = {"name": "stats", "label": "Stats", "app_name": "stats_app"}
    # Act
    module = _manifest_to_module_config(manifest)
    # Assert
    assert module.scope == "project"
    assert module.availability == "coming_soon"


def test_launcher_project_url_carries_the_active_project():
    # Arrange
    launcher = importlib.import_module("apps.workspace.apps_app.views.launcher")
    project = SimpleNamespace(
        slug="continuity-paper",
        owner=SimpleNamespace(username="continuity-user"),
    )
    # Act
    url = launcher.project_launch_url("/apps/scholar/", project)
    # Assert
    assert url == "/apps/scholar/?project=continuity-user%2Fcontinuity-paper"


def test_launcher_rejects_a_registry_url_swallowed_by_the_project_catchall():
    # Arrange
    launcher = importlib.import_module("apps.workspace.apps_app.views.launcher")
    missing = SimpleNamespace(
        name="unmounted-continuity-leaf",
        get_url=lambda: "/apps/unmounted-continuity-leaf/",
    )
    scholar = SimpleNamespace(name="scholar", get_url=lambda: "/apps/scholar/")
    # Act
    reachability = (
        launcher.module_route_is_reachable(missing),
        launcher.module_route_is_reachable(scholar),
    )
    # Assert
    assert reachability == (False, True)


def test_launcher_project_url_preserves_existing_query_and_fragment():
    # Arrange
    launcher = importlib.import_module("apps.workspace.apps_app.views.launcher")
    project = SimpleNamespace(slug="paper", owner=SimpleNamespace(username="alice"))
    # Act
    url = launcher.project_launch_url("/apps/writer/?mode=review#editor", project)
    # Assert
    assert url == "/apps/writer/?mode=review&project=alice%2Fpaper#editor"


def test_launcher_never_discloses_project_identity_to_an_external_url():
    # Arrange
    launcher = importlib.import_module("apps.workspace.apps_app.views.launcher")
    project = SimpleNamespace(
        slug="private-paper", owner=SimpleNamespace(username="alice")
    )
    urls = ["https://evil.example/collect?source=hub", "//evil.example/collect"]
    # Act
    launched = [launcher.project_launch_url(url, project) for url in urls]
    # Assert
    assert launched == urls
    assert all("project=" not in url for url in launched)


def test_active_project_is_applied_only_to_launchable_project_scoped_tiles():
    # Arrange
    launcher = importlib.import_module("apps.workspace.apps_app.views.launcher")
    project = SimpleNamespace(slug="paper", owner=SimpleNamespace(username="alice"))
    tiles = [
        {
            "name": "scholar",
            "scope": "project",
            "is_launchable": True,
            "launch_url": "/apps/scholar/",
        },
        {
            "name": "writer",
            "scope": "project",
            "is_launchable": True,
            "launch_url": "/apps/writer/",
        },
        {"name": "stats", "scope": "project", "is_launchable": False, "launch_url": ""},
        {
            "name": "docs",
            "scope": "user",
            "is_launchable": True,
            "launch_url": "/apps/docs/",
        },
    ]
    # Act
    launcher.apply_active_project(tiles, project)
    # Assert
    assert [tile["launch_url"] for tile in tiles] == [
        "/apps/scholar/?project=alice%2Fpaper",
        "/apps/writer/?project=alice%2Fpaper",
        "",
        "/apps/docs/",
    ]


def test_scholar_declares_project_scope_like_writer_and_figrecipe():
    # Arrange
    manifests = [
        ROOT / "apps/workspace/scholar_app/manifest.json",
        ROOT / "apps/workspace/figrecipe_app/manifest.json",
        ROOT / "apps/workspace/writer_app/manifest.json",
    ]
    # Act
    scopes = [
        json.loads(path.read_text(encoding="utf-8")).get("scope") for path in manifests
    ]
    # Assert
    assert scopes == ["project", "project", "project"]
