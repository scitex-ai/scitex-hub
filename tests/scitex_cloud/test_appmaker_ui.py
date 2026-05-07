"""Tests for scitex_cloud.appmaker._ui and _validate.validate_dependencies."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path


class TestUIStepBuilders:
    """UI automation step builders produce correct action dicts."""

    def test_navigate_to(self):
        from scitex_cloud.appmaker import ui

        steps = ui.navigate_to("/apps/writer/")
        assert len(steps) == 1
        assert steps[0]["action"] == "navigate"
        assert steps[0]["url"] == "/apps/writer/"

    def test_click_element(self):
        from scitex_cloud.appmaker import ui

        steps = ui.click_element("#save-btn")
        assert steps[0]["action"] == "click"
        assert steps[0]["selector"] == "#save-btn"

    def test_highlight_with_message(self):
        from scitex_cloud.appmaker import ui

        steps = ui.highlight("#editor", message="Edit here", position="bottom")
        assert steps[0]["action"] == "highlight"
        assert steps[0]["message"] == "Edit here"
        assert steps[0]["position"] == "bottom"

    def test_highlight_minimal(self):
        from scitex_cloud.appmaker import ui

        steps = ui.highlight(".toolbar")
        assert "message" not in steps[0]
        assert "position" not in steps[0]

    def test_scroll_to(self):
        from scitex_cloud.appmaker import ui

        steps = ui.scroll_to("#footer")
        assert steps[0]["action"] == "scroll"
        assert steps[0]["selector"] == "#footer"

    def test_fill_input(self):
        from scitex_cloud.appmaker import ui

        steps = ui.fill_input("#search", "quantum")
        assert steps[0]["action"] == "fill"
        assert steps[0]["value"] == "quantum"

    def test_clear_highlights(self):
        from scitex_cloud.appmaker import ui

        steps = ui.clear_highlights()
        assert steps[0]["action"] == "clear"

    def test_switch_sidebar(self):
        from scitex_cloud.appmaker import ui

        steps = ui.switch_sidebar("scholar")
        assert steps[0]["action"] == "click"
        assert 'data-module="scholar"' in steps[0]["selector"]

    def test_send_notification(self):
        from scitex_cloud.appmaker import ui

        steps = ui.send_notification("Done!")
        assert steps[0]["action"] == "highlight"
        assert steps[0]["message"] == "Done!"


class TestUIChain:
    """chain() combines multiple step sequences."""

    def test_chain_combines(self):
        from scitex_cloud.appmaker import ui

        combined = ui.chain(
            ui.navigate_to("/apps/writer/"),
            ui.click_element("#edit"),
            ui.highlight("#panel", message="Look here"),
        )
        assert len(combined) == 3
        assert combined[0]["action"] == "navigate"
        assert combined[1]["action"] == "click"
        assert combined[2]["action"] == "highlight"

    def test_chain_empty(self):
        from scitex_cloud.appmaker import ui

        assert ui.chain() == []


class TestUIActionFormat:
    """to_ui_action() produces the tool call format."""

    def test_format(self):
        from scitex_cloud.appmaker import ui

        steps = ui.navigate_to("/apps/writer/")
        action = ui.to_ui_action(steps, delay_ms=500)
        assert action["steps"] == steps
        assert action["delay_ms"] == 500

    def test_default_delay(self):
        from scitex_cloud.appmaker import ui

        action = ui.to_ui_action([])
        assert action["delay_ms"] == 900


class TestValidateDependencies:
    """validate_dependencies() checks manifest dependencies structure."""

    def _write_manifest(self, td, data):
        path = Path(td) / "manifest.json"
        path.write_text(json.dumps(data))
        return td

    def test_valid_deps(self):
        from scitex_cloud.appmaker import validate_dependencies

        with tempfile.TemporaryDirectory() as td:
            self._write_manifest(
                td,
                {
                    "dependencies": {
                        "python": ["numpy"],
                        "system": [],
                        "node": [],
                        "r": [],
                        "other": [],
                    }
                },
            )
            assert validate_dependencies(td) == []

    def test_missing_deps_field(self):
        from scitex_cloud.appmaker import validate_dependencies

        with tempfile.TemporaryDirectory() as td:
            self._write_manifest(td, {"name": "test"})
            errors = validate_dependencies(td)
            assert any("missing 'dependencies'" in e for e in errors)

    def test_invalid_deps_type(self):
        from scitex_cloud.appmaker import validate_dependencies

        with tempfile.TemporaryDirectory() as td:
            self._write_manifest(td, {"dependencies": "not-a-dict"})
            errors = validate_dependencies(td)
            assert any("must be a JSON object" in e for e in errors)

    def test_unknown_dep_type(self):
        from scitex_cloud.appmaker import validate_dependencies

        with tempfile.TemporaryDirectory() as td:
            self._write_manifest(td, {"dependencies": {"julia": ["Flux"]}})
            errors = validate_dependencies(td)
            assert any("unknown dependency type" in e for e in errors)

    def test_deps_not_a_list(self):
        from scitex_cloud.appmaker import validate_dependencies

        with tempfile.TemporaryDirectory() as td:
            self._write_manifest(td, {"dependencies": {"python": "numpy"}})
            errors = validate_dependencies(td)
            assert any("must be a list" in e for e in errors)

    def test_deps_items_not_strings(self):
        from scitex_cloud.appmaker import validate_dependencies

        with tempfile.TemporaryDirectory() as td:
            self._write_manifest(td, {"dependencies": {"python": [123]}})
            errors = validate_dependencies(td)
            assert any("must be strings" in e for e in errors)

    def test_no_manifest_no_error(self):
        from scitex_cloud.appmaker import validate_dependencies

        with tempfile.TemporaryDirectory() as td:
            assert validate_dependencies(td) == []


# EOF
