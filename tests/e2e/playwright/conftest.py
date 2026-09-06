#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright E2E Test Configuration

Provides:
- iPhone 14 mobile fixture (390x844, has_touch=True)
- Desktop fixture (1920x1080)
- Visitor session with storage_state save/reuse
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
# Visitor session with storage_state reuse
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


@pytest.fixture(scope="session")
def visitor_storage_state(browser_type, pw_base_url):
    """
    Authenticate as visitor and save storage_state for reuse.

    The storage state is saved to disk so subsequent test runs
    can skip the login step if the session is still valid.
    """
    state_file = STORAGE_STATE_DIR / "visitor_state.json"

    # Try to reuse existing state
    if state_file.exists():
        context = browser_type.launch().new_context(
            base_url=pw_base_url,
            storage_state=str(state_file),
            ignore_https_errors=True,
        )
        page = context.new_page()
        # Verify the session is still valid
        page.goto("/")
        if "login" not in page.url.lower():
            # Session is still valid
            browser = context.browser
            page.close()
            context.close()
            browser.close()
            return str(state_file)
        page.close()
        context.close()
        context.browser.close()

    # Create fresh session by logging in
    from tests.e2e.playwright.page_ready import wait_for_page_ready

    browser = browser_type.launch()
    context = browser.new_context(
        base_url=pw_base_url,
        ignore_https_errors=True,
    )
    context.set_default_timeout(TIMEOUT)
    page = context.new_page()

    page.goto("/auth/login/")
    page.wait_for_load_state("domcontentloaded")
    # Wait for body.app-ready which disables loading screen pointer-events.
    # The safety-net script in global_base.html guarantees this within 3s
    # even if the Vite bundle fails to load.
    page.wait_for_function(
        "document.body.classList.contains('app-ready')", timeout=15000
    )
    page.fill('input[name="username"]', TEST_USER)
    page.fill('input[name="password"]', TEST_PASS)
    page.click('button[type="submit"]')
    # NOT networkidle. THIS LINE IS WHY 14/14 MOBILE TESTS ERRORED AT SETUP.
    #
    # Measured 2026-09-06, job 101449817274:
    #     E  playwright._impl._errors.TimeoutError: Timeout 30000ms exceeded.
    #     E  "domcontentloaded" event fired
    #     E  "load" event fired
    # Both real load events fired. Only networkidle never came -- because the
    # session this fixture has just created is a POOLED VISITOR, and a pooled
    # visitor polls a heartbeat for as long as the page is open
    # (PoolAllocator.extend_session_on_activity). "500 ms with no requests in
    # flight" is a state it can never reach, so this wait could only ever time
    # out, and every test depending on this fixture died before its first
    # assertion.
    #
    # tests/e2e/playwright/page_ready.py was written for exactly this after the
    # same exception took the screenshot capture down with 33 errors (CI run
    # 31955719803, 2026-08-16). Its docstring even notes that this fixture
    # already waits on body.app-ready for the login page -- which it does,
    # eleven lines above. The helper was adopted by pooled_visitor_page in this
    # same file and not here, and that gap is the whole defect.
    # WAIT FOR THE NAVIGATION, NOT JUST FOR A LOAD STATE. `click()` starts the
    # POST, but wait_for_load_state("load") can be satisfied by the document
    # ALREADY on screen -- the login page -- and return before the response
    # lands. Without this line the storage state below can be captured while
    # still on /auth/login/, i.e. with no session at all.
    try:
        page.wait_for_url(lambda url: "/auth/login" not in url, timeout=TIMEOUT)
    except Exception as exc:  # noqa: BLE001 -- re-raised with a usable message
        raise AssertionError(
            "login did not navigate away from /auth/login/ within "
            f"{TIMEOUT}ms (still at {page.url!r}). Every test using this "
            "fixture would otherwise run against a LOGGED-OUT site and still "
            f"report 200. Check SCITEX_E2E_TEST_USER / _TEST_PASS.\n"
            f"{_login_page_diagnosis(page)}\n({exc})"
        ) from exc

    wait_for_page_ready(page)

    # PROVE THE SESSION EXISTS BEFORE SAVING IT.
    #
    # MEASURED 2026-09-06, job 101458943232 -- the run that first executed this
    # suite at all. Without this assertion the fixture completed happily and
    # handed every test an ANONYMOUS session:
    #     /apps/workspace/  rendered the public landing page ("Sign in")
    #     /apps/store/      rendered with "Login to install" on every card
    #     /apps/scholar/    rendered a shell stuck on "Loading..."
    # and the suite reported 8 PASSED, because those tests assert
    # `resp.status == 200` and a logged-out page returns 200. Five more
    # SKIPPED with "No workspace pane element found on page" -- which is what
    # a logged-out page looks like to a selector.
    #
    # That is worse than the crash this fixture used to produce: a loud error
    # tells you nothing works; eight vacuous passes tell you everything does.
    # #742 removed a job that was green over zero tests; this stops the same
    # job going green over zero SESSIONS, which MIN_EXECUTED cannot detect
    # because the tests genuinely do run.
    #
    # The role vocabulary is the product's own (body[data-session-role], see
    # session_role_check.py). This fixture logs in as a REGISTERED ACCOUNT, so
    # the expected role here is "user" -- deliberately NOT the pooled "visitor"
    # that the screenshot capture requires, which is why this asserts the
    # absence of a logged-out state rather than reusing assert_pooled_visitor.
    from tests.e2e.playwright.session_role_check import (
        READ_SESSION_ROLE_JS,
        ROLE_ANONYMOUS,
    )

    role = page.evaluate(READ_SESSION_ROLE_JS)
    if role in (ROLE_ANONYMOUS, ""):
        raise AssertionError(
            f"logged in as {TEST_USER!r} but the page reports session role "
            f"{role!r} at {page.url!r}. "
            + (
                "An empty role means the page carries no data-session-role "
                "attribute, so it does not extend global_base and cannot be "
                "vouched for at all."
                if role == ""
                else "An anonymous role means the credentials were rejected "
                "or the session cookie was not set."
            )
            + " REFUSING to save a session-less storage state: every test "
            "using it would run against a logged-out site and still pass."
        )

    # Save storage state
    context.storage_state(path=str(state_file))

    page.close()
    context.close()
    browser.close()

    return str(state_file)


