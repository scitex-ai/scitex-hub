"""Regression: project RENAME must reject path-traversal names.

`project.name` becomes a filesystem path component (…/users/<user>/<name>) in
services that build workspace paths from it (e.g. gitea_auto_sync builds
Path(f"/app/data/users/{username}/{project.name}")). The CREATE paths validate
the name (Project.validate_repository_name — ^[a-zA-Z0-9._-]+$, no leading/
trailing special → blocks '/' and '..'), but the RENAME endpoints historically
did not, so an authenticated owner could rename to '../../users/victim/proj' and
escape their jail (cross-tenant path traversal). See
sec-nonclass-pathinjection-triage.

DB-FREE by design: the security-regression CI gate runs tests/security/ WITHOUT
a Postgres service, so this file must not touch the DB (no @pytest.mark.django_db)
and — per the no-mock rule — must not fake the ORM either. Instead it exercises
the REAL validator (a pure classmethod, no DB) directly, and statically asserts
both rename endpoints wire it in. The full DB-backed endpoint behaviour is covered
by the pytest-matrix (Postgres) suite, not this gate.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.security

TRAVERSAL_NAME = "../../users/victim/victimproj"

_VIEWS = Path(__file__).resolve().parents[2] / "apps" / "infra" / "project_app" / "views"
_SETTINGS_VIEW = _VIEWS / "settings_views.py"
_EDIT_VIEW = _VIEWS / "projects" / "edit.py"


def test_validate_repository_name_rejects_parent_traversal():
    # Arrange
    from apps.infra.project_app.models import Project

    # Act
    is_valid, _error = Project.validate_repository_name(TRAVERSAL_NAME)
    # Assert
    assert is_valid is False


def test_validate_repository_name_rejects_a_slash():
    # Arrange
    from apps.infra.project_app.models import Project

    # Act
    is_valid, _error = Project.validate_repository_name("a/b/c")
    # Assert
    assert is_valid is False


def test_validate_repository_name_accepts_a_normal_name():
    # Arrange
    from apps.infra.project_app.models import Project

    # Act
    is_valid, _error = Project.validate_repository_name("my-project_1.0")
    # Assert
    assert is_valid is True


def test_settings_rename_endpoint_wires_the_name_validator():
    # Arrange
    source = _SETTINGS_VIEW.read_text(encoding="utf-8")
    # Act
    wired = "validate_repository_name" in source
    # Assert
    assert wired, (
        "settings_views.update_general must call Project.validate_repository_name "
        "on rename (else project.name can traverse)"
    )


def test_project_edit_endpoint_wires_the_name_validator():
    # Arrange
    source = _EDIT_VIEW.read_text(encoding="utf-8")
    # Act
    wired = "validate_repository_name" in source
    # Assert
    assert wired, (
        "projects/edit.py project_edit must call Project.validate_repository_name "
        "on rename (else project.name can traverse)"
    )
