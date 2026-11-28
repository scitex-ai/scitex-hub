#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production serves built assets only; no Vite dev server is reachable.

A Vite dev server compiles and serves files from disk on request. It belongs
to development. These tests read the real production nginx config, the real
production entrypoint, and render the real template tags with production
settings.
"""

from __future__ import annotations

import os
from pathlib import Path

import django
import pytest

REPO = Path(__file__).resolve().parents[2]
NGINX_PROD = REPO / "deployment" / "docker" / "common" / "nginx" / "nginx_prod.conf"
ENTRYPOINT_PROD = REPO / "deployment" / "docker" / "docker_prod" / "entrypoint.sh"
DEV_APP_PORT = "5174"


def _tags():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.settings_dev")
    try:
        django.setup()
    except RuntimeError:
        pass
    import apps.infra.public_app.templatetags.vite as vite_module

    return vite_module


def test_production_nginx_proxies_nothing_to_the_dev_server_port():
    # Arrange
    config = NGINX_PROD.read_text()
    # Act
    hits = [line for line in config.splitlines() if f":{DEV_APP_PORT}" in line]
    # Assert
    assert hits == []


def test_production_entrypoint_starts_no_dev_app_vite():
    # Arrange
    script = ENTRYPOINT_PROD.read_text()
    # Act
    starts_vite = "vite.config.devapp" in script
    # Assert
    assert starts_vite is False


def test_production_hmr_client_tag_is_empty():
    # Arrange
    from django.test import override_settings

    vite = _tags()
    # Act
    with override_settings(DEBUG=False, VITE_DEV_APP_ENABLED=True):
        html = vite.vite_hmr_client()
    # Assert
    assert html == ""


@pytest.fixture
def production_dev_app_tag():
    from django.test import override_settings

    vite = _tags()
    with override_settings(DEBUG=False):
        yield vite.vite_script("someones_dev_app/main")


def test_production_dev_app_entry_points_at_no_dev_server(production_dev_app_tag):
    # Arrange
    html = production_dev_app_tag
    # Act
    references_dev_server = "_vite_dev_app" in html or DEV_APP_PORT in html
    # Assert
    assert references_dev_server is False


def test_production_dev_app_entry_fails_loud(production_dev_app_tag):
    # Arrange
    html = production_dev_app_tag
    # Act
    loud = "console.error" in html and "someones_dev_app/main" in html
    # Assert
    assert loud is True
