#!/usr/bin/env python3
"""Per-module registry overrides that cannot be expressed in manifest JSON."""

from __future__ import annotations

MANIFEST_OVERRIDES: dict[str, dict] = {
    # Stats verified working end-to-end (operator 2026-09-26): Calculate
    # returns real statistics (t, p, effect size, power, APA line, plot).
    # The app is project-scoped; keep the scope pin, drop the gate.
    "stats": {"scope": "project", "availability": "available"},
}
