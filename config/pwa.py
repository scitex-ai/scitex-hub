#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Root-scoped PWA assets: ``/sw.js`` and ``/manifest.json``.

A service worker may only control URLs BELOW the path it was served from, so
``sw.js`` has to answer at the site ROOT to get root scope — it cannot be a
``{% static %}`` link under ``/static/``. The manifest is resolved relative to
the document and is declared next to it, so it gets the same treatment. That is
why these two files have URL patterns of their own.

Serving them is fiddlier than it looks, because the file exists in TWO places
and which one is present depends on the environment:

    static/shared/sw.js        the source tree      (always, it is tracked)
    staticfiles/shared/sw.js   the collected copy   (only after collectstatic)

The previous form hard-coded the document root at URLconf import time::

    document_root = settings.STATIC_ROOT or settings.STATICFILES_DIRS[0]

which READS as "collected copy, else source tree" but never behaves that way.
``STATIC_ROOT`` is ``BASE_DIR / "staticfiles"`` (settings_static.configure) — a
``Path``, and a ``Path`` is ALWAYS truthy, even when the directory does not
exist. The ``or`` branch was therefore unreachable dead code, and the route
always pointed at the collectstatic DESTINATION whether or not anything had
been collected into it.

So every environment that boots WITHOUT collectstatic 404'd on ``/sw.js``.
Prod and staging were fine — their entrypoints run collectstatic at boot — but
a plain ``manage.py runserver`` was not, and neither was CI.

It failed SILENTLY, which is why it survived: ``pwa-register.ts`` swallows the
rejection with ``.catch(() => {})``, so nothing renders differently and no
request shows up in the page's own network log — the service-worker script
fetch is made by the browser's SW machinery, not by the document. The only
trace is a console error.

Measured in run 32059143367 (the Product Screenshots job, all 20 checks green):

    console.error: A bad HTTP response code (404) was received when
                   fetching the script.

on 10 of the 11 captured pages — every page built on ``global_base.html``,
whose ``global_base_partials/global_head_meta.html`` loads ``pwa-register``.
The single page without it, Cards, is served by the external ``scitex_cards``
app and does not extend that base.

The fix is to resolve at REQUEST time through the same staticfiles machinery
that serves ``/static/`` and that ``collectstatic`` itself reads: prefer the
collected copy (prod/staging, where STATIC_ROOT is the canonical served tree),
and fall back to the finders when it is not there. That fallback is what the
old ``or`` was trying to express; this actually performs it.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import Http404
from django.views.static import serve


def serve_root_static(request, *, path: str):
    """Serve the staticfiles-relative ``path`` from the URL root.

    ``path`` comes from the URLconf's extra-kwargs dict, never from the
    request, so there is no user-controlled traversal to defend against here —
    and it must stay that way. Do not wire this up behind a ``<path:...>``
    capture.
    """
    resolved = _resolve_static(path)
    if resolved is None:
        # Loud, not silent. If neither STATIC_ROOT nor any finder can produce
        # the file, the asset is genuinely missing from the deployment and the
        # 404 should say which name failed rather than looking like a routing
        # miss.
        raise Http404(
            f"{path!r} is not present in STATIC_ROOT and no staticfiles "
            "finder can locate it"
        )
    return serve(request, resolved.name, document_root=str(resolved.parent))


def _resolve_static(path: str) -> Path | None:
    """Return the on-disk file for ``path``, or None if nothing has it.

    STATIC_ROOT first: in prod/staging that is the collected, content-hashed
    tree the rest of the site is served from, and it is the copy that has
    actually been through collectstatic's post-processing.
    """
    static_root = settings.STATIC_ROOT
    if static_root:
        collected = Path(static_root) / path
        if collected.is_file():
            return collected

    found = finders.find(path)
    if not found:
        return None
    # find() returns a list only when called with all=True, which we never do.
    # Handle it anyway rather than trusting the shape of someone else's return.
    if isinstance(found, (list, tuple)):
        found = found[0]
    return Path(found)


# EOF
