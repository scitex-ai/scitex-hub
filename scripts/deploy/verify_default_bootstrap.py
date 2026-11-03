"""Check image defaults and run the real root bootstrap with synthetic tmpfs state.

No Django entrypoint, database, server, model, or user data is invoked. The full
probe refuses nonempty/non-tmpfs mount roots before writing any fixture.
"""

import argparse
import hashlib
import json
import os
import pathlib
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile

ROOTS = ("/app/data", "/app/.scitex", "/app/logs", "/app/run")
DIRECTORIES = (
    "/app/data",
    "/app/data/users",
    "/app/data/slurm",
    "/app/logs",
    "/app/run",
    "/app/.scitex",
    "/app/.scitex/logs",
    "/app/.scitex/hub",
    "/app/.scitex/hub/runtime",
    "/app/.scitex/hub/runtime/logs",
)
PRIVATE_MOUNTS = ("/app/data/users", "/app/.scitex")
PROBE = """import json,os,sys
assert os.getuid()==os.geteuid()==1000
paths=json.loads(sys.argv[1])
assert all(os.path.isdir(p) and os.access(p,os.R_OK|os.W_OK|os.X_OK) for p in paths)
print('DEFAULT_BOOTSTRAP_JSON='+json.dumps({'uid':os.getuid(),'rwx_paths':paths}))
"""


def constructor_metadata(roots, directories, uid, gid):
    """Inspect owned default-state directories and every existing config file."""
    for name in directories:
        path = pathlib.Path(name)
        assert path.is_dir() and not path.is_symlink(), name
    entries = {}
    for name in roots:
        root = pathlib.Path(name)
        for path in (root, *root.rglob("*")):
            info = path.lstat()
            assert not path.is_symlink(), str(path)
            assert (info.st_uid, info.st_gid) == (uid, gid), str(path)
            assert stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), str(path)
            entries[str(path)] = {
                "uid": info.st_uid,
                "gid": info.st_gid,
                "mode": stat.S_IMODE(info.st_mode),
            }
    return entries


def constructor():
    """Inspect actual unmounted defaults, including root-owned config files."""
    account = pwd.getpwnam("scitex")
    assert account.pw_uid == 1000
    entries = constructor_metadata(ROOTS, DIRECTORIES, account.pw_uid, account.pw_gid)
    check = subprocess.run(
        [
            "gosu",
            "scitex",
            sys.executable,
            "-I",
            "-S",
            "-c",
            PROBE,
            json.dumps(DIRECTORIES),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert check.returncode == 0, check.stderr
    return {"constructor_paths": entries, "application_uid_rwx": True}


def full_root_init():
    """Exercise the unchanged full bootstrap, not extracted shell functions."""
    assert os.getuid() == 0
    mounts = {}
    for line in pathlib.Path("/proc/self/mountinfo").read_text().splitlines():
        left, right = line.split(" - ", 1)
        mounts[left.split()[4]] = right.split()[0]
    for name in PRIVATE_MOUNTS:
        path = pathlib.Path(name)
        assert mounts.get(name) == "tmpfs", "Only synthetic tmpfs mounts are admitted"
        assert not path.is_symlink() and not list(path.iterdir()), name
    parent = pathlib.Path("/app/data").stat()
    print(
        "DEFAULT_PARENT_JSON="
        + json.dumps(
            {
                "uid": parent.st_uid,
                "gid": parent.st_gid,
                "mode": stat.S_IMODE(parent.st_mode),
            }
        ),
        flush=True,
    )
    account = pwd.getpwnam("scitex")
    for name in PRIVATE_MOUNTS:
        os.chown(name, account.pw_uid, account.pw_gid)
        os.chmod(name, 0o700)
    private = []
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="bootstrap-smoke-"))
    os.chown(scratch, account.pw_uid, account.pw_gid)
    before = {}
    try:
        for name in PRIVATE_MOUNTS:
            folder = pathlib.Path(
                tempfile.mkdtemp(prefix=".owned-bootstrap-", dir=name)
            )
            os.chown(folder, account.pw_uid, account.pw_gid)
            folder.chmod(0o700)
            private.append(folder)
            file = folder / "private.txt"
            file.write_bytes(b"Owned synthetic bootstrap fixture; not user data")
            os.chown(file, account.pw_uid, account.pw_gid)
            file.chmod(0o600)
            for path in (pathlib.Path(name), folder, file):
                info = path.stat()
                before[str(path)] = (
                    stat.S_IMODE(info.st_mode),
                    info.st_uid,
                    info.st_gid,
                    hashlib.sha256(path.read_bytes()).hexdigest()
                    if path.is_file()
                    else None,
                )
        env = os.environ.copy()
        for key in tuple(env):
            if key.startswith(("PG", "SCITEX_STORE_")):
                env.pop(key)
        env.update(
            SCITEX_STORE_DSN="postgresql://unavailable@127.0.0.1:1/unavailable?connect_timeout=1",
            SCITEX_DIR=str(scratch / "state"),
            XDG_CACHE_HOME=str(scratch / "cache"),
            MPLCONFIGDIR=str(scratch / "matplotlib"),
        )
        result = subprocess.run(
            [
                "/root-init.sh",
                sys.executable,
                "-I",
                "-S",
                "-c",
                PROBE,
                json.dumps(DIRECTORIES),
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        assert result.returncode == 0, "Actual root-init bootstrap failed"
        marker = next(
            line
            for line in result.stdout.splitlines()
            if line.startswith("DEFAULT_BOOTSTRAP_JSON=")
        )
        after = {}
        for name in before:
            path = pathlib.Path(name)
            info = path.stat()
            after[name] = (
                stat.S_IMODE(info.st_mode),
                info.st_uid,
                info.st_gid,
                hashlib.sha256(path.read_bytes()).hexdigest()
                if path.is_file()
                else None,
            )
        assert after == before, "Bootstrap changed private fixture metadata or payload"
        return {
            "full_root_init": True,
            "private_metadata_payload_preserved": True,
            "application_probe": json.loads(marker.split("=", 1)[1]),
            "bootstrap_sha256": hashlib.sha256(
                pathlib.Path("/root-init.sh").read_bytes()
            ).hexdigest(),
        }
    finally:
        for folder in private:
            shutil.rmtree(folder)
        shutil.rmtree(scratch)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--constructor", action="store_true")
    group.add_argument("--full-root-init", action="store_true")
    args = parser.parse_args()
    proof = constructor() if args.constructor else full_root_init()
    print("BOOTSTRAP_PROOF_JSON=" + json.dumps(proof, sort_keys=True))
