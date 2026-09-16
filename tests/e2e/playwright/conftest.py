#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright E2E Test Configuration

Provides:
- iPhone 14 mobile fixture (390x844, has_touch=True)
- Desktop fixture (1920x1080)
- Authenticated session with storage_state save/reuse
- Screenshot directory setup
"""

import os
from pathlib import Path

import pytest

# =============================================================================
# Configuration
# =============================================================================

BASE_URL = os.getenv("SCITEX_BASE_URL", "http://127.0.0.1:8000")
TEST_USER = os.getenv("SCITEX_E2E_TEST_USER", "test-user")
# No literal default — see tests/develop/test_no_usable_credential_defaults.py.
TEST_PASS = os.getenv("SCITEX_E2E_TEST_PASS", "")
TIMEOUT = int(os.getenv("SCITEX_E2E_TIMEOUT", "30")) * 1000  # ms for Playwright

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SCREENSHOT_DIR = PROJECT_ROOT / "GITIGNORED" / "e2e_screenshots"
STORAGE_STATE_DIR = PROJECT_ROOT / "GITIGNORED" / "e2e_storage_states"

# iPhone 14 device descriptor
IPHONE_14 = {
    "viewport": {"width": 390, "height": 844},
    "user_agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/16.0 Mobile/15E148 Safari/604.1"
    ),
    "device_scale_factor": 3,
    "is_mobile": True,
    "has_touch": True,
}

DESKTOP = {
    "viewport": {"width": 1920, "height": 1080},
    "user_agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "device_scale_factor": 1,
    "is_mobile": False,
    "has_touch": False,
}


# =============================================================================
# Directory setup
# =============================================================================


@pytest.fixture(scope="session", autouse=True)
def setup_directories():
    """Create output directories for screenshots and storage states."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_STATE_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Base URL
# =============================================================================


@pytest.fixture(scope="session")
def pw_base_url():
    """Base URL for the running server."""
    return BASE_URL.rstrip("/")


# =============================================================================
# Browser contexts
# =============================================================================


@pytest.fixture
def mobile_context(browser, pw_base_url):
    """
    iPhone 14 browser context.

    Viewport: 390x844, has_touch=True, iOS Safari user agent.
    """
    context = browser.new_context(
        base_url=pw_base_url,
        viewport=IPHONE_14["viewport"],
        user_agent=IPHONE_14["user_agent"],
        device_scale_factor=IPHONE_14["device_scale_factor"],
        is_mobile=IPHONE_14["is_mobile"],
        has_touch=IPHONE_14["has_touch"],
        ignore_https_errors=True,
    )
    context.set_default_timeout(TIMEOUT)
    yield context
    context.close()


@pytest.fixture
def mobile_page(mobile_context):
    """A page within the iPhone 14 browser context."""
    page = mobile_context.new_page()
    yield page
    page.close()


@pytest.fixture
def desktop_context(browser, pw_base_url):
    """
    Desktop browser context.

    Viewport: 1920x1080, standard Chrome user agent.
    """
    context = browser.new_context(
        base_url=pw_base_url,
        viewport=DESKTOP["viewport"],
        user_agent=DESKTOP["user_agent"],
        device_scale_factor=DESKTOP["device_scale_factor"],
        is_mobile=DESKTOP["is_mobile"],
        has_touch=DESKTOP["has_touch"],
        ignore_https_errors=True,
    )
    context.set_default_timeout(TIMEOUT)
    yield context
    context.close()


@pytest.fixture
def desktop_page(desktop_context):
    """A page within the desktop browser context."""
    page = desktop_context.new_page()
    yield page
    page.close()


# =============================================================================
# Authenticated session with storage_state reuse
# =============================================================================



#: Selectors Django/Bootstrap use to render form errors, most specific first.
#: Read as a LIST rather than one selector so the message can say WHICH kind of
#: error was found -- "errorlist" and "alert" mean different things.
_LOGIN_ERROR_SELECTORS = (
    ".errorlist",
    ".invalid-feedback",
    ".alert-danger",
    ".alert",
    "[role='alert']",
)


