#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The create-app tile serves the SDK wizard; the hub keeps no copy.

The wizard's canonical home is /apps/new/. The compatibility /create-app/
mount serves the same SDK wizard and retains the same login boundary.

Real client, real ORM, real templates; no mocks. One assert per test.
"""

from django.contrib.auth.models import User
from django.test import TestCase


class SdkCreatorMountTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="sdk-creator-mount-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_tile_links_to_the_sdk_wizard(self):
        # Arrange
        self.client.force_login(self.user)

        # Act
        html = self.client.get("/apps/").content.decode("utf-8")
        start = html.index('data-module="create-app"')
        anchor = html[html.rindex("<a", 0, start) : html.index(">", start)]

        # Assert
        assert 'href="/apps/new/"' in anchor

    def test_wizard_requires_login(self):
        # Arrange (signed out)

        # Act
        response = self.client.get("/apps/new/")

        # Assert
        assert response.status_code == 302

    def test_wizard_renders_for_a_signed_in_user(self):
        # Arrange
        self.client.force_login(self.user)

        # Act
        response = self.client.get("/apps/new/")

        # Assert
        assert response.status_code == 200

    def test_wizard_lists_the_sdk_starters(self):
        # Arrange
        self.client.force_login(self.user)

        # Act
        html = self.client.get("/apps/new/").content.decode("utf-8")

        # Assert
        assert 'value="data_entry"' in html

    def test_wizard_health_probe_answers(self):
        # Arrange
        self.client.force_login(self.user)

        # Act
        response = self.client.get("/apps/new/healthz")

        # Assert
        assert response.json() == {"ok": True, "app": "scitex-sdk-creator"}

    def test_hub_starters_are_the_sdk_object(self):
        # Arrange
        import scitex_sdk.creator
        from apps.workspace.apps_app.services import app_create

        # Act
        same = app_create.STARTERS is scitex_sdk.creator.STARTERS

        # Assert
        assert same

    def test_hub_module_naming_is_the_sdk_function(self):
        # Arrange
        import scitex_sdk.creator
        from apps.workspace.apps_app.services import app_create

        # Act
        same = app_create.app_module_name is scitex_sdk.creator.app_module_name

        # Assert
        assert same

    def test_create_app_is_a_reserved_username(self):
        # Arrange
        from apps.infra.auth_app.validators import is_username_reserved

        # Act
        reserved = is_username_reserved("create-app")

        # Assert
        assert reserved

    def test_canonical_creator_prefix_is_a_reserved_username(self):
        # Arrange
        from apps.infra.auth_app.validators import is_username_reserved

        # Act
        reserved = is_username_reserved("new")

        # Assert
        assert reserved

    def test_legacy_wizard_requires_login(self):
        # Arrange — bookmarked URLs keep the real SDK login boundary.
        from django.conf import settings

        # Act
        response = self.client.get("/create-app/")
        outcome = (response.status_code, response["Location"].split("?")[0])

        # Assert
        assert outcome == (302, settings.LOGIN_URL)

    def test_legacy_wizard_serves_the_same_real_sdk_health_view(self):
        # Arrange
        self.client.force_login(self.user)

        # Act
        response = self.client.get("/create-app/healthz")

        # Assert
        assert response.json() == {"ok": True, "app": "scitex-sdk-creator"}


# EOF
