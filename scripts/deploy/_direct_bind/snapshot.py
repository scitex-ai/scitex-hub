"""Snapshot clean Git sources; serving checkouts are never built or edited."""

import subprocess
from pathlib import Path


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
    if git(source, "status", "--porcelain", "--untracked-files=normal"):
        raise ValueError(
            "commit development source changes before a container recreation"
        )
    return git(source, "rev-parse", "HEAD")


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
        head = identity(row["source"])
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
        objects.update(object_directories(destination / ".git/objects"))
        snapshots[target] = dict(row, head=head, snapshot=str(destination))
    return snapshots, sorted(
        str(path)
        for path in objects
        if path != directory and directory not in path.parents
    )


def verify(snapshots):
    for row in snapshots.values():
        if identity(row["source"]) != row["head"]:
            raise ValueError("development source changed during qualification")
