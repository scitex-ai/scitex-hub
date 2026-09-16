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

from apps.infra.workspace_app.registry import get_all_modules
from apps.workspace.apps_app.models import (
    AppsModule,
    ModuleInstallation,
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
def test_project_module_id_migration_refuses_identity_collisions():
    migration = importlib.import_module(
        "apps.workspace.apps_app.migrations.0022_canonical_project_module_names"
    )
    AppsModule.objects.create(module_name="home")
    AppsModule.objects.create(module_name="my_projects")

    with pytest.raises(RuntimeError, match="home.*my_projects"):
        migration.rename_project_modules(importlib.import_module("django.apps").apps, None)
