"""Explicit offline-to-render refresh: public GitHub REST, never visitor requests.

Run from the repository root:
python -m apps.infra.public_app.services.refresh_landing_github
"""

from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .landing_github import API_ROOT, REPOSITORIES, SNAPSHOT, validate_repository


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Do not follow API redirects into a different repository or host."""
        return None


def refresh_snapshot(*, timeout: float = 4, budget: float = 60) -> dict:
    """Fetch fixed public repositories with bounded requests and a batch deadline.

    Timeout bounds socket operations; the batch budget is checked between
    requests. A failed/limited/invalid response becomes explicitly unavailable.
    No environment token or authentication configuration is read.
    """
    if not all(math.isfinite(x) and x > 0 for x in (timeout, budget)):
        raise ValueError("timeout and budget must be finite and positive")
    opener = urllib.request.build_opener(_NoRedirect())
    deadline = time.monotonic() + budget
    records = {}
    for name in REPOSITORIES:
        remaining = deadline - time.monotonic()
        row = {"available": False, "source": API_ROOT + name}
        if remaining > 0:
            request = urllib.request.Request(
                API_ROOT + name,
                headers={
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "SciTeX-landing-public-metadata",
                },
            )
            try:
                with opener.open(request, timeout=min(timeout, remaining)) as response:
                    raw = response.read(128_001)
                    if len(raw) > 128_000:
                        raise ValueError("repository response exceeds size limit")
                    row = validate_repository(name, json.loads(raw))
            except (OSError, ValueError, urllib.error.URLError):
                pass  # Explicit unavailable row; never retain or invent current counts.
        records[name] = row
    return {
        "schema": 1,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repositories": records,
    }


def write_snapshot(data: dict, destination: Path = SNAPSHOT) -> None:
    """Atomically publish a complete snapshot; leave the prior file on failure."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=destination.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o644)
        os.replace(temporary, destination)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main() -> None:
    """Refresh the checked-in public snapshot; no server or scheduler is started."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=SNAPSHOT)
    args = parser.parse_args()
    data = refresh_snapshot()
    write_snapshot(data, args.output)
    if not all(row["available"] for row in data["repositories"].values()):
        parser.exit(
            1,
            "Some GitHub counts are unavailable; inspect the snapshot before committing.\n",
        )


if __name__ == "__main__":
    main()
