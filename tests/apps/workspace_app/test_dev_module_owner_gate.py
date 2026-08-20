#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for the dev-module cross-tenant template read.

Card: sec-dev-module-crosstenant-template-read-20260803

``_serve_dev_module`` used to resolve and render the template BEFORE consulting
the ``DevInstallation`` record, and the ownership lookup gated only the context
builder. So when the record was absent — i.e. the app belonged to SOMEONE ELSE —
``dev_install`` was ``None``, the ``if`` body was skipped, and control fell
through to ``read_text()`` + render anyway. Any logged-in user could render
another tenant's ``index_partial.html``.

That contradicts ``DevInstallation``'s own documented contract: "Dev apps are
personal — only visible to the user who installed them."

Refusals are paired with POSITIVE CONTROLS so no assertion can pass merely
because the thing it looks for is absent, and the victim's file is asserted
READABLE on disk first, so "content not in response" cannot pass vacuously.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from apps.workspace.apps_app.models import DevInstallation

SECRET = "VICTIM-ONLY-TEMPLATE-CONTENT"
SHELL_HEADER = {"HTTP_X_WORKSPACE_SHELL": "1"}
VICTIM_MODULE = "dev__victim__myapp"


@pytest.fixture
def base_dir(tmp_path):
    """A BASE_DIR holding the victim's dev-app template."""
    templates = tmp_path / "data" / "users" / "victim" / "proj" / "myapp" / "templates"
    templates.mkdir(parents=True)
    (templates / "index_partial.html").write_text(f"<p>{SECRET}</p>")
    return tmp_path


@pytest.fixture
def victim_template(base_dir):
    return base_dir / "data/users/victim/proj/myapp/templates/index_partial.html"


@pytest.fixture
def attacker(db):
    return get_user_model().objects.create_user(username="attacker", password="pw-a")


@pytest.fixture
def victim(db):
    return get_user_model().objects.create_user(username="victim", password="pw-v")


def _content_url(module):
    return reverse("workspace_app:module_content", args=[module])


def test_victim_template_really_holds_the_secret(victim_template):
    """RED-EQUIVALENT: the file exists and is readable, so a later 'secret is
    absent from the response' assertion cannot pass for the wrong reason."""
    # Arrange
    path = victim_template
    # Act
    content = path.read_text()
    # Assert
    assert SECRET in content


def test_attacker_is_refused_the_victims_module(base_dir, client, attacker, victim):
    # Arrange
    DevInstallation.objects.create(
        user=victim, source_owner="victim", source_repo="myapp",
        module_name=VICTIM_MODULE, is_enabled=True,
    )
    client.force_login(attacker)
    # Act
    with override_settings(BASE_DIR=base_dir):
        response = client.get(_content_url(VICTIM_MODULE), **SHELL_HEADER)
    # Assert
    assert response.status_code == 404


def test_attacker_response_never_carries_the_victims_content(
    base_dir, client, attacker, victim
):
    """The status code is not the point — the BYTES are."""
    # Arrange
    DevInstallation.objects.create(
        user=victim, source_owner="victim", source_repo="myapp",
        module_name=VICTIM_MODULE, is_enabled=True,
    )
    client.force_login(attacker)
    # Act
    with override_settings(BASE_DIR=base_dir):
        response = client.get(_content_url(VICTIM_MODULE), **SHELL_HEADER)
    # Assert
    assert SECRET not in response.content.decode("utf-8", "replace")


def test_owner_passes_the_ownership_gate(base_dir, client, victim):
    """POSITIVE CONTROL — the gate must not lock the legitimate owner out.

    Asserts only that the owner is NOT refused: whether the render then succeeds
    depends on the Apptainer dev runner, which is out of scope for this test.
    """
    # Arrange
    DevInstallation.objects.create(
        user=victim, source_owner="victim", source_repo="myapp",
        module_name=VICTIM_MODULE, is_enabled=True,
    )
    client.force_login(victim)
    # Act
    with override_settings(BASE_DIR=base_dir):
        response = client.get(_content_url(VICTIM_MODULE), **SHELL_HEADER)
    # Assert
    assert response.status_code != 404


def test_user_without_an_installation_is_refused_their_own_namespace(
    base_dir, client, victim
):
    """The gate keys on the RECORD, not on the username matching the path."""
    # Arrange — victim owns the files on disk but has no DevInstallation row
    client.force_login(victim)
    # Act
    with override_settings(BASE_DIR=base_dir):
        response = client.get(_content_url(VICTIM_MODULE), **SHELL_HEADER)
    # Assert
    assert response.status_code == 404


def test_disabled_installation_is_refused(base_dir, client, victim):
    # Arrange
    DevInstallation.objects.create(
        user=victim, source_owner="victim", source_repo="myapp",
        module_name=VICTIM_MODULE, is_enabled=False,
    )
    client.force_login(victim)
    # Act
    with override_settings(BASE_DIR=base_dir):
        response = client.get(_content_url(VICTIM_MODULE), **SHELL_HEADER)
    # Assert
    assert response.status_code == 404


def test_refusal_is_indistinguishable_from_a_missing_module(
    base_dir, client, attacker, victim
):
    """No username oracle: 'not yours' and 'no such app' must read identically."""
    # Arrange
    DevInstallation.objects.create(
        user=victim, source_owner="victim", source_repo="myapp",
        module_name=VICTIM_MODULE, is_enabled=True,
    )
    client.force_login(attacker)
    # Act
    with override_settings(BASE_DIR=base_dir):
        real_but_not_mine = client.get(_content_url(VICTIM_MODULE), **SHELL_HEADER)
        no_such_module = client.get(
            _content_url("dev__nobody__nothing"), **SHELL_HEADER
        )
    # Assert
    assert real_but_not_mine.status_code == no_such_module.status_code
