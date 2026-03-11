#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""License Generator — create LICENSE files in Gitea repos.

License text generation is delegated to scitex_cloud.appmaker._license
(single source of truth). This module handles Gitea file creation.
"""

from __future__ import annotations

import logging

from apps.infra.gitea_app.api_client.client import GiteaClient
from apps.infra.gitea_app.exceptions import GiteaAPIError
from scitex_cloud.appmaker._license import generate_license_text  # noqa: F401

logger = logging.getLogger(__name__)


def generate_license_file(project, spdx_id: str) -> bool:
    """Create a LICENSE file in the project's Gitea repo.

    Returns True on success, False on failure.
    """
    author = project.owner.get_full_name() or project.owner.username
    text = generate_license_text(spdx_id, author)
    if text is None:
        logger.warning("Unknown SPDX identifier: %s", spdx_id)
        return False

    owner = project.owner.username
    repo = project.gitea_repo_name or project.slug

    try:
        client = GiteaClient()
        client.create_file(
            owner,
            repo,
            "LICENSE",
            text,
            message=f"Add {spdx_id} license",
            branch=project.current_branch or "main",
        )
        return True
    except GiteaAPIError as exc:
        logger.error("Failed to create LICENSE in %s/%s: %s", owner, repo, exc)
        return False


# EOF
