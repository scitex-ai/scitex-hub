#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical internal identities for the two project launcher apps."""

import importlib
import json
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.urls import resolve

from apps.infra.project_app.models import Project
from apps.infra.workspace_app.registry import get_all_modules
from apps.workspace.apps_app.models import (
    AppsModule,
    ModuleInstallation,
    ModuleVersion,
    PlannedAppInterest,
)
from apps.workspace.apps_app.planned_apps import PLANNED_BY_ID
from apps.workspace.apps_app.views.launcher import launcher_context

ROOT = Path(settings.BASE_DIR)
WORKSPACE = ROOT / "apps" / "workspace"


@pytest.mark.parametrize(
    ("package", "module_name", "route", "namespace"),
    [
        ("my_projects_app", "my_projects", "/apps/my-projects/", "my_projects_app"),
        (
            "public_projects_app",
            "public_projects",
            "/apps/public-projects/",
            "public_projects_app",
        ),
    ],
)
def test_project_apps_use_canonical_packages_manifests_and_routes(
    package, module_name, route, namespace
):
    manifest = json.loads((WORKSPACE / package / "manifest.json").read_text("utf-8"))

    assert importlib.import_module(f"apps.workspace.{package}")
    assert manifest["name"] == module_name
    assert manifest["app_name"] == package
    assert manifest["url"] == route
    assert resolve(route).namespace == namespace


@pytest.mark.parametrize(
    ("package", "module_name", "route"),
    [
        ("repo_app", "home", "/apps/home/"),
        ("discovery_app", "discovery", "/apps/discovery/"),
    ],
)
def test_project_apps_expose_no_legacy_package_module_or_route(package, module_name, route):
    assert not (WORKSPACE / package).exists()
    assert module_name not in {module.name for module in get_all_modules()}
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(f"apps.workspace.{package}")
    match = resolve(route)
    assert match.namespace not in {"my_projects_app", "public_projects_app"}


@pytest.mark.django_db
def test_launcher_keeps_public_and_my_projects():
    user = User.objects.create_user(username="canonical-project-apps", is_staff=True)
    request = RequestFactory().get("/apps/")
    request.user = user
    request.session = {}

    names = {tile["name"] for tile in launcher_context(request)["tiles"]}

    assert {"my_projects", "public_projects"} <= names


def test_retired_apps_and_rejected_placeholders_are_absent():
    assert not (WORKSPACE / "slides_app").exists()
    assert "slides" not in {module.name for module in get_all_modules()}
    assert {"slides", "mail", "screen-recorder"}.isdisjoint(PLANNED_BY_ID)
    assert resolve("/apps/slides/").namespace != "slides_app"


@pytest.mark.django_db(transaction=True)
def test_project_module_id_migration_preserves_installations():
    migration = importlib.import_module(
        "apps.workspace.apps_app.migrations.0022_canonical_project_module_names"
    )
    user = User.objects.create_user(username="project-module-migration")
    old_public = AppsModule.objects.create(module_name="discovery")
    old_mine = AppsModule.objects.create(module_name="home")
    public_install = ModuleInstallation.objects.create(
        user=user,
        module=old_public,
        tab_order=17,
        config={
            "pinned": True,
            "launcher_dock": ["home", "discovery", "slides", "chat"],
            "launcher_link_order": {
                "home": 10,
                "discovery": 20,
                "slides": 30,
                "chat": 40,
            },
        },
    )
    mine_install = ModuleInstallation.objects.create(
        user=user, module=old_mine, tab_order=23, config={"pinned": True}
    )
    retired = AppsModule.objects.create(module_name="slides")
    ModuleInstallation.objects.create(user=user, module=retired)
    PlannedAppInterest.objects.create(user=user, app_id="mail", kind="notify")

    migration.rename_project_modules(importlib.import_module("django.apps").apps, None)
    migration.remove_retired_apps(importlib.import_module("django.apps").apps, None)

    public_install.refresh_from_db()
    mine_install.refresh_from_db()
    assert public_install.module.module_name == "public_projects"
    assert mine_install.module.module_name == "my_projects"
    assert not AppsModule.objects.filter(module_name__in=["discovery", "home"]).exists()
    assert not AppsModule.objects.filter(module_name="slides").exists()
    assert not PlannedAppInterest.objects.filter(app_id="mail").exists()
    assert public_install.config["launcher_dock"] == [
        "my_projects",
        "public_projects",
        "chat",
    ]
    assert public_install.config["launcher_link_order"] == {
        "my_projects": 10,
        "public_projects": 20,
        "chat": 40,
    }


