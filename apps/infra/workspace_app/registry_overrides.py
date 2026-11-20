#!/usr/bin/env python3
"""Per-module registry overrides that cannot be expressed in manifest JSON."""

from __future__ import annotations


MANIFEST_OVERRIDES: dict[str, dict] = {
    # Operator 2026-10-16 (revised): Storage shows NO badge at all —
    # neither Coming Soon/dev-only nor Experimental. Hub-side override
    # only; the leaf's own visibility (internal) and wip state stay.
    "storage": {"hide_badges": True},
    # Stats verified working end-to-end (operator 2026-09-26): Calculate
    # returns real statistics (t, p, effect size, power, APA line, plot).
    # The app is project-scoped; keep the scope pin, drop the gate.
    "stats": {"scope": "project", "availability": "available"},
}
