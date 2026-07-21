#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_hub/_cli/test_verb_renames.py

"""Slice 6a pilot verb renames — canonical names + deprecation ladder.

Renames under test (doctrine §1d / deprecation ladder §11, warn phase,
removed in v0.20):

* ``show-status``  -> ``status``
* ``show-logs``    -> ``logs``
* ``setup-environment`` -> ``init`` (``setup`` stays an error redirect)
* ``deploy-project``    -> ``deploy``
* ``sync-to``      -> ``workspace push``
* ``sync-from``    -> ``workspace pull``
* ``sync-status``  -> ``workspace status``
* ``ss``           -> ``workspace status`` (banned short alias)

The warn-phase aliases and the spec-built categorized root help come
from scitex-dev's ``click_compat``/``help_spec`` helpers, which are not
in a scitex-dev release yet — those tests skip on a released scitex-dev
(see ``scitex_hub._cli._click_compat``; scitex-python#352 precedent).

No mocks: every test drives the real ``main`` group via ``CliRunner``.
The alias forwarding tests use side-effect-free invocations only
(``--dry-run`` early exits, ``--json`` envelope paths, or an isolated
non-git directory that stops the target before any network call).
"""

from __future__ import annotations

import os

import pytest
from click.testing import CliRunner

from scitex_hub._cli._click_compat import HAS_CLI_HELPERS
from scitex_hub._cli.main import main

requires_cli_helpers = pytest.mark.skipif(
    not HAS_CLI_HELPERS,
    reason=(
        "released scitex-dev lacks click_compat/help_spec "
        "(warn aliases + spec help skipped; see _click_compat.py)"
    ),
)


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture(autouse=True)
def fresh_warn_marker_dir(tmp_path):
    """Isolate the once-per-shell warning marker so every test warns.

    The warn-phase alias writes a once-per-shell marker file under
    ``$XDG_RUNTIME_DIR``; pointing it at a per-test tmp dir keeps tests
    order-independent (real env var, restored on teardown).
    """
    previous = os.environ.get("XDG_RUNTIME_DIR")
    os.environ["XDG_RUNTIME_DIR"] = str(tmp_path)
    yield
    if previous is None:
        os.environ.pop("XDG_RUNTIME_DIR", None)
    else:
        os.environ["XDG_RUNTIME_DIR"] = previous


# ── Canonical names work (both scitex-dev generations) ──────────


