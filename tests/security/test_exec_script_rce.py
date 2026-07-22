#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Security regression tests for POST /apps/console/api/execute/ (script run).

Guards ``apps.workspace.console_app.workspace_api.execution.api_execute_script``
against the host-RCE / secret-exfiltration vulnerability tracked in card
``hub-workspace-api-host-rce``.

THE EXPLOIT (pre-fix code)::

    subprocess.run(["python", str(file_full_path)] + args,
                   cwd=file_full_path.parent, capture_output=True,
                   text=True, timeout=300)          # <-- NO env=

Three distinct attacker paths existed:

1. SECRET EXFILTRATION / HOST RCE. No ``env=`` means the child inherits the
   Django process environment verbatim — ``SCITEX_HUB_DJANGO_SECRET_KEY``, DB
   credentials, every ``SCITEX_HUB_*``. It also ran as the Django UID, so any
   authenticated user could write ``os.environ`` into a ``.py`` in their own
   project and own the host.
2. ANONYMOUS REACHABILITY. A dead ``else`` branch trusted
   ``request.session["visitor_project_id"]`` for unauthenticated callers. It was
   unreachable only because of the ``@login_required`` decorator — one decorator
   away from anonymous host-RCE.
3. CROSS-JAIL EXECUTION. Only a string-prefix check against the project's own
   ``git_clone_path`` was performed, so a Project row whose ``git_clone_path``
   pointed into ANOTHER user's data jail executed code from that jail.

THE FIX mirrors the hardened sibling ``api_execute_command``: the visitor branch
is deleted, the child is spawned through ``setpriv --reuid/--regid`` (argv list,
no shell), the project dir and the resolved target are validated with
``validate_path_in_user_jail``, and an explicit minimal ``env`` is passed.

These tests reproduce each path and assert it is BLOCKED. They FAIL on the
pre-fix code.

Design notes:
- NO mock library (fleet-forbidden) and NO database. ``subprocess`` is swapped
  on the module under test for a plain capturing stub; ``Project`` is swapped
  for a plain stub object. Users are UNSAVED model instances (``pk`` assigned by
  hand), so the suite never touches the test database and runs in milliseconds.
- The capturing stub snapshots ``os.environ`` whenever ``env=`` is absent,
  because that is exactly what the real ``subprocess.run`` would hand the child.
  That makes "the secret leaks" an observable fact rather than an inference.
- Arrange+act live in fixtures so each test carries a single assertion.
"""

import inspect
import json
import os
import subprocess
import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, override_settings

from apps.infra.accounts_app.services import unix_user as unix_user_mod
from apps.workspace.console_app.workspace_api import execution as execution_mod

pytestmark = pytest.mark.security

# The complete environment the hardened endpoint may hand the child.
EXPECTED_ENV_KEYS = {
    "HOME",
    "USER",
    "LOGNAME",
    "PATH",
    "TERM",
    "SCITEX_HUB_CODE_WORKSPACE",
    "SCITEX_HUB_CODE_BACKEND",
    "SCITEX_HUB_CODE_SESSION_ID",
    "SCITEX_HUB_CODE_PROJECT_ROOT",
}

# Substrings that must never appear in a key handed to the child process.
_SECRET_MARKERS = ("SECRET", "PASSWORD", "PASSWD", "TOKEN", "DATABASE_URL", "DB_")

# Planted in os.environ during the act phase; the child must never see it.
_CANARY_KEY = "SCITEX_HUB_DJANGO_SECRET_KEY"
_CANARY_VALUE = "canary-secret-must-not-leak"


def _secret_keys(env):
    return sorted(
        k for k in (env or {}) if any(m in k.upper() for m in _SECRET_MARKERS)
    )


class _CapturingSubprocess:
    """Stand-in for the ``subprocess`` module inside the view.

    Records argv + kwargs of every ``run()`` and returns a CompletedProcess-like
    object WITHOUT spawning anything. ``effective_env`` is what the child would
    actually receive: the explicit ``env=`` when given, otherwise the inherited
    ``os.environ`` snapshot taken at call time.
    """

    TimeoutExpired = subprocess.TimeoutExpired

    def __init__(self):
        self.calls = []

    def run(self, argv, **kwargs):
        env = kwargs.get("env")
        self.calls.append(
            {
                "argv": list(argv),
                "kwargs": kwargs,
                "explicit_env": env,
                "effective_env": dict(os.environ) if env is None else dict(env),
            }
        )
        return types.SimpleNamespace(returncode=0, stdout="ok", stderr="")


class _StubCollaborators:
    def __init__(self, members=()):
        self._members = list(members)

    def all(self):
        return list(self._members)


class _StubProject:
    """Minimal stand-in for the Project model row (no DB)."""

    def __init__(self, pk, owner, git_clone_path):
        self.id = pk
        self.pk = pk
        self.owner = owner
        self.git_clone_path = str(git_clone_path)
        self.collaborators = _StubCollaborators()


class _StubProjectManager:
    def __init__(self, project):
        self._project = project

    def select_related(self, *_args, **_kwargs):
        return self

    def get(self, **_kwargs):
        return self._project


class _StubProjectModel:
    def __init__(self, project):
        self.objects = _StubProjectManager(project)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def owner():
    """Unsaved user instance — get_unix_uid() only needs pk + username."""
    user = get_user_model()(username="rce_owner")
    user.pk = 4242
    return user


@pytest.fixture
def other():
    user = get_user_model()(username="rce_other")
    user.pk = 4343
    return user


@pytest.fixture(autouse=True)
def _no_linux_account():
    """Neutralise the OS-account bootstrap so tests never spawn id/useradd."""
    original = unix_user_mod.ensure_linux_account
    unix_user_mod.ensure_linux_account = lambda user: True
    try:
        yield
    finally:
        unix_user_mod.ensure_linux_account = original


@pytest.fixture
def spawns():
    """Swap the view module's ``subprocess`` for a capturing stub."""
    stub = _CapturingSubprocess()
    original = execution_mod.subprocess
    execution_mod.subprocess = stub
    try:
        yield stub
    finally:
        execution_mod.subprocess = original


