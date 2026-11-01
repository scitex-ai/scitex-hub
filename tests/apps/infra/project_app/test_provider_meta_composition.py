"""Host adapter and leaf tag emit one contextual SDK provider authority."""
from types import SimpleNamespace
from django.template import Context, Engine
from django.test import RequestFactory, override_settings
import pytest


class ScopedHost:
    def list_projects(self, request):
        return []

    def last_visited(self, request):
        return None

    def remember(self, request, project_id):
        raise ValueError("none")

    def current_scope(self, request):
        return None

    def remember_scope(self, request, selection):
        raise ValueError("none")

    def project_provider_url(self, request, base_url):
        return base_url + "?app=" + request.path_info.split("/")[2]


def composition(tmp_path):
    (tmp_path / "leaf.html").write_text("{% load scitex_project_picker %}{% scitex_project_provider_meta %}")
    engine = Engine(dirs=[tmp_path], libraries={
        "project_scope_tags": "apps.infra.project_app.templatetags.project_scope_tags",
        "scitex_project_picker": "scitex_sdk.ui.templatetags.scitex_project_picker",
    })
    return engine.from_string('{% load project_scope_tags %}<head>{% hub_project_provider_meta %}</head><body>{% include "leaf.html" %}</body>')


def request_for(app):
    request = RequestFactory().get(f"/apps/{app}/")
    request.user = SimpleNamespace(is_authenticated=True)
    return request


def test_host_and_leaf_share_one_contextual_scoped_authority(tmp_path):
    # Arrange
    template = composition(tmp_path)
    context = Context({"request": request_for("figrecipe")})
    # Act
    with override_settings(SCITEX_PROJECT_PROVIDER=f"{__name__}.ScopedHost",
                           SCITEX_PROJECT_PROVIDER_URL="/api/project/scope/"):
        rendered = template.render(context)
    # Assert
    assert (rendered.count('name="stx-project-provider"') == 1
            and 'content="/api/project/scope/?app=figrecipe" data-scoped-protocol="true"' in rendered)


def test_reused_context_emits_authority_for_each_new_document(tmp_path):
    # Arrange
    template = composition(tmp_path)
    context = Context({"request": request_for("figrecipe")})
    # Act
    with override_settings(SCITEX_PROJECT_PROVIDER=f"{__name__}.ScopedHost",
                           SCITEX_PROJECT_PROVIDER_URL="/api/project/scope/"):
        first, second = template.render(context), template.render(context)
    # Assert
    assert first.count('name="stx-project-provider"') == second.count('name="stx-project-provider"') == 1


def test_conflicting_context_is_refused_in_one_document(tmp_path):
    # Arrange
    engine = composition(tmp_path).engine
    template = engine.from_string('{% load scitex_project_picker %}{% scitex_project_provider_meta %}{% with request=other %}{% scitex_project_provider_meta %}{% endwith %}')
    context = Context({"request": request_for("figrecipe"), "other": request_for("writer")})
    # Act / Assert
    with override_settings(SCITEX_PROJECT_PROVIDER=f"{__name__}.ScopedHost",
                           SCITEX_PROJECT_PROVIDER_URL="/api/project/scope/"):
        with pytest.raises(ValueError, match="Conflicting project provider"):
            template.render(context)
