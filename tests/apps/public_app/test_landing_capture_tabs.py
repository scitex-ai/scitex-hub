"""Public capture projection and actual two-level Django markup contract."""

import json
from html.parser import HTMLParser
from pathlib import Path

import pytest
from django.template import Context, Engine
from django.test import override_settings

from apps.infra.public_app.templatetags.landing_capture_tabs import (
    MANIFEST,
    capture_tab_groups,
)

ROOT = Path(__file__).resolve().parents[3]
GALLERY = (
    ROOT
    / "apps/infra/public_app/templates/public_app/landing_partials/landing_app_gallery.html"
)


class Tabs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def test_manifest_drives_four_groups_and_all_eleven_versions_without_private_metadata():
    groups = capture_tab_groups()
    assert [g["key"] for g in groups] == [
        "platform",
        "infrastructure",
        "research",
        "publication",
    ]
    assert [len(g["apps"]) for g in groups] == [2, 3, 4, 2]
    apps = [a for g in groups for a in g["apps"]]
    assert [a["index"] for a in apps] == list(range(11))
    assert (
        apps[6]["version"] == "1.0.0"
        and "No app-version badge" in apps[6]["version_note"]
    )
    assert apps[7]["version"] == "0.44.0" and "0.44.1" in apps[7]["version_note"]
    assert all(
        set(a) == {"key", "label", "index", "version", "version_basis", "version_note"}
        for a in apps
    )
    assert "/scratch/" not in repr(groups) and "privacy_mask_selectors" not in repr(
        groups
    )


def test_actual_django_template_has_two_linked_tab_levels_and_correct_initial_selection():
    engine = Engine(
        libraries={
            "static": "django.templatetags.static",
            "i18n": "django.templatetags.i18n",
            "landing_capture_tabs": "apps.infra.public_app.templatetags.landing_capture_tabs",
        }
    )
    with override_settings(
        STATIC_URL="/static/",
        STORAGES={
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
            }
        },
    ):
        html = engine.from_string(GALLERY.read_text()).render(Context())
    parsed = Tabs()
    parsed.feed(html)
    categories = [a for _, a in parsed.tags if "data-carousel-category-tab" in a]
    apps = [a for _, a in parsed.tags if "data-carousel-dot" in a]
    panels = [a for _, a in parsed.tags if "data-carousel-category-panel" in a]
    ids = {a["id"] for _, a in parsed.tags if "id" in a}
    assert len(categories) == 4 and len(apps) == 11 and len(panels) == 4
    assert all(
        a["aria-controls"] in ids and a["role"] == "tab" for a in categories + apps
    )
    assert [p["data-carousel-category-panel"] for p in panels if "hidden" not in p] == [
        "platform"
    ]
    assert [
        c["data-carousel-category-tab"]
        for c in categories
        if c["aria-selected"] == "true"
    ] == ["platform"]
    assert [a["data-carousel-dot"] for a in apps if a["aria-selected"] == "true"] == [
        "0"
    ]
    assert html.count('class="landing-v2-app-version"') == 11
    assert "v1.0.0" in html and "No app-version badge" in html
    assert "Header/source mismatch" in html


@pytest.mark.parametrize(
    "mutation", ["duplicate-index", "unknown-category", "invalid-version"]
)
def test_invalid_public_presentation_metadata_refuses_instead_of_fabricating_tabs(
    tmp_path, mutation
):
    manifest = json.loads(MANIFEST.read_text())
    row = manifest["captures"][0]
    if mutation == "duplicate-index":
        row["gallery_slide_index"] = manifest["captures"][1]["gallery_slide_index"]
    elif mutation == "unknown-category":
        row["gallery_category"] = "invented-category"
    else:
        row["capture_version"] = "<script>"
    path = tmp_path / "captures.json"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        capture_tab_groups(path)
