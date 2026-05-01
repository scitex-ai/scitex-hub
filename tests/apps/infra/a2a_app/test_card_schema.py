#!/usr/bin/env python3
"""Validate AgentCard projections produced by `apps.infra.a2a_app._card`.

Two layers of validation:

1. **Structural** — required A2A v1 top-level fields are present and
   correctly typed. This is the first line of defense and runs without
   any external schema.
2. **Schema** — the bundled official Google A2A JSON Schema (committed
   alongside this test) is loaded and applied to every projected card
   via ``jsonschema``. If the bundled schema is missing or malformed,
   the schema test is skipped (the structural test still runs).

To refresh the schema:
   curl -fsSL <url> -o tests/fixtures/a2a_schema/agent_card.schema.json

The structural test is the contract that fails the build on projection
regressions; the schema test catches everything else.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from apps.infra.a2a_app import _card

REQUIRED_TOP_FIELDS = {
    "name": str,
    "description": str,
    "url": str,
    "version": str,
    "capabilities": dict,
    "defaultInputModes": list,
    "defaultOutputModes": list,
    "skills": list,
}

BASE_URL = "https://a2a.scitex.ai"

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "fixtures"
    / "a2a_schema"
    / "agent_card.schema.json"
)


def _all_agent_names() -> list[str]:
    """List every agent the projector knows about."""
    names = list(_card.list_agents())
    if not names:
        pytest.skip(
            "no agents available — SCITEX_OROCHI_AGENTS_DIR not mounted in this env"
        )
    return names


@pytest.fixture(scope="module")
def agent_names() -> list[str]:
    return _all_agent_names()


@pytest.fixture(scope="module")
def schema() -> dict | None:
    if not SCHEMA_PATH.exists():
        return None
    try:
        return json.loads(SCHEMA_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return None


class TestAgentCardStructural:
    """Hand-rolled structural checks — no external schema needed."""

    def test_every_agent_card_loads(self, agent_names: list[str]) -> None:
        for name in agent_names:
            card = _card.load_card(name, base_url=BASE_URL)
            assert card is not None, f"load_card returned None for {name!r}"

    def test_required_top_fields(self, agent_names: list[str]) -> None:
        for name in agent_names:
            card = _card.load_card(name, base_url=BASE_URL)
            for field, ftype in REQUIRED_TOP_FIELDS.items():
                assert field in card, f"{name}: missing required field {field!r}"
                assert isinstance(card[field], ftype), (
                    f"{name}: field {field!r} expected {ftype.__name__}, "
                    f"got {type(card[field]).__name__}"
                )

    def test_url_points_at_a2a_subdomain(self, agent_names: list[str]) -> None:
        for name in agent_names:
            card = _card.load_card(name, base_url=BASE_URL)
            url = card["url"]
            assert url.startswith(f"{BASE_URL}/v1/agents/"), (
                f"{name}: card.url should be under {BASE_URL}/v1/agents/, got {url!r}"
            )
            assert url.endswith(f"/{name}"), (
                f"{name}: card.url should end with /{name}, got {url!r}"
            )

    def test_skills_have_required_fields(self, agent_names: list[str]) -> None:
        for name in agent_names:
            card = _card.load_card(name, base_url=BASE_URL)
            skills = card["skills"]
            for skill in skills:
                for sub in ("id", "name", "description"):
                    assert sub in skill, f"{name}: skill missing {sub!r}: {skill!r}"

    def test_x_orochi_extension_present(self, agent_names: list[str]) -> None:
        """Every card must carry the x-orochi extension."""
        for name in agent_names:
            card = _card.load_card(name, base_url=BASE_URL)
            assert "x-orochi" in card, f"{name}: missing x-orochi extension"
            xo = card["x-orochi"]
            assert isinstance(xo, dict)
            for sub in ("identity_url", "runtime_url", "role_class"):
                assert sub in xo, f"{name}: x-orochi missing {sub!r}"


class TestAgentCardJsonSchema:
    """Optional layer — runs only if the bundled schema is present."""

    def test_schema_is_loadable(self, schema: dict | None) -> None:
        if schema is None:
            pytest.skip(
                f"bundled A2A schema not found at {SCHEMA_PATH}; "
                "run the refresh command in this file's docstring"
            )
        assert isinstance(schema, dict)
        assert "$schema" in schema or "type" in schema or "properties" in schema

    def test_every_card_validates(
        self, agent_names: list[str], schema: dict | None
    ) -> None:
        if schema is None:
            pytest.skip("bundled A2A schema not present")
        jsonschema = pytest.importorskip("jsonschema")
        validator = jsonschema.Draft202012Validator(schema)
        for name in agent_names:
            card = _card.load_card(name, base_url=BASE_URL)
            errors = sorted(validator.iter_errors(card), key=lambda e: e.path)
            assert not errors, f"{name}: A2A schema violations: " + "; ".join(
                f"{list(e.path)}: {e.message}" for e in errors[:3]
            )


if __name__ == "__main__":
    import os

    pytest.main([__file__, "-v", os.environ.get("PYTEST_OPTS", "")])
