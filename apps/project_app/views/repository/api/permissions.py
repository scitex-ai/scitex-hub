#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 (auto-generated)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/repository/api/permissions.py
# ----------------------------------------
"""
Permission checking utilities for repository API endpoints
"""

from __future__ import annotations


def check_project_read_access(request, project) -> bool:
    """
    Check if user has read access to project.

    Args:
        request: Django request object
        project: Project model instance

    Returns:
        True if user has read access, False otherwise
    """
    if request.user.is_authenticated:
        return (
            project.owner == request.user
            or project.collaborators.filter(id=request.user.id).exists()
            or project.visibility == "public"
        )
    else:
        # For visitor users, check if this is their allocated visitor project
        visitor_project_id = request.session.get("visitor_project_id")
        return (
            project.visibility == "public"
            or (visitor_project_id and project.id == visitor_project_id)
        )


def check_project_write_access(request, project) -> bool:
    """
    Check if user has write access to project.

    Args:
        request: Django request object
        project: Project model instance

    Returns:
        True if user has write access, False otherwise
    """
    return (
        project.owner == request.user
        or project.collaborators.filter(id=request.user.id).exists()
    )


def check_user_repository_access(request, user) -> bool:
    """
    Check if user can access repository health/management for a user.

    Args:
        request: Django request object
        user: User model instance

    Returns:
        True if user has access, False otherwise
    """
    return user == request.user or request.user.is_staff


# EOF
