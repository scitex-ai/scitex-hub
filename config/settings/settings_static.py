#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static + media file settings.

Extracted from settings_shared.py, which had grown past the project's file-size
limit. Everything about how an asset gets from the repo to the browser lives
here, in one place.

Imported with ``from .settings_static import *`` by settings_shared, so
``BASE_DIR`` must be passed in — see ``configure(base_dir)``.
"""

from pathlib import Path

STATIC_URL = "/static/"
MEDIA_URL = "/media/"

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "apps.workspace.apps_app.finders.DevAppStaticFinder",
]

# CONTENT-HASH THE STATIC URLS. This is not an optimisation — it is a
# correctness fix, and it is load-bearing.
#
# Without it, {% static 'x.css' %} emits a STABLE url (/static/x.css) that never
# changes, while Cloudflare hands the browser `Cache-Control: max-age=2592000`
# — THIRTY DAYS. Measured on prod (2026-07-13):
#
#     GET /static/apps_app/css/launcher/grid.css
#     cache-control: max-age=2592000, must-revalidate
#
# So a returning browser keeps last month's CSS and never even revalidates.
#
# That is bad on its own — every UI fix is invisible to returning users for
# weeks — but the real damage is SKEW. The Vite bundles ARE content-hashed, so
# JS updates on every deploy while CSS does not, and the two then disagree about
# the DOM. It bit us for real: the launcher's new pager JS wrapped the app tiles
# into "page" elements, the operator's phone still had month-old CSS with no rule
# for a page, and his iPhone rendered the app grid as two columns of stacked
# icons. The page was not broken — it was being drawn by two different versions
# of itself.
#
# ManifestStaticFilesStorage derives every URL from the file's CONTENT
# (launcher.<md5>.css) and rewrites the url()/@import references inside CSS to
# match. A deploy therefore changes the URL, the browser must re-fetch, and the
# 30-day TTL becomes correct (immutable) instead of harmful. The HTML itself is
# served DYNAMIC (cf-cache-status: DYNAMIC), so a page always points at the
# current hashes.
#
# STRICT ON PURPOSE: this backend RAISES rather than silently serving an asset it
# cannot find — at collectstatic and at render. That is the behaviour we want
# (CLAUDE.md: no silent fallbacks), and it is why the 101 dangling
# CSS-@import/url() and {% static %} references had to be fixed first. Do NOT
# reach for `manifest_strict = False` to quieten it — that re-introduces exactly
# the silent 404s this exists to surface. Fix the reference instead.
# ...but ONLY in the environments that actually run collectstatic.
#
# The manifest backend resolves {% static %} through staticfiles.json, and that
# file only exists AFTER collectstatic has run. The test suite never runs it, so
# making this the global default made EVERY page render raise "Missing
# staticfiles manifest entry" — the base template's favicon is simply the first
# {% static %} it reaches. (CI caught exactly this; the gate below earned its
# keep on its first run.) Dev does not want it either: hashed URLs would kill
# CSS hot-reload.
#
# So the default stays Django's plain storage, and settings_prod /
# settings_staging opt IN — they are the two environments whose entrypoint runs
# collectstatic at boot.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# The hashing backend, named once here so prod/staging/the CI gate cannot drift.
#
# config.storage.HashedStaticFilesStorage is whitenoise's backend with ONE rule
# removed: it does not rewrite `sourceMappingURL` comments. Vendored bundles ship
# minified code without their maps (scitex-ui vendors Monaco's vs/ but no
# min-maps/), so Django was failing collectstatic over a debug pointer to a file
# that was deliberately never distributed. Everything user-facing — CSS url(),
# @import, {% static %} — stays STRICT. See config/storage.py.
HASHED_STATICFILES_BACKEND = "config.storage.HashedStaticFilesStorage"


def hashed_storages(current: dict) -> dict:
    """Return ``current`` with staticfiles switched to the hashing backend.

    Returns a NEW dict rather than mutating: ``STORAGES`` arrives in prod/staging
    by ``from .settings_shared import *``, so it is the *same object* as the
    shared module's — an in-place edit would reach across settings modules.
    """
    return {**current, "staticfiles": {"BACKEND": HASHED_STATICFILES_BACKEND}}


def configure(base_dir: Path) -> dict:
    """Return the path-dependent static/media settings for ``base_dir``."""
    return {
        "STATIC_ROOT": base_dir / "staticfiles",
        "STATICFILES_DIRS": [base_dir / "static", base_dir / ".jsbuild"],
        "MEDIA_ROOT": base_dir / "media",
    }


# EOF
