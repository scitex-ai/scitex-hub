#!/usr/bin/env python3
"""Local-only preflight for dirt that tracked-source CI gates cannot inspect."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests.tracked_source import local_untracked_paths  # noqa: E402


def main() -> int:
    paths = local_untracked_paths(REPO)
    if not paths:
        print("local untracked preflight: clean")
        return 0
    print(
        "local untracked preflight: files below are outside CI tracked-source claims",
        file=sys.stderr,
    )
    for path in paths:
        # repr keeps embedded whitespace/newlines on one line; content is never read.
        print(f"  {path!r}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
