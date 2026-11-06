"""Snapshot clean Git sources; serving checkouts are never built or edited."""

import hashlib
import os
import subprocess
from pathlib import Path

from . import locks


def git(source, *args):
    return subprocess.check_output(
        ["git", "-C", str(source), *args], stderr=subprocess.PIPE, text=True, timeout=60
    ).strip()


def identity(source):
    if (
        Path(git(source, "rev-parse", "--show-toplevel")).resolve()
        != Path(source).resolve()
    ):
        raise ValueError("direct-bound packages must be repository roots")
    return {
        "head": git(source, "rev-parse", "HEAD"),
        "locks": locks.fingerprints(source),
    }


def object_directories(objects):
    """Git shared clones need object stores, not serving data or credentials."""
    pending, result = [Path(objects).resolve()], set()
    while pending:
        path = pending.pop()
        if path in result:
            continue
        if not path.is_dir() or any(c in str(path) for c in ",:\x00"):
            raise ValueError("Git object store is unavailable")
        result.add(path)
        if len(result) > 128:
            raise ValueError("Git object-store chain exceeds the supported bound")
        alternate = path / "info/alternates"
        if alternate.exists():
            for line in alternate.read_text().splitlines():
                if line:
                    pending.append((path / line).resolve())
    return result


def prepare(roots, directory):
    snapshots, objects = {}, set()
    for target, row in roots.items():
        state = identity(row["source"])
        head = state["head"]
        destination = directory / ("hub" if target == "/app" else target.lstrip("/"))
        subprocess.run(
            [
                "git",
                "clone",
                "--shared",
                "--no-checkout",
                "--",
                row["source"],
                str(destination),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=60,
        )
        git(destination, "checkout", "--detach", head)
        if git(destination, "rev-parse", "HEAD") != head:
            raise ValueError("snapshot checkout identity differs")
        for relative, fingerprint in state["locks"].items():
            output = destination / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            payload = locks.read_payload(Path(row["source"]) / relative)
            if hashlib.sha256(payload).hexdigest() != fingerprint["sha256"]:
                raise ValueError("generated npm lock changed while being snapshotted")
            parent = output.parent.resolve()
            if (
                parent != destination.resolve()
                and destination.resolve() not in parent.parents
            ):
                raise ValueError("generated lock snapshot escapes its owned repository")
            if output.is_symlink():
                output.unlink()
            descriptor = os.open(
                output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
        objects.update(object_directories(destination / ".git/objects"))
        snapshots[target] = dict(
            row, head=head, dirty_locks=state["locks"], snapshot=str(destination)
        )
    return snapshots, sorted(
        str(path)
        for path in objects
        if path != directory and directory not in path.parents
    )


def verify(snapshots):
    for row in snapshots.values():
        if identity(row["source"]) != {
            "head": row["head"],
            "locks": row["dirty_locks"],
        }:
            raise ValueError("development source changed during qualification")
