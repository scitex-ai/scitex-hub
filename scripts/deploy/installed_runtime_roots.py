#!/usr/bin/env python3
"""Retain every cached runtime package while resolving its graph with Hub."""

from __future__ import annotations

import importlib.metadata as metadata
import re
import sys
from pathlib import Path


def installed_names(distributions=None) -> list[str]:
    """Return requirement-safe names, leaving the local Hub to its [all] input."""
    names = set()
    for dist in metadata.distributions() if distributions is None else distributions:
        name = dist.metadata.get("Name", "")
        if not isinstance(name, str) or not re.fullmatch(
            r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?", name
        ):
            raise ValueError("Installed distribution has an invalid project name")
        name = re.sub(r"[-_.]+", "-", name).lower()
        if name != "scitex-hub":
            names.add(name)
    if not names:
        raise ValueError("Installed runtime roots are empty")
    return sorted(names)


def main() -> None:
    names = installed_names()
    Path(sys.argv[1]).write_text("\n".join(names) + "\n")
    print(f"Retaining {len(names)} installed runtime roots for the final resolution")


if __name__ == "__main__":
    main()
