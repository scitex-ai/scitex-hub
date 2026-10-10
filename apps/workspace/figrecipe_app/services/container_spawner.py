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


def resolve_uid(username: str) -> int:
    """Map a web login to its OS uid; unmapped → fail closed."""
    if not username:
        raise SpawnerUnavailable("Anonymous logins have no uid")
    try:
        mapping = uid_map()
    except SpawnerUnavailable:
        raise
    if username not in mapping:
        raise SpawnerUnavailable(f"No uid mapped for {username!r}")
    uid = mapping[username]
    if uid < MIN_PILOT_UID:
        raise SpawnerUnavailable(f"Mapped uid {uid} below pilot floor")
    return uid


def user_port(uid: int) -> int:
    """Deterministic loopback port per uid (hub is the sole client)."""
    base = int(os.environ.get(PORT_BASE_ENV, DEFAULT_PORT_BASE))
    return base + (int(uid) % PORT_SPAN)


def binds_for(project_root: str, username: str) -> list:
    """Least-privilege binds: ONLY this user's project jail + own tmp."""
    if not project_root or not str(project_root).startswith("/"):
        raise SpawnerUnavailable("Refusing non-absolute project bind")
    tmp = f"/tmp/figrecipe-{username}"
    return [f"{project_root}:/work:rw", f"{tmp}:/tmp/figrecipe:rw"]


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
    binds = binds_for(project_root, username)
    mode = os.environ.get(SPAWNER_ENV, "direct")
    if mode == "direct":
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
