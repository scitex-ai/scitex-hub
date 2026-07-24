#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub-side security wrapper for the scitex-storage GUI plugin.

SECURITY (card sec-working-dir-passthrough-family, SITE 4)
----------------------------------------------------------
Upstream ``scitex_storage._django.views.index`` reads ``?path=`` and runs
a recursive ``scan()`` over it with NO auth, NO ownership check and NO
containment — its own module docstring states ``?path= lets the caller
point the scan anywhere``. Mounted raw, that was live, UNAUTHENTICATED
recursive enumeration of ANY host directory (other tenants' workspaces,
/home, SECRET/): child names, sizes, file counts.

This wrapper mounts in place of the raw upstream urls (see config/urls.py):
  * ``@login_required`` — no anonymous access.
  * ``?path=`` is containment-validated against the requester's own data
    jail via ``validate_path_in_user_jail`` (component-wise
    ``Path.relative_to``, NOT a string prefix). A path outside the jail is
    rejected with an explicit 403 — fail closed, no scan, no silent
    fallback to a safe default.

``JailScopedScanView`` takes the downstream package view as a constructor
argument (dependency injection), so the guard is exercised with a
hand-rolled fake in tests without running a real ``fd`` scan. It reuses the
SAME upstream view for the happy path (so the real-data scan and the hub
template override keep working) and the SAME upstream ``healthz`` probe.

IMPORT SAFETY (optional upstream)
---------------------------------
``scitex_storage`` is an OPTIONAL upstream package — the hub mounts this
wrapper only when ``_scitex_storage_installed()`` (see ``config/urls.py``),
exactly like writer/figrecipe are conditionally imported. So this module
must NOT hard-fail at import when the package is absent (a module-level
``from scitex_storage... import`` aborts test COLLECTION with
``ModuleNotFoundError``). Both upstream symbols are therefore imported
LAZILY, inside the call that needs them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden


def _rejected(requested_path: str) -> HttpResponseForbidden:
    """403 — the requested path is outside the caller's own jail."""
    return HttpResponseForbidden(
        "SciTeX Storage: that path is outside your workspace. You can only "
        "scan directories inside your own project data."
    )


def _raw_index(request):
    """Lazily import + call the upstream storage scan view.

    Imported inside the call so this module stays import-safe when the
    optional ``scitex_storage`` package is absent (the mount is gated on
    ``_scitex_storage_installed()`` upstream, so this only ever runs when
    the package IS present).
    """
    from scitex_storage._django.views import index as _upstream_index

    return _upstream_index(request)


def healthz(request):
    """Lazy delegate to the upstream storage ``healthz`` probe.

    Kept as a module-level name so ``storage_app/urls.py`` can route
    ``views.healthz`` without importing the optional package at import time.
    """
    from scitex_storage._django.views import healthz as _upstream_healthz

    return _upstream_healthz(request)


class JailScopedScanView:
    """Delegate to a storage scan view only for paths inside the user jail.

    ``downstream(request) -> HttpResponse`` is injected so the containment
    guard is testable without a real filesystem scan. It defaults to the
    lazily-resolved upstream scan view (:func:`_raw_index`), so constructing
    this object never imports the optional ``scitex_storage`` package.
    """

    def __init__(self, downstream: Optional[Callable] = None):
        self.downstream = downstream or _raw_index

    def __call__(self, request):
        from apps.infra.project_app.services.filesystem.permissions import (
            validate_path_in_user_jail,
        )

        raw_path = request.GET.get("path")
        if raw_path and not validate_path_in_user_jail(
            request.user, Path(raw_path)
        ):
            return _rejected(raw_path)
        return self.downstream(request)


_scan_view = JailScopedScanView()


@login_required
def index(request):
    """Auth + jail-scoped delegate to the upstream storage scan view."""
    return _scan_view(request)


# EOF
