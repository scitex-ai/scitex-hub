#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single source of truth for where a project's Writer workspace lives.

``scitex_writer.ensure_workspace()`` creates the workspace at
``{project_root}/.scitex/writer/`` — dot-prefixed, dotfile convention.
Hub must never re-type that string, because it has now drifted twice
and both times the failure was silent:

- 2026-07-08: visitor-pool verification checked ``scitex/writer`` (no
  dot) while the real package created ``.scitex/writer``. Verification
  never passed, so EVERY visitor slot was quarantined — and the
  security suite stayed green because its fakes fabricated the same
  wrong layout.
- 2026-07-28 → 2026-08-02: ``writer_app`` still resolved the undotted
  path in 8 places, so ``writer_initialized`` was always False, the
  frontend took a dead early-return branch, the sections fetch was
  never issued, and every visitor saw an empty editor under a
  permanent "Loading...".

One defect, twice: the same path spelled in two places. Import from
here rather than writing the literal.
"""

from pathlib import Path

# The workspace directory scitex_writer.ensure_workspace() creates,
# relative to the project root. Reality-locked against the REAL
# package by tests/apps/project_app/services/visitor_pool/
# test_template_marker_reality.py — if the package convention ever
# moves again, that test goes red instead of production.
WRITER_WORKSPACE_RELPATH = ".scitex/writer"

# Subdirectory whose presence means the workspace is initialized.
MANUSCRIPT_DIRNAME = "01_manuscript"


def get_writer_workspace_path(project_root) -> Path:
    """Absolute Writer workspace path for ``project_root``."""
    return Path(project_root) / WRITER_WORKSPACE_RELPATH


def get_manuscript_path(project_root) -> Path:
    """Absolute manuscript directory path for ``project_root``."""
    return get_writer_workspace_path(project_root) / MANUSCRIPT_DIRNAME


def is_writer_initialized(project_root) -> bool:
    """True when the Writer workspace has its manuscript directory."""
    return get_manuscript_path(project_root).exists()
