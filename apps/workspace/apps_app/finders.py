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
        if not _is_dir_safe(users_dir):
            return [] if all else None

        for owner_dir in _safe_iterdir(users_dir):
            proj_dir = owner_dir / "proj"
            if not _is_dir_safe(proj_dir):
                continue
            for repo_dir in _safe_iterdir(proj_dir):
                static_dir = repo_dir / "static"
                if not _is_dir_safe(static_dir):
                    continue
                candidate = static_dir / path
                try:
                    is_file = candidate.is_file()
                except PermissionError:
                    continue
                if is_file:
                    matched = str(candidate)
                    if not all:
                        return matched
                    matches.append(matched)

        return matches if all else None

    def list(self, ignore_patterns):
        users_dir = settings.BASE_DIR / "data" / "users"
        if not _is_dir_safe(users_dir):
            return

        for owner_dir in _safe_iterdir(users_dir):
            proj_dir = owner_dir / "proj"
            if not _is_dir_safe(proj_dir):
                continue
            for repo_dir in _safe_iterdir(proj_dir):
                static_dir = repo_dir / "static"
                if not _is_dir_safe(static_dir):
                    continue
                storage = FileSystemStorage(location=str(static_dir))
                storage.prefix = ""
                for root_path in static_dir.rglob("*"):
                    try:
                        is_file = root_path.is_file()
                    except PermissionError:
                        continue
                    if is_file:
                        rel = root_path.relative_to(static_dir)
                        yield str(rel), storage


def _is_dir_safe(path: Path) -> bool:
    """Return True iff path is an existing directory; swallow PermissionError.

    pathlib's Path.is_dir() raises PermissionError when the parent is
    unreadable (e.g. BASE_DIR is /root for an unprivileged process). The
    finder is invoked on every static lookup, including during tests where
    BASE_DIR may point at a directory we cannot stat; in those cases the
    correct behavior is "no dev-app static files here", not a crash.
    """
    try:
        return path.is_dir()
    except PermissionError:
        return False


def _safe_iterdir(directory: Path):
    """Iterate subdirectories, skipping hidden/system dirs."""
    try:
        for item in sorted(directory.iterdir()):
            try:
                if item.is_dir() and not item.name.startswith("."):
                    yield item
            except PermissionError:
                continue
    except PermissionError:
        pass


# EOF
