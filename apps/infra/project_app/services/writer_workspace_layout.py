#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Where a project's Writer workspace lives — imported, never re-typed.

``scitex_writer.ensure_workspace()`` creates the workspace at a
dot-prefixed path under the project root. Hub used to spell that path
out, and it drifted three times, every time silently:

- 2026-07-08: visitor-pool verification checked the UNDOTTED spelling
  while the real package created the dotted one. Verification never
  passed, so EVERY visitor slot was quarantined — and the security suite
  stayed green because its fakes fabricated the same wrong layout.
- 2026-07-28 -> 2026-08-02: ``writer_app`` still resolved the undotted
  path in 8 places, so ``writer_initialized`` was always False, the
  frontend took a dead early-return branch, the sections fetch was never
  issued, and every visitor saw an empty editor under a permanent
  "Loading...".
- 2026-08-17: the third drift was not a re-typing but an OMISSION.
  ``writer_app/views/editor/api/compilation.py`` built the compile-script
  path as ``scripts/shell/compile_manuscript.sh`` and exec'd
  ``bash /workspace/<that>``. The apptainer runner binds the PROJECT ROOT
  as ``/workspace`` while the scripts are vendored INSIDE the workspace,
  so the path was one segment too high and full compilation returned
  ``returncode 127`` for every user on scitex.ai.

The lesson of the third one is that "hub owns one copy of the string" is
still one copy too many: hub is not the package that decides the layout.
scitex-writer now PUBLISHES it (``scitex_writer.workspace_layout``, from
2.42.0), so this module holds NO path literal at all — it re-exports the
leaf package's values under hub's existing names. If the convention ever
moves again, it moves in one repository and hub follows automatically.
"""

from pathlib import Path

from scitex_writer.workspace_layout import WORKSPACE_RELPATH as _WORKSPACE_RELPATH
from scitex_writer.workspace_layout import workspace_dir as _workspace_dir

# The workspace directory scitex_writer.ensure_workspace() creates,
# relative to the project root. Kept as a POSIX string because hub's
# callers interpolate it into container paths and log lines; the VALUE
# comes from the leaf package, so there is nothing here to drift.
WRITER_WORKSPACE_RELPATH = Path(_WORKSPACE_RELPATH).as_posix()

# Subdirectory whose presence means the workspace is initialized.
MANUSCRIPT_DIRNAME = "01_manuscript"

# The compiled PDF a full compilation writes. scitex-writer's
# config_manuscript.yaml pins ``paths.compiled_pdf`` to
# ``./01_manuscript/manuscript.pdf`` — relative to the WORKSPACE, which is
# what the compile script resolves as its own PROJECT_ROOT.
COMPILED_PDF_NAME = "manuscript.pdf"


def get_writer_workspace_path(project_root) -> Path:
    """Absolute Writer workspace path for ``project_root``."""
    return _workspace_dir(project_root)


def get_manuscript_path(project_root) -> Path:
    """Absolute manuscript directory path for ``project_root``."""
    return get_writer_workspace_path(project_root) / MANUSCRIPT_DIRNAME


def get_compiled_pdf_path(project_root) -> Path:
    """Absolute path of the PDF a full compilation writes.

    The compile script resolves its own ``PROJECT_ROOT`` from
    ``$(dirname $0)/../..`` — i.e. the WORKSPACE — and then writes
    ``./01_manuscript/manuscript.pdf`` relative to it. So the output lands
    inside the workspace, not at the project root. Looking for it at the
    project root is a second off-by-one on the same segment, and it turns
    a successful compile into "NO PDF FOUND".
    """
    return get_manuscript_path(project_root) / COMPILED_PDF_NAME


def is_writer_initialized(project_root) -> bool:
    """True when the Writer workspace has its manuscript directory."""
    return get_manuscript_path(project_root).exists()
