#!/usr/bin/env python3
"""Layout CI — screenshot every workspace app + key pages, mobile + desktop.

Enumerates the app tiles from the launcher home (their real launch URLs), then
captures each in an isolated page at both an iPhone-ish and a desktop viewport.
Saves PNGs to --out and prints a per-URL status line (ok / http code / error)
so broken routes (404) and blank/incomprehensible interiors are caught without
a human opening each one by hand.

Each per-target line also reports the boot-wait outcome for its page kind:
workspace-shell pages get pane=rendered / pane=LOADING-TIMEOUT(..) /
pane=WAIT-ERROR(..), standalone app pages (no #ws-module-pane but a
full-screen #app-loading-screen overlay) get boot=ready / boot=BOOT-TIMEOUT(..)
/ boot=WAIT-ERROR(..); n/a marks the signal a page does not carry. An
end-of-run summary lists any captures that are just a loading spinner.
With --strict the run exits nonzero on any of those, so a sweep of
spinner frames can never masquerade as a green run.

Usage:
    /opt/venv-sac/bin/python scripts/qa/screenshot_all.py \
        --base https://scitex.ai --out /tmp/qa_shots [--only writer,scholar]
"""
import argparse, os, subprocess, sys
from playwright.sync_api import TimeoutError as PWTimeoutError, sync_playwright

VIEWPORTS = {"mobile": (390, 844, 2), "desktop": (1440, 900, 1)}
PANE_WAIT_MS = 12000
# How long to wait for the app to actually PAINT text after it reports booted.
# Generous on purpose: a slow paint wrongly captured is far more expensive than
# a slow run -- it produced two false "this app is broken" reports on
# 2026-08-04, both of which reached the operator.
CONTENT_WAIT_MS = 15000

# The DOM effect of being SIGNED IN. Emitted by
# templates/global_base_partials/global_header.html inside
# `{% elif user.is_authenticated %}`, so it is absent for every
# unauthenticated page kind.
#
# WHY A POSITIVE MARKER, NOT "the visitor badge is absent": the first version
# of this check asserted absence of #header-visitor-badge-mobile, and it was
# VACUOUS. That badge is gated on `is_visitor` -- a visitor-POOL session --
# which is NOT the same state as "not logged in". A plain anonymous request is
# routed to /landing/ and carries no badge at all, so the absence test passed
# and the run cheerfully labelled an anonymous capture `session=signed-in`.
# Measured against live scitex.ai before this comment was written.
# Absence of one failure mode is not presence of success: assert the thing you
# actually require.
SIGNED_IN_SEL = "#user-menu-toggle"


def _warn_if_no_symbol_font():
    """Warn when this machine cannot draw the Unicode symbols the UI uses as icons.

    MEASURED 2026-08-04, and it cost a false bug report to the operator. The
    cards board uses BARE UNICODE CHARACTERS as its icons -- the template
    carries the likes of U+2699 gear, U+25B8 triangle, U+23F1 stopwatch -- and
    ships no icon font at all. This capture container has 22 fonts, none with
    symbol coverage, so Chromium substituted the missing-glyph box and the
    screenshots showed a row of squares. I read those squares as a product
    defect and sent them to the operator. They were an artefact of the renderer.

    The failure is silent by construction: a missing glyph raises nothing, the
    page still "renders", the run still reports success, and the artefact looks
    exactly like a broken UI. Nothing downstream can distinguish the two -- so
    the check belongs HERE, once, at the only point that knows.

    Deliberately does NOT fail the run. Missing fonts do not invalidate layout,
    routing, http status or session findings, which is most of what this sweep
    measures. It marks the one conclusion these artefacts cannot support.
    """
    try:
        out = subprocess.run(["fc-list"], capture_output=True, text=True,
                             timeout=10).stdout
    except Exception:
        # No fontconfig at all: coverage cannot be established either way. Say
        # so, rather than staying silent and implying the captures are clean.
        print("WARNING: fc-list unavailable — symbol-font coverage UNKNOWN. Do "
              "not read missing-glyph boxes in these captures as UI defects.",
              file=sys.stderr)
        return
    if not any(k in out.lower() for k in
               ("emoji", "symbola", "symbols", "dejavu", "freeserif")):
        print("!" * 72, file=sys.stderr)
        print(f"!!! NO SYMBOL/EMOJI FONT on this machine "
              f"({len(out.splitlines())} fonts installed).", file=sys.stderr)
        print("!!! This UI draws icons as bare Unicode characters. Without "
              "coverage they capture as □.", file=sys.stderr)
        print("!!! Those boxes are an artefact of THIS CONTAINER, not a site "
              "bug — do not report them.", file=sys.stderr)
        print("!!! Fix: install fonts-noto-core + fonts-noto-color-emoji in the "
              "image that runs this harness.", file=sys.stderr)
        print("!" * 72, file=sys.stderr)


