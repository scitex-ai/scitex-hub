"""Safe, fail-closed Git-index corpus for repository source-policy gates.

CI and local gates inspect the same staged/index blobs.  Working-tree and
untracked files are deliberately outside that claim; use ``local_untracked_paths``
for a local-only dirt preflight.
"""
from __future__ import annotations

import fnmatch
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class TrackedSourceError(RuntimeError):
    """The Git index cannot provide a trustworthy policy corpus."""


class EmptyTrackedSetError(TrackedSourceError):
    """A requested tracked corpus is empty and would make a gate vacuous."""


@dataclass(frozen=True, slots=True)
class TrackedSourceFile:
    path: str
    data: bytes
    mode: str
    repo: Path

    @property
    def name(self) -> str:
        return Path(self.path).name

    def __fspath__(self) -> str:
        return str(self.repo / self.path)

    def relative_to(self, other: Path) -> Path:
        return (self.repo / self.path).relative_to(other)

    def text(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        return self.data.decode(encoding, errors)

    def read_text(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        """Path-compatible read that still returns staged index content."""
        return self.text(encoding, errors)


def _run(repo: Path, args: list[str], *, stdin: bytes | None = None) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        input=stdin,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        # Do not expose stderr: hooks/aliases can echo credentials or command lines.
        raise TrackedSourceError(f"git {args[0]} failed with exit {completed.returncode}")
    return completed.stdout


def _index_entries(repo: Path) -> list[tuple[str, str, str]]:
    raw = _run(repo, ["ls-files", "--stage", "-z"])
    entries: list[tuple[str, str, str]] = []
    for record in filter(None, raw.split(b"\0")):
        metadata, raw_path = record.split(b"\t", 1)
        mode, oid, stage = metadata.decode("ascii").split()
        path = raw_path.decode("utf-8", "surrogateescape")
        if stage != "0":
            raise TrackedSourceError(
                f"unmerged index entry at {path!r}; resolve conflicts before policy scans"
            )
        entries.append((path, oid, mode))
    return entries


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    if not patterns:
        return True
    return any(
        fnmatch.fnmatchcase(path, pattern)
        or fnmatch.fnmatchcase(Path(path).name, pattern)
        for pattern in patterns
    )


def _batch_blobs(repo: Path, oids: Iterable[str]) -> dict[str, bytes]:
    unique = tuple(dict.fromkeys(oids))
    if not unique:
        return {}
    payload = "".join(f"{oid}\n" for oid in unique).encode("ascii")
    raw = _run(repo, ["cat-file", "--batch"], stdin=payload)
    blobs: dict[str, bytes] = {}
    offset = 0
    for requested in unique:
        end = raw.index(b"\n", offset)
        header = raw[offset:end].decode("ascii").split()
        if len(header) != 3 or header[1] != "blob":
            raise TrackedSourceError("git cat-file returned a non-blob index object")
        oid, _, size_text = header
        size = int(size_text)
        start = end + 1
        blobs[requested] = raw[start : start + size]
        if len(blobs[requested]) != size:
            raise TrackedSourceError("git cat-file returned a truncated index blob")
        offset = start + size + 1
        if oid != requested:
            raise TrackedSourceError("git cat-file returned objects out of order")
    return blobs


def tracked_source_files(
    repo: Path,
    patterns: Iterable[str] = (),
    *,
    require_nonempty: bool = True,
) -> tuple[TrackedSourceFile, ...]:
    """Return matching stage-0 index files and their staged bytes.

    Staged additions/edits are included, staged deletions are absent, unstaged
    edits are ignored, and an unmerged index fails closed.
    """
    repo = repo.resolve()
    wanted = tuple(patterns)
    entries = [entry for entry in _index_entries(repo) if _matches(entry[0], wanted)]
    if require_nonempty and not entries:
        raise EmptyTrackedSetError(
            f"Git index has no tracked files matching {wanted!r}; refusing vacuous scan"
        )
    blobs = _batch_blobs(repo, (oid for _, oid, _ in entries))
    return tuple(
        TrackedSourceFile(path=path, data=blobs[oid], mode=mode, repo=repo)
        for path, oid, mode in entries
    )


def local_untracked_paths(repo: Path) -> tuple[str, ...]:
    """Return non-ignored untracked names for local preflight; never read content."""
    raw = _run(repo.resolve(), ["ls-files", "--others", "--exclude-standard", "-z"])
    return tuple(
        item.decode("utf-8", "surrogateescape")
        for item in raw.split(b"\0")
        if item
    )
