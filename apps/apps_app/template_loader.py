#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Custom template loader for user-submitted apps.

Resolves templates like ``apps_app/user_apps/{module_name}_partial.html``
from the user's project directory on disk (Gitea checkout).
"""

from __future__ import annotations

import logging
import re

from django.conf import settings
from django.template import Origin, TemplateDoesNotExist
from django.template.loaders.base import Loader

logger = logging.getLogger(__name__)

# Templates must NOT override these protected block names
_PROTECTED_BLOCKS = re.compile(
    r"\{%\s*block\s+(extra_css|extra_js|content|title)\s*%\}"
)

_PREFIX = "apps_app/user_apps/"


class UserAppTemplateLoader(Loader):
    """Load AJAX partials for user-submitted apps from project directories."""

    def get_template_sources(self, template_name, template_dirs=None):
        if not template_name.startswith(_PREFIX):
            return
        # Derive module_name from e.g. "apps_app/user_apps/my_app_partial.html"
        rel = template_name[len(_PREFIX) :]
        module_name = rel.replace("_partial.html", "")
        if not module_name:
            return

        path = self._resolve_path(module_name)
        if path:
            yield Origin(
                name=str(path),
                template_name=template_name,
                loader=self,
            )

    def get_contents(self, origin):
        try:
            with open(origin.name, encoding="utf-8") as f:
                contents = f.read()
        except FileNotFoundError:
            raise TemplateDoesNotExist(origin)

        # Security: reject templates that override protected workspace blocks
        if _PROTECTED_BLOCKS.search(contents):
            logger.warning(
                "[template_loader] Rejected %s: overrides protected block",
                origin.name,
            )
            raise TemplateDoesNotExist(origin)

        return contents

    def _resolve_path(self, module_name):
        """Find the partial template on disk for a user app module.

        Handles two cases:
        1. Published apps (AppsModule with visibility=public)
        2. Dev apps (module_name starts with ``dev__``)
        """
        # Dev apps: resolve from source owner's project directory
        if module_name.startswith("dev__"):
            return self._resolve_dev_path(module_name)

        from apps.apps_app.models import AppsModule

        try:
            app_module = (
                AppsModule.objects.filter(
                    module_name=module_name,
                    visibility="public",
                    project__isnull=False,
                )
                .select_related("project")
                .first()
            )
        except Exception:
            return None

        if not app_module or not app_module.project:
            return None

        # Look in the project's Gitea-cloned directory
        project_dir = settings.BASE_DIR / "data" / "projects" / app_module.project.slug
        partial = project_dir / "templates" / module_name / "index_partial.html"
        if partial.is_file():
            return partial
        return None

    def _resolve_dev_path(self, module_name):
        """Resolve template for a dev app from the source owner's project dir.

        Module name format: ``dev__<owner>__<repo>``
        Template path: data/users/<owner>/proj/<repo>/templates/index_partial.html
        """
        from apps.apps_app.services.dev_app_loader import resolve_dev_template

        return resolve_dev_template(module_name)


# EOF
