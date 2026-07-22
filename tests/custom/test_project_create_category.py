#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/custom/test_project_create_category.py

"""Unit tests for ``scitex_hub.project.project_create`` category/app surface.

Covers the operator-12845 publish-flow client tidy:
- ``category`` validates against ``PROJECT_CATEGORIES``.
- ``category="app"`` auto-suffixes the name with ``_app`` (unless already
  present) and sends ``is_app=True`` in the payload.
- ``app_category`` is only valid when ``category="app"``.
- ``app_category`` round-trips through the payload when present.

No mocks, no monkeypatch. ``project_create`` exposes a ``request_fn``
dependency-injection seam: tests pass a small hand-rolled
``_FakeRequester`` that records calls on a real attribute.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest


@dataclass
class _FakeRequester:
    """Hand-rolled stand-in for the HTTP transport.

    Returns a fixed response dict, records each invocation's (method,
    endpoint, data) on ``self.calls``.
    """

    response: dict[str, Any] = field(
        default_factory=lambda: {
            "success": True,
            "project_id": 42,
            "slug": "my-tool-app",
            "url": "/ywatanabe/my-tool-app/",
            "is_app": True,
            "app_category": "",
            "message": 'Project "my-tool_app" created successfully',
        }
    )
    calls: list[tuple[str, str, dict[str, Any] | None]] = field(default_factory=list)

    def __call__(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        auth_required: bool = True,
    ) -> dict[str, Any]:
        self.calls.append((method, endpoint, data))
        return self.response

    @property
    def last_payload(self) -> dict[str, Any]:
        """Last ``data`` payload the production code sent us."""
        return self.calls[-1][2] or {}

    @property
    def called(self) -> bool:
        return bool(self.calls)


def test_project_categories_constant_is_closed_set():
    # Arrange
    from scitex_hub.project import PROJECT_CATEGORIES

    # Act
    actual = tuple(PROJECT_CATEGORIES)

    # Assert
    assert actual == ("project", "app")


def test_invalid_category_raises_value_error():
    # Arrange
    from scitex_hub.project import project_create

    fake = _FakeRequester()
    raised: Exception | None = None

    # Act
    try:
        project_create("my-thing", category="not-a-category", request_fn=fake)
    except ValueError as exc:
        raised = exc

    # Assert
    assert raised is not None and "category must be one of" in str(raised)


def test_invalid_category_does_not_call_server():
    # Arrange
    from scitex_hub.project import project_create

    fake = _FakeRequester()

    # Act
    try:
        project_create("my-thing", category="not-a-category", request_fn=fake)
    except ValueError:
        pass

    # Assert
    assert fake.called is False


def test_default_category_sends_is_app_false():
    # Arrange
    from scitex_hub.project import project_create

    fake = _FakeRequester()

    # Act
    project_create("my-research", request_fn=fake)

    # Assert
    assert fake.last_payload["is_app"] is False


def test_default_category_does_not_apply_app_suffix():
    # Arrange
    from scitex_hub.project import project_create

    fake = _FakeRequester()

    # Act
    project_create("my-research", request_fn=fake)

    # Assert
    assert fake.last_payload["name"] == "my-research"


def test_app_category_sets_is_app_true():
    # Arrange
    from scitex_hub.project import project_create

    fake = _FakeRequester()

    # Act
    project_create("my-tool", category="app", request_fn=fake)

    # Assert
    assert fake.last_payload["is_app"] is True


def test_app_category_appends_app_suffix():
    # Arrange
    from scitex_hub.project import project_create

    fake = _FakeRequester()

    # Act
    project_create("my-tool", category="app", request_fn=fake)

    # Assert
    assert fake.last_payload["name"] == "my-tool_app"


def test_app_category_skips_suffix_when_already_present():
    # Arrange
    from scitex_hub.project import project_create

    fake = _FakeRequester()

    # Act
    project_create("already_app", category="app", request_fn=fake)

    # Assert
    assert fake.last_payload["name"] == "already_app"


def test_app_category_with_app_subcategory_round_trips():
    # Arrange
    from scitex_hub.project import project_create

    fake = _FakeRequester()

    # Act
    project_create("my-tool", category="app", app_category="writing", request_fn=fake)

    # Assert
    assert fake.last_payload["app_category"] == "writing"


def test_project_category_with_app_subcategory_raises():
    # Arrange
    from scitex_hub.project import project_create

    fake = _FakeRequester()
    raised: Exception | None = None

    # Act
    try:
        project_create(
            "my-thing",
            category="project",
            app_category="writing",
            request_fn=fake,
        )
    except ValueError as exc:
        raised = exc

    # Assert
    assert raised is not None and "app_category is only valid" in str(raised)


def test_project_category_with_app_subcategory_does_not_call_server():
    # Arrange
    from scitex_hub.project import project_create

    fake = _FakeRequester()

    # Act
    try:
        project_create(
            "my-thing",
            category="project",
            app_category="writing",
            request_fn=fake,
        )
    except ValueError:
        pass

    # Assert
    assert fake.called is False


def test_app_subcategory_omitted_keeps_payload_without_key():
    # Arrange
    from scitex_hub.project import project_create

    fake = _FakeRequester()

    # Act
    project_create("my-tool", category="app", request_fn=fake)

    # Assert
    assert "app_category" not in fake.last_payload


def test_server_error_propagates_as_runtime_error():
    # Arrange
    from scitex_hub.project import project_create

    failing = _FakeRequester(response={"success": False, "error": "name conflict"})
    raised: Exception | None = None

    # Act
    try:
        project_create("my-tool", category="app", request_fn=failing)
    except RuntimeError as exc:
        raised = exc

    # Assert
    assert raised is not None and "name conflict" in str(raised)


# EOF
