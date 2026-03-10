#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scholar app admin package.

Re-exports admin classes from submodules for Django autodiscovery.
"""

from __future__ import annotations

# Import all admin classes to register them with Django admin
from .actions import sync_datasets_with_repository, test_repository_connections
from .basic import (
    AuthorAdmin,
    CollectionAdmin,
    JournalAdmin,
    SearchIndexAdmin,
    TopicAdmin,
    UserLibraryAdmin,
)
from .dataset import (
    DatasetAdmin,
    DatasetFileAdmin,
    DatasetFileInline,
    DatasetVersionAdmin,
)
from .repository import RepositoryAdmin, RepositoryConnectionAdmin
from .sync import RepositorySyncAdmin

# Attach actions to admin classes
DatasetAdmin.actions = [sync_datasets_with_repository]
RepositoryConnectionAdmin.actions = [test_repository_connections]

__all__ = [
    # Basic admins
    "AuthorAdmin",
    "JournalAdmin",
    "TopicAdmin",
    "SearchIndexAdmin",
    "CollectionAdmin",
    "UserLibraryAdmin",
    # Repository admins
    "RepositoryAdmin",
    "RepositoryConnectionAdmin",
    # Dataset admins
    "DatasetAdmin",
    "DatasetFileAdmin",
    "DatasetFileInline",
    "DatasetVersionAdmin",
    "RepositorySyncAdmin",
    # Actions
    "sync_datasets_with_repository",
    "test_repository_connections",
]


# EOF
