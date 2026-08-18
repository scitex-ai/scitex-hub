#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reality lock: the template marker production verifies must match what
the REAL scitex packages create (fake-vs-real divergence guard, card
hub-integration-smoke-test-suite).

2026-07-08 incident: verification checked ``{project}/scitex/writer``
(no dot) while the real ``scitex_template.clone_scitex_minimal`` /
``scitex_writer.ensure_workspace`` create dot-prefixed
``.scitex/writer`` — so verification NEVER passed, every slot was
quarantined, and prod+staging had zero writable visitor slots. The
security suite stayed green because its fakes fabricated the wrong
(no-dot) layout too. These tests run the REAL packages into a tmp dir
and assert the exact marker path production checks — if the layout
convention ever moves again, this file goes red instead of production.

Notes:
- The real writer workspace clone is a ``git clone`` of
  github.com/ywatanabe1989/scitex-writer (needs network, ~15s), hence
  ``@pytest.mark.integration`` + ``@pytest.mark.slow``. The expensive
  clone runs ONCE per module via module-scoped fixtures.
- Skips (never fakes) when the real package is absent or its wheel is
  broken (the 2.18.0-2.26.0 PyPI wheels raise ModuleNotFoundError on
  ``import scitex_writer.writer``; the Dockerfile build smoke guards
  that failure mode separately).
"""

from pathlib import Path

import pytest

from apps.infra.project_app.services.visitor_pool.workspace_manager import (
    TEMPLATE_MARKER_RELPATH,
    verify_template_marker,
)

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _require_intact_writer():
    """Import the real scitex_writer, skipping on absence/broken wheel."""
    scitex_writer = pytest.importorskip("scitex_writer")
    try:
        import scitex_writer.writer  # noqa: F401
    except Exception as exc:  # broken wheel (2.18.0-2.26.0 PyPI breakage)
        pytest.skip(f"scitex-writer wheel is broken here: {exc}")
    return scitex_writer


@pytest.fixture(scope="module")
def real_writer_workspace(tmp_path_factory):
    """REAL writer workspace creation (same call clone_scitex_minimal
    makes), run once for the module. Yields (project_dir, writer_path)."""
    scitex_writer = _require_intact_writer()
    project_dir = tmp_path_factory.mktemp("real-writer-ensure")
    writer_path = scitex_writer.ensure_workspace(str(project_dir), git_strategy=None)
    return project_dir, Path(writer_path)


@pytest.fixture(scope="module")
def real_minimal_clone(tmp_path_factory):
    """REAL full template clone (the exact call the visitor-slot reset
    makes), run once for the module. Yields the cloned project dir."""
    scitex_template = pytest.importorskip("scitex_template")
    _require_intact_writer()
    project_path = tmp_path_factory.mktemp("real-minimal-clone") / "default-project"
    ok = scitex_template.clone_scitex_minimal(str(project_path), git_strategy=None)
    if not ok:
        # The clone itself is not runnable with the package versions in
        # this environment (e.g. scholar/template version mismatch) — we
        # cannot judge the marker layout from a failed clone. The
        # falsy-clone quarantine path is covered in
        # test_slot_recycling_security.py; the wheel-integrity failure
        # mode is covered by the Dockerfile build smoke.
        pytest.skip(
            "real clone_scitex_minimal returned False in this environment; "
            "marker layout cannot be judged from a failed clone"
        )
    return project_path


class TestRealWriterWorkspaceMatchesProductionMarker:
    def test_real_ensure_workspace_lands_at_the_marker_relpath(
        self, real_writer_workspace
    ):
        # Arrange
        project_dir, writer_path = real_writer_workspace
        # Act
        expected = project_dir / TEMPLATE_MARKER_RELPATH
        # Assert
        assert writer_path == expected

    def test_real_ensure_workspace_passes_production_verification(
        self, real_writer_workspace
    ):
        # Arrange
        project_dir, _writer_path = real_writer_workspace
        # Act
        marker_ok = verify_template_marker(project_dir)
        # Assert
        assert marker_ok is True


class TestRealMinimalCloneMatchesProductionMarker:
    def test_real_clone_scitex_minimal_passes_production_verification(
        self, real_minimal_clone
    ):
        # Arrange
        project_path = real_minimal_clone
        # Act
        marker_ok = verify_template_marker(project_path)
        # Assert
        assert marker_ok is True
