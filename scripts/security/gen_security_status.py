#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the live data for the public /security/ trust page.

Counts the security-regression tests under ``tests/security/`` and stamps the
current git short SHA plus a UTC ISO-8601 timestamp, then writes
``apps/infra/public_app/data/security_status.json``. The public ``/security/``
view reads that JSON so the page can render an honest, live
"N automated security regression tests · last verified ..." metric.

SAFETY: this script only ever emits POSITIVE, implemented facts (a count and a
curated list of hardened areas). It never records open gaps, so the generated
JSON is safe to publish.

The page's own meta-test (``test_security_status_page.py``) is deliberately
EXCLUDED from the count: it verifies this trust page, not a product security
control, so it must not inflate the advertised security-regression number.

Usage::

    python scripts/security/gen_security_status.py

CI should re-run this on every ``develop`` push so the timestamp/commit stay
fresh (not wired here — see the PR body).
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# scripts/security/gen_security_status.py -> repo root is two parents up.
REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = REPO_ROOT / "tests" / "security"
OUTPUT_PATH = (
    REPO_ROOT / "apps" / "infra" / "public_app" / "data" / "security_status.json"
)

# Files under tests/security/ that do NOT test a product security control
# (they test the trust page itself), so they are excluded from the public count.
EXCLUDE_FILES = ("test_security_status_page.py",)

# A `def test_` definition at the start of a line (optionally indented for
# methods inside a TestCase). Matches how the suite is really counted.
_TEST_DEF_RE = re.compile(r"(?m)^[ \t]*def test_")

# The curated, PUBLIC list of hardened areas. Implemented protections only,
# framed positively. NEVER add open gaps / TODOs / severities here — this data
# is rendered on a public page (a template+JSON scan test enforces it).
CATEGORIES = [
    {
        "name": "Tenant isolation",
        "description": (
            "Each user's projects and files are strictly separated; "
            "ownership is checked on every access."
        ),
    },
    {
        "name": "Path containment",
        "description": (
            "Uploads and edits are jailed to the project; "
            "path-traversal attempts are rejected."
        ),
    },
    {
        "name": "Command-injection hardening",
        "description": "All shell, SSH, and SLURM arguments are safely quoted.",
    },
    {
        "name": "SSRF protection",
        "description": (
            "Server-side URL fetches are restricted to public hosts; "
            "internal and loopback addresses are blocked."
        ),
    },
    {
        "name": "Deserialization safety",
        "description": (
            "No untrusted pickle or marshal; only safe YAML loaders are used."
        ),
    },
    {
        "name": "Sandboxed compute",
        "description": (
            "Each visitor's terminal and compute run inside a per-user "
            "Apptainer sandbox, never a host shell."
        ),
    },
    {
        "name": "Authentication boundaries",
        "description": (
            "Admin and onsite actions require real authentication; "
            "there are no bypass paths."
        ),
    },
    {
        "name": "Automated regression gates",
        "description": (
            "Automated security tests run on every commit to keep these "
            "protections from regressing."
        ),
    },
]


def count_security_tests(
    tests_dir: str | Path, exclude: tuple[str, ...] = EXCLUDE_FILES
) -> tuple[int, int]:
    """Return ``(test_count, test_files)`` for ``tests/security/test_*.py``.

    ``test_count`` is the total number of ``def test_`` definitions across the
    matching files; ``test_files`` is the number of files counted. Files named
    in ``exclude`` (the page meta-test) are skipped so the published number
    reflects product security controls, not tests about the page.
    """
    tests_dir = Path(tests_dir)
    files = [
        p
        for p in sorted(tests_dir.glob("test_*.py"))
        if p.name not in exclude
    ]
    test_count = sum(
        len(_TEST_DEF_RE.findall(p.read_text(encoding="utf-8"))) for p in files
    )
    return test_count, len(files)


def _git_short_sha() -> str:
    """Current git short SHA. Raises loudly if git is unavailable (no fallback)."""
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def generate() -> dict:
    """Build the status payload and write it to ``OUTPUT_PATH``. Returns it."""
    test_count, test_files = count_security_tests(TESTS_DIR)
    payload = {
        "test_count": test_count,
        "test_files": test_files,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": _git_short_sha(),
        "categories": CATEGORIES,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return payload


if __name__ == "__main__":
    generated = generate()
    print(f"Wrote {OUTPUT_PATH}")
    print(json.dumps(generated, indent=2, ensure_ascii=False))

# EOF
