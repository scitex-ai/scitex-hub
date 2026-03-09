#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI/CD Actions Views - modular structure."""

from .list_views import actions_list, workflow_detail, workflow_run_detail
from .crud_views import workflow_create, workflow_edit, workflow_delete
from .control_views import workflow_trigger, workflow_enable_disable
from .helpers import (
    get_workflow_template,
    get_available_templates,
    save_workflow_to_filesystem,
    delete_workflow_from_filesystem,
)

__all__ = [
    # List views
    "actions_list",
    "workflow_detail",
    "workflow_run_detail",
    # CRUD views
    "workflow_create",
    "workflow_edit",
    "workflow_delete",
    # Control views
    "workflow_trigger",
    "workflow_enable_disable",
    # Helpers
    "get_workflow_template",
    "get_available_templates",
    "save_workflow_to_filesystem",
    "delete_workflow_from_filesystem",
]

# EOF
