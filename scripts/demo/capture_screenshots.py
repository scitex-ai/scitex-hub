#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2026-02-18 20:15:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/scripts/demo/capture_screenshots.py

"""
SciTeX Demo Screenshot Capture Script

Captures screenshots of SciTeX pages after logging in as test-user.
Uses parallel browser tabs for fast capture.

Credentials are automatically loaded from deployment/docker/envs/.env.dev:
    - SCITEX_CLOUD_TEST_USER_USERNAME (default: test-user)
    - SCITEX_CLOUD_TEST_USER_PASSWORD (default: Password123!)

Usage:
    python scripts/demo/capture_screenshots.py [OPTIONS]

Examples:
    # Fast: repo + modules only (default)
    python scripts/demo/capture_screenshots.py

    # All groups, no zen mode (fastest full coverage)
    python scripts/demo/capture_screenshots.py --groups all --no-zen

    # Modules + tools pages
    python scripts/demo/capture_screenshots.py --groups repo,modules,tools

    # Everything with zen mode
    python scripts/demo/capture_screenshots.py --groups all --zen

    # Headless mode
    python scripts/demo/capture_screenshots.py --headless

Page groups:
    repo     - User profile and project pages
    modules  - Writer, Scholar, Vis, Console, Clew, Home, Discovery, Figrecipe, Store, Tools
    tools    - All individual tool pages under /apps/tools/ (25 tools)
    docs     - Documentation pages (/apps/docs/: index, Python, API)
    basic    - Homepage, About, Server Status
"""

import asyncio
from pathlib import Path

from _capture import run_capture_async
from _config import (
    DEFAULT_VIEWPORT,
    VALID_GROUPS,
    VIEWPORT_PRESETS,
    build_pages,
)
from scitex.logging import getLogger
from scitex.session import session

logger = getLogger(__name__)


@session(verbose=True, sdir_suffix="demo-screenshots")
def main(
    headless: bool = False,
    viewport: str = DEFAULT_VIEWPORT,
    width: int = None,
    height: int = None,
    concurrency: int = 8,
    groups: str = "repo,modules",
    zen: bool = True,
) -> int:
    """
    Capture SciTeX demo screenshots with parallel browser tabs.

    Args:
        headless: Run browser in headless mode
        viewport: Viewport preset name (desktop, laptop, tablet, mobile)
        width: Custom viewport width in pixels (overrides preset)
        height: Custom viewport height in pixels (overrides preset)
        concurrency: Max parallel browser tabs (default: 8)
        groups: Comma-separated page groups to capture (default: repo,modules).
                Valid groups: repo, modules, tools, docs, basic. Use "all" for everything.
        zen: Capture zen mode for module pages (default: True)

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    logger.info("Starting SciTeX demo screenshot capture")

    # Validate groups (allow "all", named groups, and "-group" exclusions)
    for token in groups.split(","):
        token = token.strip().lstrip("-")
        if token and token != "all" and token not in VALID_GROUPS:
            logger.error(f"Unknown group '{token}'. Valid: {VALID_GROUPS}")
            return 1

    # Build page list
    pages, slow_pages = build_pages(groups=groups, zen=zen)

    if not pages:
        logger.error("No pages to capture. Check --groups argument.")
        return 1

    logger.info(f"Groups: {groups} | Zen: {zen}")
    logger.info(f"Pages to capture: {len(pages)}")

    # Determine viewport size
    if width is None or height is None:
        if viewport not in VIEWPORT_PRESETS:
            logger.warning(
                f"Unknown viewport preset '{viewport}', using '{DEFAULT_VIEWPORT}'"
            )
            viewport = DEFAULT_VIEWPORT

        viewport_config = VIEWPORT_PRESETS[viewport]
        width = viewport_config["width"]
        height = viewport_config["height"]
        viewport_name = viewport
    else:
        viewport_name = "custom"

    logger.info(f"Using viewport: {viewport_name} ({width}x{height})")

    output_dir = Path(CONFIG["SDIR_RUN"]) / "screenshots"

    # Run async workflow
    exit_code = asyncio.run(
        run_capture_async(
            output_dir,
            pages=pages,
            slow_pages=slow_pages,
            headless=headless,
            width=width,
            height=height,
            viewport_name=viewport_name,
            concurrency=concurrency,
        )
    )

    if exit_code == 0:
        logger.info("Screenshot capture completed successfully")
    else:
        logger.error(f"Screenshot capture failed with exit code {exit_code}")

    return exit_code


def _inject_page_listing_into_help():
    """Programmatically inject page listings into --help from PAGE_GROUPS config."""
    from _config import PAGE_GROUPS

    detail = "\n".join(
        f"                {name:10s}: {', '.join(pages)}"
        for name, pages in PAGE_GROUPS.items()
    )
    new_text = (
        "Valid groups:\n" + detail + '\n                Use "all" for everything.'
    )
    old_text = (
        'Valid groups: repo, modules, tools, docs, basic. Use "all" for everything.'
    )

    main.__doc__ = main.__doc__.replace(old_text, new_text)
    if hasattr(main, "__wrapped__"):
        main.__wrapped__.__doc__ = main.__wrapped__.__doc__.replace(old_text, new_text)


if __name__ == "__main__":
    _inject_page_listing_into_help()
    main()

# EOF
