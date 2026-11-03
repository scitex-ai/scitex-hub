#!/usr/bin/env python3
"""Hub header ownership plus the retained legacy project-selector contract."""

from __future__ import annotations

import re
from importlib.util import find_spec
from pathlib import Path

import pytest

from tests.tracked_source import TrackedSourceFile, tracked_source_files

REPO = Path(__file__).resolve().parents[2]
WRITER_INDEX = REPO / "apps/workspace/writer_app/templates/writer_app/index.html"
WRITER_PARTIAL = REPO / "apps/workspace/writer_app/templates/writer_app/writer_partial.html"
WRITER_HEADER = REPO / "apps/workspace/writer_app/templates/writer_app/shared/_app_header.html"
WRITER_APP_BASE = REPO / "apps/workspace/writer_app/templates/writer_app/base/app_base.html"
APPMAKER = REPO / "apps/workspace/apps_app/templates/apps_app/appmaker/workspace.html"
OLD_WRAPPER = REPO / "apps/workspace/writer_app/templates/writer/_project_picker.html"


def _text(path: Path | TrackedSourceFile) -> str:
    if isinstance(path, TrackedSourceFile):
        return path.text()
    return path.read_text(encoding="utf-8")


def test_writer_standalone_and_partial_use_one_canonical_header_entry() -> None:
    assert all(_text(path).count('writer_app/shared/_app_header.html') == 1 for path in (WRITER_INDEX, WRITER_PARTIAL))


def test_writer_header_delegates_row_creation_to_the_shared_sdk() -> None:
    text = _text(WRITER_HEADER)
    assert (text.count("<div data-stx-app-header"), "scitex_sdk/ui/js/app/app-header.js" in text,
            "stx-app-header__identity" in text, "stx-app-header__actions" in text) == (1, True, False, False)


def test_writer_header_delegates_one_picker_and_slot_placement_to_the_leaf() -> None:
    text = _text(WRITER_HEADER)
    assert (text.count('{% include "writer/_project_picker.html" %}'),
            text.count("writer/js/header-picker.js"), "{% scitex_project_picker" in text) == (1, 1, False)


def test_writer_has_no_legacy_local_picker_wrapper() -> None:
    assert not OLD_WRAPPER.exists()


def test_writer_entries_do_not_render_a_second_picker() -> None:
    assert all("scitex_project_picker" not in _text(path) and "writer/_project_picker.html" not in _text(path) for path in (WRITER_INDEX, WRITER_PARTIAL))


def test_writer_ancillary_header_uses_the_same_canonical_slot() -> None:
    text = _text(WRITER_APP_BASE)
    assert text.count('writer_app/shared/_app_header.html') == 1


def test_appmaker_real_header_uses_the_same_canonical_slot() -> None:
    text = _text(APPMAKER)
    assert 'data-stx-app-header data-app-title="{{ app_label }}"' in text
    assert 'class="appmaker-head stx-app-header"' not in text
    assert text.count("{% scitex_project_picker") == 1
    assert text.index("data-stx-app-header") < text.index("{% scitex_project_picker") < text.index("appmaker-actions")


def test_hub_templates_use_only_the_canonical_picker_tag() -> None:
    templates = tracked_source_files(REPO, ("apps/**/templates/**/*.html",))
    offenders = [path.path for path in templates if "project-picker.js" in _text(path)]
    assert offenders == []


def test_installed_022_picker_loads_canonical_entry() -> None:
    if find_spec("scitex_ui") is None:
        pytest.skip("scitex-ui is not installed in this test environment")
    import scitex_ui

    template = Path(scitex_ui.__file__).parent / "templates/scitex_ui/_project_picker.html"
    assert "scitex_ui/js/app/project-selector.js" in _text(template)


def test_responsive_contract_is_inherited_from_scitex_ui() -> None:
    if find_spec("scitex_ui") is None:
        pytest.skip("scitex-ui is not installed in this test environment")
    import scitex_ui

    css = Path(scitex_ui.__file__).parent / "static/scitex_ui/css/app/project-selector.css"
    text = re.sub(r"/\*.*?\*/", "", _text(css), flags=re.S)
    phone = text[text.index("@media (max-width: 600px)") :]
    assert all(contract in phone for contract in ("width: 100%", "order: 0", "height: 44px", "min-height: 44px", "max-height:"))


def test_writer_header_render_keeps_one_sdk_mount_and_one_leaf_picker():
    from html.parser import HTMLParser
    from django.template.loader import render_to_string
    from django.test import override_settings

    class Elements(HTMLParser):
        def __init__(self):
            super().__init__()
            self.attributes = []

        def handle_starttag(self, _tag, attrs):
            self.attributes.append(dict(attrs))

    # Arrange: the public provider URL SPI is sufficient for fragment rendering.
    with override_settings(SCITEX_PROJECT_PROVIDER="", SCITEX_PROJECT_PROVIDER_URL="/owned/projects/"):
        # Act
        html = render_to_string("writer_app/shared/_app_header.html", {
            "writer_label": "SciTeX Writer", "writer_version": "owned-version",
        })
    elements = Elements()
    elements.feed(html)
    mounts = [a for a in elements.attributes if "data-stx-app-header" in a]
    pickers = [a for a in elements.attributes if "data-stx-project-picker" in a]
    # Assert
    assert (len(mounts), len(pickers), mounts[0].get("data-app-version"),
            html.count("writer/js/header-picker.js"),
            "scitex_sdk/ui/js/app/app-header.js?v=" in html,
            "scitex_sdk/ui/css/app/app-header.css?v=" in html) == (1, 1, "owned-version", 1, True, True)
