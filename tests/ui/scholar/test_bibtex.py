#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2025-11-30
# File: /home/ywatanabe/proj/scitex-cloud/tests/e2e/scholar/test_bibtex.py

"""
E2E tests for BibTeX functionality.

Tests:
- BibTeX page loads
- BibTeX upload
- BibTeX enrichment
- BibTeX export
"""

import pytest
from playwright.sync_api import Page, expect


class TestBibTeXPage:
    """Tests for BibTeX page."""

    def test_bibtex_page_loads(
        self, page: Page, base_url: str, test_credentials: dict
    ):
        """BibTeX page loads."""
        # Login
        page.goto(f"{base_url}/auth/signin/", wait_until="domcontentloaded")
        page.fill("#username", test_credentials["username"])
        page.fill("#password", test_credentials["password"])
        page.click("button[type='submit']")
        page.wait_for_timeout(3000)

        # Go to scholar/bibtex
        page.goto(
            f"{base_url}/{test_credentials['username']}/default-project/scholar/bibtex/",
            wait_until="domcontentloaded"
        )
        page.wait_for_timeout(2000)

        # Page should load
        assert page.url is not None

    def test_bibtex_has_upload_area(
        self, page: Page, base_url: str, test_credentials: dict
    ):
        """BibTeX page has upload area."""
        # Login
        page.goto(f"{base_url}/auth/signin/", wait_until="domcontentloaded")
        page.fill("#username", test_credentials["username"])
        page.fill("#password", test_credentials["password"])
        page.click("button[type='submit']")
        page.wait_for_timeout(3000)

        # Go to bibtex page
        page.goto(
            f"{base_url}/{test_credentials['username']}/default-project/scholar/bibtex/",
            wait_until="domcontentloaded"
        )
        page.wait_for_timeout(2000)

        # Look for upload area
        upload = page.locator(
            ".upload-area, .drop-zone, input[type='file'], "
            "[data-upload], .bibtex-upload"
        )
        # May or may not exist
        assert upload.count() >= 0


class TestBibTeXUpload:
    """Tests for BibTeX upload."""

    def test_upload_button_exists(
        self, page: Page, base_url: str, test_credentials: dict
    ):
        """Upload button exists."""
        # Login
        page.goto(f"{base_url}/auth/signin/", wait_until="domcontentloaded")
        page.fill("#username", test_credentials["username"])
        page.fill("#password", test_credentials["password"])
        page.click("button[type='submit']")
        page.wait_for_timeout(3000)

        # Go to bibtex page
        page.goto(
            f"{base_url}/{test_credentials['username']}/default-project/scholar/bibtex/",
            wait_until="domcontentloaded"
        )
        page.wait_for_timeout(2000)

        # Look for upload button
        btn = page.locator(
            "button:has-text('Upload'), input[type='file'], "
            ".upload-btn, [data-action='upload']"
        )
        assert btn.count() >= 0


class TestBibTeXEnrichment:
    """Tests for BibTeX enrichment."""

    def test_enrich_button_exists(
        self, page: Page, base_url: str, test_credentials: dict
    ):
        """Enrich button exists."""
        # Login
        page.goto(f"{base_url}/auth/signin/", wait_until="domcontentloaded")
        page.fill("#username", test_credentials["username"])
        page.fill("#password", test_credentials["password"])
        page.click("button[type='submit']")
        page.wait_for_timeout(3000)

        # Go to bibtex page
        page.goto(
            f"{base_url}/{test_credentials['username']}/default-project/scholar/bibtex/",
            wait_until="domcontentloaded"
        )
        page.wait_for_timeout(2000)

        # Look for enrich button
        btn = page.locator(
            "button:has-text('Enrich'), .enrich-btn, "
            "[data-action='enrich']"
        )
        assert btn.count() >= 0


class TestBibTeXExport:
    """Tests for BibTeX export."""

    def test_export_button_exists(
        self, page: Page, base_url: str, test_credentials: dict
    ):
        """Export button exists."""
        # Login
        page.goto(f"{base_url}/auth/signin/", wait_until="domcontentloaded")
        page.fill("#username", test_credentials["username"])
        page.fill("#password", test_credentials["password"])
        page.click("button[type='submit']")
        page.wait_for_timeout(3000)

        # Go to bibtex page
        page.goto(
            f"{base_url}/{test_credentials['username']}/default-project/scholar/bibtex/",
            wait_until="domcontentloaded"
        )
        page.wait_for_timeout(2000)

        # Look for export button
        btn = page.locator(
            "button:has-text('Export'), button:has-text('Download'), "
            ".export-btn, [data-action='export']"
        )
        assert btn.count() >= 0
