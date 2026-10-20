#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/workspace/figrecipe_app/urls/figrecipe_django.py
"""Mount `figrecipe._django` as the canonical FigRecipe UI, BEHIND HUB'S AUTH.

Companion to `scholar_app/urls/scholar_django.py` (Scholar #1074 template),
and deliberately the same shape.

WHY THE GATE IS THE WHOLE POINT
-------------------------------
The leaf's views carry no hub login decorator of their own: 0.36 self-
authenticates inside `prepare_request` (401), older leaves mount raw. Either
way the hub-served boundary must not depend on which leaf release is
installed — hub has already paid for a raw mount once (writer's unwrapped
upstream mount was removed as a P0: card sec-working-dir-passthrough-family,
SITE 3; the figrecipe SITE-2 wrapper exists for the same reason). This module
exists so the cutover default cannot be made by copying the obvious snippet.

WHY ONLY LOGIN HERE, NOT THE SITE-2 JAIL GUARD
----------------------------------------------
Scholar's wrapper is login-only because scholar has no filesystem inputs.
FigRecipe DOES touch files — but the 0.36 leaf resolves SDK project authority
and jails every path channel itself (`prepare_request`: working_dir +
path/recipe/recipe_path containment, endpoint-gated compose/gallery/URL-
segment sinks, recipe validation), and declares that contract in its own
manifest `mount_policy` jail block (figrecipe#456, SDK reference verbatim).
So the DEFAULT's file containment is leaf-side; the hub SITE-2 guard in
`figrecipe.py` stays authoritative for the old-direct reference mount UNTIL
SAC-manager sign-off calls the thinning — see legacy.py. Thinning the guard
is a SAC-manager call, not this move.

WHY IT WRAPS THE URLCONF INSTEAD OF IMPORTING VIEWS ONE BY ONE
--------------------------------------------------------------
The leaf exposes a COMPLETE urlconf (`app_name = "figrecipe"`, editor +
workspace + nested API routes). Naming views individually here would mean a
route added upstream silently does not exist under hub. So the patterns are
taken wholesale and each callback is decorated — a new upstream route is
mounted and gated with zero hub changes.

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
# This module is imported by figrecipe_app/urls/__init__.py, which
# config/urls.py imports to build the ROOT urlconf. A module-scope ImportError
# here therefore does not disable figrecipe — it takes down EVERY URL hub
# serves, including the landing page. Scholar measured exactly this on
# 2026-08-23 (#687): an editable-install skew between scitex-scholar and
# scitex-app 500'd the whole site minutes after merge.
#
# NOT A SILENT FALLBACK (CCT 2768, binding). The failure is logged at ERROR
# with the exception and the routes are omitted, so /apps/figrecipe/* 404s
# fail-closed while the dev-only /apps/figrecipe/old-direct/ reference is
# unaffected. Hub already uses exactly this shape for optional plugin mounts
# (config/urls.py: "Only mounted when the package is importable"). The user
# path is NEVER relit with hub-side views — no app earns its route back
# without a working leaf plugin (RED START, CCT 2806).
try:
    import figrecipe._django.urls as _leaf
except Exception as exc:  # noqa: BLE001 - any import-time failure must be caught
    _leaf = None
    _LEAF_IMPORT_ERROR = exc
else:
    _LEAF_IMPORT_ERROR = None

# CUTOVER (CCT-2784) + OPERATOR ROUTE RULE (CCT 2763/2764) + RED START
# (CCT 2806, binding): the leaf is the DEFAULT at /apps/figrecipe/ and the
# ONLY thing on the user path. The pre-cutover hub-native routes live in
# legacy.py and are served ONLY at /apps/figrecipe/old-direct/ in dev (mount
# + gate in config/urls.py), never in production, and old-direct is deleted
# outright once v1 parity closes. When the leaf is missing or broken,
# urlpatterns is [] exactly as before and /apps/figrecipe/* 404s fail-closed.
# NO alias mount is added here (CCT 2795 lesson from scholar: the /v2/
# compat alias was transitional scaffolding, deleted not kept) — the leaf is
# mounted ONCE at the root; resolve() by path is what matters.


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
                "figrecipe._django.urls now nests an include(); "
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
        "figrecipe's Django app could not be imported, so /apps/figrecipe/ "
        "is NOT mounted. The dev-only "
        "/apps/figrecipe/old-direct/ reference is unaffected. Cause: %r. Check "
        "that the installed figrecipe and its own dependencies agree — "
        "note that editable installs from bind-mounted working trees ignore "
        "hub's pyproject floors entirely.",
        _LEAF_IMPORT_ERROR,
    )
    urlpatterns = []
else:
    # One gated copy, mounted once: the cutover default at "" (=
    # /apps/figrecipe/). No alias mount (CCT 2795 lesson): the leaf's own
    # hosted-compat names (its "" also answers as "figure_editor", its
    # "figrecipe/" subtree preserves the established nested API path) travel
    # inside the single mount, so reverse() stays unambiguous under the one
    # figrecipe-leaf namespace.
    assert _leaf is not None  # else-branch: the import above succeeded
    _gated_patterns = _gated(_leaf.urlpatterns)
    urlpatterns = [
        path(
            "",
            include((_gated_patterns, "figrecipe"), namespace="figrecipe-leaf"),
        ),
    ]

# EOF
