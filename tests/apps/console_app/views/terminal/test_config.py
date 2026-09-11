#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/console_app/views/terminal/config.py"""

import importlib
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from unittest import mock

import pytest


class TestContainerPathInDjango:
    """The Docker-visible alias is configurable independently of SLURM."""

    def test_explicit_docker_path_wins_over_legacy_setting(self):
        config_path = (
            Path(__file__).parents[5]
            / "apps/workspace/console_app/views/terminal/config.py"
        )
        program = textwrap.dedent(
            """
            import importlib.util
            import sys
            import types

            settings = types.SimpleNamespace(
                SINGULARITY_IMAGE_PATH="/legacy/current-sandbox",
                USER_DATA_ROOT="/legacy/users",
            )
            django = types.ModuleType("django")
            django.__path__ = []
            django_conf = types.ModuleType("django.conf")
            django_conf.settings = settings
            sys.modules["django"] = django
            sys.modules["django.conf"] = django_conf

            spec = importlib.util.spec_from_file_location("terminal_config_test", sys.argv[1])
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if module.BASE_CONTAINER_PATH != "/app/singularity/current":
                raise SystemExit(module.BASE_CONTAINER_PATH)
            """
        )
        env = os.environ.copy()
        env["SCITEX_HUB_CONTAINER_PATH_IN_DJANGO"] = "/app/singularity/current"
        result = subprocess.run(
            [sys.executable, "-c", program, str(config_path)],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr or result.stdout


class TestDevReposParsing:
    """Test DEV_REPOS parsing from SCITEX_HUB_DEV_REPOS env var."""

    def _reload_config(self):
        """Reload config module to pick up env changes."""
        import apps.workspace.console_app.views.terminal.config as cfg

        importlib.reload(cfg)
        return cfg

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
