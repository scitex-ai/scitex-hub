"""The library page's "Import BibTeX (.bib)" button posts to a real route.

The view existed but no URL pattern pointed at it, so every import was a 404.

CUTOVER (CCT 2760) + OPERATOR ROUTE RULE (CCT 2763/2764): /apps/scholar/
serves the Scholar LEAF now. The hub-native import endpoint lives ONLY at
/apps/scholar/old-direct/ in dev (dev-gated, never in production) — the
parity/fallback reference while v1 parity is open.
"""

from __future__ import annotations

import importlib

from django.test.utils import override_settings
from django.urls import resolve
from django.urls.exceptions import Resolver404

from apps.workspace.scholar_app.views.library.bibtex_import import api_import_bibtex

OLD_DIRECT_PATH = "apps/scholar/old-direct/api/import/bibtex/"
USER_PATH = "/apps/scholar/api/import/bibtex/"


def _resolve_old_direct(path: str):
    """Resolve ``path`` against the REAL root urlconf with the dev gate on.

    The suite runs prod-shaped (DEBUG False), so old-direct is absent
    unless the explicit flag opts in — exactly the rule. Same reload
    pattern as test_scholar_route_flip_parity.py. The restore reload runs
    AFTER the override exits (outer finally), so it rebuilds the urlconf
    prod-shaped; restoring inside the `with` would re-mount old-direct and
    leak the gate into the suite's ambient urlconf.
    """
    import config.urls as root_urlconf
    from django.urls.resolvers import RoutePattern, URLResolver

    try:
        with override_settings(SCHOLAR_OLD_DIRECT_ENABLED=True):
            reloaded = importlib.reload(root_urlconf)
            resolver = URLResolver(RoutePattern(""), reloaded.urlpatterns)
            return resolver.resolve(path)
    finally:
        importlib.reload(root_urlconf)


def test_import_bibtex_endpoint_resolves_to_the_import_view():
    # Arrange — the cutover home of the hub-native import endpoint.
    # Act
    match = _resolve_old_direct(OLD_DIRECT_PATH)
    # Assert — still the real view itself, not a redirect or a stub.
    assert match.func is api_import_bibtex


def test_import_bibtex_endpoint_is_off_the_user_path():
    # CCT 2763/2764: no hub-side scholar view answers on the user path
    # anymore. Unmatched /apps/* paths fall through to the pre-existing
    # project_app catch-all; the assertion is that no SCHOLAR view answers,
    # not a bare 404.
    # Act
    try:
        match = resolve(USER_PATH)
    except Resolver404:
        return
    # Assert
    assert match.namespaces != ["scholar_app"], (
        f"{USER_PATH} is served by hub-side scholar under the legacy namespace."
    )
    assert not match.func.__module__.startswith("apps.workspace.scholar_app"), (
        f"{USER_PATH} is served by hub-side scholar {match.func}."
    )
