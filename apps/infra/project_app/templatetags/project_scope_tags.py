"""``{% hub_project_provider_meta %}``: advertises the hub's project provider (a host service).

Leaf apps place the SDK project picker themselves; the hub only serves the
projects. Renders nothing while the installed scitex-ui predates the tag.
"""

from __future__ import annotations

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def hub_project_provider_meta(context):
    try:
        from scitex_ui.templatetags.scitex_project_picker import (
            scitex_project_provider_meta,
        )
    except ImportError:
        return ""
    return scitex_project_provider_meta(context)
