#!/usr/bin/env python3
"""Build balanced pytest file groups and detect usable CPUs."""
from __future__ import annotations

import argparse
import math
import os
import re
from pathlib import Path


def test_weight(path: Path) -> int:
    """Estimate a file's collection cost from its test definitions."""
    text = path.read_text(errors="ignore")
    return max(1, len(re.findall(r"(?m)^\s*(?:async\s+)?def\s+test_", text)))


def group_files(files: list[Path], shard_count: int) -> list[list[Path]]:
    """Greedily balance indivisible test-file groups by collected-test proxy."""
    if shard_count < 1:
        raise ValueError("shard_count must be positive")
    groups: list[list[Path]] = [[] for _ in range(shard_count)]
    totals = [0] * shard_count
    weighted = sorted(((test_weight(path), path) for path in files), key=lambda x: (-x[0], str(x[1])))
    for weight, path in weighted:
        target = min(range(shard_count), key=lambda i: (totals[i], i))
        groups[target].append(path)
        totals[target] += weight
    return groups


def cgroup_cpu_limit() -> int | None:
    """Return the cgroup v2 CPU quota rounded down, if constrained."""
    try:
        quota, period = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if quota == "max":
            return None
        return max(1, math.floor(int(quota) / int(period)))
    except (FileNotFoundError, PermissionError, ValueError, ZeroDivisionError):
        return None


def effective_cpu_count() -> int:
    """Use the tightest of hardware, affinity, and cgroup limits."""
    limits = [os.cpu_count() or 1]
    try:
        limits.append(len(os.sched_getaffinity(0)))
    except AttributeError:
        pass
    quota = cgroup_cpu_limit()
    if quota is not None:
        limits.append(quota)
    return max(1, min(limits))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    files = sub.add_parser("files")
    files.add_argument("--index", type=int, required=True)
    files.add_argument("--count", type=int, required=True)
    files.add_argument("--root", type=Path, default=Path("tests"))
    sub.add_parser("workers")
    args = parser.parse_args()
    if args.command == "workers":
        print(effective_cpu_count())
        return
    if not 0 <= args.index < args.count:
        parser.error("index must be in [0, count)")
    discovered = sorted(args.root.rglob("test_*.py"))
    selected = group_files(discovered, args.count)[args.index]
    if not selected:
        raise SystemExit("selected shard is empty")
    for path in selected:
        print(path)


if __name__ == "__main__":
    main()
