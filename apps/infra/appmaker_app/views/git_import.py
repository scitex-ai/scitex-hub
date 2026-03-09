#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""App Maker — GitHub/git repository import endpoints."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess  # noqa: S404 — needed for git clone
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods

from ..models import UserModule
from ._helpers import has_forbidden_patterns

logger = logging.getLogger(__name__)


class GitImportError(Exception):
    """Raised when git import fails."""


@login_required
@require_http_methods(["POST"])
def api_import_from_github(request):
    """Import a module from a GitHub/git repository URL.

    Clones the repo to a temp dir, reads module.py for source code,
    reads manifest.yaml for metadata, validates, and creates UserModule.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON."}, status=400)

    repo_url = data.get("repo_url", "").strip()
    ref = data.get("ref", "main").strip()

    if not repo_url:
        return JsonResponse(
            {"success": False, "error": "Repository URL is required."}, status=400
        )

    if not _is_valid_git_url(repo_url):
        return JsonResponse(
            {"success": False, "error": "Invalid repository URL."}, status=400
        )

    try:
        module_data = _clone_and_extract_module(repo_url, ref)
    except GitImportError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

    if has_forbidden_patterns(module_data["source_code"]):
        return JsonResponse(
            {"success": False, "error": "Source code contains forbidden patterns."},
            status=400,
        )

    slug = slugify(module_data["label"])[:60]
    if not slug:
        slug = slugify(module_data["name"])[:60]
    if not slug:
        return JsonResponse(
            {"success": False, "error": "Cannot derive a valid slug from module name."},
            status=400,
        )

    if UserModule.objects.filter(author=request.user, slug=slug).exists():
        return JsonResponse(
            {"success": False, "error": f"Module with slug '{slug}' already exists."},
            status=400,
        )

    user_module = UserModule.objects.create(
        slug=slug,
        label=module_data["label"],
        author=request.user,
        source_code=module_data["source_code"],
        icon=module_data.get("icon", "fa-puzzle-piece"),
        category=module_data.get("category", "utility"),
        description=module_data.get("description", "")[:300],
        version=module_data.get("version", "0.1.0"),
        source_repo_url=repo_url,
        source_repo_ref=ref,
    )

    return JsonResponse(
        {
            "success": True,
            "slug": user_module.slug,
            "message": f"Module '{user_module.label}' imported from {repo_url}.",
        }
    )


@login_required
@require_http_methods(["POST"])
def api_sync_from_github(request, slug):
    """Re-sync a git-sourced module from its origin repository."""
    user_module = get_object_or_404(
        UserModule, slug=slug, author=request.user, is_active=True
    )

    if not user_module.source_repo_url:
        return JsonResponse(
            {"success": False, "error": "Module has no source repository."}, status=400
        )

    try:
        module_data = _clone_and_extract_module(
            user_module.source_repo_url,
            user_module.source_repo_ref or "main",
        )
    except GitImportError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

    if has_forbidden_patterns(module_data["source_code"]):
        return JsonResponse(
            {"success": False, "error": "Source code contains forbidden patterns."},
            status=400,
        )

    user_module.source_code = module_data["source_code"]
    user_module.description = module_data.get("description", "")[:300]
    user_module.version = module_data.get("version", user_module.version)
    user_module.save()

    return JsonResponse(
        {
            "success": True,
            "slug": user_module.slug,
            "message": f"Module '{user_module.label}' synced from repository.",
        }
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _is_valid_git_url(url: str) -> bool:
    """Validate that the URL looks like a git repository."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("https", "http"):
        return False
    if not parsed.netloc:
        return False
    return True


def _clone_and_extract_module(repo_url: str, ref: str) -> dict:
    """Clone a git repo to a temp dir and extract module source + metadata.

    Returns dict with keys: name, label, source_code, icon, category,
    description, version.
    """
    tmpdir = tempfile.mkdtemp(prefix="stx-module-import-")
    try:
        result = subprocess.run(  # noqa: S603, S607
            ["git", "clone", "--depth", "1", "--branch", ref, repo_url, tmpdir],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            # Retry without --branch (use default branch)
            shutil.rmtree(tmpdir, ignore_errors=True)
            tmpdir = tempfile.mkdtemp(prefix="stx-module-import-")
            result = subprocess.run(  # noqa: S603, S607
                ["git", "clone", "--depth", "1", repo_url, tmpdir],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise GitImportError(f"Git clone failed: {result.stderr.strip()}")

        repo_path = Path(tmpdir)
        module_py = _find_module_file(repo_path)

        if module_py is None:
            raise GitImportError(
                "No module.py found. Repository must contain a module.py "
                "with @stx.module decorator."
            )

        source_code = module_py.read_text(encoding="utf-8")
        metadata = _read_manifest(repo_path)

        if not metadata.get("name"):
            parsed = urlparse(repo_url)
            repo_name = parsed.path.rstrip("/").split("/")[-1]
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]
            metadata["name"] = repo_name

        if not metadata.get("label"):
            metadata["label"] = (
                metadata["name"].replace("-", " ").replace("_", " ").title()
            )

        metadata["source_code"] = source_code
        return metadata

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _find_module_file(repo_path: Path):
    """Find the primary module Python file in a repository."""
    module_py = repo_path / "module.py"
    if module_py.exists():
        return module_py

    for candidate in repo_path.rglob("*.py"):
        try:
            content = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "@stx.module" in content or "stx.module" in content:
            return candidate

    return None


def _read_manifest(repo_path: Path) -> dict:
    """Read manifest.yaml from repo if it exists."""
    manifest_path = repo_path / "manifest.yaml"
    if not manifest_path.exists():
        manifest_path = repo_path / "manifest.yml"
    if not manifest_path.exists():
        return {}

    try:
        import yaml

        with manifest_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return {
            "name": data.get("name", ""),
            "label": data.get("label", ""),
            "icon": data.get("icon", "fa-puzzle-piece"),
            "category": data.get("category", "utility"),
            "description": data.get("description", ""),
            "version": data.get("version", "0.1.0"),
        }
    except Exception:
        return {}


# EOF
