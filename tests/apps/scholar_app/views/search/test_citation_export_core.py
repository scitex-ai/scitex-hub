#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/scholar_app/views/search/citation_export_core.py"""

import pytest

from apps.scholar_app.views.search.citation_export_core import (
    generate_bibtex,
    generate_citation,
    generate_endnote,
    generate_ris,
    get_file_extension,
    make_citation_key,
    sanitize_filename,
)


class TestGenerateCitationKey:
    """make_citation_key delegates to scitex.scholar.formatting.make_citation_key."""

    def test_basic(self):
        result = make_citation_key("Smith", 2020)
        assert "smith" in result.lower()
        assert "2020" in result

    def test_no_year(self):
        result = make_citation_key("Jones", None)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_string(self):
        assert isinstance(make_citation_key("Doe", 1999), str)


class TestSanitizeFilename:
    """sanitize_filename re-exports scitex.scholar.formatting.sanitize_filename."""

    def test_basic(self):
        result = sanitize_filename("My Paper Title")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_removes_special_chars(self):
        result = sanitize_filename("Paper: A/B Test?")
        assert "/" not in result
        assert "?" not in result

    def test_max_length(self):
        long_name = "A" * 200
        result = sanitize_filename(long_name)
        assert len(result) <= 50


class TestGetFileExtension:
    def test_bibtex(self):
        assert get_file_extension("bibtex") == "bib"

    def test_endnote(self):
        assert get_file_extension("endnote") == "enw"

    def test_ris(self):
        assert get_file_extension("ris") == "ris"

    def test_unknown(self):
        assert get_file_extension("unknown") == "txt"

    def test_case_insensitive(self):
        assert get_file_extension("BibTeX") == "bib"


class TestGenerateBibtex:
    def test_basic(self):
        result = generate_bibtex(
            "Smith2020",
            "Test Title",
            "Smith, J.",
            "Nature",
            2020,
            "10.1234/test",
            "",
            "",
            "",
            "",
        )
        assert "@article" in result
        assert "Test Title" in result
        assert "Smith2020" in result


class TestGenerateEndnote:
    def test_basic(self):
        result = generate_endnote(
            "Test Title", "Smith, J.", "Nature", 2020, "10.1234/test", "", "", "", ""
        )
        assert "Test Title" in result
        assert "Smith" in result  # scitex splits "Smith, J." into separate %A fields


class TestGenerateRis:
    def test_basic(self):
        result = generate_ris(
            "Test Title", "Smith, J.", "Nature", 2020, "10.1234/test", "", "", "", ""
        )
        assert "TY  - JOUR" in result
        assert "Test Title" in result
        assert "ER  -" in result


class TestGenerateCitation:
    def test_bibtex_format(self):
        paper = {
            "title": "Test",
            "authors": "Smith, J.",
            "journal": "Nature",
            "year": 2020,
        }
        result = generate_citation(paper, "bibtex")
        assert result is not None
        assert "@" in result

    def test_ris_format(self):
        paper = {
            "title": "Test",
            "authors": "Smith, J.",
            "journal": "Nature",
            "year": 2020,
        }
        result = generate_citation(paper, "ris")
        assert result is not None
        assert "TY" in result

    def test_endnote_format(self):
        paper = {
            "title": "Test",
            "authors": "Smith, J.",
            "journal": "Nature",
            "year": 2020,
        }
        result = generate_citation(paper, "endnote")
        assert result is not None

    def test_unknown_format_returns_none(self):
        paper = {"title": "Test"}
        assert generate_citation(paper, "unknown_format") is None


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])

# EOF
