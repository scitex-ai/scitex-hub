#!/usr/bin/env python3
"""Acquire the genuine sibling sources required by Hub's file: dependencies.

This stages Node source only. It never installs a Python package, runs npm,
updates an existing checkout, or substitutes a wheel for a missing leaf tree.
Hub's selected Python SDK remains separate from FigRecipe's nested SDK.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    commit: str
    package: str
    package_sha256: str


SOURCES = (
    Source(
        "scitex-ui", "https://github.com/scitex-ai/scitex-ui.git",
        "764c92cbab5818ad88ef69bf146bd2ce2c36c0ba", "package.json",
        "8c4ef2f7570937bee822f29599a532a07a527ce511f30ba9138640c4c9db3e15",
    ),
    Source(
        "figrecipe", "https://github.com/scitex-ai/figrecipe.git",
        "0e16e703a95941eb4e4ab77ff986326baf79c0f6",
        "src/figrecipe/_django/frontend/package.json",
        "4f7a2e9b5ab8c244277423f1514f57c3b6768baab65650d25575b696ec0f0b9b",
    ),
    Source(
        "scitex-sdk", "https://github.com/scitex-ai/scitex-sdk.git",
        "9f5747a8ef5431e7412cdafa58f0dc0f3609a74d",
        "src/scitex_sdk/package.json",
        "50ac8154cbe121d1dfcd9e74977399abec6b11ecf6861c479883f26551d8efb7",
    ),
)


def _git(directory: Path, *arguments: str) -> str:
    environment = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(
        ["git", "-C", str(directory), *arguments], check=True,
        capture_output=True, text=True, timeout=120, env=environment,
    )
    return result.stdout


def _member_path(root: Path, relative: PurePosixPath) -> Path:
    cursor = root
    for part in relative.parts[:-1]:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"Source directory is a symlink: {relative}")
    return root.joinpath(*relative.parts)


def _regular_path(root: Path, relative: PurePosixPath) -> Path:
    path = _member_path(root, relative)
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError(f"Source file is not regular: {relative}")
    return path


def verify_checkout(directory: Path, source: Source) -> dict:
    """Verify real source bytes, including changes hidden from Git status."""
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"Source root is not a regular directory: {source.name}")
    if Path(_git(directory, "rev-parse", "--show-toplevel").strip()) != directory:
        raise ValueError(f"Source is not its own checkout: {source.name}")
    if _git(directory, "rev-parse", "HEAD").strip() != source.commit:
        raise ValueError(f"Source checkout has a different commit: {source.name}")
    if _git(directory, "status", "--porcelain", "--untracked-files=no").strip():
        raise ValueError(f"Source checkout has tracked changes: {source.name}")
    count = 0
    for record in _git(directory, "ls-tree", "-r", "-z", source.commit).split("\0"):
        if not record:
            continue
        metadata, name = record.split("\t", 1)
        mode, kind, blob = metadata.split()
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name:
            raise ValueError("Source tree contains an unsafe member")
        if kind != "blob" or mode not in {"100644", "100755", "120000"}:
            raise ValueError("Source tree contains an unsupported member")
        if mode == "120000":
            # Preserve genuine documentation links as literal Git bytes only.
            # Their targets are never followed or used as frontend source.
            path = _member_path(directory, relative)
            if not path.is_symlink():
                raise ValueError(f"Source literal link changed: {name}")
            data = os.fsencode(os.readlink(path))
        else:
            path = _regular_path(directory, relative)
            if bool(path.lstat().st_mode & 0o111) != (mode == "100755"):
                raise ValueError(f"Source executable mode changed: {name}")
            data = path.read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if actual != blob:
            raise ValueError(f"Source bytes differ from the selected commit: {name}")
        count += 1
    package = _regular_path(directory, PurePosixPath(source.package))
    if hashlib.sha256(package.read_bytes()).hexdigest() != source.package_sha256:
        raise ValueError(f"Source npm manifest differs from the selected input: {source.name}")
    return {"name": source.name, "commit": source.commit, "tracked_entries": count}


def acquire_source(parent: Path, source: Source) -> dict:
    directory = parent / source.name
    if directory.exists() or directory.is_symlink():
        return verify_checkout(directory, source)
    # Exclusive mkdir cannot replace another caller's checkout or symlink.
    # A failed acquisition remains visible and is refused on the next call.
    directory.mkdir()
    _git(directory, "init", "--quiet")
    _git(directory, "fetch", "--depth=1", source.url, source.commit)
    _git(directory, "checkout", "--quiet", "--detach", "FETCH_HEAD")
    return verify_checkout(directory, source)


def prepare(project: Path) -> list[dict]:
    project = project.resolve(strict=True)
    declarations = json.loads((project / "package.json").read_text())["dependencies"]
    required = {
        "@scitex/ui": "file:../scitex-ui",
        "figrecipe-editor": "file:../figrecipe/src/figrecipe/_django/frontend",
        "@scitex/sdk": "file:.frontend-packages/scitex-sdk.tgz",
    }
    if any(declarations.get(name) != path for name, path in required.items()):
        raise ValueError("Hub frontend dependency declarations changed")
    receipts = [acquire_source(project.parent, source) for source in SOURCES]
    frontend = project.parent / "figrecipe/src/figrecipe/_django/frontend"
    metadata = json.loads((frontend / "package.json").read_text())
    if (metadata.get("dependencies", {}).get("@scitex/sdk") !=
            "file:../../../../../scitex-sdk/src/scitex_sdk"):
        raise ValueError("FigRecipe's genuine nested SDK declaration changed")
    if metadata.get("scitexSdk", {}).get("commit") != SOURCES[2].commit:
        raise ValueError("FigRecipe's declared SDK source differs from the selected input")
    return receipts


def main() -> int:
    try:
        if sys.argv[1:]:
            raise ValueError("Usage: prepare_frontend_sources.py")
        receipts = prepare(Path(__file__).resolve().parents[2])
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"ERROR: frontend source acquisition refused: {error}", file=sys.stderr)
        return 1
    print(json.dumps(receipts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
