#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-04"
# File: /home/ywatanabe/proj/scitex-hub/apps/project_app/views/pull_requests/form.py
# ----------------------------------------
"""
Pull Request Form Views

Handles PR creation and branch comparison.
"""

from __future__ import annotations

import logging
import subprocess

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404

from apps.infra.project_app.models import (
    Project,
    PullRequest,
    PullRequestEvent,
)
from apps.infra.project_app.services.git_ref_validation import (
    END_OF_OPTIONS,
    is_valid_git_ref,
)

logger = logging.getLogger(__name__)


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
        return redirect("project_app:detail", username=username, slug=slug)

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
                    "project_app:pr_detail",
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


def pr_compare(request, username, slug):
    """
    Branch comparison for creating PR.

    URL: /<username>/<slug>/compare/<base>...<head>/
    """
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


# ============================================================================
# Helper Functions
# ============================================================================


def get_project_branches(project):
    """
    Get list of branches for a project.

    Returns:
        list: Branch names
    """
    try:
        from apps.infra.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        manager = get_project_filesystem_manager(project.owner)
        project_path = manager.get_project_root_path(project)

        if not project_path or not project_path.exists():
            return []

        # Get branches from git
        result = subprocess.run(
            ["git", "branch", "-a"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return []

        # Parse branch names
        branches = []
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line and not line.startswith("*"):
                # Remove remote prefix
                branch = line.replace("remotes/origin/", "")
                if branch not in branches:
                    branches.append(branch)

        return sorted(branches)

    except Exception as e:
        logger.error(f"Failed to get branches: {e}")
        return []


def compare_branches(project, base, head):
    """
    Compare two branches.

    Returns:
        dict: Comparison data (commits, files changed, diff)
    """
    try:
        from apps.infra.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        manager = get_project_filesystem_manager(project.owner)
        project_path = manager.get_project_root_path(project)

        if not project_path or not project_path.exists():
            return None

        # base/head are request-derived; reject option-injecting refs and
        # terminate options before them (see services.git_ref_validation).
        if not (is_valid_git_ref(base) and is_valid_git_ref(head)):
            logger.warning("Rejected invalid branch ref in compare: %r...%r", base, head)
            return None

        # Get diff between branches
        result = subprocess.run(
            ["git", "diff", "--stat", END_OF_OPTIONS, f"{base}...{head}"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return None

        # Get commit count
        commit_result = subprocess.run(
            ["git", "rev-list", "--count", END_OF_OPTIONS, f"{base}..{head}"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10,
        )

        commit_count = (
            int(commit_result.stdout.strip()) if commit_result.returncode == 0 else 0
        )

        return {
            "base": base,
            "head": head,
            "commit_count": commit_count,
            "diff_stat": result.stdout,
        }

    except Exception as e:
        logger.error(f"Failed to compare branches: {e}")
        return None


def sync_pr_commits(pr):
    """
    Sync commits from git to PR.

    Args:
        pr: PullRequest instance
    """
    try:
        from apps.infra.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )
        from apps.infra.project_app.models import PullRequestCommit

        manager = get_project_filesystem_manager(pr.project.owner)
        project_path = manager.get_project_root_path(pr.project)

        if not project_path or not project_path.exists():
            return

        # Get commits between base and head
        result = subprocess.run(
            [
                "git",
                "log",
                "--format=%H|%an|%ae|%at|%s",
                END_OF_OPTIONS,
                f"{pr.target_branch}..{pr.source_branch}",
            ],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return

        # Parse and create commit records
        for line in result.stdout.split("\n"):
            if not line.strip():
                continue

            parts = line.split("|")
            if len(parts) >= 5:
                commit_hash, author_name, author_email, timestamp, message = parts[:5]

                # Create or update commit
                PullRequestCommit.objects.get_or_create(
                    pull_request=pr,
                    commit_hash=commit_hash,
                    defaults={
                        "commit_message": message,
                        "author_name": author_name,
                        "author_email": author_email,
                        "committed_at": timezone.datetime.fromtimestamp(int(timestamp)),
                    },
                )

    except Exception as e:
        logger.error(f"Failed to sync PR commits: {e}")


def check_pr_conflicts(pr):
    """
    Check if PR has merge conflicts.

    Args:
        pr: PullRequest instance
    """
    try:
        from apps.infra.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        manager = get_project_filesystem_manager(pr.project.owner)
        project_path = manager.get_project_root_path(pr.project)

        if not project_path or not project_path.exists():
            return

        # Try to merge (dry run)
        result = subprocess.run(
            ["git", "merge-tree", END_OF_OPTIONS, pr.target_branch, pr.source_branch],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Check for conflicts in output
        has_conflicts = "CONFLICT" in result.stdout

        # Update PR
        pr.has_conflicts = has_conflicts
        if has_conflicts:
            # Parse conflict files
            conflict_files = []
            for line in result.stdout.split("\n"):
                if "CONFLICT" in line:
                    # Extract filename from conflict message
                    parts = line.split()
                    if len(parts) > 2:
                        conflict_files.append(parts[-1])
            pr.conflict_files = conflict_files

        pr.save(update_fields=["has_conflicts", "conflict_files"])

    except Exception as e:
        logger.error(f"Failed to check PR conflicts: {e}")


# EOF
