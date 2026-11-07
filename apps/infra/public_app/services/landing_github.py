"""Public repository catalog and local-only landing snapshot reader.

No network, credentials, user state or database access occurs during rendering.
"""

from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parents[1] / "data/landing_github.json"
API_ROOT = "https://api.github.com/repos/scitex-ai/"
REPOSITORY_GROUPS = (
    ("Platform", ("scitex-python", "scitex-hub", "scitex-sdk")),
    (
        "Research apps",
        (
            "scitex-agent-container",
            "scitex-cards",
            "scitex-storage",
            "scitex-scholar",
            "scitex-stats",
            "figrecipe",
            "scitex-writer",
            "scitex-live-paper",
            "scitex-agentic-journal",
        ),
    ),
    (
        "Shared foundations",
        (
            "scitex-clew",
            "scitex-io",
            "scitex-dev",
            "openalex-local",
            "crossref-local",
        ),
    ),
)
REPOSITORIES = tuple(name for _, names in REPOSITORY_GROUPS for name in names)


def validate_repository(name: str, payload: object) -> dict:
    """Reduce an official public repository response to non-sensitive fields."""
    if name not in REPOSITORIES or not isinstance(payload, dict):
        raise ValueError("unknown repository or malformed metadata")
    if (
        payload.get("full_name") != f"scitex-ai/{name}"
        or payload.get("private") is not False
    ):
        raise ValueError("metadata does not identify the expected public repository")
    for key in ("stargazers_count", "forks_count"):
        if type(payload.get(key)) is not int or payload[key] < 0:
            raise ValueError("invalid repository count")
    description = payload.get("description")
    if description is not None and not isinstance(description, str):
        raise ValueError("invalid repository description")
    return {
        "available": True,
        "stars": payload["stargazers_count"],
        "forks": payload["forks_count"],
        "description": (description or "")[:400],
        "source": API_ROOT + name,
    }


@lru_cache(maxsize=2)
def _read_snapshot(path: str, modified_ns: int) -> dict:
    """Cache immutable snapshot bytes until the source file is replaced."""
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(128_001)
        if len(raw) > 128_000:
            return {}
        data = json.loads(raw)
        if (
            not isinstance(data, dict)
            or type(data.get("schema")) is not int
            or data["schema"] != 1
        ):
            return {}
        timestamp = data.get("checked_at")
        if (
            not isinstance(timestamp, str)
            or datetime.fromisoformat(timestamp).tzinfo is None
        ):
            return {}
        return data
    except (OSError, ValueError):
        return {}


def repository_cards(snapshot: Path = SNAPSHOT) -> dict:
    """Return all catalog cards, with unavailable counts rather than fake zeros."""
    try:
        data = _read_snapshot(str(snapshot), snapshot.stat().st_mtime_ns)
    except OSError:
        data = {}
    records = data.get("repositories", {})
    if not isinstance(records, dict):
        records = {}
    checked_at = data.get("checked_at")
    groups = []
    for label, names in REPOSITORY_GROUPS:
        cards = []
        for name in names:
            record = records.get(name, {})
            available = (
                isinstance(record, dict)
                and record.get("available") is True
                and all(
                    type(record.get(key)) is int and record[key] >= 0
                    for key in ("stars", "forks")
                )
                and record.get("source") == API_ROOT + name
                and isinstance(record.get("description", ""), str)
            )
            cards.append(
                {
                    "name": name,
                    "url": "https://github.com/scitex-ai/" + name,
                    "available": available,
                    "stars": record["stars"] if available else None,
                    "forks": record["forks"] if available else None,
                    "description": record.get("description", "") if available else "",
                }
            )
        groups.append({"label": label, "cards": cards})
    return {
        "groups": groups,
        "checked_at": checked_at if isinstance(checked_at, str) else None,
    }
