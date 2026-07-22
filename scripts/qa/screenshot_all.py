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
import argparse, os, sys
from playwright.sync_api import TimeoutError as PWTimeoutError, sync_playwright

VIEWPORTS = {"mobile": (390, 844, 2), "desktop": (1440, 900, 1)}
PANE_WAIT_MS = 12000


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
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    only = [s.strip().lower() for s in args.only.split(",") if s.strip()]
    vps = [v.strip() for v in args.viewports.split(",") if v.strip()]

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        # discover app links once (mobile ctx)
        w, h, dsf = VIEWPORTS["mobile"]
        disc = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=dsf)
        dp = disc.new_page()
        links = collect_app_links(dp, args.base, args.settle_ms)
        disc.close()
        # always include the home itself
        targets = [("home", args.base + "/")] + links
        if only:
            targets = [(l, u) for (l, u) in targets if l == "home" or any(s in l.lower() or s in u.lower() for s in only)]
        print(f"discovered {len(links)} app links; capturing {len(targets)} targets x {len(vps)} viewport(s)")
        results = []  # (viewport, label, pane_outcome, boot_outcome, captured)
        for vpname in vps:
            w, h, dsf = VIEWPORTS[vpname]
            ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=dsf)
            for label, url in targets:
                pg = ctx.new_page()
                status, pane, boot = "?", "n/a", "n/a"
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
                    safe = "".join(c if c.isalnum() else "_" for c in label)[:32]
                    fn = os.path.join(args.out, f"{vpname}__{safe}.png")
                    pg.screenshot(path=fn)
                    print(f"[{vpname}] {label:24} {url:42} http={status}  pane={pane}  boot={boot}  -> {os.path.basename(fn)}")
                    results.append((vpname, label, pane, boot, True))
                except Exception as e:
                    print(f"[{vpname}] {label:24} {url:42} http={status}  pane={pane}  boot={boot}  ERROR {type(e).__name__}: {str(e)[:80]}")
                    results.append((vpname, label, pane, boot, False))
                finally:
                    pg.close()
            ctx.close()
        b.close()

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
        for vp, label, pane, boot, _ in bad:
            print(f"!!!   [{vp}] {label}  pane={pane}  boot={boot}")
        print("!" * 72)
        if args.strict:
            sys.exit(1)


if __name__ == "__main__":
    main()
