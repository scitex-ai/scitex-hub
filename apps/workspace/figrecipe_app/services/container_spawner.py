"""Per-user-UID spawner for the FigRecipe Apptainer pilot (HPC model).

The container runs as the REQUESTING USER's own OS uid, never the hub
uid. The hub is the submit host: web login → uid via an explicit
allowlist, then a minimal privileged spawner does the uid switch before
the apptainer launch.

* Mapping: ``FIGRECIPE_UID_MAP="alice:10001,bob:10002"`` (Infra-owned).
  Unmapped logins fail closed to the in-process render (pilot
  reversibility) — never to another user's uid. Uid pool ≥10000 avoids
  the host's uid-1000 service/human collision (measured on compute-03).
* Spawner: ``FIGRECIPE_SPAWNER=direct`` runs apptainer as the current uid
  (dev/test only, no privilege). Production uses the audited setuid
  helper ``/usr/local/sbin/scitex-figrecipe-spawn`` (C source beside this
  module for audit): it allows caller=hub service account only,
  allowlists target uid + a single bind under the users tree, scrubs the
  environment, then ``setresuid(target)`` + ``exec apptainer run``.
  This module builds the helper's argv so the audited surface is exact.
* Binds per instance (least privilege): ONLY the user's own project jail
  ``-B <users>/<owner>/<slug>:/work:rw`` + ``-B /tmp/figrecipe-<user>:
  /tmp/figrecipe:rw``. No hub code, no hub secrets, no other users' data,
  ``--contain --cleanenv --no-home --pid --ipc``, loopback port per uid.
* Credentials inside: NONE (no DB, no hub creds — the uid IS the file
  credential). The per-request HMAC token stays as defense in depth.

Verify-by-probing runbook (Infra, as the mapped uid): ``id -u`` == map;
``ls /work`` == own project only; ``ls /app`` absent; ``env | grep -i
secret`` empty. Automated: cross-tenant token + escape tests live on the
leaf (``test__container_auth``) and the bind/argv tests below.
"""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)

UID_MAP_ENV = "FIGRECIPE_UID_MAP"
SPAWNER_ENV = "FIGRECIPE_SPAWNER"
HELPER_ENV = "FIGRECIPE_SPAWN_HELPER"
PORT_BASE_ENV = "FIGRECIPE_PORT_BASE"

DEFAULT_HELPER = "/usr/local/sbin/scitex-figrecipe-spawn"
DEFAULT_PORT_BASE = 18100
PORT_SPAN = 1000
#: Pilot uid pool floor. System (<1000), service, AND human/service-collision
#: (1000, e.g. ywatanabe/scitex on compute-03) ranges are refused: mapping a
#: web login to uid 1000 would run the container as the host owner. Infra
#: provisions pilot users at >=10000.
MIN_PILOT_UID = 10000
#: Pilot uid pool ceiling — mirrors the setuid helper's MAX_UID (60000).
#: The two layers must agree or a login could pass the hub check and die
#: (or worse, behave differently) at the helper gate.
MAX_PILOT_UID = 60000
#: Users tree the Python layer confines project binds to (m4). Same value
#: the setuid helper compiles in via -DUSERS_TREE; Infra-owned.
USERS_TREE_ENV = "FIGRECIPE_USERS_TREE"
DEFAULT_USERS_TREE = "/opt/scitex/data/users"
#: Explicit per-uid port overrides, ``"10001:18101,10002:18102"`` (m3).
#: The deterministic ``uid % PORT_SPAN`` fallback collides once the pilot
#: exceeds ~1000 users (10001 and 11001 share a port); overrides are the
#: registry until the pilot gets a real allocator. HMAC scoping stays as
#: defense in depth, never as the collision fix.
PORT_MAP_ENV = "FIGRECIPE_PORT_MAP"
#: ``direct`` spawner mode (apptainer as the current uid, no privilege)
#: must never run in production (m4): it performs no uid switch and its
#: binds are hub-side strings, not the helper's audited gates. It runs
#: only when explicitly allowed for dev/test.
ALLOW_DIRECT_ENV = "FIGRECIPE_ALLOW_DIRECT"
#: Login names interpolated into the per-user tmp bind (``/tmp/figrecipe-<user>``).
#: Same allowlist the setuid helper enforces in C — the hub must refuse a
#: bad login before it ever reaches helper argv.
_USERNAME_RE = re.compile(r"[A-Za-z0-9_.-]{1,128}\Z")


class SpawnerUnavailable(Exception):
    """No per-user container can be spawned for this request (fail closed)."""


def uid_map() -> dict:
    """Parse ``FIGRECIPE_UID_MAP`` into ``{username: uid}`` (empty = unset)."""
    raw = os.environ.get(UID_MAP_ENV, "").strip()
    mapping = {}
    if not raw:
        return mapping
    for entry in raw.split(","):
        name, _, uid = entry.partition(":")
        name, uid = name.strip(), uid.strip()
        if not name or not uid.isdigit():
            raise SpawnerUnavailable(f"Bad {UID_MAP_ENV} entry: {entry!r}")
        mapping[name] = int(uid)
    return mapping


def check_username(username: str) -> str:
    """Enforce the tmp-bind login allowlist; bad logins fail closed.

    Mirrors the helper's C gate exactly: charset ``[A-Za-z0-9_.-]`` plus an
    explicit ``..`` refusal (dots are legal singly, runs are traversal).
    """
    if not username or ".." in username or not _USERNAME_RE.match(username):
        raise SpawnerUnavailable(f"Refusing unsafe username {username!r}")
    return username