def _login_page_diagnosis(page) -> str:
    """Say WHAT THE PAGE SAID when a login fails to navigate.

    WHY THIS EXISTS. The bare assertion this feeds reports that the login did
    not complete and the URL it is stuck on. Measured 2026-09-06, job
    101461416410: that was enough to make the failure loud and NOT enough to
    say why, leaving three candidates open (credentials rejected / CSRF
    re-render / the submit control never firing) and needing a human to go and
    look. Django re-renders the login page at the SAME URL on a failed login,
    so the URL cannot discriminate between them; the rendered error text can.

    This is scholar's rule -- a skip must name what it looked for and where --
    applied to an assertion instead of a skip.

    READS innerText, NOT textContent: textContent returns text inside
    display:none nodes, and Django's error containers are frequently present
    and empty until a POST fails. innerText reports what a person would see.

    NEVER RAISES. It runs inside an `except` block, so a failure here would
    replace a diagnosable error with an incomprehensible one. Every branch
    degrades to a sentence saying what could not be read.
    """
    parts = []
    for sel in _LOGIN_ERROR_SELECTORS:
        try:
            texts = page.eval_on_selector_all(
                sel,
                "els => els.map(e => (e.innerText || '').trim()).filter(Boolean)",
            )
        except Exception:  # noqa: BLE001 -- diagnosis must not mask the real error
            continue
        if texts:
            parts.append(f"  {sel}: {texts!r}")
    if parts:
        return "THE PAGE SAID:\n" + "\n".join(parts)

    # No recognised error container carried text. That is itself informative --
    # it argues AGAINST "credentials rejected" (which renders an errorlist) and
    # FOR the form never having been submitted at all.
    try:
        body = page.evaluate("() => (document.body.innerText || '').trim()")
    except Exception:  # noqa: BLE001
        return "THE PAGE SAID: <could not read the page at all>"
    return (
        "NO error container carried visible text, which argues against "
        "'credentials rejected' and toward 'the form was never submitted'. "
        f"First 300 chars of what is on screen: {body[:300]!r}"
    )


#: Version the storage-state filename. Bump to invalidate any previously saved
#: state (e.g. a stale anonymous one) on the first run after a fixture change.
_STORAGE_STATE_VERSION = 2


def _form_login(page) -> None:
    """Perform the scoped login-form submission on ``page``.

    Shared by the session-scoped storage-state login and the mobile context's
    direct authentication, so the selectors and the post-submit navigation
    wait live in ONE place. Caller has already navigated ``page`` to
    /auth/login/. After a successful login the browser leaves /auth/login
    (the view redirects to "/" or ?next= -- the login FORM itself carries no
    next field, so by default it lands at "/").

    The submit selector is SCOPED TO #login-form ON PURPOSE: button[type="submit"]
    is NOT unique on the page (the language switcher submits first in DOM order).
    See the measured history in the fixture docstrings below -- do not "fix"
    this to a positional selector.
    """
    page.wait_for_load_state("domcontentloaded")
    # body.app-ready disables the loading screen's pointer-events; the
    # global_base.html safety-net guarantees it within 3s even if the Vite
    # bundle fails to load.
    page.wait_for_function(
        "document.body.classList.contains('app-ready')", timeout=15000
    )
    page.fill('#login-form input[name="username"]', TEST_USER)
    page.fill('#login-form input[name="password"]', TEST_PASS)
    page.click('#login-form button[type="submit"]')
    # WAIT FOR THE NAVIGATION away from the login page: click() starts the POST,
    # but a load state can be satisfied by the document ALREADY on screen (the
    # login page) and return before the response lands. Without this, the caller
    # could proceed (and save a storage state) while still on /auth/login/ --
    # i.e. with no session at all. A rejected login re-renders /auth/login
    # (same URL), so "left /auth/login" is the login-succeeded signal.
    try:
        page.wait_for_url(lambda url: "/auth/login" not in url, timeout=TIMEOUT)
    except Exception as exc:  # noqa: BLE001 -- re-raised with a usable message
        raise AssertionError(
            "login did not navigate away from /auth/login/ within "
            f"{TIMEOUT}ms (still at {page.url!r}). Either the credentials were "
            "rejected, or CSRF re-rendered the login page. Check "
            f"SCITEX_E2E_TEST_USER / _TEST_PASS.\n"
            f"{_login_page_diagnosis(page)}\n({exc})"
        ) from exc


