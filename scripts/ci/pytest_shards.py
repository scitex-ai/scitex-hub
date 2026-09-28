#!/usr/bin/env python3
"""Build deterministic, safety-aware pytest file shards.

This planner is deliberately not wired into required CI yet.  It models every
cross-file serial directory as one indivisible scheduling bundle so a later CI
migration cannot split tests that share mutable state.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


@dataclass(frozen=True)
class SerialGroup:
    """Declared directories whose test files must stay on one shard."""

    name: str
    directories: tuple[Path, ...]


@dataclass(frozen=True)
class Shard:
    """A planned shard and its estimated test count."""

    files: tuple[Path, ...]
    weight: int


@dataclass(frozen=True)
class _Bundle:
    key: str
    files: tuple[Path, ...]
    weight: int


_TEST_DEFINITION = re.compile(r"(?m)^\s*(?:async\s+)?def\s+test_")


def test_weight(repository_root: Path, path: Path) -> int:
    """Estimate file cost from test definitions, failing on unreadable input."""

    text = (repository_root / path).read_text(encoding="utf-8")
    return max(1, len(_TEST_DEFINITION.findall(text)))


def _in_directory(path: Path, directory: Path) -> bool:
    return path == directory or directory in path.parents


def plan_shards(
    repository_root: Path,
    files: Iterable[Path],
    shard_count: int,
    *,
    serial_groups: tuple[SerialGroup, ...] = (),
    weight_file: Callable[[Path, Path], int] = test_weight,
) -> tuple[Shard, ...]:
    """Balance files by weight without splitting declared serial groups."""

    if shard_count < 1:
        raise ValueError("shard_count must be positive")

    ordered_files = tuple(sorted(Path(path) for path in files))
    if not ordered_files:
        raise ValueError("no test files selected")
    if len(set(ordered_files)) != len(ordered_files):
        raise ValueError("test file selection contains duplicates")
    group_names = [group.name for group in serial_groups]
    if len(set(group_names)) != len(group_names):
        raise ValueError("serial group names must be unique")
    for group in serial_groups:
        if not group.name or not group.directories:
            raise ValueError("serial groups require a name and at least one directory")
        if len(set(group.directories)) != len(group.directories):
            raise ValueError(f"serial group {group.name!r} repeats a directory")
        for directory in group.directories:
            if directory.is_absolute() or ".." in directory.parts:
                raise ValueError(
                    f"serial group {group.name!r} has a non-repository-relative path"
                )

    grouped: dict[str, list[Path]] = {group.name: [] for group in serial_groups}
    ungrouped: list[Path] = []
    for path in ordered_files:
        matches = [
            group
            for group in serial_groups
            if any(_in_directory(path, directory) for directory in group.directories)
        ]
        if len(matches) > 1:
            names = ", ".join(group.name for group in matches)
            raise ValueError(f"{path} belongs to multiple serial groups: {names}")
        if matches:
            grouped[matches[0].name].append(path)
        else:
            ungrouped.append(path)

    bundles: list[_Bundle] = []
    for group in serial_groups:
        members = tuple(grouped[group.name])
        if not members:
            raise ValueError(f"serial group {group.name!r} selected no files")
        for directory in group.directories:
            if not any(_in_directory(path, directory) for path in members):
                raise ValueError(
                    f"serial group {group.name!r} directory {directory} selected no files"
                )
        bundles.append(
            _Bundle(
                key=f"serial:{group.name}",
                files=members,
                weight=sum(weight_file(repository_root, path) for path in members),
            )
        )
    for path in ungrouped:
        bundles.append(
            _Bundle(
                key=f"file:{path.as_posix()}",
                files=(path,),
                weight=weight_file(repository_root, path),
            )
        )

    if shard_count > len(bundles):
        raise ValueError(
            f"{shard_count} shards would leave an empty selection from "
            f"{len(bundles)} indivisible bundles"
        )

    shard_files: list[list[Path]] = [[] for _ in range(shard_count)]
    shard_weights = [0] * shard_count
    for bundle in sorted(bundles, key=lambda item: (-item.weight, item.key)):
        index = min(range(shard_count), key=lambda item: (shard_weights[item], item))
        shard_files[index].extend(bundle.files)
        shard_weights[index] += bundle.weight

    shards = tuple(
        Shard(files=tuple(sorted(paths)), weight=shard_weights[index])
        for index, paths in enumerate(shard_files)
    )
    selected = Counter(path for shard in shards for path in shard.files)
    expected = Counter(ordered_files)
    if selected != expected:
        raise ValueError("planned shards do not cover every selected file exactly once")
    if any(not shard.files for shard in shards):
        raise ValueError("planned shard has an empty file selection")
    return shards


def discover_test_files(repository_root: Path, test_root: Path) -> tuple[Path, ...]:
    """Discover test files as repository-relative paths."""

    repository_root = repository_root.resolve()
    search_root = (repository_root / test_root).resolve()
    if not search_root.is_relative_to(repository_root):
        raise ValueError("test root must be inside the repository root")
    if not search_root.is_dir():
        raise ValueError(f"test root is not a directory: {test_root}")
    files = tuple(
        sorted(
            path.relative_to(repository_root)
            for path in search_root.rglob("test_*.py")
            if path.is_file()
        )
    )
    if not files:
        raise ValueError(f"no test files found under {test_root}")
    return files


def _manifest(
    shards: tuple[Shard, ...], serial_groups: tuple[SerialGroup, ...]
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "serial_groups": [
            {
                "name": group.name,
                "directories": [path.as_posix() for path in group.directories],
            }
            for group in serial_groups
        ],
        "shards": [
            {
                "index": index,
                "weight": shard.weight,
                "files": [path.as_posix() for path in shard.files],
            }
            for index, shard in enumerate(shards)
        ],
    }


def _serial_group(value: str) -> tuple[str, Path]:
    """Parse NAME=REPOSITORY/RELATIVE/DIRECTORY from the command line."""

    name, separator, raw_directory = value.partition("=")
    directory = Path(raw_directory)
    if not separator or not name or not raw_directory:
        raise argparse.ArgumentTypeError("serial groups must use NAME=PATH")
    if directory.is_absolute() or ".." in directory.parts:
        raise argparse.ArgumentTypeError(
            "serial group paths must be repository-relative and cannot contain '..'"
        )
    return name, directory


def _coalesce_serial_groups(
    declarations: list[tuple[str, Path]],
) -> tuple[SerialGroup, ...]:
    grouped: dict[str, list[Path]] = {}
    for name, directory in declarations:
        directories = grouped.setdefault(name, [])
        if directory in directories:
            raise ValueError(f"serial group {name!r} repeats directory {directory}")
        directories.append(directory)
    return tuple(
        SerialGroup(name=name, directories=tuple(sorted(directories)))
        for name, directories in sorted(grouped.items())
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Plan deterministic pytest file shards as a JSON manifest."
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--test-root", type=Path, default=Path("tests"))
    parser.add_argument("--shards", type=int, required=True)
    parser.add_argument(
        "--serial-group",
        action="append",
        default=[],
        type=_serial_group,
        metavar="NAME=PATH",
        help="keep every selected test under PATH on one shard; repeatable",
    )
    args = parser.parse_args(argv)

    try:
        files = discover_test_files(args.repo_root, args.test_root)
        serial_groups = _coalesce_serial_groups(args.serial_group)
        shards = plan_shards(
            args.repo_root.resolve(),
            files,
            args.shards,
            serial_groups=serial_groups,
        )
    except (OSError, UnicodeError, ValueError) as error:
        print(f"pytest shard planning failed: {error}", file=sys.stderr)
        return 1

    json.dump(_manifest(shards, serial_groups), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
