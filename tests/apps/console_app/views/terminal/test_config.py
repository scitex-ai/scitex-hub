#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/console_app/views/terminal/config.py"""

import importlib
import os
from unittest import mock

import pytest


class TestDevReposParsing:
    """Test DEV_REPOS parsing from SCITEX_HUB_DEV_REPOS env var."""

    def _reload_config(self):
        """Reload config module to pick up env changes."""
        import apps.workspace.console_app.views.terminal.config as cfg

        importlib.reload(cfg)
        return cfg

    def teardown_method(self, method):
        """Reload config under the restored (post-patch) environment.

        Each test reloads the shared config module under a patched env; without
        restoring it, the module is left holding test-specific values, which
        leaks into unrelated tests that later import/patch this module (e.g.
        terminal_broker tests patching config.SHOW_MOTD). Reloading here returns
        the module to its real-environment state.
        """
        import apps.workspace.console_app.views.terminal.config as cfg

        importlib.reload(cfg)

    @mock.patch.dict(os.environ, {"SCITEX_HUB_DEV_REPOS": ""}, clear=False)
    def test_empty_env_returns_empty_list(self):
        cfg = self._reload_config()
        assert cfg.DEV_REPOS == []

    @mock.patch.dict(
        os.environ,
        {"SCITEX_HUB_DEV_REPOS": "scitex-python:/home/user/proj/scitex-python:all"},
        clear=False,
    )
    def test_single_repo_parsed(self):
        cfg = self._reload_config()
        assert len(cfg.DEV_REPOS) == 1
        assert cfg.DEV_REPOS[0]["name"] == "scitex-python"
        assert cfg.DEV_REPOS[0]["host_path"] == "/home/user/proj/scitex-python"
        assert cfg.DEV_REPOS[0]["extras"] == "all"

    @mock.patch.dict(
        os.environ,
        {
            "SCITEX_HUB_DEV_REPOS": (
                "scitex-python:/home/user/proj/scitex-python:all,"
                "figrecipe:/home/user/proj/figrecipe:all"
            )
        },
        clear=False,
    )
    def test_multiple_repos_parsed(self):
        cfg = self._reload_config()
        assert len(cfg.DEV_REPOS) == 2
        assert cfg.DEV_REPOS[0]["name"] == "scitex-python"
        assert cfg.DEV_REPOS[1]["name"] == "figrecipe"

    @mock.patch.dict(
        os.environ,
        {"SCITEX_HUB_DEV_REPOS": "myrepo:/some/path"},
        clear=False,
    )
    def test_missing_extras_defaults_to_all(self):
        cfg = self._reload_config()
        assert len(cfg.DEV_REPOS) == 1
        assert cfg.DEV_REPOS[0]["extras"] == "all"

    @mock.patch.dict(
        os.environ,
        {"SCITEX_HUB_DEV_REPOS": "bad-entry"},
        clear=False,
    )
    def test_malformed_entry_skipped(self):
        cfg = self._reload_config()
        assert cfg.DEV_REPOS == []

    @mock.patch.dict(
        os.environ,
        {
            "SCITEX_HUB_DEV_REPOS": (
                "scitex-python:/home/user/proj/scitex-python:all,"
                "bad,"
                "figrecipe:/home/user/proj/figrecipe:all"
            )
        },
        clear=False,
    )
    def test_malformed_entry_among_valid_ones(self):
        cfg = self._reload_config()
        assert len(cfg.DEV_REPOS) == 2
        assert cfg.DEV_REPOS[0]["name"] == "scitex-python"
        assert cfg.DEV_REPOS[1]["name"] == "figrecipe"


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__)])
