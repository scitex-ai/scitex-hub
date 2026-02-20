#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workspace context processors — inject module registry data into all templates.

Added to TEMPLATES["OPTIONS"]["context_processors"] in settings.
"""

from __future__ import annotations

from .registry import extract_module_from_path, get_all_modules, is_workspace_path


def workspace_context(request):
    """Provide workspace module info to all templates."""
    path = request.path
    is_ws = is_workspace_path(path)
    active_name = extract_module_from_path(path) if is_ws else None

    modules = get_all_modules()
    for mod in modules:
        mod.is_active = mod.name == active_name

    active_mod = None
    if active_name:
        active_mod = next((m for m in modules if m.name == active_name), None)

    return {
        "is_workspace_page": is_ws,
        "workspace_modules": modules,
        "workspace_module_names_csv": ",".join(m.name for m in modules),
        "active_module_name": active_name,
        "active_module": active_mod,
    }


# EOF
