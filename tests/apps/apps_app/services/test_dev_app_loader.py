#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for ``dev_app_loader``'s delegation to ``scitex_app.paths``.

The Phase-2 refactor (0f1dd39cf) replaced local helpers with calls to
``scitex_app.paths`` functions but never imported them, so every public
helper except ``build_module_config`` raised ``NameError`` at call time —
this 500'd ``POST /api/apps/submit/`` on prod (2026-07-07 incident, the
user-install publish flow). Python only resolves module-level names at
call time, so an import-only smoke test cannot catch this; each test
below actually CALLS through one formerly-broken code path.
"""

from apps.workspace.apps_app.services.dev_app_loader import (
    read_manifest,
    resolve_dev_project_dir,
    resolve_dev_template,
    validate_dev_repo,
)


def test_read_manifest_returns_empty_dict_when_manifest_missing(tmp_path):
    # Arrange
    project_dir = tmp_path

    # Act
    manifest = read_manifest(project_dir)

    # Assert
    assert manifest == {}


def test_resolve_dev_project_dir_returns_none_for_unknown_owner_repo():
    # Arrange
    owner, repo = "no-such-owner", "no-such-repo"

    # Act
    project_dir = resolve_dev_project_dir(owner, repo)

    # Assert
    assert project_dir is None


def test_resolve_dev_template_returns_none_for_unknown_dev_module():
    # Arrange
    module_name = "dev__no-such-owner__no-such-repo"

    # Act
    template = resolve_dev_template(module_name)

    # Assert
    assert template is None


def test_validate_dev_repo_rejects_missing_project_directory():
    # Arrange
    owner, repo = "no-such-owner", "no-such-repo"

    # Act
    ok, _message = validate_dev_repo(owner, repo)

    # Assert
    assert ok is False