class TestCanonicalNames:
    """Each new canonical name resolves and renders help."""

    def test_status_canonical_name_renders_help(self, runner):
        """``status --help`` exits 0 with the --env option."""
        # Arrange
        args = ["status", "--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert result.exit_code == 0 and "--env" in result.output

    def test_logs_canonical_name_renders_help(self, runner):
        """``logs --help`` exits 0 with the --tail option."""
        # Arrange
        args = ["logs", "--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert result.exit_code == 0 and "--tail" in result.output

    def test_init_canonical_name_renders_help(self, runner):
        """``init --help`` exits 0 with the --env option."""
        # Arrange
        args = ["init", "--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert result.exit_code == 0 and "--env" in result.output

    def test_deploy_canonical_name_renders_help(self, runner):
        """``deploy --help`` exits 0 with the --build option."""
        # Arrange
        args = ["deploy", "--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert result.exit_code == 0 and "--build" in result.output

    def test_workspace_push_canonical_name_renders_help(self, runner):
        """``workspace push --help`` exits 0 with the --dry-run flag."""
        # Arrange
        args = ["workspace", "push", "--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert result.exit_code == 0 and "--dry-run" in result.output

    def test_workspace_pull_canonical_name_renders_help(self, runner):
        """``workspace pull --help`` exits 0 with the --dry-run flag."""
        # Arrange
        args = ["workspace", "pull", "--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert result.exit_code == 0 and "--dry-run" in result.output

    def test_workspace_status_canonical_name_renders_help(self, runner):
        """``workspace status --help`` exits 0 with the --json flag."""
        # Arrange
        args = ["workspace", "status", "--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert result.exit_code == 0 and "--json" in result.output

    def test_workspace_status_dry_run_exits_with_code_zero(self, runner):
        """``workspace status --dry-run`` short-circuits before any probe."""
        # Arrange
        args = ["workspace", "status", "--dry-run"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert result.exit_code == 0 and "[dry-run]" in result.output


# ── Old names: warn-phase forwarding (needs scitex-dev develop) ──


@requires_cli_helpers
class TestWarnPhaseAliases:
    """Old spellings warn on stderr and forward to the new command."""

    def test_show_status_alias_warns_and_forwards_json_envelope(self, runner):
        """``show-status --json`` warns then emits the status envelope."""
        # Arrange
        args = ["show-status", "--json"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert (
            result.exit_code == 0
            and "deprecated" in result.stderr
            and '"success"' in result.output
        )

    def test_show_logs_alias_warns_and_forwards_json_envelope(self, runner):
        """``show-logs --json`` warns then emits the logs envelope."""
        # Arrange
        args = ["show-logs", "--json"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert (
            result.exit_code == 0
            and "deprecated" in result.stderr
            and '"success"' in result.output
        )

    def test_setup_environment_alias_warns_and_forwards_dry_run(self, runner):
        """``setup-environment --env dev --dry-run`` warns then dry-runs init."""
        # Arrange
        args = ["setup-environment", "--env", "dev", "--dry-run"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert (
            result.exit_code == 0
            and "deprecated" in result.stderr
            and "[dry-run]" in result.output
        )

    def test_deploy_project_alias_warns_and_forwards_dry_run(self, runner):
        """``deploy-project --dry-run`` warns then dry-runs deploy."""
        # Arrange
        args = ["deploy-project", "--dry-run"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert (
            result.exit_code == 0
            and "deprecated" in result.stderr
            and "[dry-run]" in result.output
        )

    def test_sync_status_alias_warns_and_forwards_dry_run(self, runner):
        """``sync-status --dry-run`` warns then dry-runs workspace status."""
        # Arrange
        args = ["sync-status", "--dry-run"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert (
            result.exit_code == 0
            and "deprecated" in result.stderr
            and "[dry-run]" in result.output
        )

    def test_ss_alias_warns_and_points_at_workspace_status(self, runner):
        """``ss --dry-run`` warns naming ``workspace status`` and forwards."""
        # Arrange
        args = ["ss", "--dry-run"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert (
            result.exit_code == 0
            and "workspace status" in result.stderr
            and "[dry-run]" in result.output
        )

    def test_sync_to_alias_warns_and_reaches_workspace_push_body(self, runner):
        """``sync-to`` warns then runs the real push body up to a guard.

        Invoked from an isolated non-git directory so the forwarded
        command stops at one of its own early guards ("already on the
        workspace" inside a workspace container, "Cannot detect repo"
        elsewhere) before any SSH/network call — proving the alias
        re-dispatched into the real target body.
        """
        # Arrange
        guards = ("Cannot detect repo", "already on the workspace")
        with runner.isolated_filesystem():
            # Act
            result = runner.invoke(main, ["sync-to", "--dry-run"])
        # Assert
        assert "deprecated" in result.stderr and any(
            guard in result.output for guard in guards
        )

    def test_sync_from_alias_warns_and_reaches_workspace_pull_body(self, runner):
        """``sync-from`` warns then runs the real pull body up to a guard."""
        # Arrange
        guards = ("Cannot detect repo", "already on the workspace")
        with runner.isolated_filesystem():
            # Act
            result = runner.invoke(main, ["sync-from", "--dry-run"])
        # Assert
        assert "deprecated" in result.stderr and any(
            guard in result.output for guard in guards
        )

    def test_warning_names_the_removal_version(self, runner):
        """The doctrine warning carries the removed-in version."""
        # Arrange
        args = ["show-status", "--json"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert "removed in v0.20" in result.stderr


# ── setup: error-phase redirect (both scitex-dev generations) ────


class TestSetupErrorRedirect:
    """Bare ``setup`` stays on the error rung, retargeted at init."""

    def test_setup_redirect_exits_with_code_two(self, runner):
        """``setup`` exits 2 without running anything."""
        # Arrange
        args = ["setup"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert result.exit_code == 2

    def test_setup_redirect_points_at_init_on_stderr(self, runner):
        """``setup`` stderr names the ``init`` replacement."""
        # Arrange
        args = ["setup"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert "init" in result.stderr


# ── Root help: categorized sections (needs scitex-dev develop) ───


@requires_cli_helpers
class TestCategorizedRootHelp:
    """Root --help renders the doctrine §4a fixed category headers."""

    def test_root_help_renders_core_category_header(self, runner):
        """Root help contains the ``Core:`` section."""
        # Arrange
        args = ["--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert "Core:" in result.output

    def test_root_help_renders_diagnostics_category_header(self, runner):
        """Root help contains the ``Diagnostics:`` section."""
        # Arrange
        args = ["--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert "Diagnostics:" in result.output

    def test_root_help_renders_no_other_catch_all_section(self, runner):
        """Every command is categorized — ``Other:`` never renders."""
        # Arrange
        args = ["--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert "Other:" not in result.output

    def test_root_help_lists_status_under_diagnostics(self, runner):
        """``status`` renders in the Diagnostics section, not Core."""
        # Arrange
        result = runner.invoke(main, ["--help"])
        diagnostics_block = result.output.split("Diagnostics:")[1].split("\n\n")[0]
        # Act
        found = "status" in diagnostics_block
        # Assert
        assert found


# EOF
