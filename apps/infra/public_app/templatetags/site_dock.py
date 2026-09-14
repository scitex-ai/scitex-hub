#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``{% site_dock %}`` — render the site-wide dock for the current request.

Used by ``templates/global_base.html`` on every hub page, and by
``SiteDockMiddleware`` for leaf pages that do not extend the base template.
"""

from django import template

from apps.infra.workspace_app.site_dock import dock_items, should_render_dock

register = template.Library()


def dock_context(request) -> dict:
    """Context for ``global_base_partials/site_dock.html``."""
    if request is None or not should_render_dock(request):
        return {"site_dock_items": None}
    return {"site_dock_items": dock_items(request.path)}


@register.inclusion_tag("global_base_partials/site_dock.html", takes_context=True)
def site_dock(context):
    return dock_context(context.get("request"))
