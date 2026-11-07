"""Scholar bibliography writes stay inside the selected project."""

from pathlib import Path

import pytest

from apps.workspace.scholar_app.views.search.library_operations import _write_paper_bib


def test_untrusted_citation_key_is_only_a_filename_component(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    filename = _write_paper_bib(
        project, "crossref", "Smith/../../escape", "@article{sample}"
    )
    assert Path(filename).name == filename
    assert (
        project / "scitex/scholar/bib_files" / filename
    ).read_text() == "@article{sample}"


@pytest.mark.parametrize("component", ["scitex", "scholar", "bib_files"])
def test_bibliography_write_refuses_directory_symlink_escape(tmp_path, component):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    parent = project
    for part in ("scitex", "scholar", "bib_files"):
        if part == component:
            (parent / part).symlink_to(outside, target_is_directory=True)
            break
        parent = parent / part
        parent.mkdir()
    with pytest.raises((OSError, ValueError)):
        _write_paper_bib(project, "crossref", "Smith2026", "@article{sample}")
    assert list(outside.iterdir()) == []


def test_normal_bibliography_filename_and_content_are_preserved(tmp_path):
    filename = _write_paper_bib(
        tmp_path, "crossref", "Smith2026", "@article{Smith2026}"
    )
    assert filename.startswith("search_crossref_Smith2026_")
    assert (
        tmp_path / "scitex/scholar/bib_files" / filename
    ).read_text() == "@article{Smith2026}"


@pytest.mark.parametrize("component", ["scitex", "scholar", "bib_files"])
def test_bulk_save_refuses_escape_before_initializing_writer_links(tmp_path, component):
    from apps.workspace.scholar_app.views.search.library_operations import (
        _save_papers_to_project_path,
    )

    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    parent = project
    for part in ("scitex", "scholar", "bib_files"):
        if part == component:
            (parent / part).symlink_to(outside, target_is_directory=True)
            break
        parent = parent / part
        parent.mkdir()
    (project / "scitex/writer/00_shared/bib_files").mkdir(parents=True)
    before = sorted(str(p.relative_to(outside)) for p in outside.rglob("*"))
    with pytest.raises((OSError, ValueError)):
        _save_papers_to_project_path(
            project,
            "example",
            [{"title": "Example", "authors": "Smith", "year": "2026"}],
        )
    assert sorted(str(p.relative_to(outside)) for p in outside.rglob("*")) == before


def test_unicode_citation_key_is_preserved_without_path_separators(tmp_path):
    filename = _write_paper_bib(tmp_path, "crossref", "渡邉2026", "@article{渡邉2026}")
    assert filename.startswith("search_crossref_渡邉2026_")
    assert (
        tmp_path / "scitex/scholar/bib_files" / filename
    ).read_text() == "@article{渡邉2026}"
