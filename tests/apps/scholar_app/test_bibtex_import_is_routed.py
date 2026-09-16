"""The library page's "Import BibTeX (.bib)" button posts to a real route.

The view existed but no URL pattern pointed at it, so every import was a 404.
"""

from __future__ import annotations

from django.urls import resolve

from apps.workspace.scholar_app.views.library.bibtex_import import api_import_bibtex


def test_import_bibtex_endpoint_resolves_to_the_import_view():
    # Arrange
    path = "/apps/scholar/api/import/bibtex/"

    # Act
    match = resolve(path)

    # Assert
    assert match.func is api_import_bibtex
