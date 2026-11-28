"""Project creation readies the Writer workspace instead of only testing a path.

``initialize_scitex_writer_template`` used to compute ``<root>/.scitex/writer``
and report failure when it was absent, so a research-template project opened
as a 404 in Writer (scitex-template#84). It now delegates to
``scitex_writer.ensure_workspace`` and reports ready only when the manuscript
directory the Writer opens exists. Real directories, real scitex-writer; the
workspaces below already carry an engine, so no template is fetched.
"""

from pathlib import Path

from apps.infra.project_app.services.project_filesystem.template_ops import (
    ensure_writer_workspace,
)


def _workspace(root: Path, *, manuscript: bool) -> Path:
    workspace = root / ".scitex" / "writer"
    (workspace / "00_shared").mkdir(parents=True)
    (workspace / "scripts" / "shell").mkdir(parents=True)
    (workspace / "00_shared" / "title.tex").write_text("\\title{Kept}\n")
    if manuscript:
        (workspace / "01_manuscript" / "contents").mkdir(parents=True)
    return workspace


def test_a_complete_workspace_is_reported_ready(tmp_path):
    # Arrange
    workspace = _workspace(tmp_path, manuscript=True)
    # Act
    ready = ensure_writer_workspace(tmp_path)
    # Assert
    assert ready == workspace


def test_readying_a_complete_workspace_keeps_the_authors_text(tmp_path):
    # Arrange
    workspace = _workspace(tmp_path, manuscript=True)
    # Act
    ensure_writer_workspace(tmp_path)
    # Assert
    assert (workspace / "00_shared" / "title.tex").read_text() == "\\title{Kept}\n"


def test_a_workspace_without_a_manuscript_directory_is_not_ready(tmp_path):
    # Arrange
    _workspace(tmp_path, manuscript=False)
    # Act
    ready = ensure_writer_workspace(tmp_path)
    # Assert
    assert ready is None
