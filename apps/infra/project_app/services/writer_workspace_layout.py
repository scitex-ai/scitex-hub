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

- 2026-08-17 (third time, and the first that was not a re-typing but an
  OMISSION): ``writer_app.views.editor.api.compilation`` hardcoded the
  compile-script path as ``scripts/shell/compile_manuscript.sh`` and
  exec'd ``/workspace/<that>``. The apptainer runner binds the PROJECT
  ROOT as ``/workspace``, but the scripts are vendored INSIDE the Writer
  workspace, so every full compilation on scitex.ai died with
  ``returncode 127`` / ``bash: /workspace/scripts/shell/
  compile_manuscript.sh: No such file or directory``. The guard added in
  2026-08-02 only caught the literal being RE-TYPED; nothing caught it
  being LEFT OUT. Hence :data:`COMPILE_SCRIPT_DIRNAME` and
  :func:`get_compile_script_relpath` below — the workspace-relative half
  of the path now has a home here too, so callers cannot assemble it by
  hand.
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

# Where scitex-writer vendors its compile scripts, relative to the WRITER
# WORKSPACE (not the project root) — the engine writes them to
# ``<workspace>/scripts/shell/`` on ensure_workspace()/update-project.
COMPILE_SCRIPT_DIRNAME = "scripts/shell"

# doc_type -> script filename, as vendored by scitex-writer.
COMPILE_SCRIPT_BY_DOC_TYPE = {
    "manuscript": "compile_manuscript.sh",
    "supplementary": "compile_supplementary.sh",
    "revision": "compile_revision.sh",
}

# The doc_type assumed when a caller sends something unrecognised.
DEFAULT_DOC_TYPE = "manuscript"

# The compiled PDF each doc_type produces, relative to the workspace.
# scitex-writer's config_manuscript.yaml pins
# ``paths.compiled_pdf: "./01_manuscript/manuscript.pdf"``.
COMPILED_PDF_NAME = "manuscript.pdf"


def get_writer_workspace_path(project_root) -> Path:
    """Absolute Writer workspace path for ``project_root``."""
    return Path(project_root) / WRITER_WORKSPACE_RELPATH


def get_manuscript_path(project_root) -> Path:
    """Absolute manuscript directory path for ``project_root``."""
    return get_writer_workspace_path(project_root) / MANUSCRIPT_DIRNAME


def get_compile_script_relpath(doc_type: str = DEFAULT_DOC_TYPE) -> str:
    """Compile-script path for ``doc_type``, relative to the PROJECT ROOT.

    Deliberately project-root-relative, because that is the path callers
    actually need: the apptainer runner binds the project root as
    ``/workspace``, so the in-container command is
    ``bash /workspace/<this>``. Returning a workspace-relative path here
    would just move the join — and the missing ``.scitex/writer`` join is
    the whole bug this function exists to make unrepeatable.

    Unknown ``doc_type`` falls back to :data:`DEFAULT_DOC_TYPE` rather
    than raising, matching the behaviour the API has always had.
    """
    script = COMPILE_SCRIPT_BY_DOC_TYPE.get(
        doc_type, COMPILE_SCRIPT_BY_DOC_TYPE[DEFAULT_DOC_TYPE]
    )
    return f"{WRITER_WORKSPACE_RELPATH}/{COMPILE_SCRIPT_DIRNAME}/{script}"


def get_compile_script_path(project_root, doc_type: str = DEFAULT_DOC_TYPE) -> Path:
    """Absolute host path of ``doc_type``'s compile script."""
    return Path(project_root) / get_compile_script_relpath(doc_type)


def get_compiled_pdf_path(project_root) -> Path:
    """Absolute path of the PDF a full compilation writes.

    The compile script resolves its own ``PROJECT_ROOT`` from
    ``$(dirname $0)/../..`` — i.e. the WORKSPACE — and then writes
    ``./01_manuscript/manuscript.pdf`` relative to it. So the output
    lands inside the workspace, not at the project root.
    """
    return get_manuscript_path(project_root) / COMPILED_PDF_NAME


def is_writer_initialized(project_root) -> bool:
    """True when the Writer workspace has its manuscript directory."""
    return get_manuscript_path(project_root).exists()
