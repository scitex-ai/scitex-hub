#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A rendered standalone-app page must offer the visitor a way OUT.

CARD: hub-adopt-assert-has-route-away-in-hub-suite-20260906 (deferred 09-06,
claimed 09-10 by scitex-hub-deepseek). Split out of
ui-standalone-shell-has-no-way-back-to-launcher-20260819, whose FIX is already
merged and live (measured 2026-09-06T03:36Z). This file is the remaining hub
half: the GUARD.

WHY THE SIBLING TEST IS NOT THIS TEST. ``tests/config/
test_mounted_app_launcher_context_processor.py`` asserts the PROCESSOR: given a
request path, does the function return a launcher dict. That is a true
statement about a function, and it stays true when the user-facing property
breaks -- an unregistered processor, a template that stopped rendering the
slot, a shell upgrade that renamed the key, a media query that hides it below
768px. Every one of those leaves that test green.

WHAT IS ASSERTED HERE is the property itself, on the RENDERED page: does the
HTML a visitor receives contain at least one route away. ``scitex_ui.testing
.assert_has_route_away`` implements exactly that predicate, and it lives in the
consumer's suite because this is the only place the app's own content has
rendered and is therefore visible as a string. That distinction is why scitex-ui
shipped the helper rather than warning from inside the shell: from
``shell_context()`` the content does not exist yet, there is nothing to count.

MEASURED, and the reason a naive version of this guard would be worthless:
``/apps/cards/`` is navigable through its OWN anchors, so a guard keyed on
"was ``launcher`` supplied" would cry on a working page -- hub rejected that
predicate when scitex-ui first proposed it, and it is preserved here by
asserting routes, never the context value. A page that has its own way out
passes; a dead end fails.

