#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Marketplace validators — check module readiness before publication."""

from __future__ import annotations


def validate_module_for_publication(mp_module):
    """Check required fields before allowing marketplace submission.

    Returns a list of error strings (empty = valid).
    """
    errors = []

    if not mp_module.short_description:
        errors.append("Short description is required.")

    if not mp_module.author:
        errors.append("Author must be set.")

    if not mp_module.category or mp_module.category == "other":
        errors.append("A specific category must be selected (not 'other').")

    # Check registry has icon
    from apps.workspace_app.registry import get_module

    reg = get_module(mp_module.module_name)
    if reg and not reg.icon_fa:
        errors.append("Module must have an icon (icon_fa in registry).")

    if mp_module.visibility == "public":
        errors.append("Module is already public.")

    return errors


# EOF
