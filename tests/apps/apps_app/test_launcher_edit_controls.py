#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused launcher edit-mode uninstall and display override tests."""

import json

from django.contrib.auth.models import User
from django.test import TestCase

from apps.workspace.apps_app.models import AppsModule, ModuleInstallation


class LauncherEditControlsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="launcher-editor",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.community = AppsModule.objects.create(
            module_name="t-community-edit",
            label="Manifest Community",
            icon="fas fa-flask",
            category="analysis",
            visibility="public",
        )
        cls.builtin = AppsModule.objects.create(
            module_name="t-core-edit",
            label="Manifest Core",
            icon="fas fa-cube",
            category="utility",
            visibility="public",
            is_builtin=True,
        )
        AppsModule.objects.create(
            module_name="store",
            label="App Store",
            icon="fas fa-store",
            category="utility",
            visibility="public",
            is_builtin=True,
        )

    def setUp(self):
        self.client.login(
            username="launcher-editor",
            password="TestPass123!",  # pragma: allowlist secret
        )
        ModuleInstallation.objects.get_or_create(
            user=self.user, module=self.community
        )
        ModuleInstallation.objects.get_or_create(user=self.user, module=self.builtin)

    def _tile(self, module_name):
        response = self.client.get("/")
        return next(t for t in response.context["tiles"] if t["name"] == module_name)

    def _post_display(self, module_name, payload):
        return self.client.post(
            f"/apps/store/api/{module_name}/launcher-display/",
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_installed_community_tile_is_uninstallable(self):
        assert self._tile(self.community.module_name)["can_uninstall"] is True

    def test_builtin_tile_is_never_uninstallable(self):
        assert self._tile(self.builtin.module_name)["can_uninstall"] is False

    def test_template_renders_accessible_controls_for_community_tile(self):
        response = self.client.get("/")
        html = response.content.decode()
        assert 'data-module="t-community-edit"' in html
        assert 'aria-label="Uninstall Manifest Community"' in html
        assert 'aria-label="Edit Manifest Community display"' in html

    def test_template_does_not_render_uninstall_control_for_builtin(self):
        response = self.client.get("/")
        assert 'aria-label="Uninstall Manifest Core"' not in response.content.decode()

    def test_display_override_is_stored_only_on_launcher_owner_config(self):
        response = self._post_display(
            self.community.module_name,
            {
                "display_name": "My Lab",
                "icon": "fas fa-microscope",
                "icon_color": "#12abcd",
            },
        )
        assert response.status_code == 200, response.json()
        target = ModuleInstallation.objects.get(
            user=self.user, module=self.community
        )
        owner = ModuleInstallation.objects.get(
            user=self.user, module__module_name="store"
        )
        saved = owner.config["launcher_display_overrides"][self.community.module_name]
        assert saved == {
            "display_name": "My Lab",
            "icon": "fas fa-microscope",
            "icon_color": "#12abcd",
        }
        assert target.config == {}
        self.community.refresh_from_db()
        assert self.community.label == "Manifest Community"
        assert self.community.icon == "fas fa-flask"

    def test_display_override_changes_only_rendered_display_metadata(self):
        self._post_display(
            self.community.module_name,
            {
                "display_name": "My Lab",
                "icon": "fas fa-microscope",
                "icon_color": "#12abcd",
            },
        )
        tile = self._tile(self.community.module_name)
        assert tile["label"] == "My Lab"
        assert tile["icon_fa"] == "fas fa-microscope"
        assert tile["icon_color"] == "#12abcd"
        assert tile["name"] == self.community.module_name
        assert tile["launch_url"] == f"/apps/store/{self.community.module_name}/"
        assert tile["manifest_label"] == "Manifest Community"
        assert tile["manifest_icon_fa"] == "fas fa-flask"

    def test_reset_removes_override_and_restores_manifest_defaults(self):
        self._post_display(
            self.community.module_name,
            {
                "display_name": "My Lab",
                "icon": "fas fa-microscope",
                "icon_color": "#12abcd",
            },
        )
        response = self._post_display(self.community.module_name, {"reset": True})
        assert response.status_code == 200, response.json()
        tile = self._tile(self.community.module_name)
        assert tile["label"] == "Manifest Community"
        assert tile["icon_fa"] == "fas fa-flask"
        assert tile["icon_color"] == ""

    def test_display_endpoint_rejects_unsafe_icon_class(self):
        response = self._post_display(
            self.community.module_name,
            {"display_name": "Safe", "icon": 'fas fa-x" onclick="alert(1)'},
        )
        assert response.status_code == 400

    def test_display_endpoint_rejects_non_hex_icon_color(self):
        response = self._post_display(
            self.community.module_name,
            {"display_name": "Safe", "icon_color": "red; background:url(x)"},
        )
        assert response.status_code == 400

    def test_display_endpoint_requires_authentication(self):
        self.client.logout()
        response = self._post_display(self.community.module_name, {"reset": True})
        assert response.status_code == 302

    def test_favorite_is_an_alias_and_is_stored_on_launcher_owner(self):
        response = self._post_display(self.community.module_name, {"favorite": True})
        assert response.status_code == 200, response.json()

        owner = ModuleInstallation.objects.get(
            user=self.user, module__module_name="store"
        )
        target = ModuleInstallation.objects.get(user=self.user, module=self.community)
        assert owner.config["launcher_favorites"] == [self.community.module_name]
        assert target.config == {}

        page = self.client.get("/apps/")
        favorite = page.context["favorite_tiles"]
        canonical = [
            tile
            for group in page.context["groups"]
            for tile in group["cells"]
            if not tile.get("is_add_slot")
        ]
        assert [tile["name"] for tile in favorite] == [self.community.module_name]
        assert self.community.module_name in [tile["name"] for tile in canonical]
        assert favorite[0]["is_favorite_alias"] is True

    def test_favorite_can_be_removed_without_changing_display_override(self):
        self._post_display(
            self.community.module_name,
            {
                "display_name": "My Lab",
                "icon": "fas fa-microscope",
                "icon_color": "#12abcd",
            },
        )
        self._post_display(self.community.module_name, {"favorite": True})

        response = self._post_display(self.community.module_name, {"favorite": False})
        assert response.status_code == 200, response.json()
        owner = ModuleInstallation.objects.get(
            user=self.user, module__module_name="store"
        )
        assert "launcher_favorites" not in owner.config
        assert owner.config["launcher_display_overrides"][self.community.module_name]
        assert self.client.get("/apps/").context["favorite_tiles"] == []

    def test_launcher_renders_favorites_page_empty_state_and_dialog_action(self):
        html = self.client.get("/apps/").content.decode()
        assert 'data-launcher-fixed-page="favorites"' in html
        assert "No favorites yet" in html
        assert 'id="launcher-display-favorite"' in html
        assert 'data-favorite="0"' in html
