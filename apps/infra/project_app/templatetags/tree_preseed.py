"""
Template tag to pre-seed sessionStorage with file tree data.

Usage in templates:
    {% load tree_preseed %}
    {% tree_preseed_script current_project %}

This generates an inline <script> that writes tree data to sessionStorage,
so the file tree renders instantly without waiting for an API call.
"""

import json
import logging

from django import template
from django.utils.safestring import mark_safe

logger = logging.getLogger(__name__)

register = template.Library()


@register.simple_tag(takes_context=True)
def tree_preseed_script(context, project):
    """Generate inline script to pre-seed sessionStorage with tree data."""
    if not project:
        return ""

    # Writer's page and the shell's worktree pane both call this; a second copy
    # doubled the HTML (~300 KB each) and rebuilt the tree.
    request = context.get("request")
    seeded = getattr(request, "_tree_preseeded", None) if request is not None else None
    if seeded is not None and project.pk in seeded:
        return ""
    if request is not None:
        if seeded is None:
            seeded = set()
            request._tree_preseeded = seeded
        seeded.add(project.pk)

    try:
        from apps.infra.project_app.services.file_tree_builder import (
            build_project_file_tree,
        )

        result = build_project_file_tree(project)
        if not result:
            return ""

        username = project.owner.username
        slug = project.slug
        cache_key = f"scitex-tree-{username}-{slug}"

        # Double-encode: the value stored in sessionStorage is a JSON string,
        # so we JSON-encode the result, then embed that string in JS
        json_str = json.dumps(result, separators=(",", ":"))
        # Escape for safe embedding in <script>
        json_str_escaped = json_str.replace("</", "<\\/").replace("<!--", "<\\!--")

        return mark_safe(
            f'<script>(function(){{var k="{cache_key}";'
            f"if(!sessionStorage.getItem(k))"
            f"{{try{{sessionStorage.setItem(k,{json.dumps(json_str_escaped)});}}"
            f"catch(e){{}}}}"
            f"}})()</script>"
        )
    except Exception as e:
        logger.debug("Tree preseed failed: %s", e)
        return ""
