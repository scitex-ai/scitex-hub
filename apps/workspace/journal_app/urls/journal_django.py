#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/workspace/journal_app/urls/journal_django.py
"""Mount `scitex_agentic_journal._django` as the journal UI, BEHIND HUB'S AUTH.

Mirrors `scholar_app/urls/scholar_django.py`: the leaf's views carry no
decorator of their own, so the urlconf is taken wholesale and every
callback is wrapped in `login_required`. A nested `include()` is refused
(decorating the outer entry would leave inner routes ungated).

The guarded import shape is load-bearing too: this module is imported
while building the ROOT urlconf, so an import-time failure must omit the
journal routes (fail-closed 404) rather than take down the whole site.
"""

from __future__ import annotations

import logging

from django.contrib.auth.decorators import login_required
from django.urls import URLPattern, URLResolver, include, path

logger = logging.getLogger(__name__)

try:
    import scitex_agentic_journal._django.urls as _leaf
except Exception as exc:  # noqa: BLE001 - any import-time failure must be caught
    _leaf = None
    _LEAF_IMPORT_ERROR = exc
else:
    _LEAF_IMPORT_ERROR = None


class ImproperlyGatedURLConf(RuntimeError):
    """The upstream urlconf has a shape this module cannot authenticate."""


def _gated(patterns):
    """Return `patterns` with login_required applied to every view."""
    gated = []
    for entry in patterns:
        if isinstance(entry, URLResolver):
            raise ImproperlyGatedURLConf(
                "scitex_agentic_journal._django.urls now nests an include(); "
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
        "scitex-agentic-journal's Django app could not be imported, so "
        "/apps/journal/ is NOT mounted. Cause: %r.",
        _LEAF_IMPORT_ERROR,
    )
    urlpatterns = []
else:
    assert _leaf is not None  # else-branch: the import above succeeded
    _gated_patterns = _gated(_leaf.urlpatterns)
    urlpatterns = [
        path(
            "",
            include((_gated_patterns, "journal"), namespace="journal-leaf"),
        ),
    ]

# EOF