def _install_project(project):
    """Swap the view module's ``Project`` for a stub returning ``project``."""
    return _StubProjectModel(project)


def _jail_dir(tmp_path, username):
    return tmp_path / "data" / "users" / username


def _post(rf, user, body, session=None):
    req = rf.post(
        "/apps/console/api/execute/",
        data=json.dumps(body),
        content_type="application/json",
    )
    req.user = user
    if session is not None:
        req.session = session
    return req


def _call(rf, tmp_path, project, user, body, session=None, undecorated=False):
    """Act: post to the endpoint with BASE_DIR pointing at the tmp jail root."""
    view = execution_mod.api_execute_script
    if undecorated:
        view = inspect.unwrap(view)
    original_model = execution_mod.Project
    execution_mod.Project = _install_project(project)
    prev = os.environ.get(_CANARY_KEY)
    os.environ[_CANARY_KEY] = _CANARY_VALUE
    try:
        with override_settings(BASE_DIR=str(tmp_path)):
            return view(_post(rf, user, body, session=session))
    finally:
        execution_mod.Project = original_model
        if prev is None:
            os.environ.pop(_CANARY_KEY, None)
        else:
            os.environ[_CANARY_KEY] = prev


@pytest.fixture
def owner_run(rf, owner, spawns, tmp_path):
    """Owner executes a legitimate ``.py`` inside their own jail."""
    project_dir = _jail_dir(tmp_path, owner.username) / "proj"
    project_dir.mkdir(parents=True)
    (project_dir / "script.py").write_text("import os; print(os.environ)\n")
    project = _StubProject(7, owner, project_dir)
    resp = _call(rf, tmp_path, project, owner, {"project_id": 7, "path": "script.py"})
    call = spawns.calls[0] if spawns.calls else None
    return types.SimpleNamespace(
        resp=resp,
        spawns=spawns,
        call=call,
        argv=(call["argv"] if call else None),
        explicit_env=(call["explicit_env"] if call else None),
        effective_env=(call["effective_env"] if call else {}),
    )


@pytest.fixture
def visitor_run(rf, owner, spawns, tmp_path):
    """EXPLOIT 2: anonymous caller with a session-planted visitor_project_id,
    against the view with its decorators stripped (the 'one decorator away'
    scenario the dead branch created)."""
    project_dir = _jail_dir(tmp_path, owner.username) / "proj"
    project_dir.mkdir(parents=True)
    (project_dir / "script.py").write_text("print('pwned')\n")
    project = _StubProject(7, owner, project_dir)
    resp = _call(
        rf,
        tmp_path,
        project,
        AnonymousUser(),
        {"project_id": 7, "path": "script.py"},
        session={"visitor_project_id": 7},
        undecorated=True,
    )
    return types.SimpleNamespace(resp=resp, spawns=spawns)


