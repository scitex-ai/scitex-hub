"""
Pull Request Detail Views

Handles PR detail display with diff, commits, and conversation.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from django.db.models import Prefetch
import logging

from apps.project_app.models import (
    Project,
    PullRequest,
    PullRequestReview,
    PullRequestComment,
    PullRequestCommit,
    PullRequestEvent,
)
from .utils import (
    get_pr_diff,
    get_pr_checks,
    get_pr_timeline,
    get_project_branches,
    compare_branches,
    sync_pr_commits,
    check_pr_conflicts,
)

logger = logging.getLogger(__name__)


def pr_detail(request, username, slug, pr_number):
    """
    Show PR detail with diff, commits, conversation.

    URL: /<username>/<slug>/pull/<pr_number>/
    """
    project = get_object_or_404(Project, owner__username=username, slug=slug)
    pr = get_object_or_404(PullRequest, project=project, number=pr_number)

    # Check permissions
    if not project.can_view(request.user):
        raise Http404("Project not found")

    # Get tab (conversation, commits, files, checks)
    active_tab = request.GET.get("tab", "conversation")

    # Get PR data with related objects
    pr = (
        PullRequest.objects.filter(project=project, number=pr_number)
        .select_related("author", "merged_by")
        .prefetch_related(
            "reviewers",
            "assignees",
            Prefetch(
                "comments", queryset=PullRequestComment.objects.select_related("author")
            ),
            Prefetch(
                "reviews", queryset=PullRequestReview.objects.select_related("reviewer")
            ),
            Prefetch("commits", queryset=PullRequestCommit.objects.all()),
            Prefetch(
                "events", queryset=PullRequestEvent.objects.select_related("actor")
            ),
        )
        .first()
    )

    if not pr:
        raise Http404("Pull request not found")

    # Get approval status
    approval_status = pr.get_approval_status()

    # Check if user can merge
    can_merge, merge_reason = (
        pr.can_merge(request.user)
        if request.user.is_authenticated
        else (False, "Not authenticated")
    )

    # Get diff if on files tab
    diff_data = None
    changed_files = []
    if active_tab == "files":
        diff_data, changed_files = get_pr_diff(project, pr)

    # Get checks status (if checks are configured)
    checks = []
    if active_tab == "checks":
        checks = get_pr_checks(project, pr)

    # Get timeline (comments + events merged chronologically)
    timeline = get_pr_timeline(pr)

    context = {
        "project": project,
        "pr": pr,
        "active_tab": active_tab,
        "approval_status": approval_status,
        "can_merge": can_merge,
        "merge_reason": merge_reason,
        "can_edit": project.can_edit(request.user),
        "is_author": request.user == pr.author
        if request.user.is_authenticated
        else False,
        "diff_data": diff_data,
        "changed_files": changed_files,
        "checks": checks,
        "timeline": timeline,
    }

    return render(request, "project_app/pull_requests/detail.html", context)


@login_required
def pr_create(request, username, slug):
    """
    Form to create new PR from branch comparison.

    URL: /<username>/<slug>/pull/new/
    """
    project = get_object_or_404(Project, owner__username=username, slug=slug)

    # Check permissions
    if not project.can_edit(request.user):
        messages.error(request, "You don't have permission to create pull requests")
        return redirect("user_projects:detail", username=username, slug=slug)

    # Get compare parameters (base and head branches)
    base_branch = request.GET.get("base", project.current_branch or "main")
    head_branch = request.GET.get("head", "")

    # Get list of branches
    branches = get_project_branches(project)

    if request.method == "POST":
        # Create PR
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        base = request.POST.get("base", base_branch)
        head = request.POST.get("head", head_branch)
        is_draft = request.POST.get("is_draft") == "on"
        reviewers = request.POST.getlist("reviewers")

        # Validation
        if not title:
            messages.error(request, "PR title is required")
        elif not head:
            messages.error(request, "Source branch is required")
        elif base == head:
            messages.error(request, "Source and target branches must be different")
        else:
            try:
                # Create PR
                pr = PullRequest.objects.create(
                    project=project,
                    title=title,
                    description=description,
                    author=request.user,
                    source_branch=head,
                    target_branch=base,
                    state="draft" if is_draft else "open",
                    is_draft=is_draft,
                )

                # Add reviewers
                if reviewers:
                    from django.contrib.auth.models import User

                    reviewer_users = User.objects.filter(username__in=reviewers)
                    pr.reviewers.set(reviewer_users)

                # Sync commits from git
                sync_pr_commits(pr)

                # Check for conflicts
                check_pr_conflicts(pr)

                # Create event
                PullRequestEvent.objects.create(
                    pull_request=pr,
                    event_type="opened",
                    actor=request.user,
                )

                messages.success(
                    request, f"Pull request #{pr.number} created successfully"
                )
                return redirect(
                    "user_projects:pr_detail",
                    username=username,
                    slug=slug,
                    pr_number=pr.number,
                )

            except Exception as e:
                logger.error(f"Failed to create PR: {e}")
                messages.error(request, f"Failed to create pull request: {str(e)}")

    # Get comparison data if both branches are selected
    comparison = None
    if head_branch and base_branch:
        comparison = compare_branches(project, base_branch, head_branch)

    # Get potential reviewers (collaborators)
    potential_reviewers = project.collaborators.exclude(id=request.user.id)

    context = {
        "project": project,
        "base_branch": base_branch,
        "head_branch": head_branch,
        "branches": branches,
        "comparison": comparison,
        "potential_reviewers": potential_reviewers,
    }

    return render(request, "project_app/pull_requests/form.html", context)
