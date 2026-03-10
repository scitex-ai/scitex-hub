#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Django → Gitea signals for organizations.

When an OrganizationMembership is created or deleted in Django, reflect the
change in the corresponding Gitea organization.

Registered in OrganizationsAppConfig.ready().
"""

from __future__ import annotations

import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="organizations_app.OrganizationMembership")
def on_membership_saved(sender, instance, created, **kwargs):
    """Sync new membership to Gitea when a member is added to a Django org."""
    if not created:
        return  # only act on creation, not role updates

    org_slug = instance.organization.slug
    username = instance.user.username

    if not org_slug:
        return

    # Run async-safe — fire-and-forget; log failures but never raise
    try:
        from apps.infra.gitea_app.services.org_sync import push_org_member_to_gitea

        push_org_member_to_gitea(org_slug, username)
    except Exception as exc:
        logger.warning(
            "[signals] Failed to push org member to Gitea: %s/%s: %s",
            org_slug,
            username,
            exc,
        )


@receiver(post_delete, sender="organizations_app.OrganizationMembership")
def on_membership_deleted(sender, instance, **kwargs):
    """Remove member from Gitea org when Django membership is deleted."""
    org_slug = instance.organization.slug
    username = instance.user.username

    if not org_slug:
        return

    try:
        from apps.infra.gitea_app.services.org_sync import remove_org_member_from_gitea

        remove_org_member_from_gitea(org_slug, username)
    except Exception as exc:
        logger.warning(
            "[signals] Failed to remove org member from Gitea: %s/%s: %s",
            org_slug,
            username,
            exc,
        )


# EOF
