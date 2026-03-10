#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/console_app/views/terminal/dotfiles.py

Covers:
- create_dotfiles_repo: file creation, content correctness, git calls
- create_dotfiles_symlinks: symlink creation, targets, overwrite behaviour
"""

import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from apps.workspace.console_app.views.terminal.dotfiles import (
    create_dotfiles_repo,
    create_dotfiles_symlinks,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USERNAME = "testuser"


def _make_dotfiles_dir(tmp_path: Path) -> Path:
    d = tmp_path / "dotfiles"
    d.mkdir()
    return d


def _make_user_data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "user_data"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# create_dotfiles_repo – file existence
# ---------------------------------------------------------------------------


class TestCreateDotfilesRepoFiles:
    """All expected files are written by create_dotfiles_repo."""

    @pytest.fixture(autouse=True)
    def _run(self, tmp_path):
        self.dotfiles_dir = _make_dotfiles_dir(tmp_path)
        with patch("subprocess.run"):
            create_dotfiles_repo(self.dotfiles_dir, USERNAME)

    def test_bashrc_created(self):
        assert (self.dotfiles_dir / "bashrc").is_file()

    def test_bash_profile_created(self):
        assert (self.dotfiles_dir / "bash_profile").is_file()

    def test_vimrc_created(self):
        assert (self.dotfiles_dir / "vimrc").is_file()

    def test_gitconfig_created(self):
        assert (self.dotfiles_dir / "gitconfig").is_file()

    def test_screenrc_created(self):
        assert (self.dotfiles_dir / "screenrc").is_file()

    def test_install_sh_created(self):
        assert (self.dotfiles_dir / "install.sh").is_file()

    def test_readme_created(self):
        assert (self.dotfiles_dir / "README.md").is_file()

    def test_gitignore_created(self):
        assert (self.dotfiles_dir / ".gitignore").is_file()

    def test_ipython_config_created(self):
        assert (self.dotfiles_dir / "ipython" / "ipython_config.py").is_file()


# ---------------------------------------------------------------------------
# create_dotfiles_repo – content correctness
# ---------------------------------------------------------------------------


class TestCreateDotfilesRepoContent:
    """Key content assertions for generated config files."""

    @pytest.fixture(autouse=True)
    def _run(self, tmp_path):
        self.dotfiles_dir = _make_dotfiles_dir(tmp_path)
        with patch("subprocess.run"):
            create_dotfiles_repo(self.dotfiles_dir, USERNAME)

    # bashrc

    def test_bashrc_contains_username_in_ps1(self):
        content = (self.dotfiles_dir / "bashrc").read_text()
        assert USERNAME in content, "bashrc must reference username (e.g. in PS1)"

    def test_bashrc_ps1_contains_scitex_host(self):
        content = (self.dotfiles_dir / "bashrc").read_text()
        assert "PS1" in content
        assert "scitex" in content

    # gitconfig

    def test_gitconfig_contains_username_in_user_section(self):
        content = (self.dotfiles_dir / "gitconfig").read_text()
        assert f"name = {USERNAME}" in content

    def test_gitconfig_contains_username_email(self):
        content = (self.dotfiles_dir / "gitconfig").read_text()
        assert f"{USERNAME}@scitex.cloud" in content

    # install.sh permissions

    def test_install_sh_is_executable(self):
        mode = (self.dotfiles_dir / "install.sh").stat().st_mode
        # Owner execute bit must be set
        assert mode & stat.S_IXUSR, "install.sh must have owner-execute permission"

    def test_install_sh_mode_is_0o755(self):
        mode = (self.dotfiles_dir / "install.sh").stat().st_mode
        assert stat.S_IMODE(mode) == 0o755

    # README

    def test_readme_contains_username(self):
        content = (self.dotfiles_dir / "README.md").read_text()
        assert USERNAME in content


# ---------------------------------------------------------------------------
# create_dotfiles_repo – git commands
# ---------------------------------------------------------------------------


class TestCreateDotfilesRepoGit:
    """subprocess.run is called for git init, add, and commit."""

    @pytest.fixture(autouse=True)
    def _run(self, tmp_path):
        self.dotfiles_dir = _make_dotfiles_dir(tmp_path)

    def _collect_git_calls(self, mock_run):
        """Return list of first-arg tuples from all subprocess.run calls."""
        return [c.args[0] for c in mock_run.call_args_list]

    def test_git_init_called(self):
        with patch("subprocess.run") as mock_run:
            create_dotfiles_repo(self.dotfiles_dir, USERNAME)
        cmds = self._collect_git_calls(mock_run)
        assert ["git", "init"] in cmds

    def test_git_add_called(self):
        with patch("subprocess.run") as mock_run:
            create_dotfiles_repo(self.dotfiles_dir, USERNAME)
        cmds = self._collect_git_calls(mock_run)
        assert ["git", "add", "-A"] in cmds

    def test_git_commit_called(self):
        with patch("subprocess.run") as mock_run:
            create_dotfiles_repo(self.dotfiles_dir, USERNAME)
        cmds = self._collect_git_calls(mock_run)
        commit_cmds = [c for c in cmds if c[:2] == ["git", "commit"]]
        assert commit_cmds, "git commit must be called"

    def test_git_commit_env_contains_author_name(self):
        with patch("subprocess.run") as mock_run:
            create_dotfiles_repo(self.dotfiles_dir, USERNAME)
        # Find the commit call
        commit_call = next(
            c for c in mock_run.call_args_list if c.args[0][:2] == ["git", "commit"]
        )
        env = commit_call.kwargs.get("env", {})
        assert env.get("GIT_AUTHOR_NAME") == USERNAME

    def test_git_failure_does_not_raise(self, tmp_path):
        """A git failure must be swallowed (non-critical path)."""
        dotfiles_dir = tmp_path / "dotfiles_git_fail"
        dotfiles_dir.mkdir()
        with patch(
            "apps.workspace.console_app.views.terminal.dotfiles.sp.run",
            side_effect=Exception("git not found"),
        ):
            # Must not raise
            create_dotfiles_repo(dotfiles_dir, USERNAME)

    def test_git_called_with_cwd_equal_to_dotfiles_dir(self):
        with patch("subprocess.run") as mock_run:
            create_dotfiles_repo(self.dotfiles_dir, USERNAME)
        for c in mock_run.call_args_list:
            assert c.kwargs.get("cwd") == self.dotfiles_dir


# ---------------------------------------------------------------------------
# create_dotfiles_symlinks – symlink existence
# ---------------------------------------------------------------------------


class TestCreateDotfilesSymlinksExistence:
    """All expected symlinks are created in user_data_dir."""

    @pytest.fixture(autouse=True)
    def _run(self, tmp_path):
        self.user_data_dir = _make_user_data_dir(tmp_path)
        self.dotfiles_dir = _make_dotfiles_dir(tmp_path)
        create_dotfiles_symlinks(self.user_data_dir, self.dotfiles_dir)

    def test_bashrc_symlink_exists(self):
        assert (self.user_data_dir / ".bashrc").is_symlink()

    def test_bash_profile_symlink_exists(self):
        assert (self.user_data_dir / ".bash_profile").is_symlink()

    def test_vimrc_symlink_exists(self):
        assert (self.user_data_dir / ".vimrc").is_symlink()

    def test_gitconfig_symlink_exists(self):
        assert (self.user_data_dir / ".gitconfig").is_symlink()

    def test_screenrc_symlink_exists(self):
        assert (self.user_data_dir / ".screenrc").is_symlink()

    def test_ipython_config_symlink_exists(self):
        ipython_config = (
            self.user_data_dir / ".ipython" / "profile_default" / "ipython_config.py"
        )
        assert ipython_config.is_symlink()


# ---------------------------------------------------------------------------
# create_dotfiles_symlinks – symlink targets (relative paths)
# ---------------------------------------------------------------------------


class TestCreateDotfilesSymlinkTargets:
    """Symlinks point to the correct relative paths."""

    @pytest.fixture(autouse=True)
    def _run(self, tmp_path):
        self.user_data_dir = _make_user_data_dir(tmp_path)
        self.dotfiles_dir = _make_dotfiles_dir(tmp_path)
        create_dotfiles_symlinks(self.user_data_dir, self.dotfiles_dir)

    def _link_target(self, name: str) -> str:
        return os.readlink(self.user_data_dir / name)

    def test_bashrc_target(self):
        assert self._link_target(".bashrc") == "proj/dotfiles/bashrc"

    def test_bash_profile_target(self):
        assert self._link_target(".bash_profile") == "proj/dotfiles/bash_profile"

    def test_vimrc_target(self):
        assert self._link_target(".vimrc") == "proj/dotfiles/vimrc"

    def test_gitconfig_target(self):
        assert self._link_target(".gitconfig") == "proj/dotfiles/gitconfig"

    def test_screenrc_target(self):
        assert self._link_target(".screenrc") == "proj/dotfiles/screenrc"

    def test_ipython_config_target(self):
        ipython_config = (
            self.user_data_dir / ".ipython" / "profile_default" / "ipython_config.py"
        )
        target = os.readlink(ipython_config)
        assert target == "../../proj/dotfiles/ipython/ipython_config.py"


# ---------------------------------------------------------------------------
# create_dotfiles_symlinks – overwrite behaviour
# ---------------------------------------------------------------------------


class TestCreateDotfilesSymlinksOverwrite:
    """Existing files and symlinks are replaced without error."""

    def test_overwrites_existing_regular_file(self, tmp_path):
        user_data_dir = _make_user_data_dir(tmp_path)
        dotfiles_dir = _make_dotfiles_dir(tmp_path)

        # Pre-create a plain file where the symlink will go
        (user_data_dir / ".bashrc").write_text("old content")

        # Must not raise and must replace with a symlink
        create_dotfiles_symlinks(user_data_dir, dotfiles_dir)

        assert (user_data_dir / ".bashrc").is_symlink()

    def test_overwrites_existing_symlink(self, tmp_path):
        user_data_dir = _make_user_data_dir(tmp_path)
        dotfiles_dir = _make_dotfiles_dir(tmp_path)

        # Pre-create a stale symlink
        (user_data_dir / ".bashrc").symlink_to("/dev/null")

        create_dotfiles_symlinks(user_data_dir, dotfiles_dir)

        assert os.readlink(user_data_dir / ".bashrc") == "proj/dotfiles/bashrc"

    def test_overwrites_existing_ipython_config_symlink(self, tmp_path):
        user_data_dir = _make_user_data_dir(tmp_path)
        dotfiles_dir = _make_dotfiles_dir(tmp_path)

        # Pre-create the ipython directory and a stale symlink
        ipython_profile = user_data_dir / ".ipython" / "profile_default"
        ipython_profile.mkdir(parents=True)
        (ipython_profile / "ipython_config.py").symlink_to("/dev/null")

        create_dotfiles_symlinks(user_data_dir, dotfiles_dir)

        target = os.readlink(ipython_profile / "ipython_config.py")
        assert target == "../../proj/dotfiles/ipython/ipython_config.py"

    def test_idempotent_second_call(self, tmp_path):
        """Calling create_dotfiles_symlinks twice must not raise."""
        user_data_dir = _make_user_data_dir(tmp_path)
        dotfiles_dir = _make_dotfiles_dir(tmp_path)

        create_dotfiles_symlinks(user_data_dir, dotfiles_dir)
        # Second call – all symlinks already exist
        create_dotfiles_symlinks(user_data_dir, dotfiles_dir)

        assert (user_data_dir / ".bashrc").is_symlink()


# ---------------------------------------------------------------------------
# create_dotfiles_symlinks – ipython directory creation
# ---------------------------------------------------------------------------


class TestCreateDotfilesSymlinksIpythonDir:
    """Nested .ipython/profile_default directory is created as needed."""

    def test_ipython_profile_default_dir_created(self, tmp_path):
        user_data_dir = _make_user_data_dir(tmp_path)
        dotfiles_dir = _make_dotfiles_dir(tmp_path)

        # Directory must NOT exist beforehand
        assert not (user_data_dir / ".ipython").exists()

        create_dotfiles_symlinks(user_data_dir, dotfiles_dir)

        assert (user_data_dir / ".ipython" / "profile_default").is_dir()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__), "-v"])

# EOF
