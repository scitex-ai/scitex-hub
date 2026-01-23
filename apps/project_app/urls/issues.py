"""
Issues Feature URLs

Handles all issue tracking related URLs.
GitHub-style patterns:
- /<username>/<slug>/issues/ - List all issues
- /<username>/<slug>/issues/new/ - Create new issue
- /<username>/<slug>/issues/<number>/ - Issue detail
- /<username>/<slug>/issues/<number>/edit/ - Edit issue
- /<username>/<slug>/issues/labels/ - Manage labels
- /<username>/<slug>/issues/milestones/ - Manage milestones
"""

from django.urls import path
from ..views.issues import (
    issues_list,
    issue_create,
    issue_detail,
    issue_edit,
    issue_comment_create,
    issue_label_manage,
    issue_milestone_manage,
    api_issue_search,
    api_issue_comment,
    api_issue_close,
    api_issue_reopen,
    api_issue_assign,
    api_issue_label,
    api_issue_milestone,
)

# No app_name here - namespace is provided by parent (user_projects)

urlpatterns = [
    # Issue list
    path("", issues_list, name="list"),
    # Create new issue
    path("new/", issue_create, name="create"),
    # Label management
    path("labels/", issue_label_manage, name="labels"),
    # Milestone management
    path("milestones/", issue_milestone_manage, name="milestones"),
    # Issue detail
    path("<int:issue_number>/", issue_detail, name="detail"),
    # Edit issue
    path("<int:issue_number>/edit/", issue_edit, name="edit"),
    # Add comment
    path("<int:issue_number>/comment/", issue_comment_create, name="comment_create"),
    # Issue API endpoints
    path("api/search/", api_issue_search, name="api_search"),
    path("api/<int:issue_number>/comment/", api_issue_comment, name="api_comment"),
    path("api/<int:issue_number>/close/", api_issue_close, name="api_close"),
    path("api/<int:issue_number>/reopen/", api_issue_reopen, name="api_reopen"),
    path("api/<int:issue_number>/assign/", api_issue_assign, name="api_assign"),
    path("api/<int:issue_number>/label/", api_issue_label, name="api_label"),
    path(
        "api/<int:issue_number>/milestone/", api_issue_milestone, name="api_milestone"
    ),
]
