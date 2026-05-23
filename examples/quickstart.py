#!/usr/bin/env python3
"""Quickstart for scitex-cloud: import + show environment + version (offline)."""

import scitex_hub
from scitex_hub import get_environment, get_version
from scitex_hub._config._environments import ENVIRONMENTS


def main() -> int:
    print(f"scitex_hub version: {get_version()}")

    print(f"\navailable environments ({len(ENVIRONMENTS)}):")
    for name, env in ENVIRONMENTS.items():
        print(f"  - {name}: host={env.host}:{env.port} — {env.description}")

    dev = get_environment("dev")
    print("\nget_environment('dev'):")
    print(f"  name:    {dev.name}")
    print(f"  host:    {dev.host}:{dev.port}")
    print(f"  compose: {dev.docker_compose_file}")

    public = [n for n in dir(scitex_hub) if not n.startswith("_")]
    print(f"\nscitex_hub public symbols: {public}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
