"""Run the source-dirt check without leaking its output.

Failure events go to the supervisor-captured stream.  That is durable, but until
an operator reads the execution log it is only ``unconfirmed`` delivery; this
module never claims that a human was notified.
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
from pathlib import Path
from typing import Callable

DELIVERY_NOT_REQUIRED = "not_required"
DELIVERY_UNCONFIRMED = "unconfirmed"
DELIVERY_FAILED = "failed"
CHECK_TIMEOUT_SEC = 240


def emit_event(event: dict[str, object], writer: Callable[[str], object]) -> str:
    """Write one content-free JSON event and report honest delivery state."""
    try:
        writer(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
    except Exception:
        return DELIVERY_FAILED
    return DELIVERY_UNCONFIRMED


def run(checkout: Path, *, writer: Callable[[str], object] = sys.stderr.write) -> int:
    """Run ``make check-source-dirt`` in *checkout*, preserving nonzero status."""
    base = {
        "event": "scitex_hub.source_dirt",
        "host": socket.gethostname(),
        "checkout": str(checkout),
    }
    try:
        completed = subprocess.run(
            ["make", "check-source-dirt"],
            cwd=checkout,
            capture_output=True,
            text=True,
            timeout=CHECK_TIMEOUT_SEC,
            check=False,
        )
        exit_code = completed.returncode
    except subprocess.TimeoutExpired:
        exit_code = 124

    if exit_code == 0:
        event = {**base, "status": "clean", "check_exit_code": 0, "delivery": DELIVERY_NOT_REQUIRED}
        try:
            writer(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        except Exception:
            return 70
        return 0

    event = {**base, "status": "failed", "check_exit_code": exit_code, "delivery": DELIVERY_UNCONFIRMED}
    state = emit_event(event, writer)
    if state == DELIVERY_FAILED:
        # Static fallback: never interpolate exceptions, output, environment, or credentials.
        try:
            sys.stderr.write('{"event":"scitex_hub.source_dirt","delivery":"failed","status":"failed"}\n')
        except Exception:
            pass
        return 70
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", required=True, type=Path)
    args = parser.parse_args(argv)
    return run(args.checkout)


if __name__ == "__main__":
    raise SystemExit(main())
