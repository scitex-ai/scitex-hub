"""Regression contract for the authenticated-only project domain."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser

from apps.infra.project_app.views.repository.api.permissions import (
    check_project_read_access,
    check_project_write_access,
)
from apps.workspace.writer_app.views.editor.auth_utils import (
    get_user_for_request,
    user_can_access_project,
)

ROOT = Path(__file__).resolve().parents[3]
VISITOR_PACKAGE = ROOT / "apps/infra/project_app/services/visitor_pool"
VISITOR_COMMANDS = {
    "assert_visitor_pool_ready.py",
    "create_visitor_pool.py",
    "mint_visitor_session.py",
    "reconcile_visitor_slots.py",
    "reset_visitor_pool.py",
    "reset_visitor_workspaces.py",
    "visitor_pool_ready.py",
}



def _runtime_python_files():
    for base in (ROOT / "apps", ROOT / "config"):
        for path in base.rglob("*.py"):
            relative = path.relative_to(ROOT)
            relative_text = relative.as_posix()
            if relative_text.startswith("apps/infra/public_app/"):
                continue
            if "/migrations/" in relative_text:
                continue
            if relative_text.startswith(
                "apps/infra/project_app/services/visitor_pool/"
            ):
                continue
            yield path


def test_authenticated_runtime_does_not_import_visitor_pool():
    offenders = []
    needle = "apps.infra.project_app.services.visitor_pool"
    for path in _runtime_python_files():
        if needle in path.read_text(encoding="utf-8"):
            offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == []


def test_visitor_service_package_is_removed():
    assert list(VISITOR_PACKAGE.glob("*.py")) == []


def test_visitor_management_commands_are_removed():
    command_dir = ROOT / "apps/infra/project_app/management/commands"
    remaining = {path.name for path in command_dir.glob("*.py")}

    assert remaining.isdisjoint(VISITOR_COMMANDS)


def test_visitor_workspace_task_and_queue_route_are_removed():
    task_path = ROOT / "apps/infra/project_app/tasks/visitor_workspace_tasks.py"
    celery_settings = (ROOT / "config/settings/settings_celery.py").read_text(
        encoding="utf-8"
    )

    assert not task_path.exists() and "visitor_workspace_tasks" not in celery_settings


def test_anonymous_session_ids_do_not_grant_private_project_read_access():
    request = SimpleNamespace(
        user=AnonymousUser(),
        session={"visitor_project_id": 17, "visitor_user_id": 23},
    )
    project = SimpleNamespace(id=17, visibility="private")

    assert check_project_read_access(request, project) is False


def test_writer_anonymous_session_ids_do_not_grant_project_access():
    request = SimpleNamespace(
        user=AnonymousUser(),
        session={"visitor_project_id": 17, "visitor_user_id": 23},
    )
    project = SimpleNamespace(id=17, owner_id=23)

    assert user_can_access_project(request, project) is False


def test_writer_never_resolves_anonymous_session_to_shared_user():
    request = SimpleNamespace(
        user=AnonymousUser(),
        session={"visitor_user_id": 23},
    )

    assert get_user_for_request(request, project_id=17) == (None, False)


class _Collaborators:
    def __init__(self, allowed_id):
        self.allowed_id = allowed_id
        self.queried_id = None

    def filter(self, *, id):
        self.queried_id = id
        return self

    def exists(self):
        return self.queried_id == self.allowed_id


def test_authenticated_owner_keeps_project_read_and_write_access():
    user = SimpleNamespace(is_authenticated=True, id=7)
    project = SimpleNamespace(
        owner=user,
        collaborators=_Collaborators(allowed_id=None),
        visibility="private",
        can_edit=lambda candidate: candidate is user,
    )
    request = SimpleNamespace(user=user, session={})

    assert check_project_read_access(request, project) is True
    assert check_project_write_access(request, project) is True


def test_authenticated_collaborator_keeps_writer_project_access():
    user = SimpleNamespace(is_authenticated=True, id=8)
    project = SimpleNamespace(
        owner_id=7,
        collaborators=_Collaborators(allowed_id=8),
    )
    request = SimpleNamespace(user=user, session={})

    assert user_can_access_project(request, project) is True


def test_signed_out_writer_is_refused_to_signup(monkeypatch):
    from apps.workspace.writer_app.views.index import main

    monkeypatch.setattr(main, "redirect", lambda target: target)
    request = SimpleNamespace(user=AnonymousUser())

    assert main.index_view(request) == "auth_app:signup"


@pytest.mark.parametrize("path", ["/apps/", "/apps/writer/"])
def test_signed_out_workspace_entry_is_refused_to_signup(monkeypatch, path):
    from apps.workspace.my_projects_app.views import dispatch

    monkeypatch.setattr(dispatch, "redirect", lambda target: target)
    request = SimpleNamespace(
        user=AnonymousUser(),
        path=path,
    )

    assert dispatch.root_dispatch(request) == "auth_app:signup"
