#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for save_paper: user-scope library + project symlinks."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from apps.infra.project_app.models import Project
from apps.workspace.scholar_app.views.search.library_operations import (
    get_user_scholar_library,
)


@pytest.mark.django_db
class TestSavePaperUserScope:
    def _post(self, client, **over):
        data = {
            "title": "Attention Is All You Need",
            "authors": "Vaswani, Ashish",
            "year": "2017",
            "journal": "NeurIPS",
            "doi": "10.48550/arXiv.1706.03762",
            "abstract": "Transformers.",
            "source": "arxiv",
            "url": "",
            "pmid": "",
        }
        data.update(over)
        return client.post("/apps/scholar/api/save-paper/", data)

    def test_user_library_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SCITEX_USER_DATA_ROOT", str(tmp_path))
        lib = get_user_scholar_library("ada")
        assert str(lib) == str(
            tmp_path / "ada" / ".scitex" / "scholar" / "library"
        )

    def test_save_without_project_writes_user_library(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("SCITEX_USER_DATA_ROOT", str(tmp_path))
        user = get_user_model().objects.create_user(username="ada", password="x")
        client = Client()
        client.force_login(user)
        resp = self._post(client)
        assert resp.status_code == 200, resp.content[:300]
        body = resp.json()
        assert body["success"] is True
        assert body["project"] is None
        lib = get_user_scholar_library("ada")
        files = list(lib.glob("*.bib"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "Attention" in content

    def test_save_with_project_symlinks_not_copies(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("SCITEX_USER_DATA_ROOT", str(tmp_path))
        user = get_user_model().objects.create_user(username="grace", password="x")
        proj_root = tmp_path / "proj"
        proj_root.mkdir()
        project = Project.objects.create(
            name="demo",
            slug="demo",
            description="d",
            owner=user,
            git_clone_path=str(proj_root),
        )
        client = Client()
        client.force_login(user)
        resp = self._post(client, project_id=str(project.id))
        assert resp.status_code == 200, resp.content[:300]
        body = resp.json()
        assert body["success"] is True
        assert body["project"] == "demo"
        bib_dir = proj_root / "scitex" / "scholar" / "bib_files"
        links = list(bib_dir.glob("*.bib"))
        assert len(links) == 1
        assert links[0].is_symlink(), "project must hold a symlink, not a copy"
        target = (bib_dir / links[0].readlink()).resolve()
        lib = get_user_scholar_library("grace")
        assert target.parent == lib.resolve()
        assert target.exists()

    def test_same_doi_reuses_canonical_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SCITEX_USER_DATA_ROOT", str(tmp_path))
        user = get_user_model().objects.create_user(username="lin", password="x")
        client = Client()
        client.force_login(user)
        self._post(client)
        self._post(client)
        lib = get_user_scholar_library("lin")
        assert len(list(lib.glob("*.bib"))) == 1
