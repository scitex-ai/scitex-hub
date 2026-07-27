#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git history and diff operations API.

Provides endpoints for:
- View commit history
- View diff
"""

from __future__ import annotations

import logging

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from ....models import Project
from ....services.git_ref_validation import END_OF_OPTIONS, is_valid_git_ref
from .git_utils import get_project_path, run_git_command
from .permissions import check_project_read_access

logger = logging.getLogger(__name__)

# Backwards-compatible alias. A git revision (``from``/``to``) is placed in a
# git argv position that PRECEDES the ``--`` path separator, so ``--`` cannot
# protect it — a value beginning with ``-`` is parsed by git as an OPTION, not
# a ref. That is argument injection even though the argv is a list and
# shell=False: e.g. ``?from=--output=/path`` makes ``git diff`` write to an
# attacker-chosen file. This endpoint is reachable UNAUTHENTICATED for any
# public project (permissions.check_project_read_access returns True for anon
# on visibility=="public"), so the ref must be validated, not merely quoted.
# The validator now lives in services.git_ref_validation and is shared across
# every git view; ``--end-of-options`` is inserted before the refs as well.
_is_valid_git_ref = is_valid_git_ref


@require_http_methods(["GET"])
def api_git_history(request, username, slug):
    """Get git history for a file or directory."""
    try:
        user = get_object_or_404(User, username=username)
        project = get_object_or_404(Project, slug=slug, owner=user)

        if not check_project_read_access(request, project):
            return JsonResponse(
                {"success": False, "error": "Permission denied"}, status=403
            )

        path = request.GET.get("path", "")
        limit = min(int(request.GET.get("limit", 20)), 100)

        project_path = get_project_path(project)
        if not project_path or not project_path.exists():
            return JsonResponse(
                {"success": False, "error": "Project directory not found"}, status=404
            )

        # Build git log command
        # Format: hash|author|date|subject
        log_format = "%H|%an|%aI|%s"
        args = ["log", f"--format={log_format}", f"-{limit}"]

        if path:
            args.extend(["--", path])

        success, stdout, stderr = run_git_command(project_path, args)
        if not success:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Failed to get history: {stderr.strip()}",
                },
                status=500,
            )

        commits = []
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append(
                    {
                        "hash": parts[0],
                        "short_hash": parts[0][:8],
                        "author": parts[1],
                        "date": parts[2],
                        "subject": parts[3],
                    }
                )

        return JsonResponse(
            {
                "success": True,
                "path": path or "(project root)",
                "commits": commits,
                "total": len(commits),
            }
        )

    except ValueError:
        return JsonResponse(
            {"success": False, "error": "Invalid limit parameter"}, status=400
        )
    except Exception as e:
        logger.error(f"Error getting history: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["GET"])
def api_git_diff(request, username, slug):
    """Get diff for a file or between commits."""
    try:
        user = get_object_or_404(User, username=username)
        project = get_object_or_404(Project, slug=slug, owner=user)

        if not check_project_read_access(request, project):
            return JsonResponse(
                {"success": False, "error": "Permission denied"}, status=403
            )

        path = request.GET.get("path", "")
        commit1 = request.GET.get("from", "")  # e.g., "HEAD~1" or specific hash
        commit2 = request.GET.get("to", "")  # e.g., "HEAD" or specific hash
        staged = request.GET.get("staged", "false").lower() == "true"

        # Reject any ref that could be parsed by git as an option (see
        # _GIT_REF_RE). These land before the ``--`` separator, so validation
        # — not the terminator — is what closes the argument injection.
        for ref in (commit1, commit2):
            if ref and not _is_valid_git_ref(ref):
                return JsonResponse(
                    {"success": False, "error": "Invalid commit reference"},
                    status=400,
                )

        project_path = get_project_path(project)
        if not project_path or not project_path.exists():
            return JsonResponse(
                {"success": False, "error": "Project directory not found"}, status=404
            )

        # Build diff command. User-supplied revs are placed AFTER
        # ``--end-of-options`` so git can never parse a ``-``-leading value as
        # an option (belt to the validation braces above).
        args = ["diff"]

        if staged:
            args.append("--cached")
        elif commit1 and commit2:
            args.extend([END_OF_OPTIONS, commit1, commit2])
        elif commit1:
            args.extend([END_OF_OPTIONS, commit1])
        # else: diff working tree vs index

        if path:
            args.extend(["--", path])

        success, stdout, stderr = run_git_command(project_path, args, timeout=10)
        if not success and stderr:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Failed to get diff: {stderr.strip()}",
                },
                status=500,
            )

        # Parse diff to get stats
        stat_args = args.copy()
        stat_args.insert(1, "--stat")
        _, stat_out, _ = run_git_command(project_path, stat_args)

        return JsonResponse(
            {
                "success": True,
                "path": path or "(all files)",
                "from": commit1 or "working tree",
                "to": commit2 or ("staged" if staged else "index"),
                "diff": stdout,
                "stat": stat_out.strip(),
            }
        )

    except Exception as e:
        logger.error(f"Error getting diff: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# EOF