@pytest.fixture
def cross_jail_run(rf, owner, spawns, tmp_path):
    """EXPLOIT 3: attacker owns the Project row, but its git_clone_path points
    into ANOTHER user's data jail."""
    victim_dir = _jail_dir(tmp_path, "victim_user") / "proj"
    victim_dir.mkdir(parents=True)
    (victim_dir / "script.py").write_text("print('victim data')\n")
    project = _StubProject(7, owner, victim_dir)
    resp = _call(rf, tmp_path, project, owner, {"project_id": 7, "path": "script.py"})
    return types.SimpleNamespace(resp=resp, spawns=spawns)


@pytest.fixture
def forbidden_run(rf, owner, other, spawns, tmp_path):
    """An authenticated user who is neither owner nor collaborator."""
    project_dir = _jail_dir(tmp_path, owner.username) / "proj"
    project_dir.mkdir(parents=True)
    (project_dir / "script.py").write_text("print('hi')\n")
    project = _StubProject(7, owner, project_dir)
    resp = _call(rf, tmp_path, project, other, {"project_id": 7, "path": "script.py"})
    return types.SimpleNamespace(resp=resp, spawns=spawns)


@pytest.fixture
def traversal_run(rf, owner, spawns, tmp_path):
    """Owner requests a path that escapes the project directory."""
    project_dir = _jail_dir(tmp_path, owner.username) / "proj"
    project_dir.mkdir(parents=True)
    project = _StubProject(7, owner, project_dir)
    resp = _call(
        rf,
        tmp_path,
        project,
        owner,
        {"project_id": 7, "path": "../../../../../../etc/passwd"},
    )
    return types.SimpleNamespace(resp=resp, spawns=spawns)


@pytest.fixture
def sibling_prefix_run(rf, owner, spawns, tmp_path):
    """Owner escapes into a SIBLING dir whose name shares the project prefix.

    A string ``startswith`` containment check accepts this — "/…/proj-other"
    does start with "/…/proj" — while component-wise containment rejects it.
    """
    jail = _jail_dir(tmp_path, owner.username)
    project_dir = jail / "proj"
    project_dir.mkdir(parents=True)
    sibling = jail / "proj-other"
    sibling.mkdir(parents=True)
    (sibling / "secret.py").write_text("print('escaped')\n")
    project = _StubProject(7, owner, project_dir)
    resp = _call(
        rf,
        tmp_path,
        project,
        owner,
        {"project_id": 7, "path": "../proj-other/secret.py"},
    )
    return types.SimpleNamespace(resp=resp, spawns=spawns)


@pytest.fixture
def non_python_run(rf, owner, spawns, tmp_path):
    """Owner requests a non-``.py`` file inside the jail."""
    project_dir = _jail_dir(tmp_path, owner.username) / "proj"
    project_dir.mkdir(parents=True)
    (project_dir / "evil.sh").write_text("echo pwned\n")
    project = _StubProject(7, owner, project_dir)
    resp = _call(rf, tmp_path, project, owner, {"project_id": 7, "path": "evil.sh"})
    return types.SimpleNamespace(resp=resp, spawns=spawns)


@pytest.fixture
def string_args_run(rf, owner, spawns, tmp_path):
    """``args`` supplied as a bare string instead of a list."""
    project_dir = _jail_dir(tmp_path, owner.username) / "proj"
    project_dir.mkdir(parents=True)
    (project_dir / "script.py").write_text("print('hi')\n")
    project = _StubProject(7, owner, project_dir)
    resp = _call(
        rf,
        tmp_path,
        project,
        owner,
        {"project_id": 7, "path": "script.py", "args": "abc"},
    )
    return types.SimpleNamespace(resp=resp, spawns=spawns)


# ---------------------------------------------------------------------------
# EXPLOIT 1 — the child must not receive the Django secret environment
# ---------------------------------------------------------------------------


def test_owner_execution_still_succeeds(owner_run):
    # Arrange
    resp = owner_run.resp
    # Act
    status = resp.status_code
    # Assert
    assert status == 200, resp.content


def test_child_receives_an_explicit_env(owner_run):
    # Arrange
    env = owner_run.explicit_env
    # Act
    passed_explicit_env = env is not None
    # Assert
    assert passed_explicit_env, "no env= passed: child inherits the Django secrets"


def test_child_cannot_read_the_django_secret_key(owner_run):
    # Arrange
    env = owner_run.effective_env
    # Act
    leaked = env.get(_CANARY_KEY)
    # Assert
    assert leaked is None, f"{_CANARY_KEY} reached the user's script"


