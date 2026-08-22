"""
Recycled-visitor HOME access: who owns the tree, and can the app reach it.

Split out of ``home_state`` (512-line cap) because it answers a different
question. ``home_state`` asks WHAT is in a recycled home; this module asks
whether the process that has to serve it can actually get at it — the unix
identity the tree is handed back to, the mode it is handed back at, and the
final-gate checks for both.

Two production incidents live here, and they fail in opposite directions:

* 2026-08-17 — the reset ran as root and left the whole tree root-owned, so
  the web process (uid 1000) could read everything and create nothing. The
  writer's first ``mkdir .scitex/`` was EACCES. Fixed by
  :func:`enforce_app_ownership`, which must run LAST.
* 2026-08-16 — a wiped slot came back mode 0700, so the app could not list
  ``data/users/visitor-001`` at all. Because the health check behind the
  site-wide "Server:" badge walks every directory under ``data/users`` and
  marks itself unhealthy on one ``PermissionError``, that single slot showed
  "Server: partial" to every visitor, anonymous ones included, for days.
  Fixed by pinning the mode explicitly and by asserting the property rather
  than the ownership (:func:`dir_is_traversable_by`).

The recurring lesson in both, and the reason the checks here are written
against ``stat()`` rather than ``os.access``: THE CHECKER MUST NOT BE
PRIVILEGED WITH RESPECT TO WHAT IT CHECKS. The reset runs as root, root
bypasses DAC, and a probe that consults the caller's own privilege reports
clean over precisely the fault it exists to catch. The card records an
operator running ``docker exec`` (uid 0) against the broken slot and getting
BROKEN=[] while the API kept reporting 1.

Failure policy is ``home_state``'s: every check raises
:class:`~.home_state.HomeStateError`, and ``workspace_manager`` wraps it into
``WorkspaceResetError`` so the slot is quarantined, never served.
"""

import grp
import logging
import os
import pwd
import stat
import subprocess
from pathlib import Path

from django.conf import settings

from .home_state import HomeStateError

logger = logging.getLogger(__name__)


APP_UNIX_OWNER_SETTING = "APP_UNIX_OWNER"
APP_UNIX_OWNER_ENV = "SCITEX_HUB_APP_UNIX_OWNER"

# The mode a recycled home root is handed back at, set EXPLICITLY rather
# than inherited. Two ambient-state routes produced mode 0700 here:
#
#   * ``os.makedirs``' ``mode=`` argument is MASKED BY UMASK. Measured
#     2026-08-22 on this codebase's interpreter:
#         umask=0022  makedirs(mode=0o755) -> 0755
#         umask=0027  makedirs(mode=0o755) -> 0750
#         umask=0077  makedirs(mode=0o755) -> 0700   <-- the card's mode
#     ``os.chmod`` is NOT masked and yielded 0755 at every umask, which is
#     why the mode is pinned with a chmod and not with a mkdir argument.
#   * ``workspace_wipe``'s permission-recovery chmod used to ASSIGN 0700
#     to the wiped directory's parent (fixed there, in ``_add_owner_rwx``).
#
# 0o755 AND NOT 0o700, and the reason is the measured site convention rather
# than this module's preference. Measured on production 2026-08-22:
#
#     ls -ln /app/data/users  ->  97 of 97 entries  drwxr-xr-x 1000:1000
#
# Every home — named users and visitor slots alike — is owned by the app uid
# AND world-traversable, with no exceptions. Handing a recycled visitor home
# back at 0700 would make those slots the only directories in the tree with a
# different mode, which is how the next reader concludes the tree is
# inconsistent and "fixes" the wrong half.
#
# The o+rx specifically is for readers OUTSIDE the container: this tree is
# bind-mounted, and SLURM binds and host-side tooling walk it as other
# identities. It is NOT needed by the app. ``enforce_app_ownership`` chowns to
# the app uid immediately before this chmod, so the app satisfies
# ``dir_is_traversable_by`` as OWNER, and the health check behind the
# site-wide "Server:" badge would pass at 0700 too. An earlier version of this
# comment cited that health check as the reason for o+rx; that was wrong — it
# is the reason the mode must be pinned AT ALL, not the reason it is 755.
#
# CodeQL flags this as py/overly-permissive-file-permission and is describing
# the mode accurately. Whether user homes should be 0750 site-wide is a real
# question, but it is a decision about all 97 directories and every consumer
# outside the container — not something to settle inside a visitor-pool
# bugfix. Carded separately.
APP_TRAVERSABLE_DIR_MODE = 0o755


