#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AppConfig for the hub-side scitex-todo mount glue.

The actual board views/templates/static ship inside the upstream
``scitex_todo._django`` package app (installed via the guarded import in
``config/settings/settings_shared.py`` and URL-mounted at ``/todo/`` in
``config/urls.py``). This hub app only carries:

- :mod:`.middleware` — per-request workspace-store tenancy injection +
  the phase-1 read-only write gate for the ``/todo/`` mount, and
- ``manifest.json`` — the launcher tile registered through the workspace
  module registry (``apps.infra.workspace_app.registry``).
"""

from django.apps import AppConfig


class TodoAppConfig(AppConfig):
    name = "apps.workspace.todo_app"
    label = "todo_app"
    verbose_name = "SciTeX Todo Board Mount"


# EOF
