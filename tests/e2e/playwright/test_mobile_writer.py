#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobile Writer Tests

Verify the writer pane dimensions on mobile viewport.
The writer editing pane must be at least 48px wide to be usable.
"""

import pytest


class TestMobileWriter:
    """Writer module on iPhone 14 viewport."""

    def test_writer_page_loads(self, visitor_mobile_page, screenshot):
        """Writer page loads on mobile."""
        resp = visitor_mobile_page.goto("/apps/writer/")
        screenshot(visitor_mobile_page, "writer_mobile_loaded")
        assert resp.status == 200, f"Writer page returned {resp.status}"

    def test_writer_pane_minimum_width(self, visitor_mobile_page, screenshot):
        """Writer editing pane is at least 48px wide on mobile."""
        visitor_mobile_page.goto("/apps/writer/")
        visitor_mobile_page.wait_for_load_state("networkidle")

        # Find the writer/editor pane
        pane = visitor_mobile_page.locator(
            "[data-testid='writer-pane'], "
            ".writer-pane, "
            "#writer-pane, "
            ".editor-pane, "
            ".editor-container, "
            ".CodeMirror, "
            "textarea.editor"
        ).first

        if pane.count() == 0:
            pytest.skip("No writer pane element found on page")

        box = pane.bounding_box()
        assert box is not None, "Writer pane has no bounding box (not visible)"
        assert (
            box["width"] >= 48
        ), f"Writer pane width is {box['width']}px, minimum required is 48px"

        screenshot(visitor_mobile_page, "writer_pane_width")

    def test_writer_pane_not_clipped(self, visitor_mobile_page):
        """Writer pane is not clipped beyond viewport on mobile."""
        visitor_mobile_page.goto("/apps/writer/")
        visitor_mobile_page.wait_for_load_state("networkidle")

        pane = visitor_mobile_page.locator(
            "[data-testid='writer-pane'], "
            ".writer-pane, "
            "#writer-pane, "
            ".editor-pane, "
            ".editor-container"
        ).first

        if pane.count() == 0:
            pytest.skip("No writer pane element found on page")

        box = pane.bounding_box()
        if box is None:
            pytest.skip("Writer pane not visible")

        viewport = visitor_mobile_page.viewport_size
        assert box["x"] + box["width"] <= viewport["width"] + 1, (
            f"Writer pane extends beyond viewport: "
            f"x={box['x']}, width={box['width']}, viewport={viewport['width']}"
        )
