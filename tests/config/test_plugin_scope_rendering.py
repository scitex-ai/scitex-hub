"""Installed leaf metadata/templates are consumed by the generic workspace view."""

import json
from types import SimpleNamespace
from unittest import mock

import pytest
from django.apps import apps
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, override_settings
from scitex_sdk.ui.project_scope import ProjectEntry

from apps.infra.workspace_app import scope_meta
from apps.infra.workspace_app.content import render_module_content
from apps.infra.workspace_app.views import workspace_module_content
from apps.workspace.apps_app.services.plugin_apps import plugin_module_config


class SyntheticProjects:
    """Fixture capability: accessible projects depend on this request's identity."""

    def list_projects(self, request):
        names = ("beta",) if request.user.username == "other" else ("alpha",)
        return [ProjectEntry(name, "Synthetic " + name) for name in names]

    def last_visited(self, request):
        return request.session.get("synthetic-project")

    def remember(self, request, project_id):
        request.session["synthetic-project"] = project_id


class SyntheticStorage:
    def __init__(self, root):
        self.root = root

    def project_path(self, project_id, request):
        return self.root / project_id

    def can_write(self, project_id, request):
        return request.user.username != "reader"


@pytest.fixture
def rendering(tmp_path, settings, django_user_model):
    settings.SCITEX_APP_MODE = "hub"
    settings.SCITEX_PROJECT_PROVIDER = __name__ + ".SyntheticProjects"
    settings.SCITEX_PROJECT_STORAGE = SyntheticStorage(tmp_path)
    settings.SCITEX_PROJECT_PROVIDER_URL = "/synthetic/projects/"
    users = {
        name: django_user_model.objects.create_user(name)
        for name in ("owner", "other", "reader")
    }
    for name in ("alpha", "beta"):
        (tmp_path / name).mkdir()
    return tmp_path, users


def _module(tmp_path, mount):
    installed = apps.get_app_config("figrecipe_editor")
    if mount == "/apps/figrecipe":
        config = installed
    else:
        manifest = dict(installed.manifest, url=mount + "/")
        directory = tmp_path / "custom-manifest"
        directory.mkdir()
        (directory / "manifest.json").write_text(json.dumps(manifest))
        config = type(installed)(installed.name, installed.module)
        config.path = str(directory)
    return plugin_module_config(config)


def _request(user, project="alpha", *, shell=True):
    request = RequestFactory().get(
        "/apps/workspace/content/figrecipe/",
        {"project": project},
        headers={"X-Workspace-Shell": "1"} if shell else {},
    )
    request.user = user
    request.session = {}
    return request


def _native_content(request, module):
    # Project presentation cannot authorize the leaf; SDK provider is authority.
    with (
        mock.patch("apps.infra.workspace_app.registry.get_module", return_value=module),
        mock.patch(
            "apps.infra.project_app.services.project_utils.get_current_project",
            return_value=SimpleNamespace(id="untrusted-presentation", name="Untrusted"),
        ),
    ):
        return workspace_module_content(request, "figrecipe")


@pytest.mark.django_db
@pytest.mark.parametrize("mount", ["/apps/figrecipe", "/custom/plot"])
def test_native_workspace_renders_installed_leaf_template_and_trusted_mount(
    rendering, mount
):
    root, users = rendering
    module = _module(root, mount)
    assert (
        module.context_builder == "figrecipe._django.workspace.build_workspace_context"
    )
    assert module.partial_template == "figrecipe/workspace_partial.html"
    request = _request(users["owner"])
    response = _native_content(request, module)
    assert response.status_code == 200
    # A leaf-rendered marker is preserved; bridges must never duplicate it.
    content = scope_meta.inject_scope_meta(response, "figrecipe").content.decode()
    assert content.count('name="stx-app-scope"') == 1
    assert f'data-stx-mount="{mount}"' in content
    assert 'data-project-id="alpha"' in content
    assert 'data-project-name="Synthetic alpha"' in content
    assert 'name="stx-project-provider" content="/synthetic/projects/"' in content
    assert "/static/figrecipe/assets/workspace.js" in content
    assert "Untrusted" not in content and 'data-project-id="beta"' not in content
    assert request.session == {"synthetic-project": "alpha"}


@pytest.mark.django_db
@pytest.mark.parametrize("name,project", [("owner", "alpha"), ("other", "beta")])
def test_module_metadata_resolves_the_current_user_not_a_prior_request(
    rendering, name, project
):
    root, users = rendering
    module = _module(root, "/apps/figrecipe")
    prior = "other" if name == "owner" else "owner"
    prior_project = "beta" if prior == "other" else "alpha"
    assert (
        _native_content(_request(users[prior], prior_project), module).status_code
        == 200
    )
    request = _request(users[name], project)
    response = _native_content(request, module)
    assert response.status_code == 200
    assert f'data-project-id="{project}"'.encode() in response.content
    assert f'data-project-id="{prior_project}"'.encode() not in response.content


@pytest.mark.django_db
@pytest.mark.parametrize("mount", ["/apps/figrecipe", "/custom/plot"])
def test_explicit_inaccessible_project_is_refused_without_fallback(rendering, mount):
    root, users = rendering
    request = _request(users["owner"], "beta")
    request.session["synthetic-project"] = "alpha"
    response = _native_content(request, _module(root, mount))
    assert response.status_code == 404 and response["Cache-Control"] == "no-store"
    assert b"app-mount" not in response.content
    assert request.session == {"synthetic-project": "alpha"}


@pytest.mark.django_db
def test_provider_unavailable_preserves_generic_503_and_no_store(rendering):
    root, users = rendering
    with override_settings(SCITEX_PROJECT_PROVIDER=None):
        response = _native_content(
            _request(users["owner"]), _module(root, "/apps/figrecipe")
        )
    assert response.status_code == 503 and response["Cache-Control"] == "no-store"
    assert response.content == b"This application is temporarily unavailable."


@pytest.mark.django_db
def test_native_workspace_requires_login_and_shell_header(rendering):
    root, users = rendering
    module = _module(root, "/apps/figrecipe")
    anonymous = _request(AnonymousUser())
    response = _native_content(anonymous, module)
    assert response.status_code == 302 and "next=" in response["Location"]
    assert (
        _native_content(_request(users["owner"], shell=False), module).status_code
        == 403
    )
    # The actual SDK error remains 401 at the generic rendering boundary.
    response = render_module_content(anonymous, module, None)
    assert response.status_code == 401 and response["Cache-Control"] == "no-store"
