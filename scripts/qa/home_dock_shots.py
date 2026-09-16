#!/usr/bin/env python3
"""Home + site-dock screenshot set: phone and desktop, dark and light, one command.

Captures /apps/, /apps/my-projects/, /apps/public-projects/ and a leaf page
(/apps/scholar/v2/) at 390x844 (DPR 3, touch), 1280x800, 1440x900 and
1920x1080, in dark and light, signed in as the probe user. Writes PNGs to --out
and prints one JSON geometry probe per capture, covering what the operator
checked by eye on 2026-09-14:
  * first-row tile count and modules (a single column at 1920 was reported;
    the first row must be the 4 Foundation apps at every width);
  * the group bands per page (Foundation / Work / System);
  * whether "ALL APPS" is clipped under the header;
  * visible page arrows (must be 0 on the phone);
  * globe and desktop-only badge size as a fraction of the icon;
  * desktop-only tile opacity and filter (must not be dimmed);
  * the dock grip's hit size;
  * anything visible near the bottom edge outside the dock.

Run INSIDE the dev container, from a checkout whose server is reachable at
--base. The server must render that checkout, e.g. a temporary
`python manage.py runserver 0.0.0.0:8012 --noreload from_docker`:

    python scripts/qa/home_dock_shots.py --base http://127.0.0.1:8012 \
        --out GITIGNORED/home-dock/shots --tag v2 [--themes dark,light]

SIGN-IN: the probe user pk=20 (leader-probe-staff-agents) is set is_active=True
for the run only, and ALWAYS restored to is_active=False, is_staff=False,
is_superuser=False, with its sessions deleted, in a finally. No user is created.

For the full app sweep see screenshot_all.py; this is the focused set for the
Home / dock surfaces.
"""

import argparse
import json
import os
import sys
from urllib.parse import urlparse

PROBE_USER_PK = 20
PROBE_USERNAME = "leader-probe-staff-agents"

PAGES = [
    ("apps", "/apps/"),
    ("myprojects", "/apps/my-projects/"),
    ("public_projects", "/apps/public-projects/"),
    ("scholar", "/apps/scholar/v2/"),
]
SIZES = [
    ("390", 390, 844, True),
    ("1280", 1280, 800, False),
    ("1440", 1440, 900, False),
    ("1920", 1920, 1080, False),
]

PROBE = """() => {
  const q = (s) => document.querySelector(s);
  const vis = (el) => { if (!el) return false; const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden'; };
  const tiles = [...document.querySelectorAll('.launcher-tile')];
  const firstTop = tiles.length ? Math.round(tiles[0].getBoundingClientRect().top) : null;
  const firstRow = tiles.filter(t => Math.abs(Math.round(t.getBoundingClientRect().top) - firstTop) < 4).length;
  const head = q('.launcher-section-head');
  const header = q('.global-header');
  const page = q('.launcher-page');
  const icon = q('.launcher-tile[data-module="public_projects"] .launcher-tile-icon');
  const globe = q('.launcher-tile-icon-badge');
  const figIcon = q('.launcher-tile[data-module="figrecipe"] .launcher-tile-icon');
  const monitor = q('.launcher-tile[data-module="figrecipe"] .launcher-badge');
  const dock = q('.site-dock');
  const grip = q('[data-dock-grabber]');
  const d = dock ? dock.getBoundingClientRect() : null;
  const strays = dock ? [...document.querySelectorAll('button, a, .launcher-page-arrow')]
    .filter(el => vis(el) && !dock.contains(el) && !el.closest('.site-footer') && !el.closest('.launcher-dots')
      && el.getBoundingClientRect().top > innerHeight - 140 && el.getBoundingClientRect().bottom <= innerHeight)
    .map(el => (el.id || String(el.className)).slice(0, 40)) : null;
  return {
    firstRowTiles: firstRow, tiles: tiles.length,
    firstRowModules: tiles.filter(t => Math.abs(Math.round(t.getBoundingClientRect().top) - firstTop) < 4).map(t => t.dataset.module),
    bands: [...document.querySelectorAll('.launcher-group')].map(b => (b.dataset.group || '-') + ':' + b.querySelectorAll('.launcher-tile').length + (b.getBoundingClientRect().right > innerWidth ? '(offscreen)' : '')),
    pageDisplay: page ? getComputedStyle(page).display + ' cols=' + getComputedStyle(page).gridTemplateColumns.split(' ').length : null,
    pages: document.querySelectorAll('.launcher-page').length,
    arrowsVisible: [...document.querySelectorAll('.launcher-page-arrow')].filter(vis).length,
    headClipped: head && vis(head) && header ? head.getBoundingClientRect().top < header.getBoundingClientRect().bottom : null,
    globeRatio: globe && icon ? +(globe.getBoundingClientRect().width / icon.getBoundingClientRect().width).toFixed(2) : null,
    monitorRatio: monitor && figIcon ? +(monitor.getBoundingClientRect().width / figIcon.getBoundingClientRect().width).toFixed(2) : null,
    figIcon: figIcon ? getComputedStyle(figIcon).opacity + ' ' + getComputedStyle(figIcon).filter : null,
    grip: grip ? (r => [Math.round(r.width), Math.round(r.height)])(grip.getBoundingClientRect()) : null,
    dockInViewport: d ? (d.left >= 0 && d.right <= innerWidth && d.bottom <= innerHeight) : null,
    bottomStrays: strays,
    hOverflow: document.documentElement.scrollWidth > innerWidth,
  };
}"""


