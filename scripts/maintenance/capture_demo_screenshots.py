#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-12-03 02:08:27 (ywatanabe)"
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
import re
from urllib.parse import urlparse
from urllib.parse import parse_qs

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

# Standard viewport sizes for consistent screenshots
VIEWPORT_PRESETS = {
    "desktop": {"width": 1920, "height": 1080},  # Full HD
    "laptop": {"width": 1366, "height": 768},  # Common laptop
    "tablet": {"width": 768, "height": 1024},  # iPad portrait
    "mobile": {"width": 375, "height": 667},  # iPhone SE
}

# Default preset for screenshots
DEFAULT_VIEWPORT = "desktop"

# Pages to capture after login
# Names are automatically generated from path normalization
PAGES_TO_CAPTURE_BASIC = [
    # Landing
    "/",
    "/about/",
    # Status
    "/server-status/",
]

PAGES_TO_CAPTURE_DEV = [
    "/dev/design/",
]

PAGES_TO_CAPTURE_REPO = [
    # Repository Operations
    # "/new/",
    f"/{TEST_USER}/",
    # # Social/Explore
    # "/social/explore/",
    # "/social/explore/?tab=users",
    # Specific Repository
    f"/{TEST_USER}/default-project/",
    # f"/{TEST_USER}/default-project/issues/",
    # f"/{TEST_USER}/default-project/pulls/",
    # f"/{TEST_USER}/default-project/settings/",
    # f"/{TEST_USER}/default-project/scitex/writer/01_manuscript/",
    # f"/{TEST_USER}/settings/repositories/",
]

PAGES_TO_CAPTURE_ACCOUNT = [
    # Account Settings
    "/accounts/settings/profile/",
    # "/accounts/settings/account/",
    # "/accounts/settings/appearance/",
    # "/accounts/settings/integrations/",
    # "/accounts/settings/ssh-keys/",
    # "/accounts/settings/api-keys/",
]

PAGES_TO_CAPTURE_MODULES = [
    # Modules
    "/scholar/",
    "/code/",
    "/vis/",
    "/writer/",
    # "/tools/",
]
PAGES_TO_CAPTURE = [
    # *PAGES_TO_CAPTURE_BASIC,
    # *PAGES_TO_CAPTURE_ACCOUNT,
    # *PAGES_TO_CAPTURE_DEV,
    *PAGES_TO_CAPTURE_REPO,
    *PAGES_TO_CAPTURE_MODULES,
]

# ============================================================================
# Utilities
# ============================================================================


def normalize_path_to_filename(path: str) -> str:
    """
    Normalize a URL path to a valid filename.

    Examples:
        "/" → "homepage"
        "/new/" → "new"
        "/social/explore/" → "social-explore"
        "/social/explore/?tab=users" → "social-explore-tab-users"
        "/test-user/default-project/" → "test-user-default-project"
        "/accounts/settings/profile/" → "accounts-settings-profile"

    Args:
        path: URL path (may include query parameters)

    Returns:
        Normalized filename (without extension)
    """
    # Parse URL to separate path and query
    parsed = urlparse(path)
    clean_path = parsed.path
    query = parsed.query

    # Handle root path
    if clean_path == "/" or clean_path == "":
        name = "homepage"
    else:
        # Remove leading/trailing slashes
        clean_path = clean_path.strip("/")

        # Replace slashes with hyphens
        name = clean_path.replace("/", "-")

    # Add query parameters to filename if present
    if query:
        # Parse query string
        params = parse_qs(query)
        # Add each param to the name
        for key, values in params.items():
            for value in values:
                # Sanitize and append
                safe_value = re.sub(r"[^\w-]", "-", value)
                name += f"-{key}-{safe_value}"

    # Sanitize: replace any remaining special characters with hyphens
    name = re.sub(r"[^\w-]", "-", name)

    # Remove consecutive hyphens
    name = re.sub(r"-+", "-", name)

    # Remove leading/trailing hyphens
    name = name.strip("-")

    return name


# ============================================================================
# Core Functions
# ============================================================================


