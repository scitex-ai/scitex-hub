#!/usr/bin/env python3
"""Hub consumer contract for scitex-ui 0.22's canonical project selector."""

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


def test_writer_header_places_picker_after_identity_before_actions() -> None:
    text = _text(WRITER_HEADER)
    assert text.index("stx-app-header__identity") < text.index("stx-app-header__slot--project-selector") < text.index("stx-app-header__actions")


def test_writer_header_renders_exactly_one_shared_picker() -> None:
    assert _text(WRITER_HEADER).count("{% scitex_project_picker") == 1


def test_writer_has_no_legacy_local_picker_wrapper() -> None:
    assert not OLD_WRAPPER.exists()


def test_writer_entries_do_not_render_a_second_picker() -> None:
    assert all("scitex_project_picker" not in _text(path) and "writer/_project_picker.html" not in _text(path) for path in (WRITER_INDEX, WRITER_PARTIAL))


def test_writer_ancillary_header_uses_the_same_canonical_slot() -> None:
    text = _text(WRITER_APP_BASE)
    assert text.count('writer_app/shared/_app_header.html') == 1


def test_appmaker_real_header_uses_the_same_canonical_slot() -> None:
    text = _text(APPMAKER)
    assert text.index("stx-app-header__identity") < text.index("stx-app-header__slot--project-selector") < text.index("appmaker-actions")


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
