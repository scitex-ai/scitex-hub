#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2025-12-08
# File: tests/e2e/shared/panel_resizer/conftest.py

"""
Shared fixtures for panel resizer E2E tests.
Uses scitex.browser for visual feedback and failure capture.
"""

import sys
from pathlib import Path

import pytest
from playwright.sync_api import Page

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / "SECRET" / ".env.dev"
ARTIFACTS_DIR = PROJECT_ROOT / "tests" / "e2e" / "artifacts"

# Add scitex-code to path
SCITEX_CODE_PATH = Path.home() / "proj" / "scitex-code" / "src"
if SCITEX_CODE_PATH.exists() and str(SCITEX_CODE_PATH) not in sys.path:
    sys.path.insert(0, str(SCITEX_CODE_PATH))

# Load credentials from .env.dev (avoid shell env interference)
TEST_USER_USERNAME = None
TEST_USER_PASSWORD = None
BASE_URL = "http://127.0.0.1:8000"

if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith("SCITEX_CLOUD_TEST_USER_USERNAME="):
                TEST_USER_USERNAME = line.split("=", 1)[1]
            elif line.startswith("SCITEX_CLOUD_TEST_USER_PASSWORD="):
                TEST_USER_PASSWORD = line.split("=", 1)[1]

CREDENTIALS_AVAILABLE = bool(TEST_USER_USERNAME and TEST_USER_PASSWORD)
if not CREDENTIALS_AVAILABLE:
    import warnings

    warnings.warn(
        f"Test credentials not found in {ENV_FILE} — panel resizer tests will be skipped"
    )

print(f"[panel_resizer conftest] Using credentials: username={TEST_USER_USERNAME}")

# Import ALL utilities from scitex.browser
from scitex.browser import (
    SyncBrowserSession,
    TestMonitor,
    collect_console_logs,
    inject_visual_effects,
    save_failure_artifacts,
    setup_console_interceptor,
    show_click_effect,
    show_cursor_at,
    show_step,
    show_test_result,
)

# Re-export for use in test files
__all__ = [
    "show_step",
    "show_test_result",
    "highlight_element",
    "login_and_navigate",
    "visual_click",
    "visual_drag",
    "TestMonitor",
]

# Workspace configurations
WORKSPACE_APPS = [
    {
        "name": "scholar",
        "url": "/scholar/",
        "sidebar": ".scholar-sidebar",
        "resizer": "#sidebar-resizer",
    },
    {
        "name": "code",
        "url": "/console/",
        "sidebar": ".code-sidebar",
        "resizer": "#sidebar-resizer",
    },
    {
        "name": "vis",
        "url": "/vis/",
        "sidebar": ".vis-sidebar",
        "resizer": "#sidebar-resizer",
    },
    {
        "name": "writer",
        "url": "/writer/",
        "sidebar": ".writer-sidebar",
        "resizer": "#sidebar-resizer",
    },
]


def highlight_element(page: Page, selector: str, duration_ms: int = 1000):
    """Highlight an element with red border for visual debugging."""
    page.evaluate(
        """
    ([selector, duration]) => {
        const element = document.querySelector(selector);
        if (!element) return;
        const rect = element.getBoundingClientRect();
        const overlay = document.createElement('div');
        overlay.id = 'highlight-overlay-' + Date.now();
        overlay.style.cssText = `
            position: fixed; top: ${rect.top}px; left: ${rect.left}px;
            width: ${rect.width}px; height: ${rect.height}px;
            border: 4px solid #FF4444; background-color: rgba(255, 68, 68, 0.2);
            pointer-events: none; z-index: 999999;
            box-shadow: 0 0 15px #FF4444; animation: pulse 0.5s ease-in-out;
        `;
        if (!document.getElementById('highlight-animation-style')) {
            const style = document.createElement('style');
            style.id = 'highlight-animation-style';
            style.textContent = `@keyframes pulse { 0%,100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.02); opacity: 0.8; } }`;
            document.head.appendChild(style);
        }
        document.body.appendChild(overlay);
        setTimeout(() => { if (overlay.parentNode) overlay.parentNode.removeChild(overlay); }, duration);
    }
    """,
        [selector, duration_ms],
    )


