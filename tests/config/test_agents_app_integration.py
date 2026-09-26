"""Permanent Hub integration contract for the optional SAC Agents app.

Agents is a PURE plugin app: the hub mounts the leaf's own urlconf through
the generic plugin mount and lists its tile from the leaf's own manifest.
There is no hub-side wrapper (no ``agents_app`` views/urls/manifest), no
delegation layer, and no per-app gate — the leaf declares
``mount_policy.login_required`` and scopes rows to the requester's identity
itself. This file pins that contract:

- the sibling checkout, dev mounts, listener token, and env templates
  (unchanged infrastructure — runs everywhere);
- thin-hub: no wrapper files, no bespoke mount, no per-app gate names;
- the live mount: /apps/agents/ resolves to the leaf namespace and
  anonymous requests are turned away at the login boundary (leaf
  installed; otherwise skipped with a reason).

Reads are login-only: the hub passes them to the upstream, which scopes
rows to the user's identity. Control stays gated upstream
(``can_control``); the hub's audience gate is generic and covered in
``tests/apps/apps_app/test_plugin_mount_guards.py``.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from django.test import Client

REPO_ROOT = Path(__file__).resolve().parents[2]
OPTIONAL_APPS_PATH = REPO_ROOT / "config/settings/_optional_apps.py"
CONFIG_URLS_PATH = REPO_ROOT / "config/urls.py"
HELPERS_PATH = REPO_ROOT / "apps/workspace/apps_app/views/helpers.py"
AGENTS_WRAPPER_ROOT = REPO_ROOT / "apps/workspace/agents_app"
APP_REGISTRY_PATH = REPO_ROOT / ".scitex-apps.json"
INSTALLER_PATH = REPO_ROOT / "deployment/docker/docker_dev/install_ecosystem.sh"
ENV_EXAMPLES = (
    REPO_ROOT / ".env.example",
    REPO_ROOT / "deployment/docker/envs/.env.example",
)

DEV_STACKS = (
    (
        REPO_ROOT / "deployment/docker/docker_dev/docker-compose.yml",
        "${SCITEX_AGENT_CONTAINER_SOURCE_DIR:-../../../../scitex-agent-container}:"
        "/scitex-agent-container:cached",
    ),
    (
        REPO_ROOT / "deployment/docker/docker-compose.override.yml",
        "${SCITEX_AGENT_CONTAINER_SOURCE_DIR:-../../../scitex-agent-container}:"
        "/scitex-agent-container:cached",
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
    assert "SCITEX_AGENT_CONTAINER_SOURCE_DIR=" in template
    assert "SCITEX_AGENT_CONTAINER_API_TOKEN_FILE_HOST=" in template
    assert "SCITEX_AGENT_CONTAINER_API_TOKEN=" not in template


def test_no_hub_side_agents_wrapper_files() -> None:
    # Thin-hub: the bespoke wrapper is deleted. URL mounting + tiles come
    # from the generic plugin mount (the leaf's own urlconf + manifest).
    # Arrange / Act
    leftovers = sorted(p.name for p in AGENTS_WRAPPER_ROOT.glob("*") if p.is_file()) if AGENTS_WRAPPER_ROOT.exists() else []

    # Assert
    assert leftovers == [], f"hub-side agents wrapper files still present: {leftovers}"
    assert "agents_app" not in CONFIG_URLS_PATH.read_text(encoding="utf-8")
    assert "_fleet_access_allowed" not in HELPERS_PATH.read_text(encoding="utf-8")


def test_root_urlconf_resolves_agents_to_the_leaf_index_when_installed() -> None:
    # Arrange — the leaf package must be installed for its mount to exist.
    pytest.importorskip(
        "scitex_agent_container._django.urls", reason="scitex-agent-container not installed"
    )
    from django.urls import resolve

    # Act
    match = resolve("/apps/agents/")

    # Assert — the generic mount serves the LEAF's own urlconf (its
    # namespace), never a hub delegate.
    assert match.view_name == "scitex_agent_container:index"


def test_anonymous_request_never_reaches_the_agents_mount() -> None:
    # Arrange — the leaf declares mount_policy.login_required, so the
    # generic mount turns anonymous traffic away at the boundary.
    pytest.importorskip(
        "scitex_agent_container._django.urls", reason="scitex-agent-container not installed"
    )
    from django.urls import resolve

    try:
        resolve("/apps/agents/")
    except Exception:
        pytest.skip("agents mount is not in this environment's URLconf")

    # Act
    resp = Client().get("/apps/agents/", follow=False)

    # Assert
    assert resp.status_code == 302
    assert resp.url.startswith("/auth/login/")