def collect_app_links(page, base, settle_ms):
    # "commit" not "domcontentloaded": on dev, media elements (landing
    # video) loop range-requests against daphne runserver and DCL never
    # fires even though the page is fully rendered. Commit + settle is
    # what a screenshot actually needs.
    page.goto(base + "/", wait_until="commit", timeout=30000)
    # the launcher grid is JS-rendered after a loading state; give it the
    # same settle the capture pass gets, or discovery sees 0 tiles
    try:
        page.wait_for_selector("#launcher-grid a[href], .launcher-grid a[href]",
                               timeout=max(settle_ms, 3000))
    except Exception:
        pass  # fall through: eval below returns [] and the caller reports 0
    page.wait_for_timeout(1000)
    # launcher tiles are <a> inside #launcher-grid with an href to the app
    # data-label is the app name; textContent's first line can be an
    # availability chip ("Desktop-only"), which collides filenames
    hrefs = page.eval_on_selector_all(
        "#launcher-grid a[href], .launcher-grid a[href]",
        "els => els.map(e => ({href: e.getAttribute('href'), label: e.getAttribute('data-label') || (e.textContent||'').trim().split('\\n')[0].trim()}))",
    )
    seen, out = set(), []
    for h in hrefs:
        u = h["href"]
        if not u or u in seen:
            continue
        seen.add(u)
        out.append((h["label"] or u, u))
    return out