def login_and_navigate(page: Page, base_url: str, credentials: dict, app: dict) -> bool:
    """Login and navigate to a workspace app. Returns True if resizer found."""
    inject_visual_effects(page)
    setup_console_interceptor(page)
    show_step(page, 1, 3, f"Logging in as {credentials['username']}...", "info")

    page.goto(f"{base_url}/auth/signin/", wait_until="load")
    page.wait_for_timeout(1000)

    is_authenticated = page.evaluate(
        "() => document.body.getAttribute('data-user-authenticated') === 'true'"
    )

    if is_authenticated:
        show_step(page, 1, 3, "Already logged in", "success")
    else:
        page.wait_for_selector("form#login-form", timeout=5000)
        page.fill("input#username", credentials["username"])
        page.wait_for_timeout(200)
        page.fill("input#password", credentials["password"])
        page.wait_for_timeout(200)
        page.click("button.btn-primary.w-100")
        page.wait_for_load_state("load")
        page.wait_for_timeout(2000)

        is_authenticated = page.evaluate(
            "() => document.body.getAttribute('data-user-authenticated') === 'true'"
        )
        if is_authenticated:
            show_step(page, 1, 3, "Login successful", "success")
        else:
            show_step(page, 1, 3, "Login failed", "error")
            show_test_result(page, False, "Login failed", delay_ms=3000)
            return False

    url = app["url"].format(username=credentials["username"])
    # Navigate FIRST, then show step (avoid context destruction)
    page.goto(f"{base_url}{url}", wait_until="load")
    page.wait_for_timeout(2000)

    inject_visual_effects(page)
    setup_console_interceptor(page)
    show_step(page, 2, 3, f"Navigated to {app['name']}", "success")

    resizer = page.locator(app["resizer"])
    if resizer.count() > 0:
        show_step(page, 3, 3, f"Panel resizer found in {app['name']}", "success")
        return True
    show_step(page, 3, 3, f"No panel resizer in {app['name']}", "warning")
    return False


def visual_click(page: Page, selector: str):
    """Click with visual feedback."""
    inject_visual_effects(page)
    element = page.locator(selector)
    box = element.bounding_box()
    if box:
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        show_cursor_at(page, x, y, "normal")
        page.wait_for_timeout(100)
        show_click_effect(page, x, y)
        page.wait_for_timeout(100)
    element.click()


def visual_drag(
    page: Page,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    steps: int = 10,
):
    """Drag with visual cursor feedback."""
    inject_visual_effects(page)
    show_cursor_at(page, start_x, start_y, "normal")
    page.wait_for_timeout(100)
    page.mouse.move(start_x, start_y)
    show_click_effect(page, start_x, start_y)
    page.mouse.down()
    show_cursor_at(page, start_x, start_y, "dragging")

    for i in range(1, steps + 1):
        progress = i / steps
        x = start_x + (end_x - start_x) * progress
        y = start_y + (end_y - start_y) * progress
        show_cursor_at(page, x, y, "dragging")
        page.mouse.move(x, y)
        page.wait_for_timeout(30)

    page.mouse.up()
    show_cursor_at(page, end_x, end_y, "normal")


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def cleanup_zombie_browsers():
    """Kill any zombie browsers from previous test runs at session start."""
    SyncBrowserSession.kill_zombie_browsers()
    yield
    # Also cleanup at session end
    SyncBrowserSession.kill_zombie_browsers()


@pytest.fixture
def browser_session(page: Page):
    """Browser session with automatic cleanup on failure."""
    with SyncBrowserSession(page) as session:
        yield session


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def test_credentials():
    return {"username": TEST_USER_USERNAME, "password": TEST_USER_PASSWORD}


@pytest.fixture
def scholar_app():
    return WORKSPACE_APPS[0]


@pytest.fixture
def console_app():
    return WORKSPACE_APPS[1]


@pytest.fixture
def vis_app():
    return WORKSPACE_APPS[2]


@pytest.fixture
def writer_app():
    return WORKSPACE_APPS[3]


@pytest.fixture(params=WORKSPACE_APPS, ids=[app["name"] for app in WORKSPACE_APPS])
def workspace_app(request):
    """Parameterized fixture that runs tests for all 4 workspace apps."""
    return request.param


@pytest.fixture(autouse=True)
def capture_on_failure(request, page: Page):
    """Auto-capture console logs and screenshot on test failure."""
    setup_console_interceptor(page)
    yield
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        console_logs = collect_console_logs(page)
        save_failure_artifacts(page, request.node.nodeid, ARTIFACTS_DIR, console_logs)


@pytest.fixture
def test_monitor(request):
    """Periodic screenshot capture during test execution.

    Usage:
        def test_something(page, test_monitor):
            # Screenshots taken every 2 seconds during test
            pass

    After test: check ~/.scitex/test_monitor/{session_id}/ for screenshots
    """
    monitor = TestMonitor(
        output_dir=ARTIFACTS_DIR / "monitor",
        interval=2.0,
        quality=70,
        verbose=True,
        test_name=request.node.nodeid,
    )
    monitor.start()
    yield monitor
    monitor.stop()
    # Create GIF from captured screenshots
    gif_path = monitor.create_gif()
    if gif_path:
        print(f"[TestMonitor] GIF: {gif_path}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to capture test outcome."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
