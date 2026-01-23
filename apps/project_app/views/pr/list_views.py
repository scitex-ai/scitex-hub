"""
Pull Request List Views

Handles PR listing with filtering, sorting, and pagination.
"""

from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.db.models import Count
from django.core.paginator import Paginator
import subprocess
import logging

from apps.project_app.models import Project, PullRequest, PullRequestLabel

logger = logging.getLogger(__name__)


def pr_list(request, username, slug):
    """
    List all PRs with filtering (open/closed/merged, author, reviewer).

    URL: /<username>/<slug>/pulls/
    """
    project = get_object_or_404(Project, owner__username=username, slug=slug)

    # Check permissions
    if not project.can_view(request.user):
        raise Http404("Project not found")

    # Get filter parameters
    state_filter = request.GET.get("state", "open")  # open, closed, merged, all
    author_filter = request.GET.get("author", "")
    reviewer_filter = request.GET.get("reviewer", "")
    label_filter = request.GET.get("label", "")
    sort_by = request.GET.get("sort", "created")  # created, updated, comments
    direction = request.GET.get("direction", "desc")  # asc, desc

    # Build query
    queryset = PullRequest.objects.filter(project=project)

    # State filter
    if state_filter == "open":
        queryset = queryset.filter(state="open")
    elif state_filter == "closed":
        queryset = queryset.filter(state="closed")
    elif state_filter == "merged":
        queryset = queryset.filter(state="merged")
    # 'all' shows everything

    # Author filter
    if author_filter:
        queryset = queryset.filter(author__username=author_filter)

    # Reviewer filter
    if reviewer_filter:
        queryset = queryset.filter(reviewers__username=reviewer_filter)

    # Label filter
    if label_filter:
        queryset = queryset.filter(labels__contains=[label_filter])

    # Sorting
    sort_field = {
        "created": "created_at",
        "updated": "updated_at",
        "comments": "comment_count",
    }.get(sort_by, "created_at")

    if direction == "asc":
        queryset = queryset.order_by(sort_field)
    else:
        queryset = queryset.order_by(f"-{sort_field}")

    # Annotate with counts
    queryset = (
        queryset.annotate(
            comment_count=Count("comments"),
            review_count=Count("reviews"),
        )
        .select_related("author")
        .prefetch_related("reviewers", "assignees")
    )

    # Pagination
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Get PR labels for filter
    labels = PullRequestLabel.objects.filter(project=project)

    # Count PRs by state
    open_count = PullRequest.objects.filter(project=project, state="open").count()
    closed_count = PullRequest.objects.filter(project=project, state="closed").count()
    merged_count = PullRequest.objects.filter(project=project, state="merged").count()

    # Get branches for branch selector
    from apps.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    manager = get_project_filesystem_manager(project.owner)
    project_path = manager.get_project_root_path(project)

    branches = []
    current_branch = project.current_branch or "develop"
    if project_path and project_path.exists():
        try:
            result = subprocess.run(
                ["git", "branch", "-a"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.strip():
                        # Remove * prefix and remotes/origin/ prefix
                        branch = line.replace("*", "").strip()
                        branch = branch.replace("remotes/origin/", "")
                        if branch and branch not in branches:
                            branches.append(branch)
                        # Check if this is the current branch
                        if line.startswith("*"):
                            current_branch = branch
        except Exception as e:
            logger.debug(f"Error getting branches: {e}")

    if not branches:
        branches = [current_branch]

    context = {
        "project": project,
        "page_obj": page_obj,
        "prs": page_obj.object_list,
        "state_filter": state_filter,
        "author_filter": author_filter,
        "reviewer_filter": reviewer_filter,
        "label_filter": label_filter,
        "sort_by": sort_by,
        "direction": direction,
        "labels": labels,
        "open_count": open_count,
        "closed_count": closed_count,
        "merged_count": merged_count,
        "can_create": project.can_edit(request.user),
        "branches": branches,
        "current_branch": current_branch,
    }

    return render(request, "project_app/pull_requests/list.html", context)


def pr_compare(request, username, slug):
    """
    Branch comparison for creating PR.

    URL: /<username>/<slug>/compare/<base>...<head>/
    """
    from .utils import get_project_branches, compare_branches

    project = get_object_or_404(Project, owner__username=username, slug=slug)

    # Check permissions
    if not project.can_view(request.user):
        raise Http404("Project not found")

    # Get compare parameters
    compare_str = request.GET.get("compare", "")
    if "..." in compare_str:
        base, head = compare_str.split("...")
    else:
        base = project.current_branch or "main"
        head = ""

    # Get list of branches
    branches = get_project_branches(project)

    # Get comparison data
    comparison = None
    if head and base:
        comparison = compare_branches(project, base, head)

    context = {
        "project": project,
        "base_branch": base,
        "head_branch": head,
        "branches": branches,
        "comparison": comparison,
        "can_create": project.can_edit(request.user),
    }

    return render(request, "project_app/pull_requests/form.html", context)