def dir_is_traversable_by(path: Path, uid: int, gid: int) -> bool:
    """Would a process running as ``uid``:``gid`` be able to list ``path``?

    POSIX resolves a permission against the FIRST matching class — owner,
    then group, then other — and a wider later class never rescues a
    narrower earlier one. Mode 0705 owned by ``uid`` therefore DENIES
    ``uid`` despite ``o+rx``, so this cannot be written as a mask test
    against the whole mode.

    That first-match rule is also why neither ownership nor mode alone is
    the invariant. On production 2026-08-16, ``drwxr-xr-x 100004
    visitor-003`` (foreign owner, ``o+rx``) worked and ``drwx------ 100001
    visitor-001`` (foreign owner, no ``o+rx``) did not. What the two
    disagree about is exactly this predicate.

    Deliberately models DAC only, with no root bypass: the reset runs as
    root, and a check that consults the CALLER's privilege passes for
    precisely the broken slot it exists to catch.
    """
    st = os.stat(path)
    mode = stat.S_IMODE(st.st_mode)
    if st.st_uid == uid:
        needed = stat.S_IRUSR | stat.S_IXUSR
    elif st.st_gid == gid:
        needed = stat.S_IRGRP | stat.S_IXGRP
    else:
        needed = stat.S_IROTH | stat.S_IXOTH
    return mode & needed == needed


def resolve_app_owner() -> tuple[int, int]:
    """Turn ``settings.APP_UNIX_OWNER`` into a numeric ``(uid, gid)`` pair.

    Accepted forms: ``scitex`` (name), ``1000`` (uid), ``scitex:scitex`` or
    ``1000:1000`` (explicit ``user:group``, either form on each side). A bare
    user resolves its group to that user's primary group; a bare numeric uid
    resolves the gid to the same number.

    Resolution happens HERE, at reset time, and any value that cannot be
    resolved raises :class:`HomeStateError` naming the setting and the env var
    to fix. There is deliberately no fallback to ``os.getuid()``: on production
    the reset runs as root, so "whoever is running" is exactly the owner that
    locks the web process out.
    """
    declared = getattr(settings, APP_UNIX_OWNER_SETTING, None)
    if not declared or not str(declared).strip():
        raise HomeStateError(
            f"settings.{APP_UNIX_OWNER_SETTING} is empty; declare the unix identity "
            f"the web process runs as (a user name, a uid, or user:group) via "
            f"{APP_UNIX_OWNER_ENV}. Nothing is chowned until it is set."
        )
    declared = str(declared).strip()
    user_part, _, group_part = declared.partition(":")

    def _uid(token: str) -> tuple[int, int | None]:
        if token.isdigit():
            return int(token), None
        try:
            entry = pwd.getpwnam(token)
        except KeyError as exc:
            raise HomeStateError(
                f"settings.{APP_UNIX_OWNER_SETTING}={declared!r}: user {token!r} does "
                f"not exist on this host. Set {APP_UNIX_OWNER_ENV} to the user name "
                f"or numeric uid the web process actually runs as (on production "
                f"that is `scitex`, uid 1000)."
            ) from exc
        return entry.pw_uid, entry.pw_gid

    def _gid(token: str) -> int:
        if token.isdigit():
            return int(token)
        try:
            return grp.getgrnam(token).gr_gid
        except KeyError as exc:
            raise HomeStateError(
                f"settings.{APP_UNIX_OWNER_SETTING}={declared!r}: group {token!r} does "
                f"not exist on this host. Set {APP_UNIX_OWNER_ENV} to an existing "
                f"user:group or to numeric ids."
            ) from exc

    uid, primary_gid = _uid(user_part)
    if group_part:
        gid = _gid(group_part)
    elif primary_gid is not None:
        gid = primary_gid
    else:
        gid = uid
    return uid, gid