@pytest.fixture(scope="session")
def authenticated_storage_state(browser_type, pw_base_url):
    """Authenticate the synthetic test user and save reusable browser state.

    Existing state is reused only when the rendered shell still proves
    ``data-session-role='user'``; otherwise the fixture logs in again.
    """
    state_file = STORAGE_STATE_DIR / (
        f"test_user_state.v{_STORAGE_STATE_VERSION}.json"
    )
    from tests.e2e.playwright.page_ready import wait_for_page_ready
    from tests.e2e.playwright.session_role_check import (
        AUTHENTICATED_WARMUP_ROUTE,
        READ_SESSION_ROLE_JS,
        is_authenticated_user_role,
    )

    def _role_of(state_path):
        """Return the session role a saved state yields at a warm-up route."""
        context = browser_type.launch().new_context(
            base_url=pw_base_url,
            storage_state=str(state_path),
            ignore_https_errors=True,
        )
        page = context.new_page()
        page.goto(AUTHENTICATED_WARMUP_ROUTE)
        wait_for_page_ready(page)
        role = page.evaluate(READ_SESSION_ROLE_JS)
        page.close()
        context.close()
        context.browser.close()
        return role

    # Reuse an existing state ONLY if it is still a registered-user session.
    if state_file.exists() and is_authenticated_user_role(_role_of(state_file)):
        return str(state_file)

    # Fresh login as the explicit test user.
    browser = browser_type.launch()
    context = browser.new_context(
        base_url=pw_base_url,
        ignore_https_errors=True,
    )
    context.set_default_timeout(TIMEOUT)
    page = context.new_page()

    page.goto("/auth/login/")
    _form_login(page)
    wait_for_page_ready(page)

    # PROVE THE SESSION IS A REGISTERED USER BEFORE SAVING IT. The login lands
    # at "/" (the form carries no next field), so validate there -- a
    # skip-listed, non-pooling route, so an authenticated user reports "user"
    # and a stale state reports "anonymous".
    role = page.evaluate(READ_SESSION_ROLE_JS)
    if not is_authenticated_user_role(role):
        raise AssertionError(
            f"logged in as {TEST_USER!r} but the page reports session role "
            f"{role!r} at {page.url!r}. REFUSING to save a non-user storage "
            "state: every test using it would run against the wrong session "
            "(a logged-out page still returns 200)."
        )

    # Save storage state
    context.storage_state(path=str(state_file))

    page.close()
    context.close()
    browser.close()

    return str(state_file)


@pytest.fixture
def authenticated_mobile_context(browser, pw_base_url):
    """
    iPhone 14 context. It does NOT load the desktop storage_state: the mobile
    profile authenticates DIRECTLY (see authenticated_mobile_page). A session created
    in a different browser profile (desktop UA, non-mobile) does not reliably
    carry into a mobile (is_mobile/has_touch/390x844) profile, and relying on
    that transfer was the defect -- the desktop->mobile handoff lost the
    sessionid, so tests navigated /chat/ logged out.
    """
    context = browser.new_context(
        base_url=pw_base_url,
        viewport=IPHONE_14["viewport"],
        user_agent=IPHONE_14["user_agent"],
        device_scale_factor=IPHONE_14["device_scale_factor"],
        is_mobile=IPHONE_14["is_mobile"],
        has_touch=IPHONE_14["has_touch"],
        ignore_https_errors=True,
    )
    context.set_default_timeout(TIMEOUT)
    yield context
    context.close()


