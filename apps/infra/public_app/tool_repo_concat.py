#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repository Concatenator Tool - Concatenate API."""

from __future__ import annotations

import json
import logging
import shutil

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .tool_repo_clone import get_temp_repos

logger = logging.getLogger(__name__)

# Patterns to ignore when processing files
IGNORE_PATTERNS = {
    ".git",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".egg-info",
    "htmlcov",
    "venv",
    ".venv",
}


@require_http_methods(["POST"])
def api_concatenate_repo(request):
    """
    Concatenate repository files and cleanup.

    POST data:
    - temp_path: Path to cloned repository
    - max_lines: Maximum lines per file
    - max_depth: Maximum directory depth
    - extensions: List of file extensions to include

    Returns:
    - content: Concatenated markdown content
    - stats: File count, line count, character count
    """
    try:
        data = json.loads(request.body)
        temp_path_key = data.get("temp_path", "")
        max_lines = data.get("max_lines", 100)
        max_depth = data.get("max_depth", 5)
        extensions = set(data.get("extensions", []))

        # Get temp path and metadata
        temp_repos = get_temp_repos()
        repo_data = temp_repos.get(temp_path_key)
        if not repo_data:
            return JsonResponse(
                {"error": "Repository not found or expired"}, status=404
            )

        temp_path = repo_data["temp_path"]
        subdirectory = repo_data.get("subdirectory")
        branch = repo_data.get("branch", "main")

        if not temp_path.exists():
            return JsonResponse({"error": "Repository path not found"}, status=404)

        # Determine the base path for concatenation
        base_path = temp_path
        if subdirectory:
            base_path = temp_path / subdirectory
            if not base_path.exists():
                return JsonResponse(
                    {"error": f'Subdirectory "{subdirectory}" not found'}, status=404
                )

        # Generate concatenated content
        output, stats = _generate_concatenated_content(
            base_path, subdirectory, branch, extensions, max_lines, max_depth
        )

        # Cleanup temporary directory
        _cleanup_temp_repo(temp_path, temp_path_key, temp_repos)

        return JsonResponse({"success": True, "content": output, "stats": stats})

    except Exception as e:
        logger.error(f"Error in concatenate_repo: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def _generate_concatenated_content(
    base_path, subdirectory, branch, extensions, max_lines, max_depth
):
    """Generate concatenated markdown content from repository files."""
    output = f"# Repository Contents: {subdirectory or 'Root'}\n\n"
    if subdirectory:
        output += f"Branch: {branch}\nSubdirectory: {subdirectory}\n\n"

    # Generate tree structure
    output += _generate_tree_structure(base_path, max_depth)

    # Concatenate file contents
    file_output, stats = _concatenate_files(base_path, extensions, max_lines, max_depth)
    output += file_output

    return output, stats


def _generate_tree_structure(base_path, max_depth):
    """Generate directory tree structure."""
    output = "## Directory Structure\n```\n"
    tree_lines = []

    for file_path in sorted(base_path.rglob("*")):
        if any(pattern in str(file_path) for pattern in IGNORE_PATTERNS):
            continue

        relative_path = file_path.relative_to(base_path)
        depth = len(relative_path.parts) - 1

        if depth <= max_depth:
            indent = "  " * depth
            tree_lines.append(f"{indent}{relative_path.name}")

    output += "\n".join(tree_lines[:500])  # Limit tree size
    output += "\n```\n\n"
    return output


def _concatenate_files(base_path, extensions, max_lines, max_depth):
    """Concatenate file contents with stats tracking."""
    output = "## File Contents\n\n"
    file_count = 0
    line_count = 0
    char_count = 0

    for file_path in sorted(base_path.rglob("*")):
        if not file_path.is_file():
            continue

        # Check ignore patterns
        if any(pattern in str(file_path) for pattern in IGNORE_PATTERNS):
            continue

        # Check extension
        ext = file_path.suffix.lower()
        if ext not in extensions:
            continue

        # Check depth
        relative_path = file_path.relative_to(base_path)
        depth = len(relative_path.parts) - 1
        if depth > max_depth:
            continue

        # Read and format file content
        file_output, lines, chars = _format_file_content(
            file_path, relative_path, ext, max_lines
        )
        if file_output:
            output += file_output
            file_count += 1
            line_count += lines
            char_count += chars

    stats = {
        "file_count": file_count,
        "line_count": line_count,
        "char_count": char_count,
    }
    return output, stats


def _format_file_content(file_path, relative_path, ext, max_lines):
    """Format a single file's content for concatenation."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()

        output = f"### {relative_path}\n```{ext[1:]}\n"

        if len(lines) <= max_lines:
            output += content
        else:
            output += "\n".join(lines[:max_lines])
            output += f"\n... [{len(lines) - max_lines} lines truncated]"

        output += "\n```\n\n"
        return output, min(len(lines), max_lines), len(content)

    except Exception as e:
        logger.warning(f"Error reading {file_path}: {e}")
        return None, 0, 0


def _cleanup_temp_repo(temp_path, temp_path_key, temp_repos):
    """Cleanup temporary repository directory."""
    try:
        shutil.rmtree(temp_path, ignore_errors=True)
        del temp_repos[temp_path_key]
    except Exception as e:
        logger.warning(f"Error cleaning up temp directory: {e}")


# EOF
