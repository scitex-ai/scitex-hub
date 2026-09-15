#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Host service for the Storage leaf: which volumes belong to the requester.

Wired as ``SCITEX_STORAGE_VOLUMES_PROVIDER``. Only the requester's own
directories are returned; the leaf measures and lists inside them and refuses
anything that resolves outside.
"""

from __future__ import annotations

import os

from django.utils.translation import gettext_lazy as _


def user_volumes(request) -> list[dict]:
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return []

    from apps.infra.project_app.services.filesystem.permissions import (
        get_user_data_root,
    )

    volumes = [
        {
            "key": "workspace",
            "label": _("Workspace files"),
            "path": str(get_user_data_root(user)),
            "machine": os.environ.get("SCITEX_HUB_STORAGE_MACHINE_LABEL", "SciTeX Hub"),
            "tier": "hot",
            "connection": _("Your projects, on the hub server's local disk"),
        }
    ]

    from apps.workspace.console_app.models import ComputeIdentity
    from apps.workspace.console_app.services.compute_user import (
        COMPUTE_NODES,
        compute_home,
    )

    identity = ComputeIdentity.objects.filter(user=user).first()
    if identity is not None:
        volumes.append(
            {
                "key": "compute-home",
                "label": _("Compute home"),
                "path": str(compute_home(identity.username)),
                "machine": ", ".join(COMPUTE_NODES),
                "tier": "cool",
                "connection": _("NAS share mounted at /storage/cool on every compute node"),
            }
        )
    return volumes


# EOF
