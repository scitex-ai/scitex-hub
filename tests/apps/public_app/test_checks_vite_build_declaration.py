#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The VITE_USE_BUILD declaration must refuse at boot when no build backs it.

Measured on compute-03 2026-09-06: the public dev preview served a
254,257-byte Django technical 500 -- settings table, locals of 32 frames --
on EVERY route for four days, because SCITEX_HUB_VITE_USE_BUILD=true was set
on a stack that runs a Vite dev server and never runs `vite build`.
get_manifest() swallowed the missing-file OSError, returned {}, and the first
{% vite_script %} tag on the first page a visitor opened raised.

These tests use real files in real temporary directories. No mocks: the thing
under test is whether a path on disk exists, and a mocked filesystem cannot
fail the way the real one did.
"""

import json
import os
from pathlib import Path

import django
import pytest


def setup_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.settings_dev")
    try:
        django.setup()
    except RuntimeError:
        pass  # Already set up


setup_django()


def _write_manifest(base_dir: Path, payload: dict) -> Path:
    """Create a real manifest where the reader expects one, and return it."""
    path = base_dir / "staticfiles" / "vite" / ".vite" / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))
    return path


class TestViteBuildDeclarationCheck:
    def test_flag_off_and_no_build_is_not_an_error(self, tmp_path):
        """Nothing is declared, so nothing can be unhonoured."""
        # Arrange
        from django.test import override_settings

        from apps.infra.public_app.checks import (
            check_vite_build_exists_when_declared,
        )

        # Act
        with override_settings(BASE_DIR=tmp_path, VITE_USE_BUILD=False):
            errors = check_vite_build_exists_when_declared(app_configs=None)

        # Assert
        assert errors == []

    def test_flag_on_without_a_build_is_an_error(self, tmp_path):
        """The RED. This is the state compute-03 was in for four days."""
        # Arrange
        from django.test import override_settings

        from apps.infra.public_app.checks import (
            check_vite_build_exists_when_declared,
        )

        # Act
        with override_settings(BASE_DIR=tmp_path, VITE_USE_BUILD=True):
            errors = check_vite_build_exists_when_declared(app_configs=None)

        # Assert
        assert len(errors) == 1, errors
        assert errors[0].id == "public_app.E001"
        # The operator must be told WHICH path is missing, not merely that
        # something is. An error that does not name the file is half-written.
        assert "manifest.json" in errors[0].msg
        assert "npm run build" in errors[0].hint

    def test_flag_on_with_a_build_passes(self, tmp_path):
        """POSITIVE CONTROL: the check must be able to go green.

        Without this, a check that returned an Error unconditionally would
        pass the test above and look correct.
        """
        # Arrange
        from django.test import override_settings

        from apps.infra.public_app.checks import (
            check_vite_build_exists_when_declared,
        )

        _write_manifest(tmp_path, {"static/shared/ts/x.ts": {"file": "x-abc.js"}})

        # Act
        with override_settings(BASE_DIR=tmp_path, VITE_USE_BUILD=True):
            errors = check_vite_build_exists_when_declared(app_configs=None)

        # Assert
        assert errors == []

    def test_the_check_and_the_reader_resolve_the_same_file(self, tmp_path):
        """The anti-drift control, and the reason manifest_path() exists.

        A guard that validates a DIFFERENT path than the code reads is worse
        than no guard: it reports green over the exact failure it exists to
        catch. So assert the coupling empirically -- one file, created and
        removed, must flip BOTH the check and get_manifest() together.
        """
        # Arrange
        from django.test import override_settings

        from apps.infra.public_app.checks import (
            check_vite_build_exists_when_declared,
        )
        from apps.infra.public_app.templatetags import vite

        payload = {"static/shared/ts/utils/console-interceptor.ts": {"file": "ci.js"}}

        with override_settings(BASE_DIR=tmp_path, VITE_USE_BUILD=True):
            # Act / Assert -- absent: both must report the failure
            vite._manifest_cache = None
            vite._manifest_mtime = 0.0
            assert check_vite_build_exists_when_declared(app_configs=None)
            assert vite.get_manifest() == {}

            # Act / Assert -- present: the SAME file must satisfy both
            written = _write_manifest(tmp_path, payload)
            vite._manifest_cache = None
            vite._manifest_mtime = 0.0
            assert check_vite_build_exists_when_declared(app_configs=None) == []
            assert vite.get_manifest() == payload

            # The reader's own path expression must be that same file.
            assert vite.manifest_path() == written

    def test_the_check_is_registered_so_manage_py_check_runs_it(self):
        """A check nothing invokes is not a check.

        public_app's AppConfig.ready() imports checks for its @register side
        effect; verify the registry actually holds it, rather than trusting
        that the import line is present.
        """
        # Arrange
        from django.core.checks import registry

        # Act
        registered = {c.__name__ for c in registry.registry.get_checks()}

        # Assert
        assert "check_vite_build_exists_when_declared" in registered
