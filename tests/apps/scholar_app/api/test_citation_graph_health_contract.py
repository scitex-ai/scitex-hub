"""The Hub health route must consume Scholar's optional capability report."""

import json

from django.test import RequestFactory, override_settings

from apps.workspace.scholar_app.api import citation_graph


def _legacy_service_must_not_start():
    raise AssertionError("Initial page health must not construct a graph backend")


def test_initial_health_reports_unconfigured_without_constructing_backend(monkeypatch):
    # Arrange
    monkeypatch.setattr(
        citation_graph, "get_citation_graph_service", _legacy_service_must_not_start
    )
    request = RequestFactory().get("/apps/scholar/citation-graph/health/")
    # Act
    with override_settings(SCITEX_SCHOLAR_CROSSREF_API_URL=None, CROSSREF_API_URL=None):
        response = citation_graph.health(request)
    # Assert
    assert response.status_code == 200
    payload = json.loads(response.content)
    assert payload["status"] == "unconfigured"
    assert payload["probed"] is False


def test_configured_initial_health_does_not_probe_an_unreachable_endpoint(monkeypatch):
    # Arrange
    monkeypatch.setattr(
        citation_graph, "get_citation_graph_service", _legacy_service_must_not_start
    )
    request = RequestFactory().get("/apps/scholar/citation-graph/health/")
    # Act
    with override_settings(SCITEX_SCHOLAR_CROSSREF_API_URL="http://127.0.0.1:1"):
        response = citation_graph.health(request)
    # Assert
    payload = json.loads(response.content)
    assert (response.status_code, payload["status"], payload["probed"]) == (
        200,
        "configured",
        False,
    )


def test_explicit_health_probe_reports_unavailable_without_internal_error():
    # Arrange
    request = RequestFactory().get("/apps/scholar/citation-graph/health/?probe=1")
    # Act
    with override_settings(SCITEX_SCHOLAR_CROSSREF_API_URL="http://127.0.0.1:1"):
        response = citation_graph.health(request)
    # Assert
    payload = json.loads(response.content)
    assert (response.status_code, payload["status"], payload["probed"]) == (
        200,
        "unavailable",
        True,
    )
    assert "127.0.0.1" not in response.content.decode()
    assert "No module named" not in response.content.decode()


def test_health_keeps_the_get_only_boundary():
    # Arrange
    request = RequestFactory().post("/apps/scholar/citation-graph/health/")
    # Act
    response = citation_graph.health(request)
    # Assert
    assert response.status_code == 405
