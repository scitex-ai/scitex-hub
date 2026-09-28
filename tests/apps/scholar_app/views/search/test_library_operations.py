#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for bulk save-to-library (Scholar Search results toolbar)."""

import json

import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory

from apps.workspace.scholar_app.views.search.library_operations import (
    BULK_SAVE_LIMIT,
    _index_saved_papers_in_db,
    _save_papers_to_project_path,
    build_bibtex_for_paper,
    save_papers_bulk,
)


def _post_request(payload=None, raw_body=None):
    """Build an authenticated POST request without touching the database."""
    factory = RequestFactory()
    if raw_body is not None:
        request = factory.post(
            "/apps/scholar/api/papers/save-bulk/",
            data=raw_body,
            content_type="application/json",
        )
    else:
        request = factory.post(
            "/apps/scholar/api/papers/save-bulk/",
            data=json.dumps(payload or {}),
            content_type="application/json",
        )
    # Unsaved User instance: is_authenticated is True, no DB hit.
    request.user = User(username="bulk-save-tester")
    return request


def _paper(title="Deep Learning for Maps", **overrides):
    paper = {
        "title": title,
        "authors": "John Smith, Jane Doe",
        "year": "2020",
        "journal": "Nature",
        "doi": "10.1234/test",
        "abstract": "An abstract.",
        "source": "crossref",
        "url": "https://doi.org/10.1234/test",
        "pmid": "",
    }
    paper.update(overrides)
    return paper


class TestBulkSaveEmptyStates:
    """Honest empty/selection states need no project and no database."""

    def test_missing_project_id_returns_400(self):
        # Arrange
        request = _post_request({"papers": [_paper()]})
        # Act
        response = save_papers_bulk(request)
        # Assert
        assert response.status_code == 400

    def test_missing_project_id_error_names_project(self):
        # Arrange
        request = _post_request({"papers": [_paper()]})
        # Act
        body = json.loads(save_papers_bulk(request).content)
        # Assert
        assert body["error"] == "No project selected"

    def test_malformed_json_without_project_returns_400(self):
        # Arrange
        request = _post_request(raw_body="{not-json")
        # Act
        response = save_papers_bulk(request)
        # Assert
        assert response.status_code == 400

    def test_empty_papers_returns_400(self):
        # Arrange
        request = _post_request({"project_id": "1", "papers": []})
        # Act
        response = save_papers_bulk(request)
        # Assert
        assert response.status_code == 400

    def test_empty_papers_error_names_selection(self):
        # Arrange
        request = _post_request({"project_id": "1", "papers": []})
        # Act
        body = json.loads(save_papers_bulk(request).content)
        # Assert
        assert body["error"] == "No papers selected"

    def test_nonlist_papers_returns_400(self):
        # Arrange
        request = _post_request({"project_id": "1", "papers": "oops"})
        # Act
        response = save_papers_bulk(request)
        # Assert
        assert response.status_code == 400

    def test_over_limit_batch_returns_400(self):
        # Arrange
        papers = [_paper(title=f"Paper {i}") for i in range(BULK_SAVE_LIMIT + 1)]
        request = _post_request({"project_id": "1", "papers": papers})
        # Act
        body = json.loads(save_papers_bulk(request).content)
        # Assert
        assert "max" in body["error"]


class TestBuildBibtexForPaper:
    """Pure bibtex builder: no DB, no filesystem."""

    def test_key_contains_year(self):
        # Arrange
        paper = _paper()
        # Act
        citation_key, _ = build_bibtex_for_paper(paper)
        # Assert
        assert "2020" in citation_key

    def test_entry_contains_title(self):
        # Arrange
        paper = _paper(title="Hippocampus Mapping")
        # Act
        _, entry = build_bibtex_for_paper(paper)
        # Assert
        assert "Hippocampus Mapping" in entry

    def test_missing_title_raises(self):
        # Arrange
        paper = _paper(title="")
        # Act / Assert
        with pytest.raises(ValueError, match="Paper title is required"):
            build_bibtex_for_paper(paper)

    def test_missing_authors_falls_back(self):
        # Arrange
        paper = _paper(authors="")
        # Act
        _, entry = build_bibtex_for_paper(paper)
        # Assert
        assert "Unknown Author" in entry

    def test_abstract_is_embedded(self):
        # Arrange
        paper = _paper(abstract="A very specific abstract sentence.")
        # Act
        _, entry = build_bibtex_for_paper(paper)
        # Assert
        assert "A very specific abstract sentence." in entry

    def test_doi_is_embedded(self):
        # Arrange
        paper = _paper(doi="10.9999/unique-doi")
        # Act
        _, entry = build_bibtex_for_paper(paper)
        # Assert
        assert "10.9999/unique-doi" in entry