@pytest.mark.django_db(transaction=True)
def test_project_module_id_migration_merges_precreated_canonical_identity():
    migration = importlib.import_module(
        "apps.workspace.apps_app.migrations.0022_canonical_project_module_names"
    )
    overlap = User.objects.create_user(username="project-module-overlap")
    old_only = User.objects.create_user(username="project-module-old-only")
    canonical_only = User.objects.create_user(username="project-module-new-only")
    source_project = Project.objects.create(
        owner=old_only,
        name="Legacy project app",
        slug="legacy-project-app",
    )
    old = AppsModule.objects.create(
        module_name="home",
        label="My Projects",
        project=source_project,
    )
    canonical = AppsModule.objects.create(
        module_name="my_projects", label="My Projects"
    )
    historical = ModuleInstallation.objects.create(
        user=overlap,
        module=old,
        tab_order=17,
        config={"pinned": True},
    )
    ModuleInstallation.objects.create(
        user=overlap,
        module=canonical,
        tab_order=1000,
        config={},
    )
    old_only_install = ModuleInstallation.objects.create(
        user=old_only,
        module=old,
        tab_order=23,
        config={"launcher_dock": ["home", "chat"]},
    )
    canonical_only_install = ModuleInstallation.objects.create(
        user=canonical_only,
        module=canonical,
        tab_order=31,
        config={"pinned": True},
    )
    ModuleVersion.objects.create(module=old, version="0.1.0")
    ModuleVersion.objects.create(module=canonical, version="0.1.0")

    migration.rename_project_modules(importlib.import_module("django.apps").apps, None)

    historical.refresh_from_db()
    old_only_install.refresh_from_db()
    canonical_only_install.refresh_from_db()
    canonical.refresh_from_db()
    source_project.refresh_from_db()
    assert historical.module_id == canonical.id
    assert historical.tab_order == 17
    assert historical.config == {"pinned": True}
    assert old_only_install.module_id == canonical.id
    assert old_only_install.config["launcher_dock"] == ["my_projects", "chat"]
    assert canonical_only_install.module_id == canonical.id
    assert ModuleInstallation.objects.filter(user=overlap, module=canonical).count() == 1
    assert ModuleVersion.objects.filter(module=canonical, version="0.1.0").count() == 1
    assert source_project.marketplace_module.id == canonical.id
    assert not AppsModule.objects.filter(module_name="home").exists()


@pytest.mark.django_db(transaction=True)
def test_stale_todo_module_migration_removes_row_and_scrubs_configs():
    migration = importlib.import_module(
        "apps.workspace.apps_app.migrations.0023_remove_stale_todo_module"
    )
    user = User.objects.create_user(username="stale-todo-migration")
    AppsModule.objects.create(
        module_name="todo", label="Cards", icon="fas fa-list-check", visibility="public"
    )
    # The install lives on the SURVIVING plugin row but its launcher config
    # still names the retired id (pinned dock / custom order from before the
    # rebrand). Installs attached to the deleted row itself cascade away.
    canonical = AppsModule.objects.create(
        module_name="scitex-cards",
        label="Cards",
        icon="fas fa-diagram-project",
        visibility="public",
    )
    install = ModuleInstallation.objects.create(
        user=user,
        module=canonical,
        tab_order=17,
        config={
            "launcher_dock": ["todo", "scitex-cards", "chat"],
            "launcher_link_order": {"todo": 10, "scitex-cards": 20, "chat": 30},
        },
    )
    PlannedAppInterest.objects.create(user=user, app_id="todo", kind="notify")

    migration.remove_stale_todo_module(importlib.import_module("django.apps").apps, None)

    install.refresh_from_db()
    assert not AppsModule.objects.filter(module_name="todo").exists()
    assert not PlannedAppInterest.objects.filter(app_id="todo").exists()
    assert install.config["launcher_dock"] == ["scitex-cards", "chat"]
    assert install.config["launcher_link_order"] == {"scitex-cards": 20, "chat": 30}