def test_child_env_never_carries_the_secret_value(owner_run):
    # Arrange
    env = owner_run.effective_env
    # Act
    leaked_value = _CANARY_VALUE in env.values()
    # Assert
    assert leaked_value is False


def test_child_env_has_no_secret_shaped_keys(owner_run):
    # Arrange
    env = owner_run.effective_env
    # Act
    leaked = _secret_keys(env)
    # Assert
    assert leaked == [], f"secret env keys leaked to child: {leaked}"


def test_child_env_is_exactly_the_minimal_allowlist(owner_run):
    # Arrange
    env = owner_run.effective_env
    # Act
    keys = set(env)
    # Assert
    assert keys == EXPECTED_ENV_KEYS


def test_child_is_launched_under_setpriv(owner_run):
    # Arrange
    argv = owner_run.argv or []
    # Act
    first = argv[0] if argv else None
    # Assert
    assert first == "setpriv", f"child not privilege-dropped: argv={argv}"


def test_child_drops_to_the_users_uid(owner_run):
    # Arrange
    argv = owner_run.argv or []
    # Act
    has_reuid = any(str(a).startswith("--reuid=") for a in argv)
    # Assert
    assert has_reuid, f"no UID drop in argv={argv}"


# ---------------------------------------------------------------------------
# EXPLOIT 2 — the dead visitor branch is gone (anonymous reachability)
# ---------------------------------------------------------------------------


def test_anonymous_visitor_session_cannot_execute(visitor_run):
    # Arrange
    spawns = visitor_run.spawns
    # Act
    spawned = bool(spawns.calls)
    # Assert
    assert spawned is False, "session-planted visitor_project_id reached execution"


def test_anonymous_visitor_session_is_rejected(visitor_run):
    # Arrange
    resp = visitor_run.resp
    # Act
    status = resp.status_code
    # Assert
    assert status >= 400, resp.content


# ---------------------------------------------------------------------------
# EXPLOIT 3 — a project pointing into another user's jail is refused
# ---------------------------------------------------------------------------


def test_project_outside_own_jail_spawns_nothing(cross_jail_run):
    # Arrange
    spawns = cross_jail_run.spawns
    # Act
    spawned = bool(spawns.calls)
    # Assert
    assert spawned is False, "executed code from another user's data jail"


def test_project_outside_own_jail_returns_403(cross_jail_run):
    # Arrange
    resp = cross_jail_run.resp
    # Act
    status = resp.status_code
    # Assert
    assert status == 403, resp.content


# ---------------------------------------------------------------------------
# Standing authorization / input guards
# ---------------------------------------------------------------------------


def test_non_owner_is_forbidden(forbidden_run):
    # Arrange
    resp = forbidden_run.resp
    # Act
    status = resp.status_code
    # Assert
    assert status == 403, resp.content


def test_non_owner_spawns_no_child(forbidden_run):
    # Arrange
    spawns = forbidden_run.spawns
    # Act
    spawned = bool(spawns.calls)
    # Assert
    assert spawned is False


def test_path_traversal_returns_4xx(traversal_run):
    # Arrange
    resp = traversal_run.resp
    # Act
    status = resp.status_code
    # Assert
    assert 400 <= status < 500, resp.content


def test_path_traversal_spawns_no_child(traversal_run):
    # Arrange
    spawns = traversal_run.spawns
    # Act
    spawned = bool(spawns.calls)
    # Assert
    assert spawned is False


def test_sibling_prefix_escape_returns_4xx(sibling_prefix_run):
    # Arrange
    resp = sibling_prefix_run.resp
    # Act
    status = resp.status_code
    # Assert
    assert 400 <= status < 500, resp.content


def test_sibling_prefix_escape_spawns_no_child(sibling_prefix_run):
    # Arrange
    spawns = sibling_prefix_run.spawns
    # Act
    spawned = bool(spawns.calls)
    # Assert
    assert spawned is False


def test_non_python_file_is_rejected(non_python_run):
    # Arrange
    resp = non_python_run.resp
    # Act
    status = resp.status_code
    # Assert
    assert status == 400, resp.content


def test_non_python_file_spawns_no_child(non_python_run):
    # Arrange
    spawns = non_python_run.spawns
    # Act
    spawned = bool(spawns.calls)
    # Assert
    assert spawned is False


def test_string_args_is_rejected_not_splatted(string_args_run):
    # Arrange
    resp = string_args_run.resp
    # Act
    status = resp.status_code
    # Assert
    assert status == 400, resp.content


# EOF
