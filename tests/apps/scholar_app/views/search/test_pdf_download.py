#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/workspace/scholar_app/views/search/pdf_download/.

Covers the single-download, status/serve, bulk, and utils modules using
RequestFactory (no database required). Network and filesystem isolation
are provided via monkeypatching.
"""

from __future__ import annotations

import asyncio
import json
import sys
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.workspace.scholar_app.views.search.pdf_download import (
    api_check_pdf_status,
    api_serve_pdf,
    api_download_pdf,
    api_download_pdf_bulk,
)
from apps.workspace.scholar_app.views.search.pdf_download import (
    bulk as bulk_module,
)
from apps.workspace.scholar_app.views.search.pdf_download import (
    single as single_module,
)
from apps.workspace.scholar_app.views.search.pdf_download import (
    status as status_module,
)
from apps.workspace.scholar_app.views.search.pdf_download import (
    utils as utils_module,
)
from apps.workspace.scholar_app.views.search.pdf_download.bulk import (
    _check_existing_pdf,
    _download_arxiv_pdf,
    _process_single_paper,
)
from apps.workspace.scholar_app.views.search.pdf_download.status import (
    _check_oa_availability,
    _find_existing_pdf,
)
from apps.workspace.scholar_app.views.search.pdf_download.utils import (
    generate_pdf_filename,
    get_oa_url_for_identifiers,
    sanitize_filename,
)

factory = RequestFactory()


def _request(method="get", path="/", data=None, body=None):
    """Build a RequestFactory request with anonymous user + stub session."""
    if method == "get":
        request = factory.get(path, data or {})
    else:
        request = factory.post(
            path, data=body or "", content_type="application/json"
        )
    request.user = AnonymousUser()
    request.session = SimpleNamespace(session_key="test-session-key")
    return request


def _json(response):
    return json.loads(response.content)


@pytest.fixture
def scitex_core():
    """Canonical scitex core module with a stable ``scitex.scholar.core`` alias.

    ``scitex.scholar`` is a lazy proxy: the first ``from scitex.scholar.core
    import ...`` can materialize a duplicate module object, which makes
    patching ``scitex.scholar.core.<attr>`` by dotted path order-dependent.
    Pre-registering the alias turns the from-import into a plain
    ``sys.modules`` hit, so attribute patches land on the object the views
    actually read.
    """
    import scitex_scholar.core as canonical

    return sys.modules.setdefault("scitex.scholar.core", canonical)


# ---------------------------------------------------------------------------
# utils
# ---------------------------------------------------------------------------


class TestSanitizeFilename:
    def test_basic(self):
        assert sanitize_filename("My Paper Title") == "My Paper Title"

    def test_removes_special_chars(self):
        result = sanitize_filename("Paper: A/B Test?")
        assert "/" not in result
        assert "?" not in result
        assert ":" not in result

    def test_truncates_to_max_length(self):
        assert len(sanitize_filename("A" * 200)) == 50

    def test_respects_custom_max_length(self):
        assert len(sanitize_filename("A" * 200, max_length=10)) == 10


class TestGeneratePdfFilename:
    def test_doi(self):
        assert (
            generate_pdf_filename("My Paper", doi="10.1234/test")
            == "My Paper_10.1234_test.pdf"
        )

    def test_arxiv(self):
        assert (
            generate_pdf_filename("My Paper", arxiv_id="2301.12345")
            == "My Paper_2301.12345.pdf"
        )

    def test_pmid(self):
        assert (
            generate_pdf_filename("My Paper", pmid="12345678")
            == "My Paper_pmid12345678.pdf"
        )

    def test_no_identifier(self):
        assert generate_pdf_filename("My Paper") == "My Paper.pdf"

    def test_doi_takes_precedence_over_arxiv(self):
        result = generate_pdf_filename(
            "T", doi="10.1/x", arxiv_id="2301.1", pmid="1"
        )
        assert "10.1_x" in result


class TestGetOaUrlForIdentifiers:
    def test_arxiv_id_builds_arxiv_url(self):
        url, method = get_oa_url_for_identifiers(arxiv_id="2301.12345")
        assert url == "https://arxiv.org/pdf/2301.12345.pdf"
        assert method == "arxiv"

    def test_arxiv_takes_precedence_over_pdf_url(self):
        url, method = get_oa_url_for_identifiers(
            arxiv_id="2301.1", pdf_url="https://example.com/x.pdf"
        )
        assert method == "arxiv"

    def test_direct_pdf_url(self):
        url, method = get_oa_url_for_identifiers(
            pdf_url="https://example.com/x.pdf"
        )
        assert url == "https://example.com/x.pdf"
        assert method == "direct_url"

    def test_doi_via_unpaywall(self, monkeypatch, scitex_core):
        # Arrange
        fake_result = SimpleNamespace(
            is_open_access=True,
            oa_url="https://example.com/oa.pdf",
            status=SimpleNamespace(value="gold"),
        )
        monkeypatch.setattr(
            scitex_core,
            "check_oa_status",
            lambda doi, use_unpaywall: fake_result,
        )
        # Act
        url, method = get_oa_url_for_identifiers(doi="10.1234/test")
        # Assert
        assert url == "https://example.com/oa.pdf"
        assert method == "unpaywall_gold"

    def test_doi_closed_access_returns_none(self, monkeypatch, scitex_core):
        # Arrange
        fake_result = SimpleNamespace(
            is_open_access=False,
            oa_url=None,
            status=SimpleNamespace(value="closed"),
        )
        monkeypatch.setattr(
            scitex_core,
            "check_oa_status",
            lambda doi, use_unpaywall: fake_result,
        )
        # Act
        assert get_oa_url_for_identifiers(doi="10.1234/test") == (None, None)

    def test_doi_lookup_failure_returns_none(self, monkeypatch, scitex_core):
        # Arrange
        def _boom(doi, use_unpaywall):
            raise ConnectionError("offline")

        monkeypatch.setattr(scitex_core, "check_oa_status", _boom)
        # Act
        assert get_oa_url_for_identifiers(doi="10.1234/test") == (None, None)

    def test_no_identifiers_returns_none(self):
        assert get_oa_url_for_identifiers() == (None, None)


# ---------------------------------------------------------------------------
# status helpers
# ---------------------------------------------------------------------------


class TestFindExistingPdf:
    def test_finds_pdf_by_doi(self, tmp_path):
        # Arrange
        downloads = tmp_path / "downloads"
        master = tmp_path / "MASTER"
        downloads.mkdir()
        master.mkdir()
        target = downloads / "Paper_10.1234_test.pdf"
        target.write_bytes(b"%PDF")
        # Act
        found = _find_existing_pdf(downloads, master, "10.1234/test", "", "")
        # Assert
        assert found == target

    def test_falls_back_to_master_dir(self, tmp_path):
        # Arrange
        downloads = tmp_path / "downloads"
        master = tmp_path / "MASTER"
        downloads.mkdir()
        master.mkdir()
        target = master / "Paper_2301.12345.pdf"
        target.write_bytes(b"%PDF")
        # Act
        found = _find_existing_pdf(downloads, master, "", "2301.12345", "")
        # Assert
        assert found == target

    def test_finds_pdf_by_pmid(self, tmp_path):
        # Arrange
        downloads = tmp_path / "downloads"
        downloads.mkdir()
        target = downloads / "Paper_pmid12345678.pdf"
        target.write_bytes(b"%PDF")
        # Act
        found = _find_existing_pdf(downloads, tmp_path / "nope", "", "", "12345678")
        # Assert
        assert found == target

    def test_returns_none_when_missing(self, tmp_path):
        # Arrange
        downloads = tmp_path / "downloads"
        downloads.mkdir()
        # Act
        assert (
            _find_existing_pdf(downloads, tmp_path / "nope", "10.1/x", "", "")
            is None
        )

    def test_skips_nonexistent_dirs(self, tmp_path):
        # Act
        assert (
            _find_existing_pdf(
                tmp_path / "no-downloads",
                tmp_path / "no-master",
                "10.1/x",
                "",
                "",
            )
            is None
        )


class TestCheckOaAvailability:
    def test_open_access_high_confidence(self, monkeypatch, scitex_core):
        # Arrange
        monkeypatch.setattr(
            scitex_core,
            "detect_oa_from_identifiers",
            lambda doi, arxiv_id, pmcid: SimpleNamespace(
                is_open_access=True,
                confidence=0.95,
                oa_url="https://arxiv.org/pdf/2301.1.pdf",
            ),
        )
        # Act
        info = _check_oa_availability("", "2301.1")
        # Assert
        assert info == {
            "is_open_access": True,
            "can_download": True,
            "oa_url": "https://arxiv.org/pdf/2301.1.pdf",
        }

    def test_low_confidence_not_downloadable(self, monkeypatch, scitex_core):
        # Arrange
        monkeypatch.setattr(
            scitex_core,
            "detect_oa_from_identifiers",
            lambda doi, arxiv_id, pmcid: SimpleNamespace(
                is_open_access=True, confidence=0.3, oa_url=None
            ),
        )
        # Act
        info = _check_oa_availability("10.1234/test", "")
        # Assert
        assert info["is_open_access"] is True
        assert info["can_download"] is False


# ---------------------------------------------------------------------------
# api_check_pdf_status
# ---------------------------------------------------------------------------


class TestApiCheckPdfStatus:
    def test_requires_identifier(self):
        # Arrange
        request = _request()
        # Act
        response = api_check_pdf_status(request)
        # Assert
        assert response.status_code == 400
        assert "identifier" in _json(response)["error"]

    def test_rejects_post(self):
        # Arrange
        request = _request(method="post", body="{}")
        # Act
        response = api_check_pdf_status(request)
        # Assert
        assert response.status_code == 405

    def test_returns_existing_pdf(self, tmp_path, monkeypatch):
        # Arrange
        downloads = tmp_path / "scholar" / "library" / "downloads"
        downloads.mkdir(parents=True)
        pdf = downloads / "Paper_10.1234_test.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")
        monkeypatch.setattr(
            status_module, "get_user_scitex_dir", lambda user, session_key: tmp_path
        )
        request = _request(data={"doi": "10.1234/test"})
        # Act
        response = api_check_pdf_status(request)
        # Assert
        assert response.status_code == 200
        payload = _json(response)
        assert payload["status"] == "success"
        assert payload["has_pdf"] is True
        assert payload["filename"] == pdf.name
        assert payload["size_bytes"] == pdf.stat().st_size
        assert "10.1234_test" in payload["path"]

    def test_falls_back_to_oa_check(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setattr(
            status_module, "get_user_scitex_dir", lambda user, session_key: tmp_path
        )
        monkeypatch.setattr(
            status_module,
            "_check_oa_availability",
            lambda doi, arxiv_id: {
                "is_open_access": True,
                "can_download": True,
                "oa_url": "https://arxiv.org/pdf/2301.1.pdf",
            },
        )
        request = _request(data={"arxiv_id": "2301.1"})
        # Act
        response = api_check_pdf_status(request)
        # Assert
        assert response.status_code == 200
        payload = _json(response)
        assert payload["has_pdf"] is False
        assert payload["can_download"] is True
        assert payload["oa_url"] == "https://arxiv.org/pdf/2301.1.pdf"


# ---------------------------------------------------------------------------
# api_serve_pdf
# ---------------------------------------------------------------------------


class TestApiServePdf:
    def test_requires_path(self):
        # Arrange
        request = _request()
        # Act
        response = api_serve_pdf(request)
        # Assert
        assert response.status_code == 400

    def test_rejects_directory_traversal(self):
        # Arrange
        request = _request(data={"path": "../secret.pdf"})
        # Act
        response = api_serve_pdf(request)
        # Assert
        assert response.status_code == 400

    def test_rejects_absolute_path(self):
        # Arrange
        request = _request(data={"path": "/etc/passwd"})
        # Act
        response = api_serve_pdf(request)
        # Assert
        assert response.status_code == 400

    def test_missing_file_returns_404(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setattr(
            status_module, "get_user_scitex_dir", lambda user, session_key: tmp_path
        )
        request = _request(data={"path": "scholar/library/downloads/nope.pdf"})
        # Act
        response = api_serve_pdf(request)
        # Assert
        assert response.status_code == 404

    def test_serves_pdf(self, tmp_path, monkeypatch):
        # Arrange
        rel = "scholar/library/downloads/paper.pdf"
        full = tmp_path / rel
        full.parent.mkdir(parents=True)
        full.write_bytes(b"%PDF-1.4 fake-content")
        monkeypatch.setattr(
            status_module, "get_user_scitex_dir", lambda user, session_key: tmp_path
        )
        request = _request(data={"path": rel})
        # Act
        response = api_serve_pdf(request)
        # Assert
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert b"".join(response.streaming_content) == b"%PDF-1.4 fake-content"


# ---------------------------------------------------------------------------
# api_download_pdf (single)
# ---------------------------------------------------------------------------


class TestApiDownloadPdf:
    def test_service_unavailable(self, monkeypatch):
        # Arrange
        monkeypatch.setattr(single_module, "SCITEX_PDF_AVAILABLE", False)
        request = _request(method="post", body=json.dumps({"doi": "10.1/x"}))
        # Act
        response = api_download_pdf(request)
        # Assert
        assert response.status_code == 503

    def test_invalid_json(self):
        # Arrange
        request = _request(method="post", body="not-json{")
        # Act
        response = api_download_pdf(request)
        # Assert
        assert response.status_code == 400
        assert _json(response)["error"] == "Invalid JSON body"

    def test_requires_identifier(self):
        # Arrange
        request = _request(method="post", body=json.dumps({"title": "x"}))
        # Act
        response = api_download_pdf(request)
        # Assert
        assert response.status_code == 400

    def test_rejects_get(self):
        # Arrange
        request = _request(data={"doi": "10.1/x"})
        # Act
        response = api_download_pdf(request)
        # Assert
        assert response.status_code == 405

    def test_no_oa_url_returns_not_downloaded(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setattr(
            single_module, "get_user_scitex_dir", lambda user, session_key: tmp_path
        )
        monkeypatch.setattr(
            single_module, "get_oa_url_for_identifiers", lambda *a: (None, None)
        )
        request = _request(
            method="post", body=json.dumps({"doi": "10.1234/closed"})
        )
        # Act
        response = api_download_pdf(request)
        # Assert
        assert response.status_code == 200
        payload = _json(response)
        assert payload["status"] == "success"
        assert payload["downloaded"] is False
        assert "reason" in payload

    def test_successful_download(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setattr(
            single_module, "get_user_scitex_dir", lambda user, session_key: tmp_path
        )
        monkeypatch.setattr(
            single_module,
            "get_oa_url_for_identifiers",
            lambda *a: ("https://arxiv.org/pdf/2301.1.pdf", "arxiv"),
        )

        async def _fake_download(oa_url, output_path, metadata, timeout):
            output_path.write_bytes(b"%PDF-1.4 fake")
            return output_path

        monkeypatch.setattr(
            single_module, "try_download_open_access_async", _fake_download
        )
        request = _request(
            method="post",
            body=json.dumps({"arxiv_id": "2301.1", "title": "Test Paper"}),
        )
        # Act
        response = api_download_pdf(request)
        # Assert
        assert response.status_code == 200
        payload = _json(response)
        assert payload["downloaded"] is True
        assert payload["method"] == "arxiv"
        assert payload["filename"].endswith(".pdf")
        assert "2301.1" in payload["filename"]
        assert payload["size_bytes"] > 0
        assert (tmp_path / payload["path"]).exists()

    def test_failed_download_returns_not_downloaded(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setattr(
            single_module, "get_user_scitex_dir", lambda user, session_key: tmp_path
        )
        monkeypatch.setattr(
            single_module,
            "get_oa_url_for_identifiers",
            lambda *a: ("https://arxiv.org/pdf/2301.1.pdf", "arxiv"),
        )

        async def _fake_none(oa_url, output_path, metadata, timeout):
            return None

        monkeypatch.setattr(
            single_module, "try_download_open_access_async", _fake_none
        )
        request = _request(
            method="post", body=json.dumps({"arxiv_id": "2301.1"})
        )
        # Act
        response = api_download_pdf(request)
        # Assert
        payload = _json(response)
        assert payload["downloaded"] is False
        assert "reason" in payload

    def test_download_exception_returns_500(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setattr(
            single_module, "get_user_scitex_dir", lambda user, session_key: tmp_path
        )
        monkeypatch.setattr(
            single_module,
            "get_oa_url_for_identifiers",
            lambda *a: ("https://arxiv.org/pdf/2301.1.pdf", "arxiv"),
        )

        async def _fake_boom(oa_url, output_path, metadata, timeout):
            raise RuntimeError("network down")

        monkeypatch.setattr(
            single_module, "try_download_open_access_async", _fake_boom
        )
        request = _request(
            method="post", body=json.dumps({"arxiv_id": "2301.1"})
        )
        # Act
        response = api_download_pdf(request)
        # Assert
        assert response.status_code == 500
        assert _json(response)["status"] == "error"


# ---------------------------------------------------------------------------
# api_download_pdf_bulk + helpers
# ---------------------------------------------------------------------------


class TestProcessSinglePaper:
    def test_no_identifier_skipped(self, tmp_path):
        # Arrange
        paper = {"title": "No IDs"}
        # Act
        result = _process_single_paper(paper, tmp_path)
        # Assert
        assert result == {
            "identifier": None,
            "status": "skipped",
            "reason": "No identifier",
        }

    def test_existing_pdf_returns_exists(self, tmp_path):
        # Arrange
        (tmp_path / "Paper_10.1_x.pdf").write_bytes(b"%PDF")
        paper = {"doi": "10.1/x", "title": "T"}
        # Act
        result = _process_single_paper(paper, tmp_path)
        # Assert
        assert result["status"] == "exists"
        assert result["identifier"] == "10.1/x"

    def test_non_arxiv_skipped(self, tmp_path):
        # Arrange
        paper = {"doi": "10.1/x", "title": "Paywalled"}
        # Act
        result = _process_single_paper(paper, tmp_path)
        # Assert
        assert result["status"] == "skipped"
        assert "open access" in result["reason"]

    def test_check_existing_pdf_by_arxiv(self, tmp_path):
        # Arrange
        (tmp_path / "T_2301.1.pdf").write_bytes(b"%PDF")
        # Act / Assert
        assert _check_existing_pdf(tmp_path, "", "2301.1") is True
        assert _check_existing_pdf(tmp_path, "10.9/other", "") is False


class TestDownloadArxivPdf:
    def test_success(self, tmp_path, monkeypatch):
        # Arrange
        async def _fake_ok(oa_url, output_path, metadata, timeout):
            output_path.write_bytes(b"%PDF")
            return output_path

        monkeypatch.setattr(
            bulk_module, "try_download_open_access_async", _fake_ok
        )
        # Act
        result = _download_arxiv_pdf("2301.1", "T", {"title": "T"}, tmp_path)
        # Assert
        assert result["status"] == "downloaded"
        assert result["identifier"] == "2301.1"
        assert result["filename"].endswith(".pdf")

    def test_failure_returns_failed(self, tmp_path, monkeypatch):
        # Arrange
        async def _fake_none(oa_url, output_path, metadata, timeout):
            return None

        monkeypatch.setattr(
            bulk_module, "try_download_open_access_async", _fake_none
        )
        # Act
        result = _download_arxiv_pdf("2301.1", "T", {"title": "T"}, tmp_path)
        # Assert
        assert result["status"] == "failed"

    def test_exception_returns_error(self, tmp_path, monkeypatch):
        # Arrange
        async def _fake_boom(oa_url, output_path, metadata, timeout):
            raise RuntimeError("boom")

        monkeypatch.setattr(
            bulk_module, "try_download_open_access_async", _fake_boom
        )
        # Act
        result = _download_arxiv_pdf("2301.1", "T", {"title": "T"}, tmp_path)
        # Assert
        assert result["status"] == "error"
        assert result["reason"] == "boom"


class TestApiDownloadPdfBulk:
    def test_service_unavailable(self, monkeypatch):
        # Arrange
        monkeypatch.setattr(bulk_module, "SCITEX_PDF_AVAILABLE", False)
        request = _request(method="post", body=json.dumps({"papers": [{}]}))
        # Act
        response = api_download_pdf_bulk(request)
        # Assert
        assert response.status_code == 503

    def test_invalid_json(self):
        # Arrange
        request = _request(method="post", body="nope{")
        # Act
        response = api_download_pdf_bulk(request)
        # Assert
        assert response.status_code == 400

    def test_empty_papers(self):
        # Arrange
        request = _request(method="post", body=json.dumps({"papers": []}))
        # Act
        response = api_download_pdf_bulk(request)
        # Assert
        assert response.status_code == 400

    def test_too_many_papers(self):
        # Arrange
        papers = [{"arxiv_id": f"2301.{i}"} for i in range(51)]
        request = _request(method="post", body=json.dumps({"papers": papers}))
        # Act
        response = api_download_pdf_bulk(request)
        # Assert
        assert response.status_code == 400

    def test_mixed_summary(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setattr(
            bulk_module, "get_user_scitex_dir", lambda user, session_key: tmp_path
        )
        downloads = tmp_path / "scholar" / "library" / "downloads"
        downloads.mkdir(parents=True)
        (downloads / "Existing_10.1_cached.pdf").write_bytes(b"%PDF")

        async def _fake_ok(oa_url, output_path, metadata, timeout):
            output_path.write_bytes(b"%PDF")
            return output_path

        monkeypatch.setattr(bulk_module, "try_download_open_access_async", _fake_ok)
        papers = [
            {"doi": "10.1/cached", "title": "Existing"},  # exists
            {"arxiv_id": "2301.1", "title": "Fresh"},  # downloaded
            {"doi": "10.1/paywalled", "title": "Paywalled"},  # skipped (no arxiv)
            {"title": "No IDs"},  # skipped (no identifier)
        ]
        request = _request(method="post", body=json.dumps({"papers": papers}))
        # Act
        response = api_download_pdf_bulk(request)
        # Assert
        assert response.status_code == 200
        payload = _json(response)
        assert payload["status"] == "success"
        assert payload["summary"] == {
            "total": 4,
            "downloaded": 1,
            "existed": 1,
            "failed": 0,
            "skipped": 2,
        }
        assert [r["status"] for r in payload["results"]] == [
            "exists",
            "downloaded",
            "skipped",
            "skipped",
        ]

    def test_rejects_get(self):
        # Arrange
        request = _request()
        # Act
        response = api_download_pdf_bulk(request)
        # Assert
        assert response.status_code == 405


class TestUtilsModuleFlags:
    def test_scitex_pdf_available_matches_install(self):
        # Arrange / Act
        try:
            from scitex.scholar.pdf_download.strategies import (  # noqa: F401
                try_download_open_access_async,
            )

            expected = True
        except ImportError:
            expected = False
        # Assert
        assert utils_module.SCITEX_PDF_AVAILABLE is expected


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__), "-v"])


# EOF
