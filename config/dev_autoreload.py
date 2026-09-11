#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Development autoreload coverage for newly created template-tag modules.

Django's stat reloader discovers imported Python modules automatically, but a
new template-tag library cannot be imported before the first template tries to
load it. Watching each application and its ``templatetags`` directory as files
ensures directory-mtime changes restart the Django process when a library is
created, while the recursive glob covers edits to tag modules that have not
yet been imported. The container itself is not recreated.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.apps import apps as django_apps
from django.utils.autoreload import autoreload_started

__all__ = ["install_templatetag_autoreload", "watch_templatetag_paths"]

_DISPATCH_UID = "scitex-hub-dev-templatetag-autoreload"


def watch_templatetag_paths(sender: Any, **kwargs: Any) -> None:
    """Register directories whose metadata exposes new tag libraries."""
    del kwargs
    for app_config in django_apps.get_app_configs():
        app_path = Path(app_config.path)
        sender.watch_dir(app_path.parent, app_path.name)
        sender.watch_dir(app_path, "templatetags")
        sender.watch_dir(app_path / "templatetags", "*.py")


def install_templatetag_autoreload() -> None:
    """Connect the development-only watcher exactly once per process."""
    autoreload_started.connect(
        watch_templatetag_paths,
        dispatch_uid=_DISPATCH_UID,
    )


# EOF
