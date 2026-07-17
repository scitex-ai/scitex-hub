#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manifest display metadata — label/icon extraction for AppsModule rows.

The app's own manifest.json is the SSoT for display metadata (mirrors
the tile-category fix, PR #362). Every path that creates or updates an
AppsModule row for a published app funnels through these helpers so the
catalog columns stay consistent. Missing/blank/non-string manifest keys
yield "" — the columns stay blank and the launcher's visible prettified
fallback applies. Nothing here fabricates data.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def manifest_display_fields(manifest: dict | None) -> dict[str, str]:
    """Display columns (label / icon) a manifest declares, else blanks.

    Returns ``{"label": ..., "icon": ...}`` ready to merge into an
    ``AppsModule`` create/update ``defaults`` dict. Non-string values
    (a malformed manifest) are treated as absent rather than stored.
    """
    data = manifest or {}
    label = data.get("label")
    icon = data.get("icon")
    return {
        "label": label.strip() if isinstance(label, str) else "",
        "icon": icon.strip() if isinstance(icon, str) else "",
    }


def project_manifest_display_fields(project) -> dict[str, str]:
    """Display columns from a Project's local manifest.json, else blanks.

    Used by the project publish flow, which has no manifest dict in
    scope — only the Django ``Project`` row. Resolves the same local
    directory the app validator uses (data/users/<owner>/proj/<slug>).
    A missing directory or manifest yields blanks, never an error: the
    publish flow must not fail over display metadata.
    """
    from .dev_app_loader import read_manifest, resolve_dev_project_dir

    try:
        project_dir = resolve_dev_project_dir(project.owner.username, project.slug)
        manifest = read_manifest(project_dir) if project_dir else {}
    except Exception:
        logger.exception(
            "[manifest_display] Failed to read manifest for %s/%s — "
            "label/icon left blank (prettified fallback applies)",
            project.owner.username,
            project.slug,
        )
        manifest = {}
    return manifest_display_fields(manifest)


# EOF
