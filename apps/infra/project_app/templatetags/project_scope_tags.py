"""``{% hub_project_picker "<app>" current_project %}``: the SDK picker, fed by the hub.

Scope comes from the leaf app's manifest (the SDK's single source of truth), so
a user-scope app renders nothing. Renders nothing too while the installed
scitex-ui predates the picker tag.
"""

from __future__ import annotations

from django import template
from django.urls import reverse

from apps.infra.project_app.services.project_scope import project_key

register = template.Library()


def picker_scope(app_name: str):
    """The leaf package manifest's scope, else the hub wrapper manifest's."""
    import json

    from django.conf import settings

    from apps.infra.workspace_app.scope_meta import _scope_for

    leaf_scope = _scope_for(app_name)
    if leaf_scope:
        return leaf_scope
    wrapper = settings.BASE_DIR / "apps" / "workspace" / f"{app_name}_app" / "manifest.json"
    try:
        return json.loads(wrapper.read_text("utf-8")).get("scope")
    except (OSError, ValueError):
        return None


@register.simple_tag(takes_context=True)
def hub_project_picker(context, app_name, current_project=None, scope=None):
    request = context.get("request")
    if request is None or not request.user.is_authenticated:
        return ""
    try:
        from scitex_ui.templatetags.scitex_project_picker import scitex_project_picker
    except ImportError:
        return ""
    return scitex_project_picker(
        context,
        provider_url=reverse("api_project_scope"),
        scope=scope if scope is not None else (picker_scope(app_name) or "user"),
        current=project_key(current_project) if current_project else "",
    )
