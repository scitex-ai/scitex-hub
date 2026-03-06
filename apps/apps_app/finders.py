#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Custom static files finder for dev-installed apps.

Mirrors UserAppTemplateLoader: searches data/users/*/proj/*/static/
for static assets requested via {% static %} tag.
"""

from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.finders import BaseFinder
from django.core.files.storage import FileSystemStorage

logger = logging.getLogger(__name__)


class DevAppStaticFinder(BaseFinder):
    """Find static files in dev app project directories.

    Searches: data/users/<owner>/proj/<repo>/static/<path>
    """

    def find(self, path, all=False, **kwargs):
        # Django's finders.find() passes find_all= as keyword arg
        all = all or kwargs.get("find_all", False)
        matches = []
        users_dir = settings.BASE_DIR / "data" / "users"
        if not users_dir.is_dir():
            return [] if all else None

        for owner_dir in _safe_iterdir(users_dir):
            proj_dir = owner_dir / "proj"
            if not proj_dir.is_dir():
                continue
            for repo_dir in _safe_iterdir(proj_dir):
                static_dir = repo_dir / "static"
                if not static_dir.is_dir():
                    continue
                candidate = static_dir / path
                if candidate.is_file():
                    matched = str(candidate)
                    if not all:
                        return matched
                    matches.append(matched)

        return matches if all else None

    def list(self, ignore_patterns):
        users_dir = settings.BASE_DIR / "data" / "users"
        if not users_dir.is_dir():
            return

        for owner_dir in _safe_iterdir(users_dir):
            proj_dir = owner_dir / "proj"
            if not proj_dir.is_dir():
                continue
            for repo_dir in _safe_iterdir(proj_dir):
                static_dir = repo_dir / "static"
                if not static_dir.is_dir():
                    continue
                storage = FileSystemStorage(location=str(static_dir))
                storage.prefix = ""
                for root_path in static_dir.rglob("*"):
                    if root_path.is_file():
                        rel = root_path.relative_to(static_dir)
                        yield str(rel), storage


def _safe_iterdir(directory: Path):
    """Iterate subdirectories, skipping hidden/system dirs."""
    try:
        for item in sorted(directory.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                yield item
    except PermissionError:
        pass


# EOF
