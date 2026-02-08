from django.urls import path

from . import views

app_name = "project_app"

urlpatterns = [
    # User-level URLs (no slug required)
    # /<username>/ - User profile/project list
    path("", views.user_profile, name="user_profile"),
    path("projects/", views.user_project_list, name="user_projects"),
    # API endpoints
    path("api/check-name/", views.api_check_name_availability, name="api_check_name"),
    path("api/list/", views.api_project_list, name="api_list"),
    path("api/create/", views.api_project_create, name="api_create"),
    path("api/<int:pk>/", views.api_project_detail, name="api_detail"),
    # Project list (redirects to user profile which shows projects)
    path("list/", views.user_profile, name="list"),
    # Repository maintenance
    path(
        "settings/repositories/",
        views.repository_maintenance,
        name="repository_maintenance",
    ),
    # Backward compatibility redirects
    path(
        "project/<slug:slug>/",
        views.project_detail_redirect,
        name="slug_redirect",
    ),
    path("id/<int:pk>/", views.project_detail_redirect, name="detail_redirect"),
    # Project-level URLs (require slug)
    # Repository root (detail)
    path("<slug:slug>/", views.project_detail, name="detail"),
    # Repository API endpoints
    path(
        "<slug:slug>/api/file-tree/",
        views.api_file_tree,
        name="api_file_tree",
    ),
    path(
        "<slug:slug>/api/create-symlink/",
        views.api_create_symlink,
        name="api_create_symlink",
    ),
    path(
        "<slug:slug>/api/concatenate-directory/",
        views.api_concatenate_directory,
        name="api_concatenate_directory",
    ),
    path(
        "<slug:slug>/api/repository-health/",
        views.api_repository_health,
        name="api_repository_health",
    ),
    path(
        "<slug:slug>/api/repository-cleanup/",
        views.api_repository_cleanup,
        name="api_repository_cleanup",
    ),
    path(
        "<slug:slug>/api/repository-sync/",
        views.api_repository_sync,
        name="api_repository_sync",
    ),
    path(
        "<slug:slug>/api/repository-restore/",
        views.api_repository_restore,
        name="api_repository_restore",
    ),
    # Project management
    path("<slug:slug>/edit/", views.project_edit, name="edit"),
    path("<slug:slug>/delete/", views.project_delete, name="delete"),
    path("<slug:slug>/settings/", views.project_settings, name="settings"),
    # File browsing
    path(
        "<slug:slug>/blob/<path:file_path>",
        views.project_file_view,
        name="file_view",
    ),
    path(
        "<slug:slug>/commits/<path:path>",
        views.file_history_view,
        name="file_history",
    ),
    path(
        "<slug:slug>/commit/<str:commit_hash>/",
        views.commit_detail,
        name="commit_detail",
    ),
    # Issues
    path("<slug:slug>/issues/", views.issues_list, name="issue_list"),
    path("<slug:slug>/issues/new/", views.issue_create, name="issue_create"),
    path(
        "<slug:slug>/issues/<int:issue_number>/",
        views.issue_detail,
        name="issue_detail",
    ),
    path(
        "<slug:slug>/issues/<int:issue_number>/edit/",
        views.issue_edit,
        name="issue_edit",
    ),
    path(
        "<slug:slug>/issues/<int:issue_number>/comment/",
        views.issue_comment_create,
        name="issue_comment_create",
    ),
    path(
        "<slug:slug>/issues/labels/",
        views.issue_label_manage,
        name="issue_label_manage",
    ),
    path(
        "<slug:slug>/issues/milestones/",
        views.issue_milestone_manage,
        name="issue_milestone_manage",
    ),
    path(
        "<slug:slug>/issues/<int:issue_number>/api/close/",
        views.api_issue_close,
        name="issue_api_close",
    ),
    path(
        "<slug:slug>/issues/<int:issue_number>/api/reopen/",
        views.api_issue_reopen,
        name="issue_api_reopen",
    ),
    # Pull Requests
    path("<slug:slug>/pulls/", views.pr_list, name="pr_list"),
    path("<slug:slug>/pull/new/", views.pr_create, name="pr_create"),
    path(
        "<slug:slug>/pull/<int:pr_number>/",
        views.pr_detail,
        name="pr_detail",
    ),
    path(
        "<slug:slug>/pull/<int:pr_number>/merge/",
        views.pr_merge,
        name="pr_merge",
    ),
    path(
        "<slug:slug>/pull/<int:pr_number>/close/",
        views.pr_close,
        name="pr_close",
    ),
    path(
        "<slug:slug>/pull/<int:pr_number>/reopen/",
        views.pr_reopen,
        name="pr_reopen",
    ),
    path(
        "<slug:slug>/pull/<int:pr_number>/review/",
        views.pr_review_submit,
        name="pr_review_submit",
    ),
    path(
        "<slug:slug>/pull/<int:pr_number>/comment/",
        views.pr_comment_create,
        name="pr_comment_create",
    ),
    # Security
    path(
        "<slug:slug>/security/",
        views.security_overview,
        name="security_overview",
    ),
    path(
        "<slug:slug>/security/alerts/",
        views.security_alerts,
        name="security_alerts",
    ),
    path(
        "<slug:slug>/security/alerts/<int:alert_id>/",
        views.security_alert_detail,
        name="security_alert_detail",
    ),
    path(
        "<slug:slug>/security/alerts/<int:alert_id>/dismiss/",
        views.dismiss_alert,
        name="api_dismiss_alert",
    ),
    path(
        "<slug:slug>/security/alerts/<int:alert_id>/reopen/",
        views.reopen_alert,
        name="api_reopen_alert",
    ),
    path(
        "<slug:slug>/security/scans/",
        views.security_scan_history,
        name="scan_history",
    ),
    path(
        "<slug:slug>/security/advisories/",
        views.security_advisories,
        name="security_advisories",
    ),
    path(
        "<slug:slug>/security/dependencies/",
        views.security_dependency_graph,
        name="dependency_graph",
    ),
    path(
        "<slug:slug>/security/policy/",
        views.security_policy,
        name="security_policy",
    ),
    # Workflows / Actions
    path("<slug:slug>/actions/", views.actions_list, name="actions_list"),
    path(
        "<slug:slug>/actions/new/",
        views.workflow_create,
        name="workflow_create",
    ),
    path(
        "<slug:slug>/actions/<int:workflow_id>/",
        views.workflow_detail,
        name="workflow_detail",
    ),
    path(
        "<slug:slug>/actions/<int:workflow_id>/edit/",
        views.workflow_edit,
        name="workflow_edit",
    ),
    path(
        "<slug:slug>/actions/<int:workflow_id>/delete/",
        views.workflow_delete,
        name="workflow_delete",
    ),
    path(
        "<slug:slug>/actions/<int:workflow_id>/toggle/",
        views.workflow_enable_disable,
        name="workflow_enable_disable",
    ),
    path(
        "<slug:slug>/actions/<int:workflow_id>/trigger/",
        views.workflow_trigger,
        name="workflow_trigger",
    ),
    path(
        "<slug:slug>/actions/<int:workflow_id>/runs/<int:run_id>/",
        views.workflow_run_detail,
        name="workflow_run_detail",
    ),
    # Directory browsing (catch-all, must be last)
    path(
        "<slug:slug>/<path:path>/",
        views.project_directory_dynamic,
        name="files",
    ),
]