def _setup_django():
    sys.path.insert(0, os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()


def _open_session() -> str:
    from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
    from django.contrib.auth.models import User
    from django.contrib.sessions.backends.db import SessionStore

    user = User.objects.get(pk=PROBE_USER_PK)
    if user.username != PROBE_USERNAME:
        raise SystemExit(f"pk={PROBE_USER_PK} is {user.username!r}, not the probe user")
    user.is_active = True
    user.save(update_fields=["is_active"])
    store = SessionStore()
    store[SESSION_KEY] = str(user.pk)
    store[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
    store[HASH_SESSION_KEY] = user.get_session_auth_hash()
    store.create()
    return store.session_key


def _restore() -> None:
    from django.contrib.auth.models import User
    from django.contrib.sessions.models import Session

    user = User.objects.get(pk=PROBE_USER_PK)
    user.is_active = False
    user.is_staff = False
    user.is_superuser = False
    user.save(update_fields=["is_active", "is_staff", "is_superuser"])
    deleted = 0
    for row in Session.objects.all():
        try:
            if row.get_decoded().get("_auth_user_id") == str(PROBE_USER_PK):
                row.delete()
                deleted += 1
        except Exception:
            pass
    print(f"RESTORED {user.username} active={user.is_active} staff={user.is_staff} "
          f"superuser={user.is_superuser} sessions_deleted={deleted}")


def _shoot(base: str, out_dir: str, tag: str, themes: list[str], session_key: str) -> list:
    from playwright.sync_api import sync_playwright

    host = urlparse(base).hostname
    os.makedirs(out_dir, exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for theme in themes:
            for sname, w, h, phone in SIZES:
                for pname, path in PAGES:
                    opts = {"viewport": {"width": w, "height": h}, "color_scheme": theme}
                    if phone:
                        opts.update(device_scale_factor=3, has_touch=True, is_mobile=True)
                    ctx = browser.new_context(**opts)
                    ctx.add_cookies([{"name": "sessionid", "value": session_key, "domain": host, "path": "/"}])
                    ctx.add_init_script(f"try {{ localStorage.setItem('stx-theme', '{theme}'); }} catch (e) {{}}")
                    page = ctx.new_page()
                    name = f"{tag}-{pname}-{sname}-{theme}"
                    try:
                        resp = page.goto(base + path, wait_until="domcontentloaded", timeout=120000)
                        page.wait_for_timeout(4500)
                        if not phone:
                            # A real window resizes; the grid must survive it.
                            page.set_viewport_size({"width": w - 17, "height": h})
                            page.wait_for_timeout(400)
                            page.set_viewport_size({"width": w, "height": h})
                            page.wait_for_timeout(700)
                        # The user's saved theme applies after load; force the
                        # attribute for the requested theme (no profile write).
                        page.evaluate(
                            "(t) => { document.documentElement.setAttribute('data-theme', t); document.documentElement.setAttribute('data-color-mode', t); }",
                            theme,
                        )
                        page.wait_for_timeout(300)
                        info = page.evaluate(PROBE)
                        page.screenshot(path=os.path.join(out_dir, name + ".png"))
                        results.append([name, resp.status if resp else None, info])
                    except Exception as exc:
                        results.append([name, "ERROR", str(exc)[:200]])
                    ctx.close()
        browser.close()
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://127.0.0.1:8012")
    parser.add_argument("--out", required=True)
    parser.add_argument("--tag", default="shot")
    parser.add_argument("--themes", default="dark,light")
    args = parser.parse_args()

    _setup_django()
    try:
        session_key = _open_session()
        results = _shoot(args.base.rstrip("/"), args.out, args.tag, args.themes.split(","), session_key)
    finally:
        _restore()
    for row in results:
        print("SHOT " + json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