ANONYMOUS CANNOT SEE THE PROPERTY ON /apps/cards/. Signed in is therefore the
primary mode here, which is also one of the three gaps the closing measurement
of 2026-09-06 left open (*/editor-v2/, */viewer-v2/, signed-in). The board is
login-gated by ``apps.workspace.todo_app.middleware
.TodoBoardTenancyMiddleware``, which answers an anonymous HTML navigation with
``302 /auth/login/?next=/apps/cards/``; asserting routes away on THAT response
would measure the login page, which has links, and would pass on the exact day
the board ships a dead end. So the test follows the redirect only to prove it
did not happen.
"""

from __future__ import annotations

from importlib.util import find_spec

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory
from django.urls import resolve
from django.urls.exceptions import Resolver404
from scitex_ui.testing import assert_has_route_away

from config.context_processors import mounted_app_launcher

#: The pages ``mounted_app_launcher`` claims -- i.e. the pages that render
#: through scitex-ui's ``standalone_shell.html`` rather than hub's own
#: full-workspace shell. Written down here as a CLAIM so the two structural
#: tests below can check it against its two sources of truth (the processor's
#: own gate, and the URLconf) instead of trusting this list.
STANDALONE_SHELL_PATHS = (
    "/apps/cards/",
    "/apps/storage/",
    "/apps/writer/editor-v2/",
    "/apps/writer/viewer-v2/",
)

#: Pages whose mount hub GUARANTEES for its own suite, because hub declares the
#: upstream package in every dependency group. A guard that quietly skipped
#: these would be a green check over an unrun suite -- the failure mode
#: ``pyproject.toml``'s scitex-cards entry documents (2026-08-09: the whole
#: tenancy suite reported "8 skipped", exit 0). Everything NOT listed here is
#: mounted conditionally (``_scitex_storage_installed()``) and skips with a
#: reason instead of failing.
MOUNTED_BY_CONTRACT = ("/apps/cards/",)

#: A page the processor does NOT claim: hub's own full-workspace shell, which
#: already carries the sidebar's own navigation. Used as the negative control --
#: without it, "the processor claims every path I listed" would also be true of
#: a processor that claims EVERY path.
PATH_THE_PROCESSOR_MUST_NOT_CLAIM = "/apps/scholar/"


def _mount_absent_reason(path: str) -> str | None:
    """Why this page cannot be rendered here, or ``None`` when it can.

    Returns a reason rather than a bool because a skip has to name the package
    that is missing: "skipped" with no cause is how a mount silently disappears
    from the suite, which is the defect class this whole file exists to stop.

    RESOLVING IS NOT ENOUGH, and this is measured rather than defensive. A path
    whose app is NOT mounted still resolves in hub, through the project
    catch-all at the end of ``config/urls.py``::

        /apps/storage/   route='<str:username>/<slug:slug>/'
                         name='detail' ns='project_app'
                         func=apps.infra.project_app.views.projects.detail.project_detail

    i.e. username="apps", slug="storage". A guard that accepted ``resolve()``
    would therefore fetch a PROJECT DETAIL page, assert routes away on it, and
    report the Storage shell as guarded -- green, over a page the Storage
    defect is not on. So the mount is confirmed by the ROUTE the path actually
    matched: a real mount's route IS the requested prefix.
    """
    requested = path.strip("/") + "/"
    try:
        match = resolve(path)
    except Resolver404:
        return (
            f"{path} is not mounted in this install -- its upstream package is "
            "not importable, so config/urls.py never registers it "
            "(scitex_storage for /apps/storage/). Nothing to guard here; the "
            "page does not exist."
        )
    route = match.route or ""
    if not route.startswith(requested):
        return (
            f"{path} is not mounted in this install: it resolves through the "
            f"catch-all route {route!r} (namespace {match.namespace!r}, "
            f"view {match.func.__module__}), not through its own app. Asserting "
            "routes away on THAT page would report this shell as guarded while "
            "measuring a different page entirely."
        )
    return None


# ---------------------------------------------------------------------------
# Structural half -- no database, no client. These run everywhere, and they are
# what makes the rendered half's skips meaningful.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", STANDALONE_SHELL_PATHS)
def test_every_guarded_path_is_one_the_launcher_processor_claims(path: str) -> None:
    # Arrange: the processor is the thing that supplies the way out for these
    # pages, so a path in this file that the processor does not claim would be
    # guarded against a mechanism that is not present.
    request = RequestFactory().get(path)
    # Act
    context = mounted_app_launcher(request)
    # Assert
    assert "launcher" in context, (
        f"{path} is guarded by this file but config.context_processors"
        ".mounted_app_launcher does not supply a launcher for it. Either the "
        "processor's gate changed (update this list) or this path never "
        "rendered through the standalone shell (remove it)."
    )


def test_the_negative_control_is_still_negative() -> None:
    # Arrange: a page the processor must NOT claim -- hub's own workspace shell
    # has the sidebar's navigation, so a second back-link would be redundant.
    request = RequestFactory().get(PATH_THE_PROCESSOR_MUST_NOT_CLAIM)
    # Act
    context = mounted_app_launcher(request)
    # Assert: if this ever starts claiming every path, the test above stops
    # discriminating and would pass for a path that is not a standalone page.
    assert context == {}


def test_an_unmounted_app_path_is_not_mistaken_for_a_mounted_page() -> None:
    # Arrange: hub's URLconf ends in a project catch-all, so a path whose app is
    # NOT mounted still RESOLVES -- measured on this branch, /apps/storage/
    # (scitex_storage absent) resolves to `<str:username>/<slug:slug>/` with
    # username="apps", slug="storage", i.e. a project detail page. A guard that
    # trusted resolve() would assert routes away on that page and call this
    # shell guarded.
    path = "/apps/not-a-mounted-app/"
    # Act
    reason = _mount_absent_reason(path)
    # Assert
    assert reason is not None, (
        f"{path} mounted no app, yet _mount_absent_reason accepted it. The "
        "guard would then render whatever the catch-all served and report a "
        "different page as this shell."
    )


def test_a_mounted_page_is_recognised_as_mounted() -> None:
    # Arrange: the other direction, so the fix for the catch-all above cannot be
    # "always report absent" -- which would skip every page and pass.
    path = "/apps/cards/"
    # Act
    reason = _mount_absent_reason(path)
    # Assert
    assert reason is None, f"{path} is mounted, but the guard skipped it: {reason}"


def test_the_pages_hub_guarantees_are_actually_mounted() -> None:
    # Arrange
    unresolvable = [path for path in MOUNTED_BY_CONTRACT if _mount_absent_reason(path)]
    # Assert: these are pages hub declares the dependency for, so "not mounted"
    # is a defect, not an environment difference -- and the rendered tests below
    # would otherwise skip them and report green over nothing.
    assert unresolvable == [], (
        f"hub declares the upstream package for {unresolvable} but the mount "
        "does not resolve. The rendered-page guard would skip these pages, "
        "which reads as a pass while guarding nothing."
    )


def test_the_guarded_install_can_import_the_assertion_it_uses() -> None:
    # Arrange: a test-only import IS a contract on the installed package. The
    # import at the top of this file is unguarded on purpose (a
    # pytest.importorskip here would turn a floor violation into a skip, which
    # is the one answer a floor must never give), so the floor itself is
    # asserted in tests/config/test_shell_pane_contract_floor.py.
    # Act
    installed = find_spec("scitex_ui")
    # Assert
    assert installed is not None, (
        "scitex_ui is not importable, so tests/config"
        "/test_rendered_pages_have_a_route_away.py cannot run at all. It is "
        "declared in every dependency group precisely so this suite runs "
        "instead of vanishing (PS-210)."
    )


def test_the_instrument_separates_a_dead_end_from_a_route_away() -> None:
    # Arrange: the positive control for the assertion this file is built on.
    # Without it, "the page has a route away" is unverifiable from the outside
    # -- a helper that returned success unconditionally would read identically.
    dead_end = "<html><body><p>no anchors at all</p></body></html>"
    with_one_way_out = (
        '<html><body><a href="#top">top</a>'
        '<a href="/apps/store/">Back to Store</a></body></html>'
    )
    # Act / Assert -- the dead end must FAIL, and the failure must say why.
    with pytest.raises(AssertionError, match="no route away"):
        assert_has_route_away(dead_end, current_path="/apps/storage/")
    # Act
    report = assert_has_route_away(with_one_way_out, current_path="/apps/storage/")
    # Assert: the in-page fragment is rejected, the launcher anchor is not.
    assert report.routes == ("/apps/store/",)


# ---------------------------------------------------------------------------
# Rendered half -- the card's ask. Needs the database because the pages are
# login-gated; skips by name where a mount is genuinely absent.
# ---------------------------------------------------------------------------


def _signed_in_user():
    """An ordinary signed-in user for the rendered-page assertions.

    Created through the user model rather than with ``force_login`` on a
    fabricated object: the pages under guard read ``request.user`` through the
    tenancy middleware, which needs a real row.
    """
    return get_user_model().objects.create_user(
        username="route-away-guard",
        password="route-away-guard",  # pragma: allowlist secret
    )


@pytest.mark.django_db
@pytest.mark.parametrize("path", STANDALONE_SHELL_PATHS)
def test_a_signed_in_visitor_receives_a_way_out(client: Client, path: str) -> None:
    # Arrange
    reason = _mount_absent_reason(path)
    if reason is not None:
        pytest.skip(reason)
    client.force_login(_signed_in_user())
    # Act -- follow=True so a redirect is measured where it LANDS.
    response = client.get(path, follow=True)
    landed_on = response.request["PATH_INFO"]
    # Assert: the page must be the app's own page. A guard that accepted a
    # redirect would measure the login page, whose links say nothing about
    # whether the board is escapable.
    assert "/auth/login" not in landed_on, (
        f"{path} redirected a SIGNED-IN visitor to {landed_on}. The rendered "
        "page then says nothing about this app's own navigation, which is the "
        "only thing this guard is about."
    )
    assert response.status_code == 200, (
        f"{path} answered {response.status_code} for a signed-in visitor, so "
        "there is no rendered page to inspect."
    )
    # Assert -- the property, not a proxy for it.
    assert_has_route_away(response.content.decode(), current_path=landed_on)
