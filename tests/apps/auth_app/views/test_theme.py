#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/infra/auth_app/views/theme.py.

Theme resolution contract (card hub-theme-default-must-be-dark):

- Anonymous / first-visit default is DARK (``source: "default"``).
- A REGISTERED user's saved preference keeps winning
  (``source: "profile"``).
"""

import json

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

GET_THEME = reverse("auth_app:api_get_theme")
SAVE_THEME = reverse("auth_app:api_save_theme")


def _login_with_saved_theme(client, django_user_model, username, theme):
    """Log a fresh user in, then save ``theme`` via the real endpoint.

    Goes through POST save-theme (rather than stamping the row) so the
    ``theme_explicit`` flag is set exactly as in production. The POST
    lands AFTER ``force_login``: login updates ``User`` which fires a
    post_save receiver re-saving a cached ``auth_profile`` instance —
    stamping first would be silently clobbered back to the default.
    """
    user = django_user_model.objects.create_user(username=username, password="x")
    client.force_login(user)
    resp = client.post(
        SAVE_THEME,
        data=json.dumps({"theme": theme}),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.content
    return user


@pytest.fixture
def anon_get(client):
    return client.get(GET_THEME).json()





@pytest.fixture
def registered_light_get(client, django_user_model):
    """get-theme as a registered user who explicitly saved light."""
    _login_with_saved_theme(client, django_user_model, "alice", "light")
    return client.get(GET_THEME).json()




@pytest.fixture
def registered_save(client, django_user_model):
    """save-theme(light) as a registered user."""
    user = django_user_model.objects.create_user(username="carol", password="x")
    client.force_login(user)
    resp = client.post(
        SAVE_THEME,
        data=json.dumps({"theme": "light"}),
        content_type="application/json",
    )
    return user, resp


class TestGetThemeAnonymous:
    def test_anonymous_theme_is_dark(self, anon_get):
        # Arrange
        data = anon_get
        # Act
        theme = data["theme"]
        # Assert
        assert theme == "dark"

    def test_anonymous_source_is_default(self, anon_get):
        # Arrange
        data = anon_get
        # Act
        source = data["source"]
        # Assert
        assert source == "default"


class TestGetThemeRegistered:
    def test_saved_light_preference_wins(self, registered_light_get):
        # Arrange
        data = registered_light_get
        # Act
        theme = data["theme"]
        # Assert
        assert theme == "light"

    def test_saved_preference_source_is_profile(self, registered_light_get):
        # Arrange
        data = registered_light_get
        # Act
        source = data["source"]
        # Assert
        assert source == "profile"

    def test_fresh_registered_profile_defaults_dark(
        self, client, django_user_model
    ):
        # Arrange
        user = django_user_model.objects.create_user(
            username="bob", password="x"
        )
        client.force_login(user)
        # Act
        data = client.get(GET_THEME).json()
        # Assert
        assert data["theme"] == "dark"

    def test_fresh_registered_profile_source_is_default_not_profile(
        self, client, django_user_model
    ):
        # Arrange: auto-created row (never explicitly saved).
        # A source of "profile" here would clobber a stored browser
        # light choice back to dark on every load (card
        # stats-dark-theme-forced-20261018).
        user = django_user_model.objects.create_user(
            username="bob2", password="x"
        )
        client.force_login(user)
        # Act
        data = client.get(GET_THEME).json()
        # Assert
        assert data["source"] == "default"

    def test_code_theme_only_update_does_not_stamp_explicit(
        self, client, django_user_model
    ):
        # Arrange: code-theme-only save must not mark the base theme
        # as an explicit choice.
        user = django_user_model.objects.create_user(
            username="erin", password="x"
        )
        client.force_login(user)
        resp = client.post(
            SAVE_THEME,
            data=json.dumps({"code_theme_dark": "dracula"}),
            content_type="application/json",
        )
        assert resp.status_code == 200, resp.content
        # Act
        data = client.get(GET_THEME).json()
        # Assert
        assert data["source"] == "default"
        user.refresh_from_db()
        assert user.auth_profile.theme_explicit is False


class TestSaveThemeAnonymous:
    def test_anonymous_save_is_rejected_401(self, client):
        # Arrange
        payload = json.dumps({"theme": "light"})
        # Act
        resp = client.post(
            SAVE_THEME, data=payload, content_type="application/json"
        )
        # Assert
        assert resp.status_code == 401


class TestSaveThemeRegistered:
    def test_registered_save_is_persisted_flag(self, registered_save):
        # Arrange
        _, resp = registered_save
        # Act
        data = resp.json()
        # Assert
        assert data["persisted"] is True

    def test_registered_save_updates_profile_row(self, registered_save):
        # Arrange
        user, _ = registered_save
        # Act
        user.refresh_from_db()
        # Assert
        assert user.auth_profile.theme_preference == "light"

    def test_invalid_theme_value_rejected_400(self, client, django_user_model):
        # Arrange
        user = django_user_model.objects.create_user(
            username="dave", password="x"
        )
        client.force_login(user)
        # Act
        resp = client.post(
            SAVE_THEME,
            data=json.dumps({"theme": "auto"}),
            content_type="application/json",
        )
        # Assert
        assert resp.status_code == 400


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
