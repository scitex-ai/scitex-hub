"""Read public gallery presentation metadata; never import or probe leaf apps."""

import json
import re
from pathlib import Path

from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()
MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "static/public_app/images/landing-v2/product-captures-eleven-apps-20261103.json"
)
CATEGORY_LABELS = {
    "platform": _("Platform"),
    "infrastructure": _("Infrastructure"),
    "research": _("Research"),
    "publication": _("Publication"),
}


def capture_tab_groups(manifest=MANIFEST):
    """Project only public labels, versions and stable screenshot indices."""
    path = Path(manifest)
    if path.stat().st_size > 131072:
        raise ValueError("Landing capture manifest exceeds its bounded size")
    captures = json.loads(path.read_text())["captures"]
    ordered = sorted(captures, key=lambda c: c["gallery_slide_index"])
    if [c["gallery_slide_index"] for c in ordered] != list(range(len(ordered))):
        raise ValueError("Landing screenshot indices must be contiguous and unique")
    if len({c["app"] for c in ordered}) != len(ordered):
        raise ValueError("Landing screenshot apps must be unique")
    groups = []
    by_key = {}
    for c in ordered:
        key = c["gallery_category"]
        if key not in CATEGORY_LABELS or not re.fullmatch(r"[a-z][a-z0-9-]*", c["app"]):
            raise ValueError("Invalid landing screenshot category or app identity")
        if not re.fullmatch(r"[0-9][0-9A-Za-z.+-]*", c["capture_version"]):
            raise ValueError("Invalid captured screenshot version")
        if key not in by_key:
            group = {"key": key, "label": CATEGORY_LABELS[key], "apps": []}
            groups.append(group)
            by_key[key] = group
        by_key[key]["apps"].append(
            {
                "key": c["app"],
                "label": c["gallery_label"],
                "index": c["gallery_slide_index"],
                "version": c["capture_version"],
                "version_basis": c["capture_version_basis"],
                "version_note": c["capture_version_note"],
            }
        )
    return groups


@register.simple_tag
def landing_capture_tabs():
    return capture_tab_groups()
