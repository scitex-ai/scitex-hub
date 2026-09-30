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
def test_cards_staff_gate_holds_at_the_mount_not_the_store(client):
    """Cards is installable from the store; the board itself stays staff-gated.

    History: the pre-plugin ``todo_app`` wrapper held Cards back with a
    ``coming_soon`` availability (store 409 on install AND toggle). The
    generic plugin mount (082a0c51f "mount agents/cards/storage exclusively
    through the generic plugin mount") deleted that wrapper, and migration
    0023 removed its stale catalog row. The hold now lives where the data
    lives: the leaf's own manifest declares a staff ``audience``, enforced
    for every signed-in non-staff user by ``PluginMountGuardMiddleware``.
    """
    user = User.objects.create_user("cards-held-user")
    staff = User.objects.create_user("cards-staff-user", is_staff=True)
    ensure_builtin_modules()

    # The retired per-app wrapper stays gone: no registry entry recreates it.
    assert not AppsModule.objects.filter(module_name="todo").exists()
    cards = AppsModule.objects.get(module_name="scitex-cards")
    assert cards.visibility == "public"

    # The store no longer holds Cards back: install and toggle succeed.
    client.force_login(user)
    install = client.post("/apps/store/api/scitex-cards/install/")
    toggle = client.post("/apps/store/api/scitex-cards/toggle/")
    assert (install.status_code, toggle.status_code) == (200, 200)
    assert ModuleInstallation.objects.filter(
        user=user, module__module_name="scitex-cards"
    ).exists()

    # The board itself holds: a plain user gets the generic restricted page
    # (no board data), while staff pass the audience gate. Navigations send
    # ``Accept: text/html`` (the guard's only generic nav-vs-fetch signal).
    board = client.get("/apps/cards/", HTTP_ACCEPT="text/html")
    assert board.status_code == 403
    assert 'data-own-scope-app="restricted"' in board.content.decode()

    client.force_login(staff)
    assert (
        client.get("/apps/cards/", HTTP_ACCEPT="text/html").status_code != 403
    )


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


def test_cards_names_its_blocker_in_its_own_manifest():
    """Cards is a public tile with no registry-level hold; it gates itself.

    The old hub-side ``todo_app`` wrapper held Cards back with a
    ``coming_soon`` availability whose reason named "scitex-cards 0.53.1"
    and the per-tenant store check. The generic plugin mount (082a0c51f)
    deleted that wrapper: Cards now names its blocker itself — a staff
    ``audience`` in its OWN manifest, enforced by the generic mount guard
    (the floor pin lives on in pyproject's ``[all]`` extra).
    """
    from apps.infra.workspace_app import registry
    from scitex_app.plugins import loaded_plugin_configs

    # No hub-side manifests: the wrappers are gone and must not come back.
    assert not (registry._APPS_ROOT / "workspace/agents_app/manifest.json").exists()
    assert not (registry._APPS_ROOT / "workspace/todo_app/manifest.json").exists()

    # Cards ships in every env (pyproject [all] floor).
    cards = registry.get_module("scitex-cards")
    assert cards is not None
    assert cards.visibility == "public"
    assert cards.availability in ("", "available")

    manifests = {
        (config.manifest.get("slug") or ""): dict(config.manifest)
        for config in loaded_plugin_configs()
    }
    assert "scitex-cards" in manifests
    assert manifests["scitex-cards"]["mount_policy"]["audience"] == "staff"


def test_agents_manifest_is_public_free_install():
    """Agents stays a public tile with no hold anywhere in its chain.

    Read through the plugin mechanism that replaced the deleted hub-side
    ``workspace/agents_app/manifest.json`` (082a0c51f): the launcher lists
    the tile from the plugin's OWN manifest. Skipped where the package is
    not installed (absent from CI's matrix venv).
    """
    from apps.infra.workspace_app import registry

    agents = registry.get_module("agents")
    if agents is None:
        pytest.skip("agents plugin is not installed in this environment")
    assert agents.visibility == "public"
    assert agents.availability in ("", "available")
