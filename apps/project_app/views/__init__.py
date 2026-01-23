#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project App Views

Exports all views following nested feature-based organization.
"""

# Workflows feature
from .workflows import (
    workflow_detail,
    workflow_create,
    workflow_edit,
    workflow_run_detail,
    workflow_trigger,
    workflow_enable_disable,
    workflow_delete,
)

# Projects feature
from .projects import (
    project_list,
    project_detail,
    project_detail_redirect,
    project_create,
    project_create_from_template,
    project_edit,
    project_delete,
    project_settings,
    # API endpoints
    api_check_name_availability,
    api_project_list,
    api_project_create,
    api_project_detail,
)

# Users feature
from .users import (
    user_profile,
    user_bio_page,
    user_project_list,
    user_overview,
    user_projects_board,
    user_stars,
)

# Actions feature
from .actions import (
    actions_list,
)

# Issues feature
from .issues import (
    issues_list,
    issue_detail,
    issue_create,
    issue_edit,
    issue_comment_create,
    issue_label_manage,
    issue_milestone_manage,
    # API endpoints
    api_issue_comment,
    api_issue_close,
    api_issue_reopen,
    api_issue_assign,
    api_issue_label,
    api_issue_milestone,
    api_issue_search,
)

# Security feature
from .security import (
    security_overview,
    security_alerts,
    security_alert_detail,
    dismiss_alert,
    reopen_alert,
    create_fix_pr,
    security_scan_history,
    trigger_security_scan,
    security_advisories,
    security_advisory_detail,
    security_dependency_graph,
    api_dependency_tree,
    security_policy,
)

# Repository feature (file browsing and editing views)
from .repository import (
    project_directory_dynamic,
    project_directory,
    project_file_view,
    project_file_edit,
    file_history_view,
    commit_detail,
)

# API views (refactored into modular structure)
from .api import (
    api_file_tree,
    api_check_name_availability,
    api_project_list,
    api_project_create,
    api_project_detail,
    api_concatenate_directory,
    api_repository_health,
    api_repository_cleanup,
    api_repository_sync,
    api_repository_restore,
)

# Legacy flat views (to be refactored in future phases)
from .directory_views import *
from .pr import *
from .integration_views import *
from .collaboration_views import *
from .settings_views import *

__all__ = [
    # Workflows
    "workflow_detail",
    "workflow_create",
    "workflow_edit",
    "workflow_run_detail",
    "workflow_trigger",
    "workflow_enable_disable",
    "workflow_delete",
    # Projects
    "project_list",
    "project_detail",
    "project_detail_redirect",
    "project_create",
    "project_create_from_template",
    "project_edit",
    "project_delete",
    "project_settings",
    # Users
    "user_profile",
    "user_bio_page",
    "user_project_list",
    "user_overview",
    "user_projects_board",
    "user_stars",
    # Actions
    "actions_list",
    # Issues
    "issues_list",
    "issue_detail",
    "issue_create",
    "issue_edit",
    "issue_comment_create",
    "issue_label_manage",
    "issue_milestone_manage",
    "api_issue_comment",
    "api_issue_close",
    "api_issue_reopen",
    "api_issue_assign",
    "api_issue_label",
    "api_issue_milestone",
    "api_issue_search",
    # Security
    "security_overview",
    "security_alerts",
    "security_alert_detail",
    "dismiss_alert",
    "reopen_alert",
    "create_fix_pr",
    "security_scan_history",
    "trigger_security_scan",
    "security_advisories",
    "security_advisory_detail",
    "security_dependency_graph",
    "api_dependency_tree",
    "security_policy",
    # Repository Views
    "project_directory_dynamic",
    "project_directory",
    "project_file_view",
    "project_file_edit",
    "file_history_view",
    "commit_detail",
    # API Views
    "api_file_tree",
    "api_check_name_availability",
    "api_project_list",
    "api_project_create",
    "api_project_detail",
    "api_concatenate_directory",
    "api_repository_health",
    "api_repository_cleanup",
    "api_repository_sync",
    "api_repository_restore",
]
