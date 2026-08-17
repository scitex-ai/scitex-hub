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
        """Return matches for ``path``; ``[]`` — never ``None`` — on a miss.

        A MISS MUST BE AN EMPTY LIST, in both modes. This looks like a
        style choice and is not: it is the contract Django's aggregating
        ``staticfiles.finders.find()`` requires, and returning ``None``
        instead turns every static-file MISS in the whole project into an
        HTTP 500.

        django/contrib/staticfiles/finders.py::find (5.2):

            for finder in get_finders():
                result = finder.find(path, find_all=find_all)
                if not find_all and result:
                    return result
                if not isinstance(result, (list, tuple)):
                    result = [result]          # None becomes [None]
                matches.extend(result)
            if matches:
                return matches                 # [None] is TRUTHY

        So one finder answering ``None`` makes the aggregate answer
        ``[None]`` for a file that exists nowhere. ``staticfiles.views``
        ``serve()`` then runs ``os.path.split([None])`` and raises
        ``TypeError: expected str, bytes or os.PathLike object, not
        list`` — a 500 where the correct answer is a 404. The built-in
        FileSystemFinder and AppDirectoriesFinder both return ``[]``,
        which is why the bug needed THIS finder to appear at all.

        Measured 2026-08-17 in CI run 32056013931: with the screenshot
        job serving Vite-built assets, every ``/static/vite/*.js`` request
        returned 500 with that exact traceback, no JavaScript ran, and the
        visitor heartbeat (a Vite entry) never fired — so the pooled
        visitor's 120-second probation lease expired mid-capture and four
        pages were photographed as ``readonly_visitor``.
        """
        # Django's finders.find() passes find_all= as keyword arg
        all = all or kwargs.get("find_all", False)
        matches = []
        users_dir = settings.BASE_DIR / "data" / "users"
        if not _is_dir_safe(users_dir):
            return []

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

        # `[]`, not `None` — see the docstring. An empty list is falsy, so
        # the aggregator's `if not find_all and result` still skips it and
        # `matches.extend([])` adds nothing; a `None` is what poisons it.
        return matches

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
