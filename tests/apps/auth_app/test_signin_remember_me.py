"""Signing in with "Remember me" ticked keeps the session across app restarts.

The checkbox was posted as ``remember-me`` while LoginForm reads
``remember_me``, so every sign-in fell into ``set_expiry(0)``: a browser-close
cookie. An iPhone home-screen app drops such a cookie whenever it is closed,
so the operator was asked for a password every time.
"""

import re

import pytest
from django.urls import reverse

from apps.infra.auth_app.forms import LoginForm


@pytest.mark.django_db
def test_signin_checkbox_posts_the_field_login_form_reads(client):
    # Arrange
    path = reverse("auth_app:signin")

    # Act
    html = client.get(path).content.decode()

    # Assert
    assert re.search(r'type="checkbox"[^>]*name="remember_me"', html)


def test_login_form_declares_remember_me():
    # Arrange
    form = LoginForm()

    # Act
    fields = form.fields

    # Assert
    assert "remember_me" in fields


@pytest.mark.django_db
def test_remember_me_sign_in_keeps_a_persistent_session(client, django_user_model):
    # Arrange
    django_user_model.objects.create_user(
        username="remember-probe", email="remember-probe@example.com", password="Remember-Probe-9x!"
    )
    payload = {
        "username": "remember-probe",
        "password": "Remember-Probe-9x!",
        "remember_me": "on",
    }

    # Act
    client.post(reverse("auth_app:signin"), payload)

    # Assert
    assert client.session.get_expire_at_browser_close() is False
