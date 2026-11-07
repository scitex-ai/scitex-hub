#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub emits the Alt+I element inspector exactly once per document.

Operator 2026-10-19 (card hub-element-inspector-double-invocation-20261019,
measured by scitex-stats): Alt+I created TWO #element-inspector-overlay
elements on hub pages. Root cause: two hub-side emissions landed in the same
document — the global_body_scripts.html DEBUG vite include plus the
ElementInspectorMiddleware injection (whose skip-check only recognizes
`js/utils/element-inspector.js` URLs, not the vite entry) — and neither copy
was evaluation-proof, so two instances registered two keydown listeners.

Fix contract pinned here: the middleware is the single hub emission path
(the template carries no copy), and the middleware still suppresses itself
when the shell already provides a copy.

No mocks for the emission logic itself (the gate is monkeypatched True so
the test does not depend on DEBUG/staff state). DB-free: RequestFactory +
render_to_string, one assertion per test.
"""

import re

import scitex_ui.middleware as inspector_middleware
import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.test import RequestFactory

PARTIAL = "global_base_partials/global_body_scripts.html"

SCRIPT_REF = re.compile(r"element-inspector[^\"']*\.(js|ts)")


def _render_chrome(settings) -> str:
    # DEBUG True: the pre-fix template emitted its vite copy only under DEBUG.
    # Force the dev-server vite path (not the manifest path) so the test
    # exercises the same emission a dev page serves: the loader URL carries
    # the `element-inspector.ts` entry path.
    settings.DEBUG = True
    settings.VITE_USE_BUILD = False
    # Wrapped in a minimal document: the middleware injects before </body>,
    # exactly as on a served page.
    partial = render_to_string(PARTIAL, {"DEBUG": True})
    return f"<html><head></head><body>{partial}</body></html>"


def _inject(html: str) -> str:
    request = RequestFactory().get("/apps/stats/")
    request.user = AnonymousUser()
    response = HttpResponse(html, content_type="text/html; charset=utf-8")
    middleware = inspector_middleware.ElementInspectorMiddleware(lambda req: response)
    middleware._maybe_inject(request, response)
    return response.content.decode()


@pytest.fixture
def gate_on(monkeypatch):
    monkeypatch.setattr(inspector_middleware, "element_inspector_enabled", lambda request: True)


def test_chrome_template_carries_no_inspector_copy(settings):
    # Arrange + Act
    html = _render_chrome(settings)

    # Assert — the middleware is the single hub emission path.
    assert SCRIPT_REF.findall(html) == []


def test_middleware_is_the_single_hub_emission(settings, gate_on):
    # Arrange
    html = _render_chrome(settings)

    # Act
    final = _inject(html)

    # Assert — exactly one inspector script in the served document.
    assert len(SCRIPT_REF.findall(final)) == 1


def test_middleware_still_skips_when_shell_provides_its_copy(gate_on):
    # Arrange — an SDK-shell page already carrying the inspector.
    html = (
        "<html><head><title>Leaf</title></head><body>"
        '<script src="/static/scitex_sdk/ui/js/utils/element-inspector.js" defer></script>'
        "</body></html>"
    )

    # Act
    final = _inject(html)

    # Assert — middleware adds nothing; the shell copy stays the only one.
    assert len(SCRIPT_REF.findall(final)) == 1
    assert final == html
