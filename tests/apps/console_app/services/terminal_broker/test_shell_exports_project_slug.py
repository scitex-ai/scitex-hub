#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests that Shell exports SCITEX_PROJECT to the child environment.

Background: the in-container setup script runs

    [ -n "$SCITEX_PROJECT" ] && cd /home/$USER/proj/$SCITEX_PROJECT

so an unset ``SCITEX_PROJECT`` silently skips the cd and the shell stays
in whatever cwd srun handed it, which is ``/tmp``. Nothing else set that
variable on the shared-allocation path: the scitex-container ``--env``
flag applies to ``apptainer instance start``, not to the later
``apptainer exec instance://`` used here, which inherits the CALLER env.

The timing is the load-bearing part. ``last_project_slug`` used to be
assigned by the caller AFTER ``shell.spawn()`` returned, but the fork
happens inside ``spawn()`` — so the child was always built from an empty
slug. These tests pin the slug to construction time, which is the only
point early enough to matter.

No mocks: a real Shell is constructed and its real ``_prepare_child_env``
is called. ``restore_cwd`` guards the sibling tests, because
``_prepare_child_env`` performs a real ``os.chdir``.
"""

import os

import pytest

from apps.workspace.console_app.services.terminal_broker.shell import Shell


@pytest.fixture
def restore_cwd():
    """Snapshot and restore CWD — _prepare_child_env really chdirs."""
    # Arrange
    saved = os.getcwd()
    # Act
    yield
    # Assert
    try:
        os.chdir(saved)
    except OSError:
        os.chdir("/tmp")


def _make_shell(project_slug: str = "") -> Shell:
    """Build a Shell without spawning it."""
    return Shell(
        shell_id="shell-1",
        allocation_id="alloc-1",
        username="alice",
        screen_session="scr-1",
        command=["/bin/true"],
        project_slug=project_slug,
    )


class TestSlugIsKnownAtConstruction:
    """The slug must be set by __init__, not by a post-spawn assignment."""

    def test_constructor_stores_the_project_slug(self):
        # Arrange
        slug = "my-paper"
        # Act
        shell = _make_shell(project_slug=slug)
        # Assert
        assert shell.last_project_slug == "my-paper"

    def test_slug_defaults_to_empty_when_not_supplied(self):
        # Arrange
        expected = ""
        # Act
        shell = _make_shell()
        # Assert
        assert shell.last_project_slug == expected


class TestChildEnvCarriesTheProjectSlug:
    """_prepare_child_env is what the forked child actually reads."""

    def test_child_env_exports_scitex_project(self, restore_cwd):
        # Arrange
        shell = _make_shell(project_slug="my-paper")
        # Act
        env = shell._prepare_child_env()
        # Assert
        assert env["SCITEX_PROJECT"] == "my-paper"

    def test_child_env_also_exports_the_apptainer_prefixed_form(
        self, restore_cwd
    ):
        """APPTAINERENV_ survives --cleanenv on the legacy exec path."""
        # Arrange
        shell = _make_shell(project_slug="my-paper")
        # Act
        env = shell._prepare_child_env()
        # Assert
        assert env["APPTAINERENV_SCITEX_PROJECT"] == "my-paper"

    def test_no_slug_means_the_variable_is_absent_not_empty(self, restore_cwd):
        """An empty value would make the setup script's -n guard misleading."""
        # Arrange
        shell = _make_shell()
        # Act
        env = shell._prepare_child_env()
        # Assert
        assert "SCITEX_PROJECT" not in env


# EOF
