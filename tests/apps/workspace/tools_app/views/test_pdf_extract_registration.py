#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the PDF text/figure extractor's registration and routing.

SCOPE, STATED UP FRONT: these do NOT exercise extraction. poppler
(`pdftotext` / `pdfimages`) is absent from the agent container these run in, so
an end-to-end test here would either fail for the wrong reason or — worse —
"pass" by exercising the 503 branch and look like coverage of the happy path.
Verifying real extraction belongs on a host that has poppler; production does
(measured 2026-08-16 in scitex-hub-prod-django-1).

What IS worth guarding mechanically is the part that silently breaks a tool
without any error: it is registered but unreachable, or reachable at a path
nobody advertises. Both look correct in the source.
"""

from django.urls import reverse

from apps.workspace.tools_app.views.tools_data import get_tool_domains
from apps.workspace.tools_app.views.tools_data_pdf import PDF_TOOLS

_TOOL_NAME = "PDF Text & Figure Extractor"


class TestExtractorIsRegistered:
    """A tool the Tools page never lists cannot be found by anyone."""

    def test_extractor_is_listed_in_the_pdf_domain(self):
        # Arrange
        domains = get_tool_domains()
        # Act
        pdf = next(d for d in domains if d["slug"] == "pdf")
        # Assert
        assert any(t["name"] == _TOOL_NAME for t in pdf["tools"])

    def test_extractor_declares_a_slug(self):
        # Every sibling in this domain carries one; a missing slug breaks the
        # hash-anchor the Tools page builds per tool.
        # Arrange
        tool = next(t for t in PDF_TOOLS if t["name"] == _TOOL_NAME)
        # Act
        slug = tool.get("slug", "")
        # Assert
        assert slug == "pdf-text-figure-extractor"


class TestExtractorRoutesResolve:
    """The advertised URL must be the one the router serves.

    The `/apps/` prefix is not decoration: the tools app is mounted under it, so
    a bare `/tools/...` path is swallowed by project_app's detail route and
    RESOLVES while returning 404 to the user. Asserting the served path — not
    merely that something resolves — is the only check that tells those apart.
    """

    def test_page_route_is_registered_under_apps(self):
        # Arrange
        expected = "/apps/tools/extract-pdf/"
        # Act
        resolved = reverse("tools_app:tool_extract_pdf")
        # Assert
        assert resolved == expected

    def test_the_advertised_url_is_the_served_one(self):
        # Arrange
        tool = next(t for t in PDF_TOOLS if t["name"] == _TOOL_NAME)
        # Act
        served = reverse("tools_app:tool_extract_pdf")
        # Assert
        assert tool["bookmarklet_url"] == served

    def test_extract_api_route_is_registered(self):
        # Arrange
        expected = "/apps/tools/api/pdf-extract/"
        # Act
        resolved = reverse("tools_app:api_pdf_extract")
        # Assert
        assert resolved == expected

    def test_capabilities_api_route_is_registered(self):
        # The page asks this BEFORE offering controls, so if it is unrouted the
        # UI silently offers options the server cannot honour.
        # Arrange
        expected = "/apps/tools/api/pdf-extract/capabilities/"
        # Act
        resolved = reverse("tools_app:api_pdf_extract_capabilities")
        # Assert
        assert resolved == expected


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
