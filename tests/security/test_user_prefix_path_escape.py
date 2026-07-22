#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CROSS-TENANT file read via prefix-match path containment.

FINDING (2026-07-22)
    ``apps/infra/llm_app/views/upload.py::api_copy_project_files`` guarded the
    user's data directory with a STRING PREFIX::

        user_base = BASE_DIR/"data"/"users"/<username>
        src = (user_base / "proj" / rel_path).resolve()
        if not str(src).startswith(str(user_base.resolve())):
            continue

    ``str.startswith`` is not path containment. A sibling directory whose name
    merely EXTENDS the username satisfies it: for user ``bob`` the resolved
    path ``/data/users/bob123/proj/secret.txt`` does start with
    ``/data/users/bob``. The endpoint then copies the victim's file into the
    attacker's own downloads directory, where it can be retrieved.

    The endpoint is ``@login_required`` only, so ANY authenticated user can do
    this to any other user whose username extends theirs — and an attacker can
    engineer that prerequisite by registering a username that is a strict
    prefix of the target's.

FIX
    ``validate_path_in_project()`` — component-wise containment via
    ``Path.resolve().relative_to()``.

DESIGN NOTES
- Users are UNSAVED model instances (``pk`` by hand), so the suite never
  touches the test database.
- ``BASE_DIR`` is pointed at a tmp tree, so the exploit runs against a real
  filesystem layout rather than a mock of one.
- Arrange+act live in the fixture so each test carries a single assertion.
"""

import json

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory, override_settings

from apps.infra.llm_app.views import upload as upload_mod

pytestmark = pytest.mark.security

ATTACKER = "bob"
# Victim's username EXTENDS the attacker's — the whole point of the finding.
VICTIM = "bob123"
SECRET = "victim-private-data-must-not-leak\n"


@pytest.fixture
def rf():
    return RequestFactory()


def _user(pk, username):
    User = get_user_model()
    return User(pk=pk, username=username)


def _users_root(tmp_path):
    return tmp_path / "data" / "users"


@pytest.fixture
def escape_run(rf, tmp_path):
    """Attacker asks for a path that climbs into the victim's directory."""
    users = _users_root(tmp_path)
    attacker_proj = users / ATTACKER / "proj"
    attacker_proj.mkdir(parents=True)
    victim_proj = users / VICTIM / "proj"
    victim_proj.mkdir(parents=True)
    (victim_proj / "secret.txt").write_text(SECRET)

    body = {"paths": [f"../../{VICTIM}/proj/secret.txt"]}
    req = rf.post(
        "/apps/llm/api/copy-project-files/",
        data=json.dumps(body),
        content_type="application/json",
    )
    req.user = _user(1, ATTACKER)

    # Call the REAL decorated view — an unsaved User satisfies @login_required,
    # so the decorators are exercised rather than bypassed.
    view = upload_mod.api_copy_project_files
    with override_settings(BASE_DIR=str(tmp_path)):
        resp = view(req)

    downloads = users / ATTACKER / "downloads"
    leaked = [p for p in downloads.iterdir() if p.is_file()] if downloads.exists() else []
    return {
        "resp": resp,
        "payload": json.loads(resp.content),
        "leaked": leaked,
        "leaked_text": [p.read_text() for p in leaked],
    }


def test_cross_tenant_path_is_not_copied(escape_run):
    # Arrange
    payload = escape_run["payload"]
    # Act
    returned = payload.get("paths", [])
    # Assert
    assert returned == [], payload


def test_no_victim_file_lands_in_attacker_downloads(escape_run):
    # Arrange
    leaked = escape_run["leaked"]
    # Act
    names = sorted(p.name for p in leaked)
    # Assert
    assert names == [], f"victim file copied into attacker downloads: {names}"


def test_victim_secret_never_reaches_the_attacker(escape_run):
    # Arrange
    texts = escape_run["leaked_text"]
    # Act
    leaked_secret = any(SECRET.strip() in t for t in texts)
    # Assert
    assert leaked_secret is False


@pytest.fixture
def own_file_run(rf, tmp_path):
    """Anti-regression: the attacker's OWN file must still copy successfully."""
    users = _users_root(tmp_path)
    own_proj = users / ATTACKER / "proj"
    own_proj.mkdir(parents=True)
    (own_proj / "mine.txt").write_text("my own data\n")

    req = rf.post(
        "/apps/llm/api/copy-project-files/",
        data=json.dumps({"paths": ["mine.txt"]}),
        content_type="application/json",
    )
    req.user = _user(1, ATTACKER)

    # Call the REAL decorated view — an unsaved User satisfies @login_required,
    # so the decorators are exercised rather than bypassed.
    view = upload_mod.api_copy_project_files
    with override_settings(BASE_DIR=str(tmp_path)):
        resp = view(req)
    return json.loads(resp.content)


def test_own_file_still_copies(own_file_run):
    # Arrange
    payload = own_file_run
    # Act
    returned = payload.get("paths", [])
    # Assert
    assert len(returned) == 1, payload

# EOF