def users_tree() -> str:
    """Return the confined users tree (Infra-owned, normalized, no trailing /)."""
    return os.environ.get(USERS_TREE_ENV, DEFAULT_USERS_TREE).rstrip("/") or DEFAULT_USERS_TREE


def resolve_uid(username: str) -> int:
    """Map a web login to its OS uid; unmapped → fail closed."""
    if not username:
        raise SpawnerUnavailable("Anonymous logins have no uid")
    check_username(username)
    try:
        mapping = uid_map()
    except SpawnerUnavailable:
        raise
    if username not in mapping:
        raise SpawnerUnavailable(f"No uid mapped for {username!r}")
    uid = mapping[username]
    if uid < MIN_PILOT_UID:
        raise SpawnerUnavailable(f"Mapped uid {uid} below pilot floor")
    if uid > MAX_PILOT_UID:
        raise SpawnerUnavailable(f"Mapped uid {uid} above pilot ceiling")
    return uid


def port_overrides() -> dict:
    """Parse ``FIGRECIPE_PORT_MAP`` into ``{uid: port}`` (empty = unset)."""
    raw = os.environ.get(PORT_MAP_ENV, "").strip()
    overrides = {}
    if not raw:
        return overrides
    for entry in raw.split(","):
        uid_s, _, port_s = entry.partition(":")
        uid_s, port_s = uid_s.strip(), port_s.strip()
        if not uid_s.isdigit() or not port_s.isdigit():
            raise SpawnerUnavailable(f"Bad {PORT_MAP_ENV} entry: {entry!r}")
        overrides[int(uid_s)] = int(port_s)
    return overrides


def port_base() -> int:
    """Validated port base (garbage env fails closed, never 500s)."""
    try:
        base = int(os.environ.get(PORT_BASE_ENV, DEFAULT_PORT_BASE))
    except (TypeError, ValueError):
        raise SpawnerUnavailable(f"Bad {PORT_BASE_ENV}")
    if not 1024 <= base <= 65535 - PORT_SPAN:
        raise SpawnerUnavailable(f"{PORT_BASE_ENV} out of range")
    return base


def user_port(uid: int) -> int:
    """Deterministic loopback port per uid (hub is the sole client).

    Explicit :data:`PORT_MAP_ENV` overrides win; otherwise ``base +
    (uid % PORT_SPAN)``. The fallback provably collides past ~1000 users
    (``port(10001) == port(11001)``) — the pilot stays small or Infra
    assigns overrides until a real allocator lands.
    """
    overrides = port_overrides()
    if int(uid) in overrides:
        return overrides[int(uid)]
    return port_base() + (int(uid) % PORT_SPAN)


def binds_for(project_root: str, username: str) -> list:
    """Least-privilege binds: ONLY this user's project jail + own tmp.

    Mirrors the helper's gates hub-side: absolute path, no ``..``, confined
    under the users tree with a path boundary (``users-evil`` refused), and
    an allowlisted login for the tmp bind source.
    """
    check_username(username)
    root = str(project_root or "")
    tree = users_tree()
    if not root.startswith("/") or ".." in root:
        raise SpawnerUnavailable("Refusing non-absolute project bind")
    if not (root == tree or root.startswith(tree + "/")):
        raise SpawnerUnavailable("Refusing project bind outside users tree")
    tmp = f"/tmp/figrecipe-{username}"
    return [f"{root}:/work:rw", f"{tmp}:/tmp/figrecipe:rw"]


def spawn_argv(
    uid: int,
    image: str,
    project_root: str,
    username: str,
    port: int,
    auth_key_present: bool,
) -> list:
    """Build the exact spawner argv (helper or direct fallback).

    ``auth_key_present`` is a BOOL, never the secret — the secret travels
    by environment through the helper's scrubbed pass-through, never on
    any command line (``ps``-visible argv must carry no credentials).
    """
    if not auth_key_present:
        raise SpawnerUnavailable("Refusing to spawn without an auth key")
    check_username(username)
    binds = binds_for(project_root, username)
    mode = os.environ.get(SPAWNER_ENV, "helper")
    if mode == "direct":
        # Dev/test only: no uid switch, no audited gates. Production must
        # use the helper — direct without the explicit allow flag refuses.
        if os.environ.get(ALLOW_DIRECT_ENV) != "1":
            raise SpawnerUnavailable(
                f"Refusing {mode!r} spawner without {ALLOW_DIRECT_ENV}=1"
            )
        argv = ["apptainer", "run", "--contain", "--cleanenv", "--no-home",
                "--pid", "--ipc"]
        for bind in binds:
            argv += ["-B", bind]
        argv += [image]
        return argv
    helper = os.environ.get(HELPER_ENV, DEFAULT_HELPER)
    return [helper, str(uid), image, project_root, username, str(port)]


def container_host_port(request) -> tuple:
    """Return ``(host, port)`` for this request's user container.

    Unmapped users raise :class:`SpawnerUnavailable` (caller falls back
    in-process). Mapped users get loopback + per-uid port.
    """
    user = getattr(request, "user", None)
    username = getattr(user, "username", "") or ""
    uid = resolve_uid(username)
    return ("127.0.0.1", user_port(uid))
