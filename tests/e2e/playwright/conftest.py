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
def visitor_storage_state(browser_type, pw_base_url):
    """
    Authenticate as the EXPLICIT test user and save storage_state for reuse.

    Historically misnamed "visitor": this logs in as ``$SCITEX_E2E_TEST_USER``,
    a REGISTERED account -- not a pooled visitor. The saved state is reused only
    if it still yields session role ``"user"`` at a warm-up route; otherwise a
    fresh login is performed. Requiring the EXACT role (not merely "not
    anonymous") is what stops a stale/anonymous state from silently running the
    whole suite logged out, since a logged-out page still returns 200.
    """
    state_file = STORAGE_STATE_DIR / (
        f"test_user_state.v{_STORAGE_STATE_VERSION}.json"
    )
    from tests.e2e.playwright.page_ready import wait_for_page_ready
    from tests.e2e.playwright.session_role_check import (
        READ_SESSION_ROLE_JS,
        VISITOR_WARMUP_ROUTE,
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
        page.goto(VISITOR_WARMUP_ROUTE)
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
            "(a logged-out / readonly / pooled page still returns 200)."
        )

    # Save storage state
    context.storage_state(path=str(state_file))

    page.close()
    context.close()
    browser.close()

    return str(state_file)


@pytest.fixture
def visitor_mobile_context(browser, pw_base_url):
    """
    iPhone 14 context. It does NOT load the desktop storage_state: the mobile
    profile authenticates DIRECTLY (see visitor_mobile_page). A session created
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
def visitor_mobile_page(visitor_mobile_context):
    """A mobile page with visitor session -- and PROOF that it has one.

    WHY THIS WARMS UP AND ASSERTS INSTEAD OF JUST HANDING OVER A PAGE.

    visitor_storage_state already proves a session exists in the LOGIN context.
    It then writes that state to a file and hands the FILE here, where a
    DIFFERENT context is built (iPhone 14 viewport, mobile UA, has_touch).
    Nothing proved the session survives that handoff -- and measured
    2026-09-06, job 101474196873 on develop 7ebd24388, IT DOES NOT:

        the login-time assertion did NOT fire (so the session was real there)
        and the screenshots from the same run show
            /apps/workspace/  -> the logged-out landing page
            /apps/store/      -> "Login to install" on every card

    The suite reported "1 failed, 8 passed". Those 8 assert
    `resp.status == 200`, and a logged-out page returns 200 -- so they passed
    while measuring nothing, exactly as they did before #745. A precondition
    proven in one context is not proven in another, and the only place worth
    proving it is WHERE THE ASSERTIONS RUN.

    This mirrors pooled_visitor_page, which has warmed up and asserted its role
    since it was written. That helper was sitting one fixture away the whole
    time; this is its adoption, not a new idea.

    ROLE EXPECTED HERE IS "user", NOT "visitor". This chain authenticates as a
    REGISTERED ACCOUNT (the explicit test user), so assert_pooled_visitor would
    be the wrong assertion -- it demands a pooled slot this fixture never asks
    for.

    The mobile context is made EXPLICITLY authenticated: if the stored session
    did not carry into this context (mobile UA / is_mobile / has_touch / 390x844
    profile), the fixture logs the test user in IN-CONTEXT and re-proves
    role == "user" before yielding. Only if it still is not a user does it
    raise. This is the migration off the Visitor-session handoff, consistent
    with the removal of Visitor/read-only sessions: the authenticated test user
    is the source of truth, and a logged-out page (which still returns 200) can
    never be vouched for.
    """
    from tests.e2e.playwright.page_ready import wait_for_page_ready
    from tests.e2e.playwright.session_role_check import (
        READ_SESSION_ROLE_JS,
        authenticated_user_role_failure,
        is_authenticated_user_role,
    )

    page = visitor_mobile_context.new_page()

    def _snap(label):
        """Authoritative cookie/role evidence for the mobile session.

        Captures the cookie jar, the sessionid specifically, page.url and the
        rendered session role. The curl probe already proved the server holds
        a session across /apps/home/ -> /chat/ -> / for a logged-in user, so
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
    # visitor_mobile_context); it authenticates DIRECTLY. Login lands at "/"
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
# account. They are named "visitor" only for back-compat with the mobile
# suites that consume them. As of the auth-fixture migration they VALIDATE the
# result (require session role "user") on both save-time and the in-context
# handoff, rather than saving whatever state the login produced.
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

    The visitor session is bound EXPLICITLY, not by auto-login. The
    visitor-retirement merge (#764) removed VisitorAutoLoginMiddleware, which
    used to pool an anonymous browser into a writable visitor slot. Instead the
    conftest MINTS the session in-process (apps.infra.project_app...
    .mint_visitor_session_key) — the same Django process, same DB, same
    SCITEX_HUB_REDIS_URL as the server, so the session lands in the store the
    server reads (CI runs Redis; settings_dev falls back to db when it does
    not) — then injects the resulting 40-char key as the sessionid cookie, so
    every page renders as data-session-role='visitor'.

    Why in-process, not a `manage.py mint_visitor_session` step feeding a file/
    env var (run 34730332276 root cause): a management command's stdout also
    carries settings-import-time prints (the Redis-fallback warning), so
    capturing it as the key produced a 150-char value the server could not
    resolve — the warm-up still read 'anonymous'. Minting here keeps the key a
    clean 40-char in-memory string with no cross-process boundary.

    REQUIRED_ROLE stays 'visitor' — the warm-up assertion is unchanged (card
    hub-product-screenshot-visitor-regression-20260913).
    """
    import hashlib

    from django.conf import settings

    from apps.infra.project_app.management.commands.mint_visitor_session import (
        mint_visitor_session_key,
    )

    # Mint + VERIFY the session in-process before the browser sees it: a
    # key that does not round-trip to the visitor here would photograph as
    # anonymous on the server, so fail now with the exact mismatch.
    visitor_key = mint_visitor_session_key()
    import importlib as _il

    from django.contrib.auth.middleware import AuthenticationMiddleware
    from django.test import RequestFactory

    from apps.infra.project_app.services.visitor_pool.session_role import (
        ROLE_VISITOR,
        get_session_role,
    )

    _store = _il.import_module(settings.SESSION_ENGINE).SessionStore(
        session_key=visitor_key
    )
    _store.load()
    _probe = RequestFactory().get("/")
    _probe.session = _store
    AuthenticationMiddleware(lambda r: None).process_request(_probe)
    _probe_role = get_session_role(_probe)
    _key_sha = hashlib.sha256(visitor_key.encode()).hexdigest()[:12]
    if _probe_role != ROLE_VISITOR:
        raise RuntimeError(
            "minted visitor session does not round-trip to role 'visitor' "
            f"(got {_probe_role!r}, engine={settings.SESSION_ENGINE}, "
            f"key len={len(visitor_key)}, sha[:12]={_key_sha}); refusing to "
            "photograph as anonymous"
        )

    context = browser.new_context(
        base_url=pw_base_url,
        service_workers="block",
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
    cookie_name = getattr(settings, "SESSION_COOKIE_NAME", "sessionid")
    context.add_cookies(
        [{"name": cookie_name, "value": visitor_key, "url": pw_base_url}]
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
    if role != "visitor":
        # Non-secret boundary evidence (card hub-product-screenshot-visitor-
        # regression-20260913). The session is now minted IN-PROCESS (no env
        # var / file), so the boundaries to name are: did the browser carry
        # the injected sessionid cookie at the warm-up URL, and what role did
        # the server resolve it to? Cookie value is sha'd, never printed.
        import hashlib

        try:
            cookies = page.context.cookies(pw_base_url)
        except Exception:
            cookies = []
        sess = next(
            (c for c in cookies if c.get("name") == "sessionid"),
            None,
        )
        cookie_sha = (
            hashlib.sha256(sess["value"].encode()).hexdigest()[:12]
            if sess and sess.get("value")
            else "absent"
        )
        print(
            "\n[pooled_visitor] WARM-UP ROLE MISMATCH — boundary evidence:\n"
            f"  base URL              : {pw_base_url}\n"
            f"  warm-up route         : {VISITOR_WARMUP_ROUTE}\n"
            f"  sessionid cookie present in browser: {'yes' if sess else 'NO'} "
            f"(len={len(sess['value']) if sess and sess.get('value') else 0}, "
            f"sha256[:12]={cookie_sha})\n"
            f"  rendered data-session-role: {role!r} (expected 'visitor')\n"
            "  meaning: cookie absent => Playwright did not send it (url/"
            "domain/path scope); cookie present but role anonymous => the "
            "running server's session engine cannot resolve the key (mint and "
            "server used different stores)."
        )
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