class TestSavePapersToProjectPath:
    """Filesystem-only bulk save against tmp_path (real .bib writes)."""

    def test_two_valid_papers_saved_count(self, tmp_path):
        # Arrange
        papers = [_paper(title="Paper One"), _paper(title="Paper Two")]
        # Act
        summary = _save_papers_to_project_path(tmp_path, "Demo", papers)
        # Assert
        assert summary["saved"] == 2

    def test_two_valid_papers_nothing_skipped(self, tmp_path):
        # Arrange
        papers = [_paper(title="Paper One"), _paper(title="Paper Two")]
        # Act
        summary = _save_papers_to_project_path(tmp_path, "Demo", papers)
        # Assert
        assert summary["skipped"] == 0

    def test_two_valid_papers_write_two_bib_files(self, tmp_path):
        # Arrange
        papers = [_paper(title="Paper One"), _paper(title="Paper Two")]
        # Act
        _save_papers_to_project_path(tmp_path, "Demo", papers)
        # Assert
        assert len(list((tmp_path / "scitex" / "scholar" / "bib_files").glob("*.bib"))) == 2

    def test_titless_paper_is_skipped_not_fatal(self, tmp_path):
        # Arrange
        papers = [_paper(title="Good Paper"), _paper(title="")]
        # Act
        summary = _save_papers_to_project_path(tmp_path, "Demo", papers)
        # Assert
        assert summary["saved"] == 1

    def test_titless_paper_skip_count(self, tmp_path):
        # Arrange
        papers = [_paper(title="Good Paper"), _paper(title="")]
        # Act
        summary = _save_papers_to_project_path(tmp_path, "Demo", papers)
        # Assert
        assert summary["skipped"] == 1

    def test_titless_paper_error_is_reported(self, tmp_path):
        # Arrange
        papers = [_paper(title="")]
        # Act
        summary = _save_papers_to_project_path(tmp_path, "Demo", papers)
        # Assert
        assert summary["errors"][0]["error"] == "Paper title is required"

    def test_non_object_entry_is_skipped(self, tmp_path):
        # Arrange
        papers = [_paper(title="Good Paper"), "not-a-dict"]
        # Act
        summary = _save_papers_to_project_path(tmp_path, "Demo", papers)
        # Assert
        assert summary["skipped"] == 1


@pytest.mark.django_db
class TestIndexSavedPapersInDb:
    """File saves must also index SearchIndex + UserLibrary rows (Library tab)."""

    def test_index_creates_search_and_library_rows(self):
        from apps.workspace.scholar_app.models.core import SearchIndex
        from apps.workspace.scholar_app.models.library.models import UserLibrary

        user = User.objects.create_user(username="index-tester")
        n = _index_saved_papers_in_db(user, None, [_paper()])
        assert n == 1
        assert SearchIndex.objects.filter(doi="10.1234/test").count() == 1
        assert UserLibrary.objects.filter(user=user).count() == 1

    def test_index_is_idempotent_on_rerun(self):
        from apps.workspace.scholar_app.models.library.models import UserLibrary

        user = User.objects.create_user(username="index-tester-2")
        papers = [_paper()]
        assert _index_saved_papers_in_db(user, None, papers) == 1
        assert _index_saved_papers_in_db(user, None, papers) == 1
        assert UserLibrary.objects.filter(user=user).count() == 1

    def test_titleless_paper_is_skipped(self):
        user = User.objects.create_user(username="index-tester-3")
        assert _index_saved_papers_in_db(user, None, [_paper(title="")]) == 0


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])