def enforce_app_ownership(home_root: Path) -> None:
    """Hand the freshly materialised tree back to the process that serves it.

    The reset runs inside the visitor Celery worker, which is ROOT, while the
    web process that must later write into this tree is ``scitex`` (uid 1000)
    and compiles IN-PROCESS with no privilege change. Measured on production
    2026-08-17: ``celery_worker_vis`` PID 7 ``Uid: 0 0 0 0``; ``daphne`` PID 7
    ``Uid: 1000 1000 1000 1000``.

    Nothing between the two ever chowned the result. ``initialize_user_workspace``
    calls ``enforce_data_dir_ownership`` at the one instant the tree is nearly
    empty, so only ``proj/`` and ``workspace_info.json`` got an owner; every
    directory created afterwards — the dotfiles repo, the project dir, the whole
    template clone — stayed ``root:root`` 0755. The app could read the tree and
    could not create a single entry in it, so the writer's first write, ``mkdir
    .scitex/``, was EACCES and the demo never compiled:

        mkdir: cannot create directory
        '/app/data/users/visitor-003/proj/dotfiles/.scitex': Permission denied

    Doing this LAST is the point. A chown in the middle is undone by every
    directory created after it, which is exactly the bug being fixed here.

    The owner comes from ``settings.APP_UNIX_OWNER`` (see settings_shared) and
    is resolved to NUMERIC ids first, so the chown never depends on a user name
    existing on the host that happens to run the reset — CI's py3.11 runner had
    no ``scitex`` account and every reset there failed with
    ``chown: invalid user``.

    ``-h`` because the home root holds relative symlinks into ``proj/``; they
    stay inside the tree, so plain ``-R`` is safe today, but ``-h`` removes the
    class of bug rather than the instance.

    OWNERSHIP IS ONLY HALF OF IT. The chown alone left the home root at
    whatever MODE the last writer happened to give it, and on 2026-08-16 that
    was 0700 — the app could not list ``data/users/visitor-001`` at all, and
    because the health check behind the site-wide badge walks every directory
    under ``data/users``, that one slot published "Server: partial" to every
    visitor for days. So the mode is pinned here too, explicitly, with a chmod
    (see ``APP_TRAVERSABLE_DIR_MODE`` for why a chmod and not a mkdir
    argument).
    """
    uid, gid = resolve_app_owner()
    result = subprocess.run(
        ["chown", "-R", "-h", f"{uid}:{gid}", str(home_root)],
        capture_output=True,
        timeout=120,
    )
    if result.returncode != 0:
        declared = getattr(settings, APP_UNIX_OWNER_SETTING, None)
        raise HomeStateError(
            f"could not hand {home_root} back to uid {uid}:{gid} "
            f"(settings.{APP_UNIX_OWNER_SETTING}={declared!r}): "
            f"{result.stderr.decode(errors='replace').strip()}. The slot is "
            f"quarantined rather than served, because a slot the web process "
            f"cannot write to cannot run the demo. If the ids are wrong, set "
            f"{APP_UNIX_OWNER_ENV} to the identity the web process runs as."
        )
    try:
        os.chmod(home_root, APP_TRAVERSABLE_DIR_MODE)
    except OSError as exc:
        raise HomeStateError(
            f"could not set mode {APP_TRAVERSABLE_DIR_MODE:04o} on {home_root}: "
            f"{exc}. The slot is quarantined rather than served: a home root the "
            f"app cannot list also fails the health check that drives the "
            f"site-wide status badge, so serving it degrades the whole site."
        ) from exc


def _refuse_unreachable(home_root: Path, entries, app_uid: int, app_gid: int) -> None:
    """Raise unless every directory in ``entries`` is listable by the app."""
    unreachable = [
        f"{'.' if entry == home_root else entry.name} "
        f"(mode {stat.S_IMODE(entry.stat().st_mode):04o}, "
        f"owner {entry.stat().st_uid}:{entry.stat().st_gid})"
        for entry in entries
        if not dir_is_traversable_by(entry, app_uid, app_gid)
    ]
    if not unreachable:
        return
    raise HomeStateError(
        f"{home_root} is not listable by the app identity "
        f"{app_uid}:{app_gid} (settings.{APP_UNIX_OWNER_SETTING}): "
        f"{unreachable!r}. This slot must not be served: the app cannot read "
        f"the workspace, and the health check that drives the site-wide status "
        f"badge walks these same directories, so one unlistable slot reports "
        f"the whole site degraded."
    )


