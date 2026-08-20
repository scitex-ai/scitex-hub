"""
Per-user Linux UID isolation service.

Each Django user is assigned a deterministic Linux UID (100000 + user.pk).
Their data directory is owned exclusively by that UID (chmod 700), so OS-level
isolation prevents one user from reading another's files via absolute paths.

This is LDAP-ready: replace get_unix_uid() with an LDAP UID lookup later
without changing any downstream code.
"""

import logging
import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

UID_BASE = 100_000
UID_MAX = 199_999


def get_unix_uid(user: User) -> int:
    """Return the deterministic Linux UID for a Django user (100000 + user.pk)."""
    uid = UID_BASE + user.pk
    if not (UID_BASE <= uid <= UID_MAX):
        raise ValueError(
            f"Computed UID {uid} for user {user.username} is outside the allowed "
            f"range {UID_BASE}–{UID_MAX}. Increase UID_MAX if needed."
        )
    return uid


def ensure_linux_account(user: User) -> bool:
    """
    Create Linux user+group in the container if not already present.

    Uses useradd/groupadd with the deterministic UID.  Safe to call
    repeatedly — exits cleanly if the account already exists.

    Returns True if the account was created or already existed, False on error.
    """
    uid = get_unix_uid(user)
    username = _safe_unix_username(user.username)

    try:
        # Check if user already exists
        result = subprocess.run(
            ["id", username], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return True  # already exists

        # Create group first (same GID as UID for simplicity)
        subprocess.run(
            ["groupadd", "--gid", str(uid), username],
            capture_output=True,
            timeout=10,
            check=False,  # May already exist — ignore error
        )

        # Create user with home dir set to their data root
        data_root = _get_user_data_root_str(user)
        subprocess.run(
            [
                "useradd",
                "--uid",
                str(uid),
                "--gid",
                str(uid),
                "--no-create-home",
                "--shell",
                "/bin/bash",
                "--home-dir",
                data_root,
                username,
            ],
            capture_output=True,
            timeout=10,
            check=True,
        )
        logger.info("Created Linux account for %s (UID=%d)", user.username, uid)
        return True

    except subprocess.CalledProcessError as exc:
        logger.warning("Failed to create Linux account for %s: %s", user.username, exc)
        return False
    except Exception as exc:
        logger.warning(
            "Unexpected error creating Linux account for %s: %s", user.username, exc
        )
        return False


def enforce_data_dir_ownership(user: User) -> bool:
    """
    Set /app/data/users/<username>/ to be owned by the user's UID and
    inaccessible to other OS users (mode 700).

    Safe to call repeatedly.  Returns True on success, False on error.

    READ THIS BEFORE RUNNING IT WITH ENOUGH PRIVILEGE TO SUCCEED.

    ``chown`` needs root. In the web process (uid 1000) it fails, the failure
    is logged and swallowed, and the directory keeps the default
    ``scitex:scitex 0755``. Every signup therefore takes that path, which means
    the isolation this function advertises **is not in force for any ordinary
    account** — it looks applied and is not. Measured 2026-08-17: 89 of 90
    accounts were 0755, i.e. the guarantee had never once held.

    When it DOES succeed, it locks the application out. Mode 700 owned by
    ``100000 + user.pk`` is not traversable by the web process, so every page
    that touches the workspace raises EACCES. Measured the same day: the one
    account provisioned through a root path (``demo-reviewer``, pk 163, dir
    owned by uid 100163, mode 0700) returned HTTP 500 on Writer, the file tree
    and git status, while the other 89 worked.

    So the two states are "isolation absent" and "application broken", and
    there is no configuration of this function alone that gives both isolation
    and a working app — the web process must be able to reach the data it
    manages. Getting real per-tenant isolation needs a different mechanism
    (a shared group the app belongs to, per-user subprocesses, or moving the
    boundary out of the filesystem), which is a design decision, not a patch.

    ``sync_unix_users`` calls this in a loop over every user. Running that
    command as root would apply the working-state-breaking half to all accounts
    at once.
    """
    uid = get_unix_uid(user)
    data_root = Path(settings.BASE_DIR) / "data" / "users" / user.username

    try:
        data_root.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            ["chown", "-R", f"{uid}:{uid}", str(data_root)],
            capture_output=True,
            timeout=30,
            check=True,
        )
        subprocess.run(
            ["chmod", "700", str(data_root)],
            capture_output=True,
            timeout=10,
            check=True,
        )
        logger.debug("Set ownership %d:%d mode 700 on %s", uid, uid, data_root)
        return True

    except subprocess.CalledProcessError as exc:
        # ERROR, not warning: this is a declared isolation guarantee that did
        # not take effect. Logging it quietly is how it stayed unnoticed on 89
        # of 90 accounts. Say plainly that the directory is NOT isolated.
        logger.error(
            "Data-dir isolation NOT applied for %s: %s. %s remains readable by "
            "other OS users in this container (chown/chmod need root; this "
            "process is uid %d). Treat that directory as unisolated.",
            user.username,
            exc,
            data_root,
            os.getuid(),
        )
        return False
    except Exception as exc:
        logger.error(
            "Data-dir isolation NOT applied for %s (unexpected error): %s. "
            "Treat %s as unisolated.",
            user.username,
            exc,
            data_root,
        )
        return False


def run_as_user(
    uid: int,
    gid: int,
    command: str,
    cwd: str,
    env: dict,
) -> "subprocess.Popen[bytes]":
    """
    Run a shell command as the given uid/gid via setpriv.

    Privilege dropping:
    - Dev (root): setpriv works directly.
    - Prod (scitex, UID 1000): requires cap_setuid,cap_setgid on /usr/bin/setpriv.
      The Dockerfile sets: setcap 'cap_setuid,cap_setgid+eip' /usr/bin/setpriv

    Raises ValueError if uid is outside the allowed app range (defence-in-depth).
    Raises subprocess.SubprocessError / FileNotFoundError on exec failure.
    """
    if not (UID_BASE <= uid <= UID_MAX):
        raise ValueError(
            f"Refusing to setpriv to UID {uid}: outside allowed range "
            f"{UID_BASE}–{UID_MAX}"
        )

    return subprocess.Popen(
        [
            "setpriv",
            f"--reuid={uid}",
            f"--regid={gid}",
            "--clear-groups",
            "--",
            "bash",
            "-c",
            command,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe_unix_username(username: str) -> str:
    """Sanitize Django username to a valid POSIX username (max 32 chars, no @)."""
    sanitized = username.replace("@", "_at_").replace(" ", "_")
    return sanitized[:32]


def _get_user_data_root_str(user: User) -> str:
    return str(Path(settings.BASE_DIR) / "data" / "users" / user.username)
