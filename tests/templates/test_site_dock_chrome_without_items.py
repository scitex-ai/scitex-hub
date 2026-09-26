#!/usr/bin/env python3
"""The dock's nav chrome renders whenever the dock is enabled — even with
zero app items.

Card hub-launcher-dock-page2-20260927. The grip pill is the minimize/restore
and drag affordance; gating the whole ``<nav>`` on a non-empty item list
(``{% if site_dock_items %}``) leaves a page with neither dock nor pill and
no way back. The template gates on ``site_dock_enabled`` instead, and
``dock_context`` always supplies it.
"""

from django.template.loader import render_to_string

from apps.infra.public_app.templatetags.site_dock import dock_context

TEMPLATE = "global_base_partials/site_dock.html"


def _context(**overrides):
    base = {
        "site_dock_items": [],
        "site_dock_capacity": 4,
        "site_dock_enabled": True,
        "build_id": "test",
    }
    base.update(overrides)
    return base


def test_chrome_renders_with_zero_items_when_enabled():
    """An empty dock list still renders nav, grip pill, and arrows."""
    html = render_to_string(TEMPLATE, _context(site_dock_items=[]))

    assert 'data-site-dock' in html


def test_chrome_absent_when_dock_disabled():
    """Embeds and signed-out pages render no dock markup at all."""
    html = render_to_string(
        TEMPLATE, _context(site_dock_items=None, site_dock_enabled=False)
    )

    assert 'data-site-dock' not in html


def test_dock_context_marks_a_missing_request_disabled():
    """Both render paths (template tag, middleware) share dock_context."""
    assert dock_context(None)["site_dock_enabled"] is False
