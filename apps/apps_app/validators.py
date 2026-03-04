#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apps validators — check module readiness before publication."""

from __future__ import annotations


def validate_module_for_publication(app_module):
    """Check required fields before allowing apps submission.

    Returns a list of error strings (empty = valid).
    """
    errors = []

    if not app_module.short_description:
        errors.append("Short description is required.")

    if not app_module.author:
        errors.append("Author must be set.")

    if not app_module.category or app_module.category == "other":
        errors.append("A specific category must be selected (not 'other').")

    if not app_module.long_description:
        errors.append("Documentation (long_description) is required for publication.")

    # Check registry has icon and AI hint
    from apps.workspace_app.registry import get_module

    reg = get_module(app_module.module_name)
    if reg and not reg.icon_fa and not reg.icon_svg_tab:
        errors.append("Module must have an icon (icon_fa or icon_svg_tab in registry).")
    if reg and not reg.ai_hint:
        errors.append("AI hint is required for publication (ai_hint in registry).")

    if app_module.visibility == "public":
        errors.append("Module is already public.")

    return errors


# EOF