async def login_to_scitex(page: Page, username: str, password: str) -> bool:
    logger.info(f"Attempting login as '{username}'")
    try:
        login_url = f"{BASE_URL}/auth/signin/"
        logger.info(f"Navigating to {login_url}")
        await page.goto(login_url, wait_until="load", timeout=30_000)
        await asyncio.sleep(2)

        is_authenticated = await page.evaluate(
            "() => document.body.getAttribute('data-user-authenticated') === 'true'"
        )
        if is_authenticated:
            logger.info(
                "Already logged in (detected via data-user-authenticated)"
            )
            await page.goto(BASE_URL, wait_until="load")
            return True

        if "/auth/signin" not in page.url:
            logger.info("Already logged in (redirected from signin page)")
            return True

        logger.info("Waiting for login form")
        await page.wait_for_selector("form#login-form", timeout=5_000)

        logger.info("Entering credentials")
        await fill_with_fallbacks_async(
            page, "input#username", username, verbose=False
        )
        await asyncio.sleep(0.3)
        await fill_with_fallbacks_async(
            page, "input#password", password, verbose=False
        )
        await asyncio.sleep(0.3)

        # Check "Remember me" checkbox if not already checked
        logger.info("Checking 'Remember me' checkbox")
        remember_checkbox = page.locator("input#remember-me, input[name='remember']")
        if await remember_checkbox.count() > 0:
            is_checked = await remember_checkbox.is_checked()
            if not is_checked:
                await remember_checkbox.check()
                await asyncio.sleep(0.2)

        logger.info("Submitting login form")
        await click_with_fallbacks_async(
            page, "button.btn-primary.w-100", verbose=False
        )

        # Wait for navigation after form submission (use 'load' instead of 'networkidle')
        try:
            await page.wait_for_load_state("load", timeout=15_000)
        except Exception:
            pass  # Continue even if load state times out
        await asyncio.sleep(3)  # Give time for redirect and page render

        is_authenticated = await page.evaluate(
            "() => document.body.getAttribute('data-user-authenticated') === 'true'"
        )
        if is_authenticated:
            logger.info(f"Login successful as '{username}'")
            return True

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
    page_path: str,
    output_dir: Path,
    index: int,
    total: int,
) -> Path | None:
    """
    Capture a screenshot of a specific SciTeX page.

    Args:
        page: Playwright page object
        page_path: URL path to capture (e.g., "/", "/new/", "/social/explore/?tab=users")
        output_dir: Directory to save screenshots
        index: Current page number (for progress)
        total: Total number of pages

    Returns:
        Path to saved screenshot, or None if failed
    """

    # Generate filename automatically from path
    page_name = normalize_path_to_filename(page_path)
    url = f"{BASE_URL}{page_path}"
    wait_sec = 3.0 if page_path in PAGES_TO_CAPTURE_MODULES else 1.0

    # Code pages have wide horizontal scroll - capture viewport only
    # Other pages can use full_page for vertical scroll
    use_full_page = page_path not in ["/code/"]

    screenshot_filename = f"{index:02d}_{page_name}.png"
    screenshot_path = output_dir / screenshot_filename

    logger.info(f"[{index}/{total}] {page_name}")
    logger.info(f"  URL: {url}")
    logger.info(f"  Mode: {'full-page' if use_full_page else 'viewport-only'}")

    try:
        # Check if page is still open
        if page.is_closed():
            logger.error(f"  ✗ Page is closed, cannot capture {page_name}")
            return None

        # Navigate
        await page.goto(url, wait_until="load", timeout=30000)
        await asyncio.sleep(wait_sec)

        # For full-page screenshots, try viewport first if it fails
        try:
            await page.screenshot(
                path=str(screenshot_path), full_page=use_full_page, type="png"
            )
        except Exception as screenshot_err:
            if use_full_page:
                logger.warning(f"  Full-page screenshot failed, trying viewport-only: {screenshot_err}")
                await page.screenshot(
                    path=str(screenshot_path), full_page=False, type="png"
                )
            else:
                raise

        logger.info(f"  ✓ Saved: {screenshot_filename}")
        return screenshot_path

    except Exception as e:
        error_msg = str(e)
        logger.error(f"  ✗ Failed to capture {page_name}: {error_msg}")
        # Check if browser/page has been closed - this is fatal
        if "closed" in error_msg.lower():
            logger.error("  Browser or page has been closed - cannot continue")
            raise  # Re-raise to stop the loop
        return None


