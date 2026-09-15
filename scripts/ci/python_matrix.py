#!/usr/bin/env python3
"""Select supported Python versions for a GitHub Actions event."""
from __future__ import annotations

import argparse
import json

FULL = ["3.11", "3.12", "3.13"]


def versions_for(event: str, base_ref: str = "") -> list[str]:
    """Feature PRs to develop are representative-only; release paths are full."""
    if event == "pull_request" and base_ref == "develop":
        return ["3.11"]
    return FULL.copy()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True)
    parser.add_argument("--base-ref", default="")
    args = parser.parse_args()
    print(json.dumps(versions_for(args.event, args.base_ref), separators=(",", ":")))


if __name__ == "__main__":
    main()
