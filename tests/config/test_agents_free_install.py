"""Authenticated, per-user installation and backend scoping for Agents."""

from __future__ import annotations

from importlib.util import find_spec

import pytest
from django.contrib.auth.models import User

from apps.workspace.apps_app.management.commands.seed_apps import ensure_builtin_modules
from apps.workspace.apps_app.models import AppsModule, ModuleInstallation

try:
    AGENTS_DJANGO_AVAILABLE = find_spec("scitex_agent_container._django") is not None
except ModuleNotFoundError:
    AGENTS_DJANGO_AVAILABLE = False

requires_agents_django = pytest.mark.skipif(
    not AGENTS_DJANGO_AVAILABLE,
    reason="scitex_agent_container._django is not installed",
)


class _Fleet:
    base_url = "http://listener"

    def list_all(self):
        return [
            {"name": "alice-local", "host": "local"},
            {"name": "bob-remote", "host": "bob.example"},
        ]

    def read_statuses(self, names):
        return {name: {} for name in names}


@pytest.mark.django_db
@requires_agents_django
def test_plain_user_can_install_agents_and_only_their_row_changes(client):
    alice = User.objects.create_user("agents-alice")
    bob = User.objects.create_user("agents-bob")
    ensure_builtin_modules()
    agents = AppsModule.objects.get(module_name="agents")

    client.force_login(alice)
    response = client.post("/apps/store/api/agents/install/")

    assert response.status_code == 200
    assert ModuleInstallation.objects.filter(user=alice, module=agents).exists()
    assert not ModuleInstallation.objects.filter(user=bob, module=agents).exists()


@pytest.mark.django_db
def test_anonymous_user_cannot_install_agents(client):
    ensure_builtin_modules()

    response = client.post("/apps/store/api/agents/install/")

    assert response.status_code == 302
    assert "/auth/login/" in response.url
    assert not ModuleInstallation.objects.filter(module__module_name="agents").exists()


@pytest.mark.django_db
def test_cards_dependency_hold_blocks_install_and_toggle(client):
    user = User.objects.create_user("cards-held-user")
    client.force_login(user)
    ensure_builtin_modules()

    install = client.post("/apps/store/api/todo/install/")
    toggle = client.post("/apps/store/api/todo/toggle/")

    assert (install.status_code, toggle.status_code) == (409, 409)
    assert not ModuleInstallation.objects.filter(
        user=user, module__module_name="todo"
    ).exists()
    launcher = client.get("/")
    assert b"canonical per-tenant store verification" in launcher.content


@pytest.mark.django_db
@requires_agents_django
def test_launcher_routes_uninstalled_agents_to_store_then_installed_agents_to_app(client):
    user = User.objects.create_user("agents-launcher")
    client.force_login(user)
    ensure_builtin_modules()

    before = next(t for t in client.get("/").context["tiles"] if t["name"] == "agents")
    client.post("/apps/store/api/agents/install/")
    after = next(t for t in client.get("/").context["tiles"] if t["name"] == "agents")

    assert (before["is_installed"], before["launch_url"]) == (
        False,
        "/apps/store/agents/",
    )
    assert (after["is_installed"], after["launch_url"]) == (
        True,
        "/apps/agents/",
    )


@pytest.mark.django_db
def test_plain_user_route_reaches_upstream_identity_scope(client, monkeypatch):
    upstream = pytest.importorskip("scitex_agent_container._django.views")
    user = User.objects.create_user("alice")
    client.force_login(user)
    monkeypatch.setattr(upstream.RemoteFleet, "from_environment", lambda: _Fleet())

    response = client.get("/apps/agents/api/fleet")

    assert response.status_code == 200
    payload = response.json()
    assert payload["identity"] == "alice"
    assert [row["name"] for row in payload["agents"]] == ["alice-local"]
    assert "bob-remote" not in response.content.decode()


@pytest.mark.django_db
def test_staff_route_still_reaches_upstream(client, monkeypatch):
    upstream = pytest.importorskip("scitex_agent_container._django.views")
    staff = User.objects.create_user("agents-staff", is_staff=True)
    client.force_login(staff)
    monkeypatch.setattr(upstream.RemoteFleet, "from_environment", lambda: _Fleet())

    response = client.get("/apps/agents/api/fleet")

    assert response.status_code == 200
    assert response.json()["identity"] == "agents-staff"


def test_agents_manifest_is_public_free_install_and_cards_names_blocker():
    from apps.infra.workspace_app import registry

    agents = registry._manifest_to_module_config(
        registry._load_manifest(registry._APPS_ROOT / "workspace/agents_app/manifest.json")
    )
    cards = registry._manifest_to_module_config(
        registry._load_manifest(registry._APPS_ROOT / "workspace/todo_app/manifest.json")
    )

    assert agents.visibility == "public"
    assert agents.builtin is False and agents.availability == "available"
    assert cards.availability == "coming_soon"
    assert "scitex-cards 0.53.1" in cards.availability_reason
    assert "per-tenant store" in cards.availability_reason
