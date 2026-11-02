"""Bounded official GitHub reads shared through the configured public cache."""

from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone

from .landing_github import REPOSITORIES, repository_cards, validate_repository
from .refresh_landing_github import _NoRedirect

CACHE_KEY = "landing:github-counts:v1"
LAST_GOOD_KEY = CACHE_KEY + ":last-good"
LOCK_KEY = CACHE_KEY + ":refresh-lock"
CACHE_SECONDS = 300
ORG_URL = "https://api.github.com/orgs/scitex-ai/repos"


def fetch_official_counts() -> dict:
    """Read at most three fixed public listing pages; never follow Link URLs."""
    opener = urllib.request.build_opener(_NoRedirect())
    deadline = time.monotonic() + 8
    records = {}
    for page in range(1, 4):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("GitHub catalog budget exhausted")
        request = urllib.request.Request(
            f"{ORG_URL}?type=public&per_page=100&sort=full_name&direction=asc&page={page}",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "SciTeX-public-counts",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with opener.open(request, timeout=min(2.5, remaining)) as response:
            chunks = []
            size = 0
            while True:
                if time.monotonic() >= deadline:
                    raise TimeoutError("GitHub catalog body budget exhausted")
                chunk = response.read1(min(65536, 2_000_001 - size))
                if not chunk:
                    break
                size += len(chunk)
                if size > 2_000_000:
                    raise ValueError("GitHub page exceeds size bound")
                chunks.append(chunk)
            raw = b"".join(chunks)
            rows = json.loads(raw)
            more = 'rel="next"' in response.headers.get("Link", "")
        if not isinstance(rows, list) or len(rows) > 100:
            raise ValueError("Invalid GitHub listing")
        for row in rows:
            name = row.get("name") if isinstance(row, dict) else None
            if name in REPOSITORIES:
                if name in records:
                    raise ValueError("Duplicate catalog repository")
                verified = validate_repository(name, row)
                records[name] = {
                    key: verified[key] for key in ("available", "stars", "forks")
                }
        if len(records) == len(REPOSITORIES):
            return {
                "status": "fresh",
                "repositories": records,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        if not more:
            break
    raise ValueError("Official catalog is incomplete")


def bootstrap_counts() -> dict:
    """Use source data only when no live last-good result exists."""
    data = repository_cards()
    return {
        "status": "snapshot",
        "fetched_at": data["checked_at"],
        "repositories": {
            row["name"]: {key: row[key] for key in ("available", "stars", "forks")}
            for group in data["groups"]
            for row in group["cards"]
        },
    }


def cached_counts(cache, *, fetcher=fetch_official_counts) -> dict:
    """One refresh per five-minute cache window, including failed attempts.

    The add-only lease deliberately expires naturally: deleting a lock after a
    paused worker resumes could otherwise delete a newer worker's lease.
    Cache errors refuse upstream traffic and return source fallback instead.
    """
    fallback = bootstrap_counts()
    try:
        cached = cache.get(CACHE_KEY)
        if cached is not None:
            return cached
        last = cache.get(LAST_GOOD_KEY)
        if last is not None:
            fallback = {**last, "status": "stale"}
        if not cache.add(LOCK_KEY, True, timeout=CACHE_SECONDS):
            return fallback
    except Exception:
        return fallback
    try:
        result = fetcher()
    except (OSError, ValueError):
        result = fallback
    try:
        if result["status"] == "fresh":
            cache.set(LAST_GOOD_KEY, result, timeout=30 * 86400)
        cache.set(CACHE_KEY, result, timeout=CACHE_SECONDS)
    except Exception:
        pass  # Serve the verified public result even if the cache becomes unavailable.
    return result
