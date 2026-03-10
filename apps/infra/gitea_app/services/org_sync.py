#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gitea ↔ Django organization sync utilities.

Bidirectional sync between Gitea organizations/collaborators and Django
Organization/OrganizationMembership models.

Gitea → Django: called by webhook handlers
Django → Gitea: called by Django signals
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Gitea → Django
# ---------------------------------------------------------------------------


def sync_org_from_gitea(org_name: str) -> None:
    """Ensure a Gitea org exists as a Django Organization.

    Creates or updates the Organization record. Does not touch members.
    """
    from apps.infra.gitea_app.api_client import GiteaAPIError, GiteaClient
    from apps.infra.organizations_app.models import Organization

    client = GiteaClient()
    try:
        gitea_org = client.get_organization(org_name)
    except GiteaAPIError as exc:
        logger.warning("[org_sync] Cannot fetch Gitea org %s: %s", org_name, exc)
        return

    Organization.objects.update_or_create(
        slug=gitea_org.get("username") or gitea_org.get("name"),
        defaults={
            "name": gitea_org.get("full_name") or gitea_org.get("name", org_name),
            "description": gitea_org.get("description", ""),
            "website": gitea_org.get("website", ""),
        },
    )
    logger.info("[org_sync] Synced Gitea org → Django: %s", org_name)


def sync_org_member_added(org_name: str, username: str) -> None:
    """Add a Gitea org member to the Django Organization."""
    from django.contrib.auth.models import User

    from apps.infra.organizations_app.models import Organization, OrganizationMembership

    org = Organization.objects.filter(slug=org_name).first()
    if not org:
        sync_org_from_gitea(org_name)
        org = Organization.objects.filter(slug=org_name).first()
    if not org:
        logger.warning("[org_sync] Org not found after sync: %s", org_name)
        return

    user = User.objects.filter(username=username).first()
    if not user:
        logger.warning("[org_sync] User not found: %s", username)
        return

    _, created = OrganizationMembership.objects.get_or_create(
        user=user,
        organization=org,
        defaults={"role": "member"},
    )
    if created:
        logger.info("[org_sync] Added %s to Django org %s", username, org_name)


def sync_org_member_removed(org_name: str, username: str) -> None:
    """Remove a Gitea org member from the Django Organization."""
    from django.contrib.auth.models import User

    from apps.infra.organizations_app.models import Organization, OrganizationMembership

    org = Organization.objects.filter(slug=org_name).first()
    user = User.objects.filter(username=username).first()
    if not org or not user:
        return

    deleted, _ = OrganizationMembership.objects.filter(
        user=user, organization=org
    ).delete()
    if deleted:
        logger.info("[org_sync] Removed %s from Django org %s", username, org_name)


def full_sync_org_members(org_name: str) -> None:
    """Full bidirectional reconcile: make Django org members = Gitea org members.

    Adds members present in Gitea but not Django.
    Removes members present in Django but not Gitea (except admins).
    """
    from django.contrib.auth.models import User

    from apps.infra.gitea_app.api_client import GiteaAPIError, GiteaClient
    from apps.infra.organizations_app.models import Organization, OrganizationMembership

    client = GiteaClient()
    try:
        gitea_members = client.list_org_members(org_name)
    except GiteaAPIError as exc:
        logger.warning("[org_sync] Cannot list Gitea members for %s: %s", org_name, exc)
        return

    org = Organization.objects.filter(slug=org_name).first()
    if not org:
        sync_org_from_gitea(org_name)
        org = Organization.objects.filter(slug=org_name).first()
    if not org:
        return

    gitea_usernames = {m.get("login") for m in gitea_members if m.get("login")}

    # Add missing
    for uname in gitea_usernames:
        user = User.objects.filter(username=uname).first()
        if user:
            OrganizationMembership.objects.get_or_create(
                user=user, organization=org, defaults={"role": "member"}
            )

    # Remove extras (preserve admins)
    OrganizationMembership.objects.filter(organization=org, role="member").exclude(
        user__username__in=gitea_usernames
    ).delete()

    logger.info(
        "[org_sync] Full sync done for org %s (%d Gitea members)",
        org_name,
        len(gitea_usernames),
    )


# ---------------------------------------------------------------------------
# Django → Gitea
# ---------------------------------------------------------------------------


def push_org_member_to_gitea(org_name: str, username: str) -> None:
    """Add a Django org member to the corresponding Gitea organization."""
    from apps.infra.gitea_app.api_client import GiteaAPIError, GiteaClient

    client = GiteaClient()
    try:
        client.add_org_member(org_name, username)
        logger.info(
            "[org_sync] Pushed org member to Gitea: %s → %s", username, org_name
        )
    except GiteaAPIError as exc:
        logger.warning(
            "[org_sync] Cannot add %s to Gitea org %s: %s", username, org_name, exc
        )


def remove_org_member_from_gitea(org_name: str, username: str) -> None:
    """Remove a Django org member from the corresponding Gitea organization."""
    from apps.infra.gitea_app.api_client import GiteaAPIError, GiteaClient

    client = GiteaClient()
    try:
        client.remove_org_member(org_name, username)
        logger.info(
            "[org_sync] Removed org member from Gitea: %s ← %s", username, org_name
        )
    except GiteaAPIError as exc:
        logger.warning(
            "[org_sync] Cannot remove %s from Gitea org %s: %s", username, org_name, exc
        )


# EOF