@pytest.fixture
def visitor_mobile_context(browser, pw_base_url, visitor_storage_state):
    """
    iPhone 14 context with visitor session pre-loaded.
    """
    context = browser.new_context(
        base_url=pw_base_url,
        storage_state=visitor_storage_state,
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
def visitor_mobile_page(visitor_mobile_context):
    """A mobile page with visitor session."""
    page = visitor_mobile_context.new_page()
    yield page
    page.close()


@pytest.fixture
def visitor_desktop_context(browser, pw_base_url, visitor_storage_state):
    """
    Desktop context with visitor session pre-loaded.
    """
    context = browser.new_context(
        base_url=pw_base_url,
        storage_state=visitor_storage_state,
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
def visitor_desktop_page(visitor_desktop_context):
    """A desktop page with visitor session."""
    page = visitor_desktop_context.new_page()
    yield page
    page.close()


# =============================================================================
# REAL pooled-visitor session (no login at all)
# =============================================================================
#
# The ``visitor_*`` fixtures above are misnamed: they FORM-LOG-IN as
# ``$SCITEX_E2E_TEST_USER`` (default ``test-user``), i.e. a registered
# account, and they assert nothing about the result — ``storage_state`` is
# saved whether the login worked or not. They are kept as-is because the
# mobile suites depend on them.
#
# A real pooled visitor is obtained by NOT logging in: SciTeX assigns one
# through ``VisitorAutoLoginMiddleware`` on the first workspace request from
# a browser user-agent. That middleware deliberately does NOT allocate on
# ``/``, ``/landing/``, ``/apps/tools/`` or ``/auth/*`` — a first-time
# reader must reach the marketing pages anonymously — so the session must
# be established on a workspace route FIRST. Everything after that renders
# as the visitor, including those four paths.


@pytest.fixture(scope="session")
def pooled_visitor_context(browser, pw_base_url):
    """ONE desktop context, no stored state, holding ONE pooled slot.

    Session-scoped ON PURPOSE. A function-scoped context would start a new
    anonymous session per test and burn a separate pool slot for each; with
    a pool of 4 and 22 capture tests the pool would exhaust mid-run and the
    remainder would be served the readonly-visitor fallback — a real
    failure caused entirely by the test's own shape. One context = one
    slot = one continuous visitor session, which is also what the
    screenshots should depict.
    """
    context = browser.new_context(
        base_url=pw_base_url,
        viewport=DESKTOP["viewport"],
        # A browser UA is load-bearing, not cosmetic:
        # VisitorAutoLoginMiddleware skips non-browser user agents (curl,
        # bots, health checks) and would leave the session anonymous.
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
def pooled_visitor_page(pooled_visitor_context):
    """A page whose session IS a writable pooled visitor slot.

    Fails the whole capture at setup — before a single PNG is written — if
    the warm-up did not yield ``body[data-session-role] == "visitor"``. The
    alternative (start shooting and check later) writes an artifact full of
    the wrong product first, and the artifact is the deliverable.
    """
    from tests.e2e.playwright.page_ready import wait_for_page_ready
    from tests.e2e.playwright.session_role_check import (
        READ_SESSION_ROLE_JS,
        VISITOR_WARMUP_ROUTE,
        assert_pooled_visitor,
    )

    page = pooled_visitor_context.new_page()
    page.goto(VISITOR_WARMUP_ROUTE)
    wait_for_page_ready(page)
    role = page.evaluate(READ_SESSION_ROLE_JS)
    assert_pooled_visitor(role, f"visitor warm-up ({VISITOR_WARMUP_ROUTE})")
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
