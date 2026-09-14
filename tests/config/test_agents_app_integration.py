"""Permanent Hub integration contract for the optional SAC Agents app."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory

from apps.workspace.agents_app import views

REPO_ROOT = Path(__file__).resolve().parents[2]
OPTIONAL_APPS_PATH = REPO_ROOT / "config/settings/_optional_apps.py"
REGISTRY_PATH = REPO_ROOT / "apps/infra/workspace_app/registry.py"
MANIFEST_PATH = REPO_ROOT / "apps/workspace/agents_app/manifest.json"
APP_REGISTRY_PATH = REPO_ROOT / ".scitex-apps.json"
INSTALLER_PATH = REPO_ROOT / "deployment/docker/docker_dev/install_ecosystem.sh"
ENV_EXAMPLES = (
    REPO_ROOT / ".env.example",
    REPO_ROOT / "deployment/docker/envs/.env.example",
)

DEV_STACKS = (
    (
        REPO_ROOT / "deployment/docker/docker_dev/docker-compose.yml",
        "../../../../scitex-agent-container:/scitex-agent-container:cached",
    ),
    (
        REPO_ROOT / "deployment/docker/docker-compose.override.yml",
        "../../../scitex-agent-container:/scitex-agent-container:cached",
    ),
)
PYTHON_SERVICES = ("django", "celery_worker", "celery_beat")
TOKEN_MOUNT = (
    "${SCITEX_AGENT_CONTAINER_API_TOKEN_FILE_HOST:-/dev/null}:"
    "/run/secrets/sac-listen-token:ro"
)
UPSTREAM_APPCONFIG = "scitex_agent_container._django.apps.AgentContainerDashboardConfig"


def _load_optional_apps_module():
    spec = importlib.util.spec_from_file_location(
        "_agents_optional_apps_under_test", OPTIONAL_APPS_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_agents_is_a_declared_sibling_with_the_gui_extra() -> None:
    registry = json.loads(APP_REGISTRY_PATH.read_text(encoding="utf-8"))
    app = next(
        item for item in registry["apps"] if item["name"] == "scitex-agent-container"
    )

    assert app == {
        "name": "scitex-agent-container",
        "source": "sibling",
        "git_url": "https://github.com/scitex-ai/scitex-agent-container.git",
        "git_ref": "develop",
        "pip_package": "scitex-agent-container",
    }
    assert (
        'try_editable_install "/scitex-agent-container" '
        '"scitex-agent-container" "[gui]"'
    ) in INSTALLER_PATH.read_text(encoding="utf-8")


@pytest.mark.parametrize(("compose_path", "source_mount"), DEV_STACKS)
def test_every_dev_python_service_mounts_agents_source(
    compose_path: Path, source_mount: str
) -> None:
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))

    missing = [
        service
        for service in PYTHON_SERVICES
        if source_mount not in compose["services"][service]["volumes"]
    ]

    assert missing == [], f"SAC source is not mounted in {compose_path}: {missing}"


@pytest.mark.parametrize(("compose_path", "_source_mount"), DEV_STACKS)
def test_django_gets_the_sac_listener_contract(
    compose_path: Path, _source_mount: str
) -> None:
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    django = compose["services"]["django"]
    environment = django["environment"]
    if isinstance(environment, list):
        environment = dict(item.split("=", 1) for item in environment)

    assert TOKEN_MOUNT in django["volumes"]
    assert environment["SCITEX_AGENT_CONTAINER_API_URL"].endswith(
        "http://host.docker.internal:7878}"
    )
    assert (
        environment["SCITEX_AGENT_CONTAINER_API_TOKEN_FILE"]
        == "/run/secrets/sac-listen-token"
    )


def test_optional_app_registration_uses_the_published_sac_appconfig(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    optional_apps = _load_optional_apps_module()
    monkeypatch.setattr(
        optional_apps,
        "_installed",
        lambda path: (
            SimpleNamespace() if path == "scitex_agent_container._django.apps" else None
        ),
    )

    assert optional_apps.optional_upstream_apps() == [UPSTREAM_APPCONFIG]


@pytest.mark.parametrize("env_example", ENV_EXAMPLES)
def test_env_templates_document_listener_without_embedding_its_bearer(
    env_example: Path,
) -> None:
    template = env_example.read_text(encoding="utf-8")

    assert "SCITEX_AGENT_CONTAINER_API_URL=http://host.docker.internal:7878" in template
    assert "SCITEX_AGENT_CONTAINER_API_TOKEN_FILE_HOST=" in template
    assert "SCITEX_AGENT_CONTAINER_API_TOKEN=" not in template


def test_launcher_manifest_targets_the_mounted_agents_route() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["name"] == "agents"
    assert manifest["url"] == "/apps/agents/"
    assert manifest["show_in_launcher"] is True
    assert manifest["availability"] == "available"
    assert manifest["renders_ui"] is False
    assert "workspace/agents_app/manifest.json" in REGISTRY_PATH.read_text(
        encoding="utf-8"
    )


def test_anonymous_request_never_reaches_upstream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = RequestFactory().get("/apps/agents/")
    request.user = AnonymousUser()

    monkeypatch.setattr(
        views,
        "_delegate",
        lambda *_args, **_kwargs: pytest.fail("anonymous request reached SAC"),
    )
    # Keep this unit test on the decorator boundary. Django's resolve_url()
    # otherwise imports the entire Hub URLconf before deciding this literal is
    # already a URL, pulling unrelated optional Scholar/browser state into a
    # test that never reaches an Agents view.
    monkeypatch.setattr(
        "django.contrib.auth.decorators.resolve_url", lambda _value: "/auth/login/"
    )
    monkeypatch.setattr(
        "django.contrib.auth.views.resolve_url", lambda _value: "/auth/login/"
    )

    response = views.index(request)

    assert response.status_code == 302
    assert response.url.startswith("/auth/login/")


@pytest.mark.parametrize(
    ("view", "path", "expected_name", "kwargs"),
    (
        (views.index, "/apps/agents/", "index", {}),
        (views.fleet_api, "/apps/agents/api/fleet", "fleet_api", {}),
        (views.healthz, "/apps/agents/healthz", "healthz", {}),
        (views.detail, "/apps/agents/worker/", "detail", {"name": "worker"}),
        (
            views.lifecycle_action,
            "/apps/agents/worker/action",
            "lifecycle_action",
            {"name": "worker"},
        ),
    ),
)
def test_authenticated_routes_delegate_to_the_upstream_contract(
    monkeypatch: pytest.MonkeyPatch, view, path: str, expected_name: str, kwargs: dict
) -> None:
    request = RequestFactory().get(path)
    request.user = SimpleNamespace(is_authenticated=True)
    calls = []

    def fake_delegate(view_name, delegated_request, *args, **delegated_kwargs):
        calls.append((view_name, delegated_request, args, delegated_kwargs))
        return HttpResponse("ok")

    monkeypatch.setattr(views, "_delegate", fake_delegate)

    response = view(request, **kwargs)

    assert response.status_code == 200
    assert calls == [(expected_name, request, (), kwargs)]
