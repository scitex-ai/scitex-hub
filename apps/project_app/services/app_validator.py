#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""App Validator — check Gitea repo structure before marketplace submission."""

from __future__ import annotations

import base64
import logging
import re

from apps.gitea_app.api_client.client import GiteaClient
from apps.gitea_app.exceptions import GiteaAPIError

logger = logging.getLogger(__name__)

REQUIRED_FILES = [
    "apps.py",
    "views.py",
    "urls.py",
    "LICENSE",
    "README.md",
]

REQUIRED_TEMPLATE_PATTERN = "templates/{app_name}/index_partial.html"

AGENTS_FILES = [".agents/agents.json", ".agents/README.md"]

FORBIDDEN_PATTERNS = [
    (r"\bsubprocess\b", "subprocess"),
    (r"\bos\.system\b", "os.system"),
    (r"\beval\s*\(", "eval()"),
    (r"\bexec\s*\(", "exec()"),
    (r"\b__import__\b", "__import__"),
]


def _list_repo_files(client, owner, repo, path="", ref="main"):
    """Recursively list all files in a repo, returning relative paths."""
    try:
        entries = client.list_files(owner, repo, path=path, ref=ref)
    except GiteaAPIError:
        return []

    files = []
    if isinstance(entries, list):
        for entry in entries:
            if entry.get("type") == "file":
                files.append(entry.get("path", ""))
            elif entry.get("type") == "dir":
                files.extend(
                    _list_repo_files(client, owner, repo, path=entry["path"], ref=ref)
                )
    return files


def _get_file_content(client, owner, repo, filepath, ref="main"):
    """Get decoded file content from Gitea repo."""
    try:
        data = client.get_file_contents(owner, repo, filepath, ref=ref)
        content_b64 = data.get("content", "")
        return base64.b64decode(content_b64).decode("utf-8", errors="replace")
    except GiteaAPIError:
        return None


def validate_app_structure(project) -> list[str]:
    """Check that the Gitea repo has the required files for an app."""
    errors = []

    owner = project.owner.username
    repo = project.gitea_repo_name or project.slug
    if not project.gitea_enabled:
        return ["Project must have a Gitea repository to be submitted as an app."]

    try:
        client = GiteaClient()
    except GiteaAPIError as exc:
        return [f"Cannot connect to Gitea: {exc}"]

    repo_files = _list_repo_files(client, owner, repo)
    if not repo_files:
        return ["Repository appears empty or inaccessible."]

    repo_files_set = set(repo_files)

    for required in REQUIRED_FILES:
        if required not in repo_files_set:
            errors.append(f"Missing required file: {required}")

    # Check template pattern
    app_name = repo.replace("-", "_")
    template_path = REQUIRED_TEMPLATE_PATTERN.format(app_name=app_name)
    if template_path not in repo_files_set:
        errors.append(
            f"Missing template: {template_path} "
            f"(app_name derived from repo: {app_name})"
        )

    # Check at least one agents file
    has_agents = any(af in repo_files_set for af in AGENTS_FILES)
    if not has_agents:
        errors.append(
            "Missing agents config: at least one of "
            + ", ".join(AGENTS_FILES)
            + " is required."
        )

    return errors


def validate_app_security(project) -> list[str]:
    """Scan Python files for forbidden patterns."""
    errors = []

    owner = project.owner.username
    repo = project.gitea_repo_name or project.slug

    try:
        client = GiteaClient()
    except GiteaAPIError:
        return ["Cannot connect to Gitea for security scan."]

    repo_files = _list_repo_files(client, owner, repo)
    py_files = [f for f in repo_files if f.endswith(".py")]

    for filepath in py_files:
        content = _get_file_content(client, owner, repo, filepath)
        if content is None:
            continue
        for pattern, name in FORBIDDEN_PATTERNS:
            if re.search(pattern, content):
                errors.append(f"Forbidden pattern '{name}' found in {filepath}")

    return errors


def validate_app(project) -> list[str]:
    """Combined validation: structure + security."""
    errors = validate_app_structure(project)
    errors.extend(validate_app_security(project))
    return errors


# EOF
