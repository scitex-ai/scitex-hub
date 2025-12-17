#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-24 19:52:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/scripts/maintenance/capture_demo_screenshots.py


"""
SciTeX Demo Screenshot Capture Script

Captures screenshots of SciTeX pages after logging in as test-user.

Credentials are automatically loaded from SECRET/.env.dev:
    - SCITEX_CLOUD_TEST_USER_USERNAME (default: test-user)
    - SCITEX_CLOUD_TEST_USER_PASSWORD (default: Password123!)

Usage:
    python scripts/maintenance/capture_demo_screenshots.py [OPTIONS]

Examples:
    # Visible browser (default)
    python scripts/maintenance/capture_demo_screenshots.py

    # Headless mode
    python scripts/maintenance/capture_demo_screenshots.py --headless

    # Custom viewport
    python scripts/maintenance/capture_demo_screenshots.py --width 1280 --height 720
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from playwright.async_api import Page
from scitex.session import session
from scitex.browser import fill_with_fallbacks_async
from scitex.browser import click_with_fallbacks_async
from scitex.logging import getLogger

logger = getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

# Load environment variables from .env file
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = PROJECT_ROOT / "SECRET" / ".env.dev"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
    logger.info(f"Loaded environment variables from {ENV_FILE}")
else:
    logger.warning(f"Environment file not found: {ENV_FILE}")

BASE_URL = "http://127.0.0.1:8000"

# Load test user credentials from environment variables
TEST_USER = os.getenv("SCITEX_CLOUD_TEST_USER_USERNAME", "test-user")
TEST_PASSWORD = os.getenv("SCITEX_CLOUD_TEST_USER_PASSWORD", "Password123!")

# Pages to capture after login
PAGES_TO_CAPTURE = [
    # Landing
    {"path": "/", "name": "homepage"},
    # Repository Operations
    {"path": "/new/", "name": "new-repository"},
    {"path": f"/{TEST_USER}/", "name": "user-profile"},
    # Social/Explore
    {"path": "/social/explore/", "name": "explore-repos"},
    {"path": "/social/explore/?tab=users", "name": "explore-users"},
    # Specific Repository
    {"path": f"/{TEST_USER}/default-project/", "name": "repo-overview"},
    {"path": f"/{TEST_USER}/default-project/issues/", "name": "repo-issues"},
    {"path": f"/{TEST_USER}/default-project/pulls/", "name": "repo-pulls"},
    {
        "path": f"/{TEST_USER}/default-project/settings/",
        "name": "repo-settings",
    },
    # Writer
    {
        "path": f"/{TEST_USER}/default-project/scitex/writer/01_manuscript/",
        "name": "writer-manuscript",
    },
    # Account Settings
    {"path": "/accounts/settings/profile/", "name": "settings-profile"},
    {"path": "/accounts/settings/account/", "name": "settings-account"},
    {"path": "/accounts/settings/appearance/", "name": "settings-appearance"},
    {
        "path": "/accounts/settings/integrations/",
        "name": "settings-integrations",
    },
    {"path": "/accounts/settings/ssh-keys/", "name": "settings-ssh-keys"},
    {"path": "/accounts/settings/api-keys/", "name": "settings-api-keys"},
    {
        "path": f"/{TEST_USER}/settings/repositories/",
        "name": "user-settings-repositories",
    },
    # Modules
    {"path": "/scholar/bibtex/", "name": "scholar"},
    {"path": "/code/", "name": "code"},
    {"path": "/vis/", "name": "vis"},
    {"path": "/writer/", "name": "writer"},
    {"path": "/tools/", "name": "tools"},
]


# ============================================================================
# Core Functions
# ============================================================================


async def login_to_scitex(page: Page, username: str, password: str) -> bool:
    """
    Log in to SciTeX using provided credentials.

    Args:
        page: Playwright page object
        username: Username for login
        password: Password for login

    Returns:
        True if login successful, False otherwise
    """
    logger.info(f"Attempting login as '{username}'")

    try:
        # Navigate to login page
        login_url = f"{BASE_URL}/auth/signin/"
        logger.info(f"Navigating to {login_url}")
        await page.goto(login_url, wait_until="load", timeout=30_000)
        await asyncio.sleep(2)

        # Check if already authenticated
        is_authenticated = await page.evaluate(
            "() => document.body.getAttribute('data-user-authenticated') === 'true'"
        )

        if is_authenticated:
            logger.info(
                "Already logged in (detected via data-user-authenticated)"
            )
            await page.goto(BASE_URL, wait_until="load")
            return True

        # Check if redirected (already logged in)
        if "/auth/signin" not in page.url:
            logger.info("Already logged in (redirected from signin page)")
            return True

        # Wait for form
        logger.info("Waiting for login form")
        await page.wait_for_selector("form#login-form", timeout=5_000)

        # Fill credentials
        logger.info("Entering credentials")
        await fill_with_fallbacks_async(
            page, "input#username", username, verbose=False
        )
        await asyncio.sleep(0.3)

        await fill_with_fallbacks_async(
            page, "input#password", password, verbose=False
        )
        await asyncio.sleep(0.3)

        # Submit
        logger.info("Submitting login form")
        await click_with_fallbacks_async(
            page, "button.btn-primary.w-100", verbose=False
        )

        # Wait for navigation
        try:
            await page.wait_for_url(
                lambda url: "/auth/signin" not in url, timeout=10_000
            )
            logger.info("Navigation detected after login")
        except:
            logger.warning("No navigation detected")

        await asyncio.sleep(2)

        # Verify
        if "/auth/signin" not in page.url:
            logger.info(f"Login successful as '{username}'")
            return True
        else:
            logger.error("Login failed - still on signin page")
            return False

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def capture_page_screenshot(
    page: Page,
    page_info: dict,
    output_dir: Path,
    index: int,
    total: int,
) -> Path | None:
    """
    Capture a screenshot of a specific SciTeX page.

    Args:
        page: Playwright page object
        page_info: Dict with 'path' and 'name' keys
        output_dir: Directory to save screenshots
        index: Current page number (for progress)
        total: Total number of pages

    Returns:
        Path to saved screenshot, or None if failed
    """

    page_path = page_info["path"]
    page_name = page_info["name"]
    url = f"{BASE_URL}{page_path}"
    wait_sec = 10.0 if page_path in ["/code/", "/writer/"] else 1.0

    screenshot_filename = f"{index:02d}_{page_name}.png"
    screenshot_path = output_dir / screenshot_filename

    logger.info(f"[{index}/{total}] {page_name}")
    logger.info(f"  URL: {url}")

    try:
        # Navigate
        await page.goto(url, wait_until="load", timeout=30000)
        await asyncio.sleep(wait_sec)

        # Capture
        await page.screenshot(
            path=str(screenshot_path), full_page=True, type="png"
        )

        logger.info(f"  ✓ Saved: {screenshot_filename}")
        return screenshot_path

    except Exception as e:
        logger.error(f"  ✗ Failed to capture {page_name}: {str(e)}")
        return None


async def run_capture_async(
    output_dir: str or Path,
    headless: bool,
    width: int,
    height: int,
) -> int:
    """
    Async screenshot capture workflow.

    Args:
        headless: Run browser in headless mode
        width: Viewport width
        height: Viewport height

    Returns:
        Exit code (0 = success, 1 = failure)
    """

    # Use session output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Browser session directory
    session_dir = Path.home() / ".scitex" / "browser" / "screenshot_session"
    session_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Session directory: {session_dir}")
    logger.info(f"Base URL: {BASE_URL}")
    logger.info(f"Pages to capture: {len(PAGES_TO_CAPTURE)}")
    logger.info(f"Viewport: {width}x{height}")
    logger.info(f"Headless: {headless}")

    try:
        async with async_playwright() as p:
            # Launch with persistent context
            logger.info("Launching browser with persistent session...")
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(session_dir),
                headless=headless,
                viewport={"width": width, "height": height},
                args=["--start-maximized"] if not headless else [],
                ignore_https_errors=True,
            )
            logger.info("✓ Browser launched")

            # Get page
            page = (
                context.pages[0] if context.pages else await context.new_page()
            )

            # Step 1: Authentication
            logger.info("\n=== Step 1: Authentication ===")
            await page.goto(BASE_URL, wait_until="load")
            await asyncio.sleep(1)

            is_authenticated = await page.evaluate(
                "() => document.body.getAttribute('data-user-authenticated') === 'true'"
            )

            if is_authenticated:
                logger.info("✓ Already authenticated")
            else:
                logger.info("Logging in...")
                if not await login_to_scitex(page, TEST_USER, TEST_PASSWORD):
                    logger.error("Cannot proceed without authentication")
                    return 1
                logger.info("✓ Login successful")

            # Step 2: Capture screenshots
            logger.info("\n=== Step 2: Capturing Screenshots ===")
            captured = []
            failed = []
            total = len(PAGES_TO_CAPTURE)

            for i, page_info in enumerate(PAGES_TO_CAPTURE, 1):
                result = await capture_page_screenshot(
                    page, page_info, output_dir, i, total
                )

                if result:
                    captured.append(result)
                else:
                    failed.append(page_info["name"])

                await asyncio.sleep(0.3)

            # Step 3: Summary
            logger.info("\n=== Summary ===")
            logger.info(f"✓ Captured: {len(captured)}/{total} screenshots")

            if failed:
                logger.warning(f"⚠ Failed: {len(failed)} screenshot(s)")
                for name in failed:
                    logger.warning(f"  - {name}")

            logger.info(f"\n📁 Output: {output_dir}")
            logger.info(
                f"📊 Total files: {len(list(output_dir.glob('*.png')))}"
            )

            await context.close()
            logger.info("✓ Browser session saved")

            return 0 if not failed else 1

    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
        return 130

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1


# ============================================================================
# Main Entry Point with @session Decorator
# ============================================================================


@session(verbose=True, sdir_suffix="demo-screenshots")
def main(
    headless: bool = False,
    width: int = 1920,
    height: int = 1080,
) -> int:
    """
    Capture SciTeX demo screenshots with persistent browser session.

    Args:
        headless: Run browser in headless mode
        width: Viewport width in pixels
        height: Viewport height in pixels

    Returns:
        Exit code (0 = success, 1 = failure)
    """

    logger.info("Starting SciTeX demo screenshot capture")

    output_dir = Path(CONFIG["SDIR_OUT"]) / "screenshots"

    # Run async workflow
    exit_code = asyncio.run(
        run_capture_async(
            output_dir,
            headless=headless,
            width=width,
            height=height,
        )
    )

    if exit_code == 0:
        logger.info("✓ Screenshot capture completed successfully")
    else:
        logger.error(f"✗ Screenshot capture failed with exit code {exit_code}")

    return exit_code


if __name__ == "__main__":
    main()

# EOF
