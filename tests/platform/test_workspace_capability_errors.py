"""Workspace embedding must retain the leaf's SDK authorization boundary."""

from types import SimpleNamespace

import pytest
from django.http import HttpResponse
from django.test import RequestFactory
from scitex_sdk.host import AccessError, CapabilityUnavailable

from apps.infra.workspace_app import content


def module(builder, mount="/custom/leaf/"):
    return SimpleNamespace(
        build_context=builder,
        get_url=lambda: mount,
        partial_template="synthetic_leaf/workspace.html",
    )


@pytest.mark.parametrize("mount,expected", [("/custom/leaf/", "/custom/leaf"), ("/", "")])
def test_authorized_context_receives_the_trusted_mount(monkeypatch, mount, expected):
    request = RequestFactory().get("/workspace/content/synthetic/")
    project = object()
    calls = []

    def build(actual_request, actual_project):
        assert actual_request is request
        assert actual_project is project
        return {"stx_mount": "/untrusted", "leaf_content": "authorized"}

    def render(actual_request, template, context):
        calls.append((actual_request, template, context))
        return HttpResponse("authorized leaf")

    monkeypatch.setattr(content, "render", render)
    response = content.render_module_content(request, module(build, mount), project)
    assert response.status_code == 200
    assert calls == [
        (request, "synthetic_leaf/workspace.html", {"stx_mount": expected, "leaf_content": "authorized"})
    ]


@pytest.mark.parametrize(
    "error,expected_status,expected_body",
    [
        (AccessError("private identity", 401), 401, b"Project access unavailable."),
        (AccessError("private project", 404), 404, b"Project access unavailable."),
        (AccessError("write denied", 403), 403, b"Project access unavailable."),
        (AccessError("invalid request", 400), 400, b"Project access unavailable."),
        (AccessError("invalid status", 999), 403, b"Project access unavailable."),
        (AccessError("invalid boolean", True), 403, b"Project access unavailable."),
        (CapabilityUnavailable("private provider detail"), 503, b"This application is temporarily unavailable."),
    ],
)
def test_denied_context_never_renders_private_leaf_content(monkeypatch, error, expected_status, expected_body):
    def build(request, project):
        raise error

    def forbidden_render(*args, **kwargs):
        pytest.fail("A refused capability must never render a leaf template")

    monkeypatch.setattr(content, "render", forbidden_render)
    response = content.render_module_content(RequestFactory().get("/workspace/"), module(build), None)
    assert response.status_code == expected_status
    assert response.content == expected_body
    assert response["Cache-Control"] == "no-store"


def test_unrelated_leaf_bugs_propagate():
    def build(request, project):
        raise RuntimeError("leaf bug")

    with pytest.raises(RuntimeError, match="leaf bug"):
        content.render_module_content(RequestFactory().get("/workspace/"), module(build), None)