def login(page, base, username, password):
    """Authenticate before discovery. Returns True only if the launcher appears.

    Anonymous sessions are routed to /landing/, which carries NO launcher grid.
    An un-authenticated run therefore discovers 0 apps and silently degrades to
    "home only" while still printing a captured N/N summary — which is how this
    harness stopped covering every app without anyone noticing (2026-07-29).

    The sign-in path is /auth/login/ (auth_app owns it); /accounts/login/ 404s.
    """
    page.goto(base.rstrip("/") + "/auth/login/", wait_until="commit", timeout=30000)
    page.wait_for_timeout(1500)
    try:
        page.fill("input[name='login'], input[name='username']", username)
        page.fill("input[name='password']", password)
        page.click("button[type='submit'], input[type='submit']")
    except Exception as exc:
        print(f"LOGIN FAILED: could not drive the sign-in form: {exc}", file=sys.stderr)
        return False
    page.wait_for_timeout(3000)
    # Verify by EFFECT, not by absence of an error banner: the launcher grid is
    # what discovery needs, so that is what "logged in" has to mean here.
    page.goto(base.rstrip("/") + "/", wait_until="commit", timeout=30000)
    try:
        page.wait_for_selector("#launcher-grid a[href], .launcher-grid a[href]",
                               timeout=8000)
        return True
    except Exception:
        print("LOGIN FAILED: submitted the form but / still has no launcher grid "
              "— credentials rejected, or the landing/launcher routing changed.",
              file=sys.stderr)
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://scitex.ai")
    ap.add_argument("--out", default="/tmp/qa_shots")
    ap.add_argument("--only", default="", help="comma list of label substrings")
    ap.add_argument("--viewports", default="mobile", help="mobile,desktop")
    ap.add_argument("--settle-ms", type=int, default=3000,
                    help="post-commit settle before screenshot (dev's unminified JS needs ~12000)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any pane/boot wait ended in a TIMEOUT or WAIT-ERROR")
    ap.add_argument("--color-scheme", default="dark",
                    choices=["dark", "light", "no-preference"],
                    help="prefers-color-scheme for both contexts; the product "
                         "is dark-by-default, so DEFAULT is dark")
    ap.add_argument("--login-user", default="",
                    help="sign in before discovery. WITHOUT this the run is "
                         "anonymous, gets routed to /landing/, and discovers 0 "
                         "apps — see --allow-empty.")
    ap.add_argument("--login-password", default="",
                    help="PREFER the env var SCITEX_HUB_QA_PASSWORD. A password "
                         "passed here lands on argv, and argv is world-readable "
                         "through /proc/<pid>/cmdline — the same leak this "
                         "codebase already closed for git credentials (see "
                         "build_gitea_auth_env, which passes the Gitea token by "
                         "environment for exactly this reason). It also lands in "
                         "shell history and CI logs.")
    ap.add_argument("--allow-empty", action="store_true",
                    help="permit a run that discovered 0 app links. Without it "
                         "zero discovery is a HARD ERROR, because per-app "
                         "coverage is the entire point of this harness and "
                         "'captured 1/1' after finding nothing is a green run "
                         "that checked nothing.")
    args = ap.parse_args()

    # Credentials from the ENVIRONMENT by preference. The flags remain for
    # compatibility but are the leaky path: a process's environ is readable
    # only by the same uid (or root), argv is readable by anyone.
    args.login_user = args.login_user or os.environ.get("SCITEX_HUB_QA_USER", "")
    args.login_password = args.login_password or os.environ.get(
        "SCITEX_HUB_QA_PASSWORD", ""
    )
    os.makedirs(args.out, exist_ok=True)
    _warn_if_no_symbol_font()
    only = [s.strip().lower() for s in args.only.split(",") if s.strip()]
    vps = [v.strip() for v in args.viewports.split(",") if v.strip()]

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        # discover app links once (mobile ctx)
        w, h, dsf = VIEWPORTS["mobile"]
        disc = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=dsf,
                             color_scheme=args.color_scheme)
        dp = disc.new_page()
        if args.login_user:
            if not login(dp, args.base, args.login_user, args.login_password):
                disc.close()
                b.close()
                print("aborting: authentication was requested and failed, so any "
                      "capture below would be an anonymous run masquerading as a "
                      "signed-in one.", file=sys.stderr)
                sys.exit(2)
        links = collect_app_links(dp, args.base, args.settle_ms)
        # CARRY THE SESSION INTO THE CAPTURE CONTEXTS.
        # Playwright contexts do NOT share cookies. Logging in on `disc` and
        # then capturing from a fresh context produced AUTHENTICATED DISCOVERY
        # AND ANONYMOUS CAPTURES: every screenshot showed the visitor
        # "Read-Only" header while the run reported a signed-in sweep. That is
        # the same "the harness is not the thing it claims to measure" failure
        # this file's login guard exists to prevent, one layer deeper.
        storage_state = disc.storage_state() if args.login_user else None
        disc.close()
        if not links and not args.allow_empty:
            b.close()
            hint = ("pass --login-user/--login-password: anonymous sessions are "
                    "routed to /landing/, which has no launcher grid"
                    if not args.login_user else
                    "signed in, but the launcher rendered no tiles — that is "
                    "itself the bug to report")
            print(f"ERROR: discovered 0 app links, so this run would cover the "
                  f"home page only. {hint}. Use --allow-empty to override.",
                  file=sys.stderr)
            sys.exit(3)
        # always include the home itself
        targets = [("home", args.base + "/")] + links
        if only:
            targets = [(l, u) for (l, u) in targets if l == "home" or any(s in l.lower() or s in u.lower() for s in only)]
        print(f"discovered {len(links)} app links; capturing {len(targets)} targets x {len(vps)} viewport(s)")
        results = []  # (viewport, label, pane_outcome, boot_outcome, captured, is_visitor)
        # Whether the visitor badge was observed ANYWHERE this run. Drives the
        # control probe below: if authentication was requested and the badge
        # never appeared, we must prove it was findable at all before reading
        # that silence as "every page was signed in". A list so the capture
        # loop can set it without a nonlocal declaration.
        marker_ever_seen = [False]
        for vpname in vps:
            w, h, dsf = VIEWPORTS[vpname]
            # storage_state is THE point of the capture: without it this context
            # is anonymous no matter what happened during discovery, and every
            # screenshot below would show the visitor shell while the run
            # reported a signed-in sweep.
            ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=dsf,
                                color_scheme=args.color_scheme,
                                storage_state=storage_state)
            for label, url in targets:
                pg = ctx.new_page()
                status, pane, boot, content = "?", "n/a", "n/a", "n/a"
                full = url if url.startswith("http") else (args.base.rstrip("/") + "/" + url.lstrip("/"))
                try:
                    resp = pg.goto(full, wait_until="commit", timeout=30000)
                    status = str(resp.status) if resp else "no-resp"
                    pg.wait_for_timeout(args.settle_ms)
                    # Two boot signals, one per page kind — the outcome is
                    # TRACKED, never swallowed (incident 2026-07-22: 16/24
                    # "http=200" captures were the identical spinner frame).
                    # A timeout still screenshots whatever is there, but the
                    # log says so.
                    # 1) Workspace-shell pages fill #ws-module-pane
                    #    client-side; a fixed settle can grade a mid-boot
                    #    frame as blank. Wait for real content OR the
                    #    fail-loud error box (anything beyond the loader).
                    #    Injected partials start with invisible
                    #    <style>/<link>/<script> children, which the plain
                    #    :not(.ws-module-loading) selector matched first —
                    #    the visible-state wait then ALWAYS timed out.
                    #    Exclude them so the wait detects rendered content.
                    # 2) Standalone app pages (writer/scholar/...) have no
                    #    module pane but boot behind a full-screen
                    #    #app-loading-screen overlay (10-25s on prod visitor
                    #    sessions). Every dismissal path (main.ts
                    #    dismissLoadingScreen(), the global_base 3s safety
                    #    net) adds body.app-ready; the overlay hiding is
                    #    DERIVED from that class via a 0.3s CSS fade whose
                    #    opacity:0 phase still counts as visible to
                    #    playwright — so the body class is the robust wait
                    #    target, not the overlay's visibility.
                    if pg.query_selector("#ws-module-pane"):
                        try:
                            pg.wait_for_selector(
                                "#ws-module-pane > :not(.ws-module-loading)"
                                ":not(style):not(link):not(script)"
                                ":not(template)",
                                state="visible",
                                timeout=PANE_WAIT_MS)
                            pane = "rendered"
                        except PWTimeoutError:
                            pane = f"LOADING-TIMEOUT({PANE_WAIT_MS // 1000}s)"
                        except Exception as we:
                            pane = f"WAIT-ERROR({type(we).__name__})"
                    elif pg.query_selector("#app-loading-screen"):
                        try:
                            pg.wait_for_selector(
                                "body.app-ready", timeout=PANE_WAIT_MS)
                            boot = "ready"
                        except PWTimeoutError:
                            boot = f"BOOT-TIMEOUT({PANE_WAIT_MS // 1000}s)"
                        except Exception as we:
                            boot = f"WAIT-ERROR({type(we).__name__})"
                    # WAIT FOR PAINT, NOT JUST FOR BOOT.
                    # `body.app-ready` means the loading screen was DISMISSED;
                    # it says nothing about whether the app drew anything. On
                    # 2026-08-04 Scholar reported boot=ready and was then
                    # photographed mid-paint: the PNG was blank while the DOM
                    # already held 596 characters. I reported that blank frame
                    # to the operator as "the content area is completely
                    # empty". It was not empty; it was unpainted. A fixed
                    # settle timer cannot tell those apart, and the artefact is
                    # indistinguishable from a genuinely broken app.
                    # So: poll the real content container until it has text,
                    # and TRACK the outcome instead of silently proceeding.
                    try:
                        pg.wait_for_function(
                            """() => {
                              // VISIBLE PIXELS BELOW THE CHROME, not text in the DOM.
                              // Text is the wrong signal: Scholar had 596 chars in
                              // .library-tab-inner at 3s while the screenshot was still
                              // blank, and a text probe also matches the tab bar, which
                              // is always present -- so it passes on every page and
                              // proves nothing. What actually differs is whether the
                              // content region has been laid out with real geometry.
                              const vh = window.innerHeight;
                              const els = document.querySelectorAll(
                                'main *, #ws-module-pane *, [class*="tab-content"] *');
                              let painted = 0;
                              for (const e of els) {
                                const r = e.getBoundingClientRect();
                                // Below the header band, on-screen, and big enough to
                                // be something a user would see.
                                if (r.top > 90 && r.top < vh && r.width > 80 && r.height > 20) {
                                  const c = getComputedStyle(e);
                                  if (c.visibility !== 'hidden' && c.display !== 'none' &&
                                      parseFloat(c.opacity) > 0.1) painted++;
                                }
                                if (painted >= 3) return true;
                              }
                              return false;
                            }""",
                            timeout=CONTENT_WAIT_MS)
                        content = "painted"
                    except PWTimeoutError:
                        content = f"NO-CONTENT({CONTENT_WAIT_MS // 1000}s)"
                    except Exception as we:
                        content = f"WAIT-ERROR({type(we).__name__})"
                    # VERIFY THE SESSION BY EFFECT, per captured page.
                    # The login guard above only proves the login POST
                    # succeeded once. It cannot see a session dropped later
                    # (cookie expiry, a visitor-pool eviction, a redirect
                    # through /landing/), and a dropped session still yields
                    # a perfectly renderable screenshot -- of the visitor
                    # shell. That run reports success while measuring the
                    # wrong thing entirely.
                    # VISITOR_BADGE_SEL is emitted inside {% if is_visitor %}
                    # (global_header.html), so its PRESENCE is the effect of
                    # being a visitor -- not a hidden element every page
                    # carries.
                    signed_in = bool(pg.query_selector(SIGNED_IN_SEL))
                    if signed_in:
                        marker_ever_seen[0] = True
                    visitor = bool(args.login_user) and not signed_in
                    safe = "".join(c if c.isalnum() else "_" for c in label)[:32]
                    fn = os.path.join(args.out, f"{vpname}__{safe}.png")
                    pg.screenshot(path=fn)
                    sess = "signed-in" if signed_in else "NOT-SIGNED-IN"
                    print(f"[{vpname}] {label:24} {url:42} http={status}  pane={pane}  boot={boot}  content={content}  session={sess}  -> {os.path.basename(fn)}")
                    results.append((vpname, label, pane, boot, True, visitor, content))
                except Exception as e:
                    print(f"[{vpname}] {label:24} {url:42} http={status}  pane={pane}  boot={boot}  content={content}  ERROR {type(e).__name__}: {str(e)[:80]}")
                    results.append((vpname, label, pane, boot, False, False, content))
                finally:
                    pg.close()
            ctx.close()
        b.close()

    # DISCRIMINATION CONTROL for the signed-in assertion.
    # "Every page showed the signed-in marker" is only meaningful if that
    # marker can also be ABSENT. If the selector matched something every page
    # carries regardless of session, the check would pass forever without
    # measuring anything. So load the base URL with NO session and require
    # the marker to be absent there. A marker present anonymously does not
    # discriminate, and this run certifies nothing.
    if args.login_user and marker_ever_seen[0]:
        with sync_playwright() as p2:
            b2 = p2.chromium.launch(headless=True)
            w, h, dsf = VIEWPORTS["mobile"]
            anon = b2.new_context(viewport={"width": w, "height": h},
                                  device_scale_factor=dsf,
                                  color_scheme=args.color_scheme)
            cp = anon.new_page()
            try:
                cp.goto(args.base, wait_until="commit", timeout=30000)
                cp.wait_for_timeout(args.settle_ms)
                # Discriminates only if ABSENT without a session.
                control_ok = not cp.query_selector(SIGNED_IN_SEL)
            except Exception as ce:
                control_ok = False
                print(f"control probe errored: {type(ce).__name__}: {ce}",
                      file=sys.stderr)
            finally:
                anon.close()
                b2.close()
        if not control_ok:
            print("!" * 72, file=sys.stderr)
            print(f"!!! ASSERTION IS VACUOUS: selector {SIGNED_IN_SEL} is present "
                  f"even on an ANONYMOUS load of {args.base} (or the probe errored).",
                  file=sys.stderr)
            print("!!! It therefore does not distinguish signed-in from anonymous, so "
                  "every 'signed-in' verdict above is unproven — a check that cannot "
                  "fail is not a check.", file=sys.stderr)
            print("!!! Fix the selector (see global_header.html, "
                  "{% elif user.is_authenticated %}) before trusting this run.",
                  file=sys.stderr)
            print("!" * 72, file=sys.stderr)
            sys.exit(4)
        print(f"control ok: {SIGNED_IN_SEL} is absent anonymously and present on "
              f"every capture, so 'signed-in' is a real measurement")

    def _bad(outcome):
        return outcome.startswith(("LOADING-TIMEOUT", "BOOT-TIMEOUT", "WAIT-ERROR"))

    captured = sum(1 for r in results if r[4])
    rendered = sum(1 for r in results if r[2] == "rendered")
    ready = sum(1 for r in results if r[3] == "ready")
    n_na = sum(1 for r in results if r[2] == "n/a" and r[3] == "n/a")
    timeouts = [r for r in results if r[2].startswith("LOADING-TIMEOUT")
                or r[3].startswith("BOOT-TIMEOUT")]
    wait_errs = [r for r in results if r[2].startswith("WAIT-ERROR")
                 or r[3].startswith("WAIT-ERROR")]
    print(f"summary: captured {captured}/{len(results)} | "
          f"pane: {rendered} rendered | boot: {ready} ready | "
          f"{n_na} n/a | {len(timeouts)} timeout, {len(wait_errs)} wait-error")
    bad = [r for r in results if _bad(r[2]) or _bad(r[3])]
    if bad:
        print("!" * 72)
        print(f"!!! {len(bad)} capture(s) are NOT a rendered page "
              f"(spinner frame or wait failure):")
        for vp, label, pane, boot, _, _v, _c in bad:
            print(f"!!!   [{vp}] {label}  pane={pane}  boot={boot}")
        print("!" * 72)
        if args.strict:
            sys.exit(1)

    # A capture that shows the visitor badge while authentication was
    # REQUESTED is an anonymous screenshot masquerading as a signed-in one.
    # This is not a warning: it invalidates the artefact, because the whole
    # point of --login-user is to see what a signed-in user sees. Fail
    # regardless of --strict; --strict grades page rendering, this grades
    # whether we measured the right session at all.
    leaked = [r for r in results if r[4] and r[5]]
    if args.login_user and leaked:
        print("!" * 72, file=sys.stderr)
        print(f"!!! {len(leaked)} of {captured} capture(s) lack the signed-in marker "
              f"despite --login-user: the session did not hold.", file=sys.stderr)
        for vp, label, _p, _b, _c, _v, _ct in leaked:
            print(f"!!!   [{vp}] {label}", file=sys.stderr)
        print("!!! These screenshots are anonymous pages. Do NOT report them as a "
              "signed-in sweep, and do not grade UX from them.", file=sys.stderr)
        print("!" * 72, file=sys.stderr)
        sys.exit(5)


if __name__ == "__main__":
    main()
