#!/usr/bin/env python3
"""First-run / settings / profile screenshot set: phone and desktop, EN and JA.

Captures the surfaces a new user meets right after signing up -- /auth/signin/,
/auth/signup/ (anonymous), /new/, /accounts/profile/, /accounts/settings/profile/,
/accounts/settings/ssh-keys/ and /console/ -- at 390x844 (DPR 3, touch) and
1440x900, and prints one JSON geometry probe per capture covering the site
audit of 2026-09-14:
  * the /new/ form column width and the name input width (D3: ~100px at 390);
  * the top of the settings content vs. the viewport height (D7: content
    started below a 13-item nav);
  * the profile heading's colour against its banner, and the Email value (D8);
  * any 404 static request (cities_timezones.json);
  * document.title (it leaked the last project name).

Run INSIDE the dev container, against a server that renders THIS checkout,
e.g. a temporary `python manage.py runserver 0.0.0.0:8013 --noreload`:

    python scripts/qa/onboarding_settings_shots.py --base http://127.0.0.1:8013 \
        --out GITIGNORED/onboarding-shots --tag before

SIGN-IN: the probe user pk=20 (leader-probe-staff-agents) is set is_active=True
for the run only, and ALWAYS restored to is_active=False, is_staff=False,
is_superuser=False, with its sessions deleted, in a finally. No user is created.
"""

import argparse
import json
import os
import sys
from urllib.parse import urlparse

PROBE_USER_PK = 20
PROBE_USERNAME = "leader-probe-staff-agents"

# (name, path, signed_in)
PAGES = [
    ("signin", "/auth/signin/", False),
    ("signup", "/auth/signup/", False),
    ("new", "/new/", True),
    ("profile", "/accounts/profile/", True),
    ("settings-profile", "/accounts/settings/profile/", True),
    ("settings-ssh-keys", "/accounts/settings/ssh-keys/", True),
    ("console", "/console/", True),
]
# (size, width, height, phone, theme, language)
VARIANTS = [
    ("390", 390, 844, True, "light", "en"),
    ("390", 390, 844, True, "dark", "ja"),
    ("1440", 1440, 900, False, "dark", "en"),
    ("1440", 1440, 900, False, "light", "ja"),
]

PROBE = """() => {
  const q = (s) => document.querySelector(s);
  const box = (el) => el ? (r => ({x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)}))(el.getBoundingClientRect()) : null;
  const heading = q('.profile-header h1');
  const banner = q('.profile-header');
  const email = [...document.querySelectorAll('.profile-field')].find(f => /mail|メール/i.test(f.textContent));
  return {
    path: location.pathname,
    title: document.title,
    lang: document.documentElement.lang,
    hOverflow: document.documentElement.scrollWidth > innerWidth,
    createForm: box(q('.create-form-card')),
    nameInput: box(q('#name')),
    settingsContent: box(q('.settings-content')),
    settingsNav: box(q('.settings-nav')),
    compactNav: box(q('.settings-nav-compact')),
    profileBanner: box(banner),
    profileHeading: heading ? {text: heading.textContent.trim(), color: getComputedStyle(heading).color, bg: getComputedStyle(banner).backgroundColor} : null,
    emailRow: email ? email.textContent.replace(/\\s+/g, ' ').trim() : null,
    h2: (q('.auth-form h2') || {}).textContent || null,
  };
}"""


def _setup_django():
    sys.path.insert(0, os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    # Sessions are minted between Playwright calls, and Playwright's sync API
    # runs an event loop on this thread; the ORM would refuse without this.
    # Single-threaded QA script, no concurrent ORM use.
    os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
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
    print(
        f"RESTORED {user.username} active={user.is_active} staff={user.is_staff} "
        f"superuser={user.is_superuser} sessions_deleted={deleted}"
    )


def _shoot(base: str, out_dir: str, tag: str, new_session, only: set) -> list:
    from playwright.sync_api import sync_playwright

    host = urlparse(base).hostname
    os.makedirs(out_dir, exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for pname, path, signed_in in PAGES:
            if only and pname not in only:
                continue
            for sname, w, h, phone, theme, lang in VARIANTS:
                opts = {"viewport": {"width": w, "height": h}, "color_scheme": theme}
                if phone:
                    opts.update(device_scale_factor=3, has_touch=True, is_mobile=True)
                ctx = browser.new_context(**opts)
                cookies = [{"name": "django_language", "value": lang, "domain": host, "path": "/"}]
                if signed_in:
                    # A fresh session per capture: one page that rotates or
                    # flushes its session must not sign out every later one.
                    cookies.append({"name": "sessionid", "value": new_session(), "domain": host, "path": "/"})
                ctx.add_cookies(cookies)
                ctx.add_init_script(f"try {{ localStorage.setItem('stx-theme', '{theme}'); }} catch (e) {{}}")
                page = ctx.new_page()
                missing = []
                page.on(
                    "response",
                    lambda r, missing=missing: missing.append(urlparse(r.url).path)
                    if r.status == 404 and "/static/" in r.url
                    else None,
                )
                name = f"{tag}-{pname}-{sname}-{theme}-{lang}"
                try:
                    resp = page.goto(base + path, wait_until="domcontentloaded", timeout=120000)
                    page.wait_for_timeout(4000)
                    page.evaluate(
                        "(t) => { document.documentElement.setAttribute('data-theme', t); document.documentElement.setAttribute('data-color-mode', t); }",
                        theme,
                    )
                    page.wait_for_timeout(300)
                    info = page.evaluate(PROBE)
                    info["static404"] = missing
                    page.screenshot(path=os.path.join(out_dir, name + ".png"))
                    results.append([name, resp.status if resp else None, info])
                except Exception as exc:
                    results.append([name, "ERROR", str(exc)[:200]])
                ctx.close()
        browser.close()
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://127.0.0.1:8013")
    parser.add_argument("--out", required=True)
    parser.add_argument("--tag", default="shot")
    parser.add_argument("--only", default="", help="comma-separated page names")
    args = parser.parse_args()

    _setup_django()
    only = {s for s in args.only.split(",") if s}
    try:
        results = _shoot(args.base.rstrip("/"), args.out, args.tag, _open_session, only)
    finally:
        _restore()
    for row in results:
        print("SHOT " + json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
