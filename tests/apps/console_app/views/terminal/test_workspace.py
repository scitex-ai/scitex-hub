#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/console_app/views/terminal/workspace.py

Covers:
- ensure_workspace: directory structure creation
- ensure_workspace: dotfiles creation on first run (mocked)
- ensure_workspace: idempotency (second call is no-op)
- _patch_bashrc_ai_tools: corruption detection triggers regeneration
- _patch_bashrc_ai_tools: correct bashrc skipped
- _patch_bashrc_ai_tools: missing bashrc returns early
"""

import asyncio
import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers to import the module under test without a running Django stack.
# workspace.py uses a relative import:  from .dotfiles import ...
# We inject a stub package into sys.modules before importing.
# ---------------------------------------------------------------------------

_MODULE_PATH = "apps.workspace.console_app.views.terminal.workspace"
_DOTFILES_PATH = "apps.workspace.console_app.views.terminal.dotfiles"


def _make_stub_dotfiles_package():
    """Return a stub dotfiles module with MagicMock callables."""
    stub = types.ModuleType(_DOTFILES_PATH)
    stub.create_dotfiles_repo = MagicMock()
    stub.create_dotfiles_symlinks = MagicMock()
    return stub


def _import_workspace(stub_dotfiles=None):
    """
    Import (or re-import) the workspace module with a fresh stub for dotfiles.

    Returns (module, stub_dotfiles).
    """
    if stub_dotfiles is None:
        stub_dotfiles = _make_stub_dotfiles_package()

    # Build the intermediate package stubs required for a dotted import
    for pkg in [
        "apps",
        "apps.workspace.console_app",
        "apps.workspace.console_app.views",
        "apps.workspace.console_app.views.terminal",
    ]:
        if pkg not in sys.modules:
            sys.modules[pkg] = types.ModuleType(pkg)

    # Inject the stub dotfiles module
    sys.modules[_DOTFILES_PATH] = stub_dotfiles

    # Force fresh load of workspace each time
    if _MODULE_PATH in sys.modules:
        del sys.modules[_MODULE_PATH]

    module = importlib.import_module(_MODULE_PATH)
    return module, stub_dotfiles


# ===========================================================================
# TestEnsureWorkspaceDirectories
# ===========================================================================


class TestEnsureWorkspaceDirectoryStructure:
    """ensure_workspace must create the expected directory tree."""

    def test_user_data_dir_created(self, tmp_path):
        workspace_dir = tmp_path / "user_home"
        mod, _ = _import_workspace()
        asyncio.run(mod.ensure_workspace(workspace_dir, "alice", "my-project"))
        assert workspace_dir.is_dir()

    def test_proj_subdir_created(self, tmp_path):
        workspace_dir = tmp_path / "user_home"
        mod, _ = _import_workspace()
        asyncio.run(mod.ensure_workspace(workspace_dir, "alice", "my-project"))
        assert (workspace_dir / "proj").is_dir()

    def test_singularity_subdir_created(self, tmp_path):
        workspace_dir = tmp_path / "user_home"
        mod, _ = _import_workspace()
        asyncio.run(mod.ensure_workspace(workspace_dir, "alice", "my-project"))
        assert (workspace_dir / ".singularity").is_dir()

    def test_project_slug_dir_created(self, tmp_path):
        workspace_dir = tmp_path / "user_home"
        mod, _ = _import_workspace()
        asyncio.run(mod.ensure_workspace(workspace_dir, "alice", "my-project"))
        assert (workspace_dir / "proj" / "my-project").is_dir()

    def test_scitex_downloads_dir_created(self, tmp_path):
        workspace_dir = tmp_path / "user_home"
        mod, _ = _import_workspace()
        asyncio.run(mod.ensure_workspace(workspace_dir, "alice", "my-project"))
        assert (workspace_dir / "proj" / "my-project" / "scitex" / "downloads").is_dir()

    def test_works_when_parent_does_not_exist(self, tmp_path):
        """user_data_dir does not need to pre-exist; parents=True handles it."""
        workspace_dir = tmp_path / "a" / "b" / "c"
        mod, _ = _import_workspace()
        asyncio.run(mod.ensure_workspace(workspace_dir, "bob", "proj-slug"))
        assert workspace_dir.is_dir()


# ===========================================================================
# TestEnsureWorkspaceDotfilesCreation
# ===========================================================================


class TestEnsureWorkspaceDotfilesCreation:
    """ensure_workspace must call dotfile helpers on first run."""

    def test_dotfiles_dir_created_on_first_run(self, tmp_path):
        workspace_dir = tmp_path / "user_home"
        mod, stub = _import_workspace()
        asyncio.run(mod.ensure_workspace(workspace_dir, "carol", "proj"))
        assert (workspace_dir / "proj" / "dotfiles").is_dir()

    def test_create_dotfiles_repo_called_once_on_first_run(self, tmp_path):
        workspace_dir = tmp_path / "user_home"
        mod, stub = _import_workspace()
        asyncio.run(mod.ensure_workspace(workspace_dir, "carol", "proj"))
        stub.create_dotfiles_repo.assert_called_once()

    def test_create_dotfiles_repo_called_with_correct_args(self, tmp_path):
        workspace_dir = tmp_path / "user_home"
        mod, stub = _import_workspace()
        asyncio.run(mod.ensure_workspace(workspace_dir, "carol", "proj"))
        expected_dotfiles_dir = workspace_dir / "proj" / "dotfiles"
        stub.create_dotfiles_repo.assert_called_once_with(
            expected_dotfiles_dir, "carol"
        )

    def test_create_dotfiles_symlinks_called_once_on_first_run(self, tmp_path):
        workspace_dir = tmp_path / "user_home"
        mod, stub = _import_workspace()
        asyncio.run(mod.ensure_workspace(workspace_dir, "carol", "proj"))
        stub.create_dotfiles_symlinks.assert_called_once()

    def test_create_dotfiles_symlinks_called_with_correct_args(self, tmp_path):
        workspace_dir = tmp_path / "user_home"
        mod, stub = _import_workspace()
        asyncio.run(mod.ensure_workspace(workspace_dir, "carol", "proj"))
        expected_dotfiles_dir = workspace_dir / "proj" / "dotfiles"
        stub.create_dotfiles_symlinks.assert_called_once_with(
            workspace_dir, expected_dotfiles_dir
        )


# ===========================================================================
# TestEnsureWorkspaceIdempotency
# ===========================================================================


class TestEnsureWorkspaceIdempotency:
    """Calling ensure_workspace a second time must not raise and must not
    call create_dotfiles_repo again (dotfiles dir already exists)."""

    def test_second_call_does_not_raise(self, tmp_path):
        workspace_dir = tmp_path / "user_home"
        mod, stub = _import_workspace()
        asyncio.run(mod.ensure_workspace(workspace_dir, "dave", "proj"))
        # second call - should be fine
        asyncio.run(mod.ensure_workspace(workspace_dir, "dave", "proj"))

    def test_create_dotfiles_repo_not_called_again_on_second_run(self, tmp_path):
        workspace_dir = tmp_path / "user_home"
        mod, stub = _import_workspace()
        asyncio.run(mod.ensure_workspace(workspace_dir, "dave", "proj"))
        call_count_after_first = stub.create_dotfiles_repo.call_count
        asyncio.run(mod.ensure_workspace(workspace_dir, "dave", "proj"))
        # dotfiles dir already exists; must not be called again
        assert stub.create_dotfiles_repo.call_count == call_count_after_first

    def test_directory_structure_intact_after_second_call(self, tmp_path):
        workspace_dir = tmp_path / "user_home"
        mod, stub = _import_workspace()
        asyncio.run(mod.ensure_workspace(workspace_dir, "dave", "proj"))
        asyncio.run(mod.ensure_workspace(workspace_dir, "dave", "proj"))
        assert (workspace_dir / "proj").is_dir()
        assert (workspace_dir / ".singularity").is_dir()
        assert (workspace_dir / "proj" / "proj").is_dir()
        assert (workspace_dir / "proj" / "proj" / "scitex" / "downloads").is_dir()


# ===========================================================================
# TestPatchBashrcAiTools
# ===========================================================================

# A minimal "correct" bashrc that satisfies all required markers.
_CORRECT_BASHRC = """\
# SciTeX Cloud - bashrc
PS1='\\[\\033[01;32m\\]testuser@scitex\\[\\033[00m\\]:\\w \\$ '

