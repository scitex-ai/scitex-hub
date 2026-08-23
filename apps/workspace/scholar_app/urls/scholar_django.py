#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/workspace/scholar_app/urls/scholar_django.py
"""Mount `scitex_scholar._django` as the canonical scholar UI, BEHIND HUB'S AUTH.

Companion to `writer_app/urls/writer_django.py`, and deliberately narrower.

WHY THE GATE IS THE WHOLE POINT
-------------------------------
The leaf's views carry NO decorator of their own. Mounting its urlconf raw —
``path("scholar/", include("scitex_scholar._django.urls"))`` — publishes every
handler unauthenticated. Hub has already paid for that once: the equivalent raw
mount for WRITER was removed as a P0 (card sec-working-dir-passthrough-family,
SITE 3; see the note in config/urls.py). This module exists so the same mistake
cannot be made by copying the obvious snippet.

WHY NOT A WorkingDirScopedView LIKE WRITER'S
--------------------------------------------
Writer's wrapper also injects a server-side ``working_dir`` because writer takes
a caller-supplied path, which is what SITE 1 of that same card was about.
Scholar has no such input: scitex-scholar reports that no ``request.GET`` value
in its views reaches the filesystem, and the DB path comes from
``settings.CROSSREF_DB_PATH`` only. So authentication is the entire wrapper.
That claim is scholar's, about scholar's code; hub's gate does not depend on it
being true — if it is ever wrong, the exposure is to *logged-in* users rather
than the world, which is the difference this file guarantees.

WHY IT WRAPS THE URLCONF INSTEAD OF IMPORTING VIEWS ONE BY ONE
--------------------------------------------------------------
Writer's wrapper names three view callables. Scholar exposes a COMPLETE urlconf
(``app_name = "scholar"``, index + 6 api/graph routes). Naming them individually
here would mean a route added upstream silently does not exist under hub, and
the page would render with a dead graph. So the patterns are taken wholesale and
each callback is decorated.

The URLResolver check below is not defensive noise: if the leaf ever nests an
``include()``, decorating the outer entry would NOT gate the routes inside it,
and the failure would be a silently ungated endpoint. Refusing to import is the
correct response to a shape this module cannot honestly gate.
"""

from __future__ import annotations

import logging

from django.contrib.auth.decorators import login_required
from django.urls import URLPattern, URLResolver, include, path

logger = logging.getLogger(__name__)

# WHY THIS IMPORT IS GUARDED — a MEASURED outage, not a hypothetical.
#
# This module is imported by scholar_app/urls/__init__.py, which config/urls.py
# imports to build the ROOT urlconf. A module-scope ImportError here therefore
# does not disable scholar — it takes down EVERY URL hub serves, including the
# landing page.
#
# That is not speculative. Measured 2026-08-23 in scitex-hub-dev-django-1,
# minutes after #687 merged and before it was deployed:
#
#     /scitex-scholar/src/scitex_scholar/_django/views.py:42
#         from scitex_app.embed import mount_prefix
#     ImportError: cannot import name 'mount_prefix' from 'scitex_app.embed'
#
# scholar 1.9.0 needs `mount_prefix`; the scitex-app in that container is 0.6.1
# and does not export it. Both are EDITABLE installs from bind-mounted working
# trees, so hub's `scitex-scholar>=1.9.0` floor does not govern either version —
# a floor binds only where something installs against it.
#
# NOT A SILENT FALLBACK. The failure is logged at ERROR with the exception and
# the routes are omitted, so /apps/scholar/v2/ 404s while the legacy
# /apps/scholar/ keeps serving. Hub already uses exactly this shape for optional
# plugin mounts (config/urls.py: "Only mounted when the package is importable").
# The alternative — letting one leaf's dependency skew 500 the whole site — is
# not "failing loud", it is failing everywhere.
try:
    import scitex_scholar._django.urls as _leaf
except Exception as exc:  # noqa: BLE001 - any import-time failure must be caught
    _leaf = None
    _LEAF_IMPORT_ERROR = exc
else:
    _LEAF_IMPORT_ERROR = None

_MOUNT_PREFIX = "v2/"


class ImproperlyGatedURLConf(RuntimeError):
    """The upstream urlconf has a shape this module cannot authenticate."""


def _gated(patterns):
    """Return `patterns` with login_required applied to every view.

    Rebuilds each URLPattern around the same route object, so routes, names and
    default args are preserved exactly and a new upstream route is picked up for
    free.
    """
    gated = []
    for entry in patterns:
        if isinstance(entry, URLResolver):
            raise ImproperlyGatedURLConf(
                "scitex_scholar._django.urls now nests an include(); "
                "decorating the resolver would leave the routes inside it "
                "UNAUTHENTICATED. Gate them explicitly before mounting."
            )
        if not isinstance(entry, URLPattern):
            raise ImproperlyGatedURLConf(
                f"unexpected urlconf entry {entry!r} ({type(entry).__name__}); "
                "refusing to mount something this module cannot gate."
            )
        gated.append(
            URLPattern(
                entry.pattern,
                login_required(entry.callback),
                entry.default_args,
                entry.name,
            )
        )
    return gated


if _LEAF_IMPORT_ERROR is not None:
    logger.error(
        "scitex-scholar's Django app could not be imported, so %s is NOT "
        "mounted. The legacy /apps/scholar/ is unaffected. Cause: %r. Check "
        "that the installed scitex-scholar and its own dependencies agree — "
        "note that editable installs from bind-mounted working trees ignore "
        "hub's pyproject floors entirely.",
        "/apps/scholar/" + _MOUNT_PREFIX,
        _LEAF_IMPORT_ERROR,
    )
    urlpatterns = []
else:
    urlpatterns = [
        path(
            _MOUNT_PREFIX,
            include((_gated(_leaf.urlpatterns), "scholar"), namespace="scholar-leaf"),
        ),
    ]

# EOF
