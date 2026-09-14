"""The user's hub workspace as a confined filesystem.

Every public function takes a path RELATIVE to the user's root
(``data/users/<username>/``) and refuses anything that could leave it.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Union

from apps.infra.project_app.services.filesystem.permissions import (
    get_user_data_root,
)

DOWNLOADS = "Downloads"
RECORDINGS = "Recordings"
PROJECTS = "proj"
STANDARD_FOLDERS = (DOWNLOADS, RECORDINGS)
# Projects are managed by the project app; removing these here would orphan
# the Project rows that point at them.
PROTECTED = frozenset({PROJECTS, DOWNLOADS, RECORDINGS})


class WorkspacePathError(ValueError):
    """A path that is malformed or would leave the user's root."""


@dataclass(frozen=True)
class Entry:
    name: str
    path: str
    is_dir: bool
    size: int
    modified: float


def user_root(user) -> Path:
    root = get_user_data_root(user)
    root.mkdir(parents=True, exist_ok=True)
    for name in STANDARD_FOLDERS:
        (root / name).mkdir(exist_ok=True)
    return root


def _clean_parts(rel: str) -> tuple[str, ...]:
    if rel is None:
        raise WorkspacePathError("missing path")
    if "\x00" in rel or "\\" in rel:
        raise WorkspacePathError("invalid character in path")
    pure = PurePosixPath(rel)
    if pure.is_absolute():
        raise WorkspacePathError("absolute paths are not allowed")
    parts = tuple(p for p in pure.parts if p not in ("", "."))
    for part in parts:
        # Dot-entries (.ssh, .scitex, .git) hold credentials and app state.
        if part == ".." or part.startswith("."):
            raise WorkspacePathError("path leaves the workspace")
    return parts


def normalize(rel: str) -> str:
    return "/".join(_clean_parts(rel))


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def resolve_path(root: Path, rel: str, *, follow: bool = True) -> Path:
    """The absolute path for ``rel`` under ``root``, or WorkspacePathError.

    ``follow=False`` checks only the parent chain, so a symlink itself can
    be renamed or deleted without touching what it points at.
    """
    candidate = root.joinpath(*_clean_parts(rel))
    check = candidate if follow else candidate.parent
    if not _inside(root, check):
        raise WorkspacePathError("path leaves the workspace")
    return candidate


def _valid_name(name: str) -> str:
    name = (name or "").strip()
    if not name or "/" in name or "\\" in name or "\x00" in name:
        raise WorkspacePathError("invalid name")
    if name in (".", "..") or name.startswith("."):
        raise WorkspacePathError("invalid name")
    return name


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def list_dir(root: Path, rel: str = "") -> list[Entry]:
    directory = resolve_path(root, rel)
    if not directory.is_dir():
        raise FileNotFoundError(rel)
    entries = []
    for child in directory.iterdir():
        if child.name.startswith(".") or not _inside(root, child):
            continue
        try:
            stat = child.stat()
        except OSError:
            continue
        entries.append(
            Entry(
                name=child.name,
                path=relative(root, child),
                is_dir=child.is_dir(),
                size=0 if child.is_dir() else stat.st_size,
                modified=stat.st_mtime,
            )
        )
    entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))
    return entries


def unique_path(directory: Path, filename: str) -> Path:
    """``name.ext``, else ``name (1).ext``, ``name (2).ext`` ..."""
    name = _valid_name(Path(filename).name)
    stem, suffix = os.path.splitext(name)
    candidate = directory / name
    n = 1
    while candidate.exists() or candidate.is_symlink():
        candidate = directory / f"{stem} ({n}){suffix}"
        n += 1
    return candidate


def _write_exclusive(directory: Path, filename: str, chunks) -> Path:
    # O_EXCL closes the race between picking a free name and creating it.
    while True:
        target = unique_path(directory, filename)
        try:
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            continue
        with os.fdopen(fd, "wb") as out:
            for chunk in chunks:
                out.write(chunk)
        return target


def save_upload(root: Path, folder_rel: str, uploaded_file) -> Path:
    folder = resolve_path(root, folder_rel)
    if not folder.is_dir():
        raise FileNotFoundError(folder_rel)
    return _write_exclusive(folder, uploaded_file.name, uploaded_file.chunks())


def make_dir(root: Path, parent_rel: str, name: str) -> Path:
    parent = resolve_path(root, parent_rel)
    target = parent / _valid_name(name)
    target.mkdir()
    return target


def _guard_mutable(root: Path, rel: str) -> Path:
    parts = _clean_parts(rel)
    if not parts:
        raise WorkspacePathError("the workspace root cannot be changed")
    is_standard = len(parts) == 1 and parts[0] in PROTECTED
    is_project_root = len(parts) == 2 and parts[0] == PROJECTS
    if is_standard or is_project_root:
        raise WorkspacePathError("this folder is managed by SciTeX")
    target = resolve_path(root, rel, follow=False)
    if not (target.exists() or target.is_symlink()):
        raise FileNotFoundError(rel)
    return target


def rename(root: Path, rel: str, new_name: str) -> Path:
    source = _guard_mutable(root, rel)
    target = source.parent / _valid_name(new_name)
    if target.exists() or target.is_symlink():
        raise FileExistsError(new_name)
    source.rename(target)
    return target


def move(root: Path, rel: str, dest_folder_rel: str) -> Path:
    source = _guard_mutable(root, rel)
    dest_folder = resolve_path(root, dest_folder_rel)
    if not dest_folder.is_dir():
        raise FileNotFoundError(dest_folder_rel)
    if source.is_dir() and not source.is_symlink():
        if dest_folder.resolve().is_relative_to(source.resolve()):
            raise WorkspacePathError("cannot move a folder into itself")
    target = dest_folder / source.name
    if target.exists() or target.is_symlink():
        raise FileExistsError(source.name)
    shutil.move(str(source), str(target))
    return target


def delete(root: Path, rel: str) -> None:
    target = _guard_mutable(root, rel)
    if target.is_dir() and not target.is_symlink():
        shutil.rmtree(target)
    else:
        target.unlink()


def save_to_downloads(user, filename: str, data: Union[bytes, str, Path]) -> Path:
    """Save an export into the user's Downloads folder; never overwrites.

    ``data`` is the file content (bytes) or a path to copy from.
    """
    downloads = user_root(user) / DOWNLOADS
    if isinstance(data, (bytes, bytearray)):
        return _write_exclusive(downloads, filename, [bytes(data)])
    with open(data, "rb") as source:
        return _write_exclusive(
            downloads, filename, iter(lambda: source.read(1 << 20), b"")
        )
