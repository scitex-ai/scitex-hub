#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deployed settings do not depend on generic env vars for safety switches.

Staging is reachable from the internet, so it must behave like production:
DEBUG off whatever a ``DEBUG`` env var says, session and CSRF cookies marked
Secure, HSTS sent. Every environment holds at most a bounded non-file request
body in memory and streams large uploaded files to disk.

The staging module is imported in a subprocess with the real configuration a
deployment supplies (the same mapping the logging gate uses), plus ``DEBUG=1``
in the environment, and the composed values are read back from a file.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    TemporaryUploadedFile,
)
from django.http import HttpResponse
from django.test import Client, override_settings
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

REPO_ROOT = Path(__file__).resolve().parents[2]

STAGING_REQUIRED_CONFIG = {
    "SCITEX_HUB_ENV": "staging",
    "SCITEX_HUB_DJANGO_SECRET_KEY": "test-only-never-a-real-secret",
    "SCITEX_HUB_GITEA_SSH_PORT": "2232",
    "SCITEX_HUB_POSTGRES_PASSWORD": "test-only-never-connected-with",
}

_PROBE = """
import importlib, json, sys

module = importlib.import_module("config.settings." + sys.argv[1])
names = sys.argv[3].split(",")
payload = {name: getattr(module, name, None) for name in names}
with open(sys.argv[2], "w", encoding="utf-8") as fh:
    json.dump(payload, fh, default=list)
"""

_PROBED = (
    "DEBUG",
    "SESSION_COOKIE_SECURE",
    "CSRF_COOKIE_SECURE",
    "SECURE_HSTS_SECONDS",
    "SECURE_PROXY_SSL_HEADER",
    "EDGE_HTTPS_REDIRECT",
    "FILE_UPLOAD_MAX_MEMORY_SIZE",
    "DATA_UPLOAD_MAX_MEMORY_SIZE",
)


def _compose(settings_module: str, extra_env: dict[str, str]) -> dict:
    env = dict(os.environ)
    env.update(STAGING_REQUIRED_CONFIG)
    env.update(extra_env)
    workdir = tempfile.mkdtemp(prefix="hub-settings-gate-")
    env["SCITEX_HUB_LOG_DIR"] = workdir
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    out = Path(workdir) / "settings.json"
    completed = subprocess.run(
        [sys.executable, "-c", _PROBE, settings_module, str(out), ",".join(_PROBED)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    return json.loads(out.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def staging() -> dict:
    # A stray DEBUG=1 in a shared env file must not turn debug pages on.
    return _compose("settings_staging", {"DEBUG": "1"})


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("DEBUG", False),
        ("SESSION_COOKIE_SECURE", True),
        ("CSRF_COOKIE_SECURE", True),
        ("EDGE_HTTPS_REDIRECT", True),
        ("SECURE_PROXY_SSL_HEADER", ["HTTP_X_FORWARDED_PROTO", "https"]),
    ],
)
def test_staging_setting_has_production_value_despite_debug_env(staging, name, expected):
    # Arrange
    composed = staging
    # Act
    value = composed[name]
    # Assert
    assert value == expected


def test_staging_sends_hsts_for_at_least_a_year(staging):
    # Arrange
    composed = staging
    # Act
    seconds = composed["SECURE_HSTS_SECONDS"]
    # Assert
    assert seconds >= 31_536_000


@pytest.mark.parametrize(
    ("name", "ceiling"),
    [
        ("FILE_UPLOAD_MAX_MEMORY_SIZE", 10 * 1024 * 1024),  # stx-allow: STX-NL001
        ("DATA_UPLOAD_MAX_MEMORY_SIZE", 20 * 1024 * 1024),  # stx-allow: STX-NL001
    ],
)
def test_staging_request_body_memory_limit_is_bounded(staging, name, ceiling):
    # Arrange
    composed = staging
    # Act
    value = composed[name]
    # Assert
    assert 0 < value <= ceiling


# --- uploads stream to disk (real request through the Django test client) ---

_seen: dict[str, type] = {}


@csrf_exempt
def _record_upload(request):
    if "file" in request.FILES:
        _seen["type"] = type(request.FILES["file"])
    else:
        request.POST  # noqa: B018 - parse the body so its size limit applies
    return HttpResponse("ok")


urlpatterns = [path("upload/", _record_upload)]


def _post_file(size: int):
    from io import BytesIO

    _seen.clear()
    payload = BytesIO(b"x" * size)
    payload.name = "data.bin"
    Client().post("/upload/", {"file": payload})
    return _seen.get("type")


@override_settings(ROOT_URLCONF=__name__)
def test_upload_above_memory_limit_is_written_to_a_temporary_file():
    # Arrange
    from django.conf import settings

    size = settings.FILE_UPLOAD_MAX_MEMORY_SIZE + 1
    # Act
    stored_as = _post_file(size)
    # Assert
    assert stored_as is TemporaryUploadedFile


@override_settings(ROOT_URLCONF=__name__)
def test_small_upload_stays_in_memory():
    # Arrange
    size = 1024  # stx-allow: STX-NL001
    # Act
    stored_as = _post_file(size)
    # Assert
    assert stored_as is InMemoryUploadedFile


@override_settings(ROOT_URLCONF=__name__)
def test_oversized_non_file_body_is_refused():
    # Arrange
    from django.conf import settings

    body = "a=" + "x" * (settings.DATA_UPLOAD_MAX_MEMORY_SIZE + 1)
    # Act
    response = Client().post(
        "/upload/", body, content_type="application/x-www-form-urlencoded"
    )
    # Assert
    assert response.status_code == 400
