#!/usr/bin/env python3
"""Public A2A discovery must survive an unavailable agent registry."""

from __future__ import annotations

import json
from pathlib import Path

from django.test import RequestFactory

from apps.infra.a2a_app import _card
from apps.infra.a2a_app.views import fleet_well_known


class _UnreadableRegistry:
    def is_dir(self) -> bool:
        return True

    def iterdir(self):
        raise PermissionError("/secret/internal/agents")


class TestFleetRegistryAvailability:
    def test_unreadable_registry_is_a_fail_closed_snapshot(self):
        original = _card._agents_dir
        _card._agents_dir = lambda: _UnreadableRegistry()
        try:
            members, registry = _card.registry_snapshot()
        finally:
            _card._agents_dir = original

        assert members == []
        assert registry == {
            "available": False,
            "ready": False,
            "status": "unreadable",
            "reason": "agent registry is not readable",
        }
        assert "/secret/internal/agents" not in json.dumps(registry)

    def test_public_card_remains_valid_json_when_registry_is_unreadable(self):
        original = _card._agents_dir
        _card._agents_dir = lambda: _UnreadableRegistry()
        try:
            response = fleet_well_known(
                RequestFactory().get(
                    "/.well-known/agent.json",
                    HTTP_HOST="scitex.ai",
                    secure=True,
                )
            )
        finally:
            _card._agents_dir = original

        payload = json.loads(response.content)
        assert response.status_code == 200
        assert payload["x-orochi"]["members"] == []
        assert payload["x-orochi"]["registry"]["available"] is False
        assert payload["x-orochi"]["registry"]["ready"] is False
        assert payload["x-orochi"]["registry"]["status"] == "unreadable"
        assert "/secret/internal/agents" not in response.content.decode()

    def test_missing_registry_is_explicitly_not_configured(self, tmp_path: Path):
        missing = tmp_path / "missing"
        original = _card._agents_dir
        _card._agents_dir = lambda: missing
        try:
            members, registry = _card.registry_snapshot()
        finally:
            _card._agents_dir = original

        assert members == []
        assert registry["available"] is False
        assert registry["ready"] is False
        assert registry["status"] == "not_configured"

    def test_readable_registry_reports_ready(self, tmp_path: Path):
        agent = tmp_path / "worker"
        agent.mkdir()
        (agent / "worker.yaml").write_text("apiVersion: scitex-agent-container/v3\n")
        original = _card._agents_dir
        _card._agents_dir = lambda: tmp_path
        try:
            members, registry = _card.registry_snapshot()
        finally:
            _card._agents_dir = original

        assert members == ["worker"]
        assert registry == {
            "available": True,
            "ready": True,
            "status": "ready",
            "reason": "",
        }
