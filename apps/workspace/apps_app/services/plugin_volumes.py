#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Host service for plugin apps: which volumes belong to the requester.

Consumed via ``SCITEX_STORAGE_VOLUMES_PROVIDER`` by any leaf that measures
storage (the Storage plugin today). Only the requester's own directories
are returned; the leaf measures and lists inside them and refuses anything
that resolves outside.

Generic hub infrastructure (user -> workspace mapping): it names no plugin
and serves any leaf the deployment wires to this provider setting.
"""

from __future__ import annotations

import os
from pathlib import Path

from django.utils.translation import gettext_lazy as _


def _user_home_name(value):
    from django.core.exceptions import PermissionDenied

    if not isinstance(value, str) or not value or value in {".", ".."} or any(
        char in value for char in ("/", "\\", "\0")
    ):
        raise PermissionDenied("Invalid user home identity")
    return value


def _checked_user_home(base: Path, home: Path, username: str) -> Path:
    from django.core.exceptions import PermissionDenied

    username = _user_home_name(username)
    try:
        resolved = home.resolve()
        expected = base.resolve() / username
    except (OSError, RuntimeError, ValueError):
        raise PermissionDenied("User home cannot be resolved safely") from None
    if resolved != expected:
        raise PermissionDenied("User home must remain in its own workspace")
    return resolved


def user_home(request) -> Path | None:
    """Trusted persistent user home for leaf plugins; no browser path input."""
    from django.conf import settings

    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None
    username = _user_home_name(getattr(user, "username", None))
    from apps.infra.project_app.services.filesystem.permissions import get_user_data_root

    return _checked_user_home(
        Path(settings.BASE_DIR) / "data" / "users", get_user_data_root(user), username
    )


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