async def run_capture_async(
    output_dir: str or Path,
    headless: bool,
    width: int,
    height: int,
    viewport_name: str = DEFAULT_VIEWPORT,
) -> int:
    """
    Async screenshot capture workflow.

    Args:
        output_dir: Directory to save screenshots
        headless: Run browser in headless mode
        width: Viewport width
        height: Viewport height
        viewport_name: Name of viewport preset used

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
    logger.info(f"Viewport: {width}x{height} ({viewport_name})")
    logger.info(f"Headless: {headless}")
    logger.info(f"Device pixel ratio: 1.0 (standard)")  # For reproducibility

    try:
        async with async_playwright() as p:
            # Launch with persistent context
            logger.info("Launching browser with persistent session...")
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(session_dir),
                headless=headless,
                viewport={"width": width, "height": height},
                device_scale_factor=1.0,  # Standard DPI for consistent rendering
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
                # Check if logged in as the correct user by visiting profile page
                # The profile link in navbar contains the username
                current_user = await page.evaluate(
                    """() => {
                        // Try to get username from navbar profile link
                        const profileLink = document.querySelector('a[href^="/@"]');
                        if (profileLink) {
                            const href = profileLink.getAttribute('href');
                            // Extract username from /@username/ pattern
                            const match = href.match(/^\/@([^/]+)/);
                            if (match) return match[1];
                        }
                        // Fallback: check for data-username attribute anywhere
                        const elem = document.querySelector('[data-username]');
                        if (elem) return elem.getAttribute('data-username');
                        return null;
                    }"""
                )
                if current_user == TEST_USER:
                    logger.info(f"✓ Already authenticated as '{TEST_USER}'")
                elif current_user is None:
                    # Could not determine current user, assume we need to re-login
                    logger.warning(
                        f"Could not determine current user. Logging out and re-logging in as '{TEST_USER}'..."
                    )
                    logout_url = f"{BASE_URL}/auth/signout/"
                    await page.goto(logout_url, wait_until="load")
                    await asyncio.sleep(1)
                    if not await login_to_scitex(page, TEST_USER, TEST_PASSWORD):
                        logger.error("Cannot proceed without authentication")
                        return 1
                    logger.info(f"✓ Login successful as '{TEST_USER}'")
                else:
                    logger.warning(
                        f"Logged in as '{current_user}', but need '{TEST_USER}'. Logging out..."
                    )
                    # Logout first
                    logout_url = f"{BASE_URL}/auth/signout/"
                    await page.goto(logout_url, wait_until="load")
                    await asyncio.sleep(1)
                    # Now login as correct user
                    if not await login_to_scitex(page, TEST_USER, TEST_PASSWORD):
                        logger.error("Cannot proceed without authentication")
                        return 1
                    logger.info(f"✓ Login successful as '{TEST_USER}'")
            else:
                logger.info(f"Logging in as '{TEST_USER}'...")
                if not await login_to_scitex(page, TEST_USER, TEST_PASSWORD):
                    logger.error("Cannot proceed without authentication")
                    return 1
                logger.info(f"✓ Login successful as '{TEST_USER}'")

            # Step 2: Capture screenshots
            logger.info("\n=== Step 2: Capturing Screenshots ===")
            captured = []
            failed = []
            total = len(PAGES_TO_CAPTURE)

            for i, page_path in enumerate(PAGES_TO_CAPTURE, 1):
                try:
                    result = await capture_page_screenshot(
                        page, page_path, output_dir, i, total
                    )

                    if result:
                        captured.append(result)
                    else:
                        failed.append(normalize_path_to_filename(page_path))

                    await asyncio.sleep(0.3)
                except Exception as loop_err:
                    # Browser closed or fatal error - stop the loop
                    logger.error(f"Fatal error during capture: {loop_err}")
                    failed.append(normalize_path_to_filename(page_path))
                    # Add remaining pages to failed list
                    for j, remaining_path in enumerate(PAGES_TO_CAPTURE[i:], i + 1):
                        failed.append(normalize_path_to_filename(remaining_path))
                    break

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
    viewport: str = DEFAULT_VIEWPORT,
    width: int = None,
    height: int = None,
) -> int:
    """
    Capture SciTeX demo screenshots with persistent browser session.

    Args:
        headless: Run browser in headless mode
        viewport: Viewport preset name (desktop, laptop, tablet, mobile)
        width: Custom viewport width in pixels (overrides preset)
        height: Custom viewport height in pixels (overrides preset)

    Returns:
        Exit code (0 = success, 1 = failure)

    Examples:
        # Use desktop preset (default)
        python scripts/maintenance/capture_demo_screenshots.py

        # Use laptop preset
        python scripts/maintenance/capture_demo_screenshots.py --viewport laptop

        # Custom size
        python scripts/maintenance/capture_demo_screenshots.py --width 1280 --height 720
    """

    logger.info("Starting SciTeX demo screenshot capture")

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
            headless=headless,
            width=width,
            height=height,
            viewport_name=viewport_name,
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
