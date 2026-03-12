#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/figrecipe_app/views/api/bundles/pltz_property.py - Property update endpoints."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.test import RequestFactory

from apps.workspace.figrecipe_app.views.api.bundles.pltz_property import (
    batch_update_pltz_properties,
    update_pltz_property,
)


@pytest.fixture
def user():
    """Create a mock authenticated user (no DB needed)."""
    u = Mock()
    u.is_authenticated = True
    u.id = 1
    u.username = "testuser"
    return u


@pytest.fixture
def request_factory():
    """Django request factory."""
    return RequestFactory()


@pytest.fixture
def mock_pltz_bundle(tmp_path):
    """Create a mock pltz bundle directory structure."""
    bundle_path = tmp_path / "test.pltz"
    bundle_path.mkdir()

    # Create spec.yaml
    spec_file = bundle_path / "spec.yaml"
    spec_file.write_text(
        "axes:\n  - labels:\n      title: Test Plot\n      xlabel: X\n      ylabel: Y\n"
    )

    # Create style.yaml
    style_file = bundle_path / "style.yaml"
    style_file.write_text("dpi: 300\nsize:\n  width_mm: 80\n  height_mm: 60\n")

    return bundle_path


class TestUpdatePltzProperty:
    """Test single property update endpoint."""

    def test_update_property_success(self, request_factory, user, mock_pltz_bundle):
        """Test successful property update."""
        request = request_factory.post(
            "/vis/api/bundles/pltz/update-property/",
            data=json.dumps(
                {
                    "path": str(mock_pltz_bundle),
                    "property_path": "style.dpi",
                    "value": 600,
                }
            ),
            content_type="application/json",
        )
        request.user = user

        with patch(
            "apps.workspace.figrecipe_app.views.api.bundles.pltz_property._get_pltz_class"
        ) as mock_get_pltz:
            mock_pltz_instance = MagicMock()
            mock_pltz_instance.spec = {"axes": [{"labels": {"title": "Test"}}]}
            mock_pltz_instance.style = {"dpi": 300}
            mock_get_pltz.return_value.return_value = mock_pltz_instance

            response = update_pltz_property(request)

            assert response.status_code == 200
            data = json.loads(response.content)
            assert data["success"] is True
            assert data["property_path"] == "style.dpi"
            assert data["value"] == 600
            assert mock_pltz_instance.save.called

    def test_update_nested_property(self, request_factory, user, mock_pltz_bundle):
        """Test updating nested property path."""
        request = request_factory.post(
            "/vis/api/bundles/pltz/update-property/",
            data=json.dumps(
                {
                    "path": str(mock_pltz_bundle),
                    "property_path": "spec.axes.0.labels.title",
                    "value": "New Title",
                }
            ),
            content_type="application/json",
        )
        request.user = user

        with patch(
            "apps.workspace.figrecipe_app.views.api.bundles.pltz_property._get_pltz_class"
        ) as mock_get_pltz:
            mock_pltz_instance = MagicMock()
            mock_pltz_instance.spec = {"axes": [{"labels": {"title": "Old"}}]}
            mock_pltz_instance.style = {}
            mock_get_pltz.return_value.return_value = mock_pltz_instance

            response = update_pltz_property(request)

            assert response.status_code == 200
            data = json.loads(response.content)
            assert data["success"] is True
            assert data["value"] == "New Title"

    def test_update_property_invalid_root(self, request_factory, user):
        """Test error when property path doesn't start with spec or style."""
        request = request_factory.post(
            "/vis/api/bundles/pltz/update-property/",
            data=json.dumps(
                {
                    "path": "/tmp/test.pltz",
                    "property_path": "invalid.property",
                    "value": 123,
                }
            ),
            content_type="application/json",
        )
        request.user = user

        response = update_pltz_property(request)

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "must start with 'spec' or 'style'" in data["error"]

    def test_update_property_missing_params(self, request_factory, user):
        """Test error when required parameters are missing."""
        request = request_factory.post(
            "/vis/api/bundles/pltz/update-property/",
            data=json.dumps({"path": "/tmp/test.pltz"}),
            content_type="application/json",
        )
        request.user = user

        response = update_pltz_property(request)

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "property_path are required" in data["error"]

    def test_update_property_invalid_json(self, request_factory, user):
        """Test error with invalid JSON."""
        request = request_factory.post(
            "/vis/api/bundles/pltz/update-property/",
            data="invalid json",
            content_type="application/json",
        )
        request.user = user

        response = update_pltz_property(request)

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "Invalid JSON" in data["error"]


class TestBatchUpdatePltzProperties:
    """Test batch property update endpoint."""

    def test_batch_update_success(self, request_factory, user, mock_pltz_bundle):
        """Test successful batch update."""
        request = request_factory.post(
            "/vis/api/bundles/pltz/batch-update-properties/",
            data=json.dumps(
                {
                    "path": str(mock_pltz_bundle),
                    "updates": [
                        {"property_path": "style.dpi", "value": 600},
                        {
                            "property_path": "spec.axes.0.labels.title",
                            "value": "New Title",
                        },
                    ],
                }
            ),
            content_type="application/json",
        )
        request.user = user

        with patch(
            "apps.workspace.figrecipe_app.views.api.bundles.pltz_property._get_pltz_class"
        ) as mock_get_pltz:
            mock_pltz_instance = MagicMock()
            mock_pltz_instance.spec = {"axes": [{"labels": {"title": "Old"}}]}
            mock_pltz_instance.style = {"dpi": 300}
            mock_get_pltz.return_value.return_value = mock_pltz_instance

            response = batch_update_pltz_properties(request)

            assert response.status_code == 200
            data = json.loads(response.content)
            assert data["success"] is True
            assert data["updated_count"] == 2
            assert "spec" in data
            assert "style" in data

    def test_batch_update_partial_success(
        self, request_factory, user, mock_pltz_bundle
    ):
        """Test batch update with some invalid properties (should skip invalid)."""
        request = request_factory.post(
            "/vis/api/bundles/pltz/batch-update-properties/",
            data=json.dumps(
                {
                    "path": str(mock_pltz_bundle),
                    "updates": [
                        {"property_path": "style.dpi", "value": 600},
                        {"property_path": "invalid.path", "value": 123},  # Invalid root
                        {"property_path": "spec.axes.0.labels.title", "value": "New"},
                    ],
                }
            ),
            content_type="application/json",
        )
        request.user = user

        with patch(
            "apps.workspace.figrecipe_app.views.api.bundles.pltz_property._get_pltz_class"
        ) as mock_get_pltz:
            mock_pltz_instance = MagicMock()
            mock_pltz_instance.spec = {"axes": [{"labels": {"title": "Old"}}]}
            mock_pltz_instance.style = {"dpi": 300}
            mock_get_pltz.return_value.return_value = mock_pltz_instance

            response = batch_update_pltz_properties(request)

            # Should succeed but skip invalid property
            assert response.status_code == 200
            data = json.loads(response.content)
            assert data["success"] is True
            # Should process all 3 updates (including skipped invalid one)
            assert data["updated_count"] == 3

    def test_batch_update_missing_params(self, request_factory, user):
        """Test error when required parameters are missing."""
        request = request_factory.post(
            "/vis/api/bundles/pltz/batch-update-properties/",
            data=json.dumps({"path": "/tmp/test.pltz"}),
            content_type="application/json",
        )
        request.user = user

        response = batch_update_pltz_properties(request)

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "updates are required" in data["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
