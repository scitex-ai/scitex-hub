#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the ``register_livepaper_demo`` management command.

The command is a thin Django ORM wrapper around ``Project.objects.
update_or_create`` plus a filesystem precondition check. The tests
exercise the command end-to-end via ``call_command`` against a real
temporary directory and the real Django ORM (no mocks, per repo
policy STX-NM00x).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command


@pytest.fixture
def live_paper_dir(tmp_path: Path) -> Path:
    """A tmp directory that mimics the live-paper-demo layout the command
    spot-checks (``00_shared/claims.json`` and ``01_manuscript/``).

    Returning ``tmp_path`` itself lets ``--local-path`` point at a real
    on-disk directory so the command's filesystem precondition succeeds
    against reality rather than a mocked stat.
    """
    (tmp_path / "00_shared").mkdir()
    (tmp_path / "00_shared" / "claims.json").write_text("{}")
    (tmp_path / "01_manuscript").mkdir()
    return tmp_path


@pytest.fixture
def owner_user(db):
    """Create the test-user record the command needs as owner.

    Uses the ``db`` fixture from pytest-django so the user is wiped at
    teardown — no global state leakage across tests.
    """
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username="test-user",
        defaults={"email": "test@example.com"},
    )
    return user


class TestRegisterLivepaperDemoCreate:
    """Happy path — the command upserts a Project row pointing at the
    live-paper directory."""

    def test_creates_project_for_owner(self, owner_user, live_paper_dir):
        # Arrange
        from apps.infra.project_app.models import Project

        # Act
        call_command(
            "register_livepaper_demo",
            "--owner=test-user",
            "--slug=live-paper-demo",
            f"--local-path={live_paper_dir}",
        )

        # Assert
        assert Project.objects.filter(owner=owner_user, slug="live-paper-demo").exists()

    def test_local_path_field_is_set(self, owner_user, live_paper_dir):
        # Arrange
        from apps.infra.project_app.models import Project

        # Act
        call_command(
            "register_livepaper_demo",
            "--owner=test-user",
            "--slug=live-paper-demo",
            f"--local-path={live_paper_dir}",
        )

        # Assert
        project = Project.objects.get(owner=owner_user, slug="live-paper-demo")
        assert project.local_path == str(live_paper_dir)


class TestRegisterLivepaperDemoIdempotent:
    """A second run with the same key updates the existing row rather
    than failing on the unique constraint."""

    def test_rerun_does_not_create_duplicate_row(self, owner_user, live_paper_dir):
        # Arrange
        from apps.infra.project_app.models import Project

        call_command(
            "register_livepaper_demo",
            "--owner=test-user",
            "--slug=live-paper-demo",
            f"--local-path={live_paper_dir}",
        )

        # Act
        call_command(
            "register_livepaper_demo",
            "--owner=test-user",
            "--slug=live-paper-demo",
            f"--local-path={live_paper_dir}",
        )

        # Assert
        assert (
            Project.objects.filter(owner=owner_user, slug="live-paper-demo").count()
            == 1
        )


class TestRegisterLivepaperDemoUndo:
    """``--undo`` removes the registration without touching files."""

    def test_undo_removes_existing_project(self, owner_user, live_paper_dir):
        # Arrange
        from apps.infra.project_app.models import Project

        call_command(
            "register_livepaper_demo",
            "--owner=test-user",
            "--slug=live-paper-demo",
            f"--local-path={live_paper_dir}",
        )

        # Act
        call_command(
            "register_livepaper_demo",
            "--owner=test-user",
            "--slug=live-paper-demo",
            "--undo",
        )

        # Assert
        assert not Project.objects.filter(
            owner=owner_user, slug="live-paper-demo"
        ).exists()


class TestRegisterLivepaperDemoErrors:
    """Precondition failures should raise ``CommandError`` instead of
    creating an inconsistent Project row."""

    def test_missing_owner_raises_command_error(self, db, live_paper_dir):
        # Arrange — no owner_user fixture, so 'test-user' does not exist.
        raised: Exception | None = None

        # Act
        try:
            call_command(
                "register_livepaper_demo",
                "--owner=nonexistent-user-12345",
                f"--local-path={live_paper_dir}",
            )
        except CommandError as exc:
            raised = exc

        # Assert
        assert isinstance(raised, CommandError)

    def test_missing_local_path_raises_command_error(self, owner_user, tmp_path):
        # Arrange — point at a directory that has no live-paper layout.
        empty = tmp_path / "empty"
        empty.mkdir()
        raised: Exception | None = None

        # Act
        try:
            call_command(
                "register_livepaper_demo",
                "--owner=test-user",
                f"--local-path={empty}",
            )
        except CommandError as exc:
            raised = exc

        # Assert
        assert isinstance(raised, CommandError)


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
