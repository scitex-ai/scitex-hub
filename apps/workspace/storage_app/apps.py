#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AppConfig for the hub-side scitex-storage mount glue.

The actual views/templates/static ship inside the upstream
``scitex_storage._django`` package app (installed via the guarded import in
``config/settings/settings_shared.py`` and URL-mounted at ``/apps/storage/`` in
``config/urls.py``). This hub app carries only ``manifest.json`` — the launcher
tile registered through the workspace module registry
(``apps.infra.workspace_app.registry``).

Deliberately no tenancy middleware (unlike the todo mount): scitex-storage is a
per-USER view over storage across the machines a user can reach, not a view of
one server's own resources, so hub must not scope it to a single project's
workspace.
"""

from django.apps import AppConfig


class StorageAppConfig(AppConfig):
    name = "apps.workspace.storage_app"
    label = "storage_app"
    verbose_name = "SciTeX Storage Mount"


# EOF
