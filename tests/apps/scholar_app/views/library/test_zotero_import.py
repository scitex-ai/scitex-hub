#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/scholar_app/views/library/zotero_import.py"""

from unittest.mock import MagicMock, patch

import pytest
from django.test import Client


class TestZoteroStatus:
    """Tests for zotero_status endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.fixture
    def user(self, django_user_model, unique_username):
        return django_user_model.objects.create_user(
            unique_username,
            password="pass",  # pragma: allowlist secret
        )

    @pytest.mark.django_db
    def test_status_when_zotero_not_found(self, client, user):
        """Returns available=False when Zotero DB not found."""
        client.force_login(user)
        with patch(
            "scitex.scholar.integration.zotero.ZoteroLocalReader",
            side_effect=FileNotFoundError("No Zotero DB"),
        ):
            response = client.get("/scholar/api/library/zotero/status/")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False

    @pytest.mark.django_db
    def test_status_requires_login(self, client):
        """Unauthenticated users are redirected."""
        response = client.get("/scholar/api/library/zotero/status/")
        assert response.status_code in (302, 403)


class TestZoteroImport:
    """Tests for zotero_import endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.fixture
    def user(self, django_user_model, unique_username):
        return django_user_model.objects.create_user(
            unique_username,
            password="pass",  # pragma: allowlist secret
        )

    @pytest.mark.django_db
    def test_import_requires_login(self, client):
        """Unauthenticated users are redirected."""
        import json

        response = client.post(
            "/scholar/api/library/zotero/import/",
            data=json.dumps({"mode": "all"}),
            content_type="application/json",
        )
        assert response.status_code in (302, 403)

    @pytest.mark.django_db
    def test_import_invalid_json(self, client, user):
        """Invalid JSON body returns 400."""
        client.force_login(user)
        response = client.post(
            "/scholar/api/library/zotero/import/",
            data="not-json",
            content_type="application/json",
        )
        assert response.status_code == 400


class TestPaperToDict:
    """Tests for the _paper_to_dict adapter."""

    def test_basic_conversion(self):
        from apps.scholar_app.views.library.zotero_import import _paper_to_dict

        paper = MagicMock()
        paper.metadata.basic.title = "Test Title"
        paper.metadata.basic.abstract = "Abstract"
        paper.metadata.basic.authors = ["Smith, J.", "Jones, K."]
        paper.metadata.basic.year = 2020
        paper.metadata.publication.journal = "Nature"
        paper.metadata.id.doi = "10.1234/test"
        paper.metadata.id.arxiv_id = None
        paper.metadata.id.pmid = None
        paper.metadata.citation_count.total = 42
        paper.metadata.access.is_open_access = True

        result = _paper_to_dict(paper)

        assert result["title"] == "Test Title"
        assert result["abstract"] == "Abstract"
        assert "Smith" in result["authors"]
        assert result["year"] == 2020
        assert result["journal"] == "Nature"
        assert result["doi"] == "10.1234/test"
        assert result["citations"] == 42
        assert result["open_access"] is True
        assert result["source"] == "zotero"

    def test_empty_authors(self):
        from apps.scholar_app.views.library.zotero_import import _paper_to_dict

        paper = MagicMock()
        paper.metadata.basic.title = "Title"
        paper.metadata.basic.abstract = ""
        paper.metadata.basic.authors = []
        paper.metadata.basic.year = None
        paper.metadata.publication.journal = ""
        paper.metadata.id.doi = None
        paper.metadata.id.arxiv_id = None
        paper.metadata.id.pmid = None
        paper.metadata.citation_count.total = None
        paper.metadata.access.is_open_access = False

        result = _paper_to_dict(paper)
        assert result["authors"] == ""
        assert result["doi"] == ""


class TestProjectWorkspace:
    """Tests for api_setup_project_workspace endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.fixture
    def user(self, django_user_model, unique_username):
        return django_user_model.objects.create_user(
            unique_username,
            password="pass",  # pragma: allowlist secret
        )

    @pytest.mark.django_db
    def test_setup_workspace_requires_login(self, client):
        """Unauthenticated users are redirected."""
        import uuid

        response = client.post(
            f"/scholar/api/library/projects/{uuid.uuid4()}/setup-workspace/"
        )
        assert response.status_code in (302, 403)

    @pytest.mark.django_db
    def test_setup_workspace_project_not_found(self, client, user):
        """Returns 404 for non-existent project."""
        import uuid

        client.force_login(user)
        response = client.post(
            f"/scholar/api/library/projects/{uuid.uuid4()}/setup-workspace/"
        )
        assert response.status_code == 404


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])

# EOF