# AI CLI tools
if ! command -v claude &>/dev/null && ! [ -f "$HOME/.ai-cli-installed" ]; then
    echo "installing..."
fi

if command -v agents &>/dev/null && [ -d ".agents" ]; then
    agents sync --quiet 2>/dev/null
fi

# Aliases
alias ll='ls -alF'
"""


def _load_patch_func():
    """Return the _patch_bashrc_ai_tools function from a freshly loaded module."""
    mod, _ = _import_workspace()
    return mod._patch_bashrc_ai_tools


class TestPatchBashrcAiToolsNoFile:
    """_patch_bashrc_ai_tools returns early when bashrc does not exist."""

    def test_returns_without_error_when_no_bashrc(self, tmp_path):
        dotfiles_dir = tmp_path / "dotfiles"
        dotfiles_dir.mkdir()
        fn = _load_patch_func()
        # Should not raise
        fn(dotfiles_dir)

    def test_create_dotfiles_repo_not_called_when_no_bashrc(self, tmp_path):
        dotfiles_dir = tmp_path / "dotfiles"
        dotfiles_dir.mkdir()
        mod, stub = _import_workspace()
        mod._patch_bashrc_ai_tools(dotfiles_dir)
        stub.create_dotfiles_repo.assert_not_called()


class TestPatchBashrcAiToolsCorrectContent:
    """_patch_bashrc_ai_tools skips regeneration for a clean bashrc."""

    def test_does_not_call_create_dotfiles_repo_for_correct_bashrc(self, tmp_path):
        dotfiles_dir = tmp_path / "dotfiles"
        dotfiles_dir.mkdir()
        (dotfiles_dir / "bashrc").write_text(_CORRECT_BASHRC)
        mod, stub = _import_workspace()
        mod._patch_bashrc_ai_tools(dotfiles_dir)
        stub.create_dotfiles_repo.assert_not_called()


class TestPatchBashrcAiToolsOrphanedDone:
    """Orphaned 'done' newline pattern triggers regeneration."""

    def _corrupted_content(self):
        return _CORRECT_BASHRC + "\n    done\n"

    def test_orphaned_done_triggers_regeneration(self, tmp_path):
        dotfiles_dir = tmp_path / "dotfiles"
        dotfiles_dir.mkdir()
        (dotfiles_dir / "bashrc").write_text(self._corrupted_content())
        mod, stub = _import_workspace()
        mod._patch_bashrc_ai_tools(dotfiles_dir)
        stub.create_dotfiles_repo.assert_called_once()

    def test_orphaned_done_passes_dotfiles_dir_to_repo_creator(self, tmp_path):
        dotfiles_dir = tmp_path / "dotfiles"
        dotfiles_dir.mkdir()
        (dotfiles_dir / "bashrc").write_text(self._corrupted_content())
        mod, stub = _import_workspace()
        mod._patch_bashrc_ai_tools(dotfiles_dir)
        args = stub.create_dotfiles_repo.call_args[0]
        assert args[0] == dotfiles_dir


class TestPatchBashrcAiToolsDuplicateAgentsSync:
    """Duplicate 'agents sync' entries trigger regeneration."""

    def _corrupted_content(self):
        # Two occurrences of 'agents sync'
        return _CORRECT_BASHRC + "\nagents sync --quiet 2>/dev/null\n"

    def test_duplicate_agents_sync_triggers_regeneration(self, tmp_path):
        dotfiles_dir = tmp_path / "dotfiles"
        dotfiles_dir.mkdir()
        (dotfiles_dir / "bashrc").write_text(self._corrupted_content())
        mod, stub = _import_workspace()
        mod._patch_bashrc_ai_tools(dotfiles_dir)
        stub.create_dotfiles_repo.assert_called_once()


class TestPatchBashrcAiToolsOldDevBlock:
    """'.scitex-dev-installed' remnant triggers regeneration."""

    def _corrupted_content(self):
        return (
            _CORRECT_BASHRC + "\nif [ -f $HOME/.scitex-dev-installed ]; then foo; fi\n"
        )

    def test_old_dev_block_triggers_regeneration(self, tmp_path):
        dotfiles_dir = tmp_path / "dotfiles"
        dotfiles_dir.mkdir()
        (dotfiles_dir / "bashrc").write_text(self._corrupted_content())
        mod, stub = _import_workspace()
        mod._patch_bashrc_ai_tools(dotfiles_dir)
        stub.create_dotfiles_repo.assert_called_once()


class TestPatchBashrcAiToolsOldMotdRemnant:
    """'# Show scitex version' MOTD remnant triggers regeneration."""

    def _corrupted_content(self):
        return _CORRECT_BASHRC + "\n# Show scitex version\necho scitex version\n"

    def test_old_motd_remnant_triggers_regeneration(self, tmp_path):
        dotfiles_dir = tmp_path / "dotfiles"
        dotfiles_dir.mkdir()
        (dotfiles_dir / "bashrc").write_text(self._corrupted_content())
        mod, stub = _import_workspace()
        mod._patch_bashrc_ai_tools(dotfiles_dir)
        stub.create_dotfiles_repo.assert_called_once()


class TestPatchBashrcAiToolsMissingSections:
    """Missing required markers trigger regeneration even without other corruption."""

    def test_missing_ai_cli_marker_triggers_regeneration(self, tmp_path):
        dotfiles_dir = tmp_path / "dotfiles"
        dotfiles_dir.mkdir()
        # Remove '.ai-cli-installed' from content
        content = _CORRECT_BASHRC.replace(".ai-cli-installed", ".REMOVED")
        (dotfiles_dir / "bashrc").write_text(content)
        mod, stub = _import_workspace()
        mod._patch_bashrc_ai_tools(dotfiles_dir)
        stub.create_dotfiles_repo.assert_called_once()

    def test_missing_agents_sync_marker_triggers_regeneration(self, tmp_path):
        dotfiles_dir = tmp_path / "dotfiles"
        dotfiles_dir.mkdir()
        content = _CORRECT_BASHRC.replace("agents sync", "agents REMOVED")
        (dotfiles_dir / "bashrc").write_text(content)
        mod, stub = _import_workspace()
        mod._patch_bashrc_ai_tools(dotfiles_dir)
        stub.create_dotfiles_repo.assert_called_once()

    def test_missing_aliases_marker_triggers_regeneration(self, tmp_path):
        dotfiles_dir = tmp_path / "dotfiles"
        dotfiles_dir.mkdir()
        content = _CORRECT_BASHRC.replace("# Aliases", "# REMOVED")
        (dotfiles_dir / "bashrc").write_text(content)
        mod, stub = _import_workspace()
        mod._patch_bashrc_ai_tools(dotfiles_dir)
        stub.create_dotfiles_repo.assert_called_once()


class TestPatchBashrcAiToolsUsernameExtraction:
    """_patch_bashrc_ai_tools extracts username from PS1 line and passes it
    to create_dotfiles_repo when regenerating."""

    def test_username_extracted_from_ps1_line(self, tmp_path):
        dotfiles_dir = tmp_path / "dotfiles"
        dotfiles_dir.mkdir()
        # Use a corrupted bashrc so regeneration is triggered
        content = _CORRECT_BASHRC + "\n    done\n"
        (dotfiles_dir / "bashrc").write_text(content)
        mod, stub = _import_workspace()
        mod._patch_bashrc_ai_tools(dotfiles_dir)
        stub.create_dotfiles_repo.assert_called_once()
        _, username_arg = stub.create_dotfiles_repo.call_args[0]
        assert username_arg == "testuser"

    def test_username_defaults_to_visitor_when_no_ps1_match(self, tmp_path):
        dotfiles_dir = tmp_path / "dotfiles"
        dotfiles_dir.mkdir()
        # Corrupted content with no PS1 line that matches the regex
        content = "# no PS1\n.ai-cli-installed\nagents sync\n# Aliases\n\n    done\n"
        (dotfiles_dir / "bashrc").write_text(content)
        mod, stub = _import_workspace()
        mod._patch_bashrc_ai_tools(dotfiles_dir)
        stub.create_dotfiles_repo.assert_called_once()
        _, username_arg = stub.create_dotfiles_repo.call_args[0]
        assert username_arg == "visitor"


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])
