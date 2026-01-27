#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scholar app admin - Admin actions."""

from __future__ import annotations

from django.contrib import admin


@admin.action(description="Sync selected datasets with repository")
def sync_datasets_with_repository(modeladmin, request, queryset):
    """Sync selected datasets with their remote repositories."""
    from ..repository_services import sync_dataset_with_repository

    for dataset in queryset:
        if dataset.repository_id:
            sync_dataset_with_repository(dataset)

    modeladmin.message_user(request, f"Started sync for {queryset.count()} datasets.")


@admin.action(description="Test repository connections")
def test_repository_connections(modeladmin, request, queryset):
    """Test connectivity of selected repository connections."""
    from ..repository_services import RepositoryServiceFactory

    results = []
    for connection in queryset:
        try:
            service = RepositoryServiceFactory.create_service(connection)
            if service.authenticate():
                results.append(f"✓ {connection.connection_name}: Connected")
            else:
                results.append(f"✗ {connection.connection_name}: Failed")
        except Exception as e:
            results.append(f"✗ {connection.connection_name}: Error - {str(e)}")

    modeladmin.message_user(request, "\n".join(results))


# EOF