@pytest.fixture
def authenticated_mobile_page(authenticated_mobile_context):
    """Log in inside the mobile profile and prove the registered-user role.

    A desktop storage state does not reliably transfer to an iPhone-profile
    context. This fixture authenticates directly, then validates the exact
    route the mobile workspace tests use before yielding the page.
    """
    from tests.e2e.playwright.page_ready import wait_for_page_ready
    from tests.e2e.playwright.session_role_check import (
        READ_SESSION_ROLE_JS,
        authenticated_user_role_failure,
        is_authenticated_user_role,
    )

    page = authenticated_mobile_context.new_page()

    def _snap(label):
        """Authoritative cookie/role evidence for the mobile session.

        Captures the cookie jar, the sessionid specifically, page.url and the
        rendered session role. The curl probe already proved the server holds
        a session across /apps/my-projects/ -> /chat/ -> / for a logged-in user, so
        these snapshots localize WHERE the mobile profile is logged out.
        """
        cookies = page.context.cookies()
        sess = next((c for c in cookies if c["name"] == "sessionid"), None)
        role = page.evaluate(READ_SESSION_ROLE_JS)
        print(
            f"[mobile-auth-diag] {label}: url={page.url} "
            f"cookies={[c['name'] for c in cookies]} "
            f"sessionid={'PRESENT' if sess else 'ABSENT'} "
            f"(domain={sess['domain'] if sess else '-'} "
            f"path={sess['path'] if sess else '-'} "
            f"secure={sess['secure'] if sess else '-'}) "
            f"role={role!r}"
        )
        return role

    # The mobile profile does NOT load the desktop storage_state (see
    # authenticated_mobile_context); it authenticates DIRECTLY. Login lands at "/"
    # (the form carries no next field); the session cookie is then in THIS
    # context's jar. We navigate to /chat/ -- the exact route the workspace
    # tests use -- and PROVE role=user there before yielding. If the session
    # does not hold at /chat/, we fail loudly here rather than hand every
    # test a logged-out page that still returns 200.
    _snap("A0 fresh mobile context (pre-login)")
    page.goto("/auth/login/")
    wait_for_page_ready(page)
    _form_login(page)
    wait_for_page_ready(page)
    _snap("B1 after direct login (at /)")
    # Navigate to the route under test and validate the session THERE.
    page.goto("/chat/")
    wait_for_page_ready(page)
    role = _snap("B2 at /chat/ (session must hold)")

    if not is_authenticated_user_role(role):
        raise AssertionError(
            f"the MOBILE context has session role {role!r} at {page.url!r} "
            "after a direct in-context login, so every test using this "
            "fixture would run against the wrong session. "
            f"{authenticated_user_role_failure(role, 'the MOBILE context')} "
            "[cookie/role snapshots printed above as [mobile-auth-diag]]"
        )

    # The session is now established IN THIS MOBILE CONTEXT and validated at
    # /chat/. Each test navigates to its own route; the session cookie is in
    # this context's jar and is sent on every subsequent request.
    yield page
    page.close()


@pytest.fixture
def authenticated_desktop_context(browser, pw_base_url, authenticated_storage_state):
    """
    Desktop context with authenticated session pre-loaded.
    """
    context = browser.new_context(
        base_url=pw_base_url,
        storage_state=authenticated_storage_state,
        viewport=DESKTOP["viewport"],
        user_agent=DESKTOP["user_agent"],
        device_scale_factor=DESKTOP["device_scale_factor"],
        is_mobile=DESKTOP["is_mobile"],
        has_touch=DESKTOP["has_touch"],
        ignore_https_errors=True,
    )
    context.set_default_timeout(TIMEOUT)
    yield context
    context.close()


