"""Per-user POSIX identity on the SLURM compute nodes (pure helpers, no ORM).

The broker runs as root; without these every user's job ran as uid 0 and
could read every other user's data. Here we derive what a job may see
(the user's own home plus a per-job scratch) and how it is submitted
(``sbatch --uid/--gid``, shells dropped via ``setpriv``).
"""

from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

COMPUTE_UID_BASE = int(os.environ.get("SCITEX_HUB_COMPUTE_UID_BASE", "20000"))
COMPUTE_HOME_ROOT = Path(
    os.environ.get("SCITEX_HUB_COMPUTE_HOME_ROOT", "/storage/cool/users")
)
# Node-local; each job gets its own 0700 directory under it.
COMPUTE_SCRATCH_ROOT = Path(os.environ.get("SCITEX_HUB_COMPUTE_SCRATCH_ROOT", "/tmp"))
COMPUTE_NODES = [
    n.strip()
    for n in os.environ.get(
        "SCITEX_HUB_COMPUTE_NODES", "compute-01,compute-02,compute-03,compute-04"
    ).split(",")
    if n.strip()
]
COMPUTE_SLURM_ACCOUNT = os.environ.get("SCITEX_HUB_COMPUTE_SLURM_ACCOUNT", "scitex")
SCRATCH_CONTAINER_PATH = "/scratch"

# useradd's default NAME_REGEX; anything else would need --badname on the nodes.
_POSIX_USERNAME = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")


def validate_posix_username(username: str) -> str:
    if not _POSIX_USERNAME.match(username or ""):
        raise ValueError(
            f"{username!r} is not a valid POSIX username for the compute nodes"
        )
    return username


def is_hub_compute_uid(uid: int) -> bool:
    """True only for hub-issued uids; billing must skip root and system users."""
    return uid >= COMPUTE_UID_BASE


def broker_is_root() -> bool:
    return os.geteuid() == 0


def compute_home(username: str) -> Path:
    return COMPUTE_HOME_ROOT / validate_posix_username(username)


def job_scratch_dir(username: str, allocation_id: str) -> Path:
    tag = re.sub(r"[^A-Za-z0-9]", "", allocation_id)[:12]
    return COMPUTE_SCRATCH_ROOT / f"scitex-{validate_posix_username(username)}-{tag}"


def with_sbatch_identity(
    cmd: list[str], uid: int | None, gid: int | None, as_root: bool | None = None
) -> list[str]:
    """Insert ``--uid/--gid`` after ``sbatch``; only root may submit as another user."""
    if uid is None or gid is None:
        return list(cmd)
    if not (broker_is_root() if as_root is None else as_root):
        return list(cmd)
    return [cmd[0], f"--uid={uid}", f"--gid={gid}", *cmd[1:]]


def as_compute_user(cmd: list[str], uid: int | None, gid: int | None) -> list[str]:
    """Drop to the user's uid/gid right before ``apptainer`` inside an srun step.

    ``srun --overlap`` from root runs the step as root, and apptainer
    instances are per-uid, so the shell must run as the job's owner.
    """
    if uid is None or gid is None or "apptainer" not in cmd:
        return list(cmd)
    i = cmd.index("apptainer")
    drop = ["setpriv", f"--reuid={uid}", f"--regid={gid}", "--clear-groups"]
    return [*cmd[:i], *drop, *cmd[i:]]


def instance_bind_sources(script: str) -> list[str]:
    """Host paths passed to ``--home``/``--bind`` in an instance start script."""
    for line in script.splitlines():
        if line.startswith("apptainer instance start "):
            tokens = shlex.split(line)
            return [
                tokens[i + 1].split(":", 1)[0]
                for i, tok in enumerate(tokens[:-1])
                if tok in ("--home", "--bind", "-B")
            ]
    return []


def is_within(path: str, root: Path) -> bool:
    try:
        Path(path).resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def foreign_user_data_binds(script: str, username: str) -> list[str]:
    """Bind sources under the shared users root that are not this user's home."""
    home = compute_home(username)
    return [
        src
        for src in instance_bind_sources(script)
        if is_within(src, COMPUTE_HOME_ROOT) and not is_within(src, home)
    ]


def wrap_script_with_scratch(script: str, scratch_dir: Path) -> str:
    """Create the per-job scratch before the instance starts; remove it on exit."""
    q = shlex.quote(str(scratch_dir))
    setup = (
        f"mkdir -m 700 {q}\n"
        f"trap 'rm -rf -- {q}' EXIT\n"
        f"trap 'exit 143' TERM INT\n"
    )
    return script.replace("set -e\n", "set -e\n" + setup, 1)


def provision_commands(
    username: str, uid: int, gid: int, nodes: list[str] | None = None
) -> list[list[str]]:
    """argv lists that create the account on every node plus its SLURM association."""
    validate_posix_username(username)
    home = str(compute_home(username))
    node_script = (
        f"getent group {username} >/dev/null || sudo groupadd -g {gid} {username}; "
        f"getent passwd {username} >/dev/null || sudo useradd -u {uid} -g {gid} "
        f"-d {shlex.quote(home)} -M -s /bin/bash {username}"
    )
    cmds = [["ssh", node, node_script] for node in (nodes or COMPUTE_NODES)]
    home_script = (
        f"sudo install -d -m 700 -o {uid} -g {gid} {shlex.quote(home)}; "
        f"sudo sacctmgr -i add user {username} DefaultAccount={COMPUTE_SLURM_ACCOUNT}"
    )
    controller = (nodes or COMPUTE_NODES)[0]
    cmds.append(["ssh", controller, home_script])
    return cmds
