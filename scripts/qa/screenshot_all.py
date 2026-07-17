#!/usr/bin/env python3
"""Layout CI — screenshot every workspace app + key pages, mobile + desktop.

Enumerates the app tiles from the launcher home (their real launch URLs), then
captures each in an isolated page at both an iPhone-ish and a desktop viewport.
Saves PNGs to --out and prints a per-URL status line (ok / http code / error)
so broken routes (404) and blank/incomprehensible interiors are caught without
a human opening each one by hand.

Usage:
    /opt/venv-sac/bin/python scripts/qa/screenshot_all.py \
        --base https://scitex.ai --out /tmp/qa_shots [--only writer,scholar]
"""
import argparse, os, sys
from playwright.sync_api import sync_playwright

VIEWPORTS = {"mobile": (390, 844, 2), "desktop": (1440, 900, 1)}


def collect_app_links(page, base):
    # "commit" not "domcontentloaded": on dev, media elements (landing
    # video) loop range-requests against daphne runserver and DCL never
    # fires even though the page is fully rendered. Commit + settle is
    # what a screenshot actually needs.
    page.goto(base + "/", wait_until="commit", timeout=30000)
    page.wait_for_timeout(3000)
    # launcher tiles are <a> inside #launcher-grid with an href to the app
    hrefs = page.eval_on_selector_all(
        "#launcher-grid a[href], .launcher-grid a[href]",
        "els => els.map(e => ({href: e.getAttribute('href'), label: (e.textContent||'').trim().split('\\n')[0].trim()}))",
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
        links = collect_app_links(dp, args.base)
        disc.close()
        # always include the home itself
        targets = [("home", args.base + "/")] + links
        if only:
            targets = [(l, u) for (l, u) in targets if l == "home" or any(s in l.lower() or s in u.lower() for s in only)]
        print(f"discovered {len(links)} app links; capturing {len(targets)} targets x {len(vps)} viewport(s)")
        for vpname in vps:
            w, h, dsf = VIEWPORTS[vpname]
            ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=dsf)
            for label, url in targets:
                pg = ctx.new_page()
                status = "?"
                full = url if url.startswith("http") else (args.base.rstrip("/") + "/" + url.lstrip("/"))
                try:
                    resp = pg.goto(full, wait_until="commit", timeout=30000)
                    status = str(resp.status) if resp else "no-resp"
                    pg.wait_for_timeout(3000)
                    safe = "".join(c if c.isalnum() else "_" for c in label)[:32]
                    fn = os.path.join(args.out, f"{vpname}__{safe}.png")
                    pg.screenshot(path=fn)
                    print(f"[{vpname}] {label:24} {url:42} http={status}  -> {os.path.basename(fn)}")
                except Exception as e:
                    print(f"[{vpname}] {label:24} {url:42} http={status}  ERROR {type(e).__name__}: {str(e)[:80]}")
                finally:
                    pg.close()
            ctx.close()
        b.close()


if __name__ == "__main__":
    main()
