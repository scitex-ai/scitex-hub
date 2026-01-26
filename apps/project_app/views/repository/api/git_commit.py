#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git commit and discard operations API.

Provides endpoints for:
- Commit staged changes
- Discard changes
"""

from __future__ import annotations

import json
import logging
import shutil

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from ....models import Project
from .git_utils import get_project_path, run_git_command
from .permissions import check_project_write_access

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def api_git_discard(request, username, slug):
    """Discard changes to files (revert to last commit)."""
    try:
        user = get_object_or_404(User, username=username)
        project = get_object_or_404(Project, slug=slug, owner=user)

        if not check_project_write_access(request, project):
            return JsonResponse(
                {"success": False, "error": "Permission denied"}, status=403
            )

        data = json.loads(request.body)
        paths = data.get("paths", [])

        if not paths:
            return JsonResponse(
                {"success": False, "error": "No paths specified"}, status=400
            )

        project_path = get_project_path(project)
        if not project_path or not project_path.exists():
            return JsonResponse(
                {"success": False, "error": "Project directory not found"}, status=404
            )

        # Discard changes for each file
        discarded = []
        errors = []
        for path in paths:
            full_path = project_path / path
            file_exists = full_path.exists()

            # Try to restore from HEAD
            success, stdout, stderr = run_git_command(
                project_path, ["restore", "--source=HEAD", "--", path]
            )

            if success:
                discarded.append(path)
            else:
                # git restore failed - check if it's an untracked file
                if file_exists:
                    # Untracked file - need to remove it
                    try:
                        if full_path.is_dir():
                            shutil.rmtree(full_path)
                        else:
                            full_path.unlink()
                        discarded.append(path)
                    except Exception as e:
                        errors.append({"path": path, "error": str(e)})
                else:
                    # File doesn't exist and restore failed - try legacy checkout
                    success2, _, stderr2 = run_git_command(
                        project_path, ["checkout", "HEAD", "--", path]
                    )
                    if success2:
                        discarded.append(path)
                    else:
                        errors.append(
                            {
                                "path": path,
                                "error": stderr.strip()
                                or stderr2.strip()
                                or "Cannot restore file",
                            }
                        )

        return JsonResponse(
            {
                "success": len(errors) == 0,
                "discarded": discarded,
                "errors": errors,
                "message": f"Discarded changes to {len(discarded)} file(s)"
                if discarded
                else "No changes discarded",
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error discarding changes: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_git_commit(request, username, slug):
    """Commit staged changes."""
    try:
        user = get_object_or_404(User, username=username)
        project = get_object_or_404(Project, slug=slug, owner=user)

        if not check_project_write_access(request, project):
            return JsonResponse(
                {"success": False, "error": "Permission denied"}, status=403
            )

        data = json.loads(request.body)
        message = data.get("message", "").strip()
        push = data.get("push", False)

        if not message:
            return JsonResponse(
                {"success": False, "error": "Commit message is required"}, status=400
            )

        project_path = get_project_path(project)
        if not project_path or not project_path.exists():
            return JsonResponse(
                {"success": False, "error": "Project directory not found"}, status=404
            )

        # Check if there are staged changes
        success, stdout, stderr = run_git_command(
            project_path, ["diff", "--cached", "--name-only"]
        )
        if not stdout.strip():
            return JsonResponse(
                {
                    "success": False,
                    "error": "No staged changes to commit. Stage files first.",
                },
                status=400,
            )

        # Commit
        success, stdout, stderr = run_git_command(
            project_path, ["commit", "-m", message]
        )
        if not success:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Commit failed: {stderr.strip()}",
                },
                status=500,
            )

        # Get commit hash
        hash_success, hash_out, _ = run_git_command(project_path, ["rev-parse", "HEAD"])
        commit_hash = hash_out.strip()[:8] if hash_success else "unknown"

        result = {
            "success": True,
            "message": f"Committed: {message}",
            "commit_hash": commit_hash,
            "pushed": False,
        }

        # Push if requested
        if push:
            push_success, push_out, push_err = run_git_command(
                project_path, ["push", "origin", "HEAD"], timeout=60
            )
            if push_success:
                result["pushed"] = True
                result["message"] += " (pushed)"
            else:
                result["push_error"] = push_err.strip()

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error committing: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# EOF