def verify_app_can_write(home_root: Path) -> None:
    """Final-gate half that catches an unusable slot BEFORE it is served.

    Asserts TWO independent properties, because a slot satisfying only one of
    them has already been served broken:

    * TRAVERSABILITY — the app's identity can actually list the home root and
      its immediate subdirectories (:func:`dir_is_traversable_by`). This is the
      2026-08-16 defect: mode 0700 on ``data/users/visitor-001``.
    * OWNERSHIP — every entry below shares the root's owner, so the app's first
      write is not EACCES. This is the 2026-08-17 defect.

    TRAVERSABILITY IS CHECKED FIRST, and the order is load-bearing rather than
    stylistic: to a NON-root caller, ``rglob`` over an unlistable directory
    yields nothing and raises nothing, so the ownership loop below would walk
    an empty sequence and report a clean tree. An empty result and a blocked
    one are indistinguishable there — the traversability check is what tells
    them apart.

    Both halves are deliberately written against ``stat()`` rather than
    ``os.access``. This runs in the ROOT worker, and root bypasses DAC —
    ``os.access(path, os.W_OK)`` returns True for any existing path regardless
    of owner or mode, so an access-based check would pass for precisely the
    broken slot it exists to catch. A check that cannot fail is not a check.
    """
    try:
        expected_uid = os.stat(home_root).st_uid
    except OSError as exc:
        raise HomeStateError(f"cannot stat home root {home_root}: {exc}") from exc

    app_uid, app_gid = resolve_app_owner()
    _refuse_unreachable(home_root, [home_root], app_uid, app_gid)
    # Only descend once the root itself is known reachable — otherwise
    # ``iterdir`` is the thing that raises, with a bare PermissionError
    # instead of the message naming the mode and the fix.
    subdirs = [
        entry
        for entry in sorted(home_root.iterdir())
        if entry.is_dir() and not entry.is_symlink()
    ]
    _refuse_unreachable(home_root, subdirs, app_uid, app_gid)

    foreign = []
    for path in home_root.rglob("*"):
        try:
            if path.lstat().st_uid != expected_uid:
                foreign.append(str(path.relative_to(home_root)))
        except OSError:
            continue
        if len(foreign) >= 5:
            break

    if foreign:
        raise HomeStateError(
            f"{home_root} still holds entries owned by another uid "
            f"(first few: {foreign!r}); the web process would get EACCES on "
            f"its first write, so this slot must not be served"
        )


def leave_home_root_listable(home_root: Path) -> bool:
    """Stop a QUARANTINED slot from degrading the whole site. Best effort.

    A reset that raises leaves the home root wherever it got to. Mid-pipeline
    that can be mode 0700 owned by ``100000 + user.pk``
    (``enforce_data_dir_ownership``, still applied at skeleton time), and
    nothing repairs it until the container next restarts. On 2026-08-16 that
    state stood for DAYS.

    The slot staying quarantined is correct and is not touched here. What is
    not correct is the blast radius: the health check behind the site-wide
    "Server:" badge lists every directory under ``data/users`` and marks the
    entire check unhealthy on one ``PermissionError``, so a single quarantined
    slot published "Server: partial" to every visitor, anonymous ones included.
    One broken slot should cost one slot.

    Only the MODE is repaired, never the ownership: ``o+rx`` is exactly what
    the listing needs, and a chown here would quietly hand a half-built tree to
    the app and could turn a quarantine into a served slot. Failure is logged,
    not raised — this runs on a path that is already reporting an error, and
    replacing that error with this one would hide the real cause.
    """
    try:
        current = stat.S_IMODE(os.stat(home_root).st_mode)
    except OSError as exc:
        logger.warning(f"[VisitorPool] cannot stat {home_root} to unblock it: {exc}")
        return False
    if current & APP_TRAVERSABLE_DIR_MODE == APP_TRAVERSABLE_DIR_MODE:
        return True
    try:
        os.chmod(home_root, current | APP_TRAVERSABLE_DIR_MODE)
    except OSError as exc:
        logger.warning(
            f"[VisitorPool] {home_root} is mode {current:04o} and could not be "
            f"widened ({exc}); until it is listable, the site-wide health badge "
            f"reports the WHOLE site degraded, not just this slot"
        )
        return False
    logger.warning(
        f"[VisitorPool] quarantined {home_root} was mode {current:04o}; widened "
        f"to {current | APP_TRAVERSABLE_DIR_MODE:04o} so one failed slot does "
        f"not degrade the site-wide health badge"
    )
    return True



# EOF
