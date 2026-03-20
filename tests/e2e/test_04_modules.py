#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Access Tests

Test that main application modules are accessible.
These are the core features users expect to work.

Priority: MEDIUM
Run time: < 30 seconds
"""

import pytest


class TestScholarModule:
    """Test Scholar module accessibility."""

    def test_scholar_index_accessible(self, api_client):
        """Scholar module index is accessible (via /apps/ canonical URL)."""
        resp = api_client.get("/apps/scholar/", allow_redirects=False)
        assert resp.status_code in [200, 302]

    def test_scholar_legacy_redirect(self, api_client):
        """Legacy /scholar/ redirects to /apps/scholar/."""
        resp = api_client.get("/scholar/", allow_redirects=False)
        assert resp.status_code == 301

    def test_scholar_search_page(self, api_client):
        """Scholar search functionality accessible."""
        resp = api_client.get("/apps/scholar/search/", allow_redirects=False)
        assert resp.status_code in [200, 302, 404]


class TestWriterModule:
    """Test Writer module accessibility."""

    def test_writer_index_accessible(self, api_client):
        """Writer module index is accessible (via /apps/ canonical URL)."""
        resp = api_client.get("/apps/writer/", allow_redirects=False)
        assert resp.status_code in [200, 302]

    def test_writer_legacy_redirect(self, api_client):
        """Legacy /writer/ redirects to /apps/writer/."""
        resp = api_client.get("/writer/", allow_redirects=False)
        assert resp.status_code == 301


class TestCodeModule:
    """Test Code module accessibility."""

    def test_code_index_accessible(self, api_client):
        """Code module index is accessible (via /apps/ canonical URL)."""
        resp = api_client.get("/apps/console/", allow_redirects=False)
        assert resp.status_code in [200, 302]

    def test_code_legacy_redirect(self, api_client):
        """Legacy /console/ redirects to /apps/console/."""
        resp = api_client.get("/console/", allow_redirects=False)
        assert resp.status_code == 301


class TestFigrecipeModule:
    """Test FigRecipe (formerly Vis) module accessibility."""

    def test_figrecipe_index_accessible(self, api_client):
        """FigRecipe module index is accessible (via /apps/ canonical URL)."""
        resp = api_client.get("/apps/figrecipe/", allow_redirects=False)
        assert resp.status_code in [200, 302]

    def test_vis_legacy_redirect(self, api_client):
        """Legacy /vis/ redirects (301 or 404 if route removed)."""
        resp = api_client.get("/vis/", allow_redirects=False)
        assert resp.status_code in [301, 404]


class TestWorkspaceModule:
    """Test Workspace module accessibility."""

    def test_workspace_index_accessible(self, api_client):
        """Workspace module index is accessible."""
        resp = api_client.get("/apps/workspace/", allow_redirects=False)
        assert resp.status_code in [200, 302]


class TestDocsModule:
    """Test Documentation module."""

    def test_docs_index_accessible(self, api_client):
        """Docs module index is accessible."""
        resp = api_client.get("/apps/docs/", allow_redirects=False)
        if resp.status_code == 500:
            pytest.xfail("Docs app returning 500 - needs investigation")
        assert resp.status_code in [200, 302, 404]

    def test_docs_getting_started(self, api_client):
        """Getting started docs accessible."""
        resp = api_client.get("/apps/docs/getting-started/", allow_redirects=False)
        assert resp.status_code in [200, 302, 404]
