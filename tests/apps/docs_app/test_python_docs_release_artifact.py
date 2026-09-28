"""Release contract for /apps/docs/python/ and its generated Sphinx tree."""

from pathlib import Path

import pytest
from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import resolve

from apps.workspace.docs_app import _sphinx


def test_python_docs_route_serves_real_generated_index(monkeypatch):
    def render_response(_request, _template, context):
        return HttpResponse(context["doc_content"])

    monkeypatch.setattr(_sphinx, "render", render_response)
    match = resolve("/apps/docs/python/")
    response = match.func(RequestFactory().get("/apps/docs/python/"))
    assert response.status_code == 200
    assert b"SciTeX Hub Documentation" in response.content
    assert b"Built with" in response.content


def test_python_docs_generated_asset_route_serves_packaged_css():
    match = resolve("/apps/docs/python/_static/pygments.css")
    response = match.func(
        RequestFactory().get("/apps/docs/python/_static/pygments.css"),
        **match.kwargs,
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "text/css"
    assert b".highlight" in response.content


def test_missing_generated_tree_is_actionable_503(monkeypatch):
    monkeypatch.setattr(_sphinx, "resolve_sphinx_path", lambda _module: None)
    match = resolve("/apps/docs/python/")
    response = match.func(RequestFactory().get("/apps/docs/python/"))
    assert response.status_code == 503
    assert response["Retry-After"] == "300"
    assert b"temporarily unavailable" in response.content
    assert b"/home/" not in response.content


@pytest.mark.parametrize("payload", [b"not html", b"\xff\xfe"])
def test_corrupt_generated_index_is_actionable_503(tmp_path, monkeypatch, payload):
    (tmp_path / "index.html").write_bytes(payload)
    monkeypatch.setattr(_sphinx, "resolve_sphinx_path", lambda _module: tmp_path)
    match = resolve("/apps/docs/python/")
    response = match.func(RequestFactory().get("/apps/docs/python/"))
    assert response.status_code == 503
    assert b"temporarily unavailable" in response.content
    assert str(tmp_path).encode() not in response.content


def test_wheel_configuration_includes_generated_sphinx_tree():
    root = Path(__file__).resolve().parents[3]
    assert '"_sphinx_html/**"' in (root / "pyproject.toml").read_text()


def test_every_landing_demo_documentation_link_targets_python_docs():
    root = Path(__file__).resolve().parents[3]
    template = (root / "apps/infra/public_app/templates/public_app/landing_partials/landing_demos.html").read_text()
    entries = [line for line in template.splitlines() if "module_demo.html" in line]
    linked_entries = [entry for entry in entries if "docs_url=" in entry]
    assert len(linked_entries) == 5
    assert all("docs_url='docs_app:python'" in entry for entry in linked_entries[:4])
    assert "docs_url='public_app:about'" in linked_entries[4]