@pytest.fixture
def authenticated_desktop_page(authenticated_desktop_context):
    """A desktop page with authenticated session."""
    page = authenticated_desktop_context.new_page()
    yield page
    page.close()


# =============================================================================
# Synthetic registered screenshot account
# =============================================================================


@pytest.fixture(scope="session")
def screenshot_test_context(browser, pw_base_url, authenticated_storage_state):
    """Desktop context authenticated as the empty synthetic E2E account.

    Screenshot artifacts must never contain an operator or customer account.
    The workflow creates/resets ``SCITEX_E2E_TEST_USER`` and this fixture uses
    the already-validated registered-user storage state.
    """
    context = browser.new_context(
        base_url=pw_base_url,
        storage_state=authenticated_storage_state,
        service_workers="block",
        viewport=DESKTOP["viewport"],
        user_agent=DESKTOP["user_agent"],
        device_scale_factor=DESKTOP["device_scale_factor"],
        is_mobile=DESKTOP["is_mobile"],
        has_touch=DESKTOP["has_touch"],
        ignore_https_errors=True,
    )
    context.set_default_timeout(TIMEOUT)
    yield context
    context.close()


@pytest.fixture(scope="session")
def screenshot_test_page(screenshot_test_context):
    """Shared screenshot page proven to use the registered E2E account."""
    from tests.e2e.playwright.page_ready import wait_for_page_ready
    from tests.e2e.playwright.session_role_check import (
        AUTHENTICATED_WARMUP_ROUTE,
        READ_SESSION_ROLE_JS,
        ROLE_USER,
        authenticated_user_role_failure,
    )

    page = screenshot_test_context.new_page()
    page.goto(AUTHENTICATED_WARMUP_ROUTE)
    wait_for_page_ready(page)
    role = page.evaluate(READ_SESSION_ROLE_JS)
    if role != ROLE_USER:
        raise AssertionError(
            authenticated_user_role_failure(role, "the screenshot E2E context")
        )
    yield page
    page.close()


# =============================================================================
# Screenshot helper
# =============================================================================


@pytest.fixture(scope="session")
def content_report():
    """Append per-page content findings NEXT TO the PNGs, in the artifact.

    Every page the capture measures gets a found/not-found block here,
    whether it passed or not. Two reasons it is a file and not just a
    print:

      * pytest captures stdout on a PASSING test, so a report that only
        printed would be invisible on exactly the runs it is meant to
        describe — the green ones. Run 32039805008 was green while
        photographing a blank FigRecipe; the whole point is that a green
        run must still say what it saw.
      * The artifact is the deliverable. Whoever downloads the PNGs for a
        talk or a grant gets, in the same zip, the measurement each image
        was passed on — so "is this screenshot showing the real product?"
        is answerable without re-running anything.

    The workflow prints it after the capture step, so it is in the run log
    too. Text is also printed, which surfaces it in pytest's output for a
    FAILING test alongside the assertion that failed.
    """
    from tests.e2e.playwright.content_check import threshold_banner

    path = SCREENSHOT_DIR / "content-report.txt"
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "Content measured per captured page. FOUND / NOT FOUND is stated\n"
        "for every signal, so a page with no content says so rather than\n"
        "being silently skipped.\n"
        "\n"
        "Thresholds in force for THIS run — a tunable bar has to be stated\n"
        "or 'the job was green' means nothing:\n"
        "  %s\n\n" % threshold_banner(),
        encoding="utf-8",
    )

    def _append(text):
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text + "\n\n")
        print(text)

    return _append


@pytest.fixture
def screenshot(request):
    """
    Screenshot helper that saves to GITIGNORED/e2e_screenshots/.

    Usage:
        def test_example(mobile_page, screenshot):
            mobile_page.goto("/")
            screenshot(mobile_page, "landing_loaded")
    """

    def _screenshot(page, name):
        filename = f"{request.node.name}_{name}.png"
        path = SCREENSHOT_DIR / filename
        page.screenshot(path=str(path), full_page=True)
        return path

    return _screenshot
