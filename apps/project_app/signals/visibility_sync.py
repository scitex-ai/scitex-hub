#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 04:54:30 (ywatanabe)"

"""
Signals for synchronizing project visibility changes with Gitea.

Tracks visibility changes and syncs them to the Gitea repository.
"""

import logging
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from ..models import Project

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Project)
def track_visibility_change(sender, instance, **kwargs):
    """
    Track old visibility value before saving.

    This signal handler records the previous visibility state so that
    post_save handlers can detect if the visibility has changed.
    """
    if instance.pk:
        try:
            old_instance = Project.objects.get(pk=instance.pk)
            instance._old_visibility = old_instance.visibility
        except Project.DoesNotExist:
            pass


@receiver(post_save, sender=Project)
def sync_project_visibility(sender, instance, created, **kwargs):
    """
    Sync project visibility changes with Gitea repository.

    When a Django project's visibility is changed (public ↔ private),
    update the corresponding Gitea repository.
    """
    # Only sync for existing projects
    if created:
        return

    # Skip if no Gitea repo associated
    if not instance.gitea_repo_url:
        return

    # Check if visibility was changed
    if not hasattr(instance, "_old_visibility"):
        return

    if instance._old_visibility == instance.visibility:
        return

    try:
        from apps.gitea_app.api_client import GiteaClient

        client = GiteaClient()
        is_private = instance.visibility == "private"

        # Update Gitea repository visibility
        # Note: Gitea API uses PATCH /repos/{owner}/{repo}
        endpoint = f"/repos/{instance.owner.username}/{instance.slug}"
        client._request("PATCH", endpoint, json={"private": is_private})

        logger.info(f"✓ Synced visibility for {instance.slug}: {instance.visibility}")

    except Exception as e:
        logger.error(f"Failed to sync visibility for {instance.slug}: {e}")


# EOF
