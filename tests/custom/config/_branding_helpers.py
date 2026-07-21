# -*- coding: utf-8 -*-
# File: tests/config/_branding_helpers.py
"""Shared helpers for the branding tests.

Underscore-prefixed so pytest does not collect it as a test module. Split out
of a single test_branding.py that outgrew the 512-line cap; the two halves
(test_branding_titles.py / test_branding_favicon.py) both need these.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.template import RequestContext, Template
from django.test import RequestFactory

from config import branding


class FakeRequest:
    """Minimal stand-in for the only attribute the branding code reads."""

    def __init__(self, path: str) -> None:
        self.path = path


def favicon_svg(env: str) -> str:
    """Read the on-disk SVG served as ``env``'s tab icon."""
    return (settings.BASE_DIR / "static" / branding.favicon_for_env(env)).read_text()


def render(source: str, path: str = "/writer/") -> str:
    """Render ``source`` through a REAL RequestContext.

    Unlike calling the template tag directly, this exercises the whole chain --
    tag-library discovery (``{% load branding_tags %}``), the tag itself, the
    context processors, and ``{% static %}`` -- so a template that would blow up
    in production fails here instead.
    """
    request = RequestFactory().get(path)
    # Auth/Session middleware normally set these; RequestFactory does not, and
    # RequestContext runs EVERY configured context processor -- including ones
    # that read request.user / request.session.
    request.user = AnonymousUser()
    request.session = {}
    return Template(source).render(RequestContext(request))
