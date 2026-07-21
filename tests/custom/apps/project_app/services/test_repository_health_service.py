#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/project_app/services/repository_health_service.py.

Currently focused on the clone-import-path regression: the file used to
``from apps.infra.project_app.signals import _clone_gitea_repo_to_data_dir``
(stale; the package root doesn't re-export that helper), which crashed
``RepositoryHealthChecker.sync_repository`` and ``.restore_repository`` at
runtime with ``ImportError`` — observed during the operator-12834
agent-publish demo against prod scitex.ai. The fix moves both imports to
the canonical submodule path. These tests pin the fix in two complementary
ways without mocks: (1) the real production source has no occurrence of
the broken path, (2) the helper is actually importable from the canonical
path the production source now uses.
"""

import inspect
from pathlib import Path

import pytest


def test_clone_helper_importable_from_canonical_submodule():
    # Arrange
    # Act
    from apps.infra.project_app.signals.project_initialization import (
        _clone_gitea_repo_to_data_dir,
    )

    # Assert
    assert callable(_clone_gitea_repo_to_data_dir)


def test_repository_health_service_source_has_no_stale_clone_import():
    # Arrange
    from apps.infra.project_app.services import repository_health_service

    src = Path(inspect.getsourcefile(repository_health_service)).read_text()
    stale = "from apps.infra.project_app.signals import _clone_gitea_repo_to_data_dir"

    # Act
    occurrences = src.count(stale)

    # Assert — guards against future regressions reintroducing the bare
    # package-root import path.
    assert occurrences == 0


def test_repository_health_checker_class_imports_without_error():
    # Arrange
    # Act
    from apps.infra.project_app.services.repository_health_service import (
        RepositoryHealthChecker,
    )

    # Assert — module-level execution succeeded (no ImportError surfacing
    # from any of the lazy local imports inside sync_repository /
    # restore_repository was the bug; the class-level smoke import is the
    # cheapest regression proof).
    assert RepositoryHealthChecker is not None


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/project_app/services/repository_health_service.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# """
# Repository Health Check Service
#
# Monitors and manages the health of Django projects and their corresponding
# Gitea repositories. Ensures strict 1:1 mapping between:
#   Local filesystem ↔ Django Project ↔ Gitea Repository
# """
#
# import logging
# from typing import Dict, List, Tuple
# from pathlib import Path
# from django.contrib.auth.models import User
# from apps.infra.project_app.models import Project
# from apps.infra.gitea_app.api_client import GiteaClient, GiteaAPIError
#
# logger = logging.getLogger(__name__)
#
#
# class RepositoryHealthIssue:
#     """Represents a single repository health issue"""
#
#     ISSUE_TYPES = {
#         "orphaned_in_gitea": "Orphaned in Gitea",
#         "missing_in_gitea": "Missing in Gitea",
#         "missing_directory": "Missing local directory",
#         "healthy": "Healthy",
#     }
#
#     def __init__(
#         self,
#         issue_type: str,
#         project_slug: str = None,
#         gitea_name: str = None,
#         message: str = None,
#     ):
#         self.issue_type = issue_type
#         self.project_slug = project_slug or gitea_name
#         self.gitea_name = gitea_name
#         self.message = message or self.ISSUE_TYPES.get(issue_type, "Unknown issue")
#         self.is_healthy = issue_type == "healthy"
#         self.is_critical = issue_type in ["orphaned_in_gitea", "missing_in_gitea"]
#
#     def to_dict(self):
#         return {
#             "issue_type": self.issue_type,
#             "project_slug": self.project_slug,
#             "gitea_name": self.gitea_name,
#             "message": self.message,
#             "is_healthy": self.is_healthy,
#             "is_critical": self.is_critical,
#         }
#
#
# class RepositoryHealthChecker:
#     """Checks and monitors repository health for a user"""
#
#     def __init__(self, user: User):
#         self.user = user
#         self.client = GiteaClient()
#
#     def check_all_repositories(self) -> Tuple[List[RepositoryHealthIssue], Dict]:
#         """
#         Check health of all repositories for a user.
#
#         Returns:
#             Tuple of (issues_list, stats_dict)
#         """
#         issues = []
#         stats = {
#             "total_django_projects": 0,
#             "total_gitea_repos": 0,
#             "healthy_count": 0,
#             "critical_issues": 0,
#             "warnings": 0,
#         }
#
#         try:
#             # Get all Django projects for this user
#             django_projects = Project.objects.filter(owner=self.user)
#             django_slugs = set(django_projects.values_list("slug", flat=True))
#             stats["total_django_projects"] = len(django_slugs)
#
#             # Get all Gitea repositories for this user
#             try:
#                 gitea_repos = self.client.list_repositories(self.user.username)
#                 gitea_names = {repo["name"]: repo for repo in gitea_repos}
#                 stats["total_gitea_repos"] = len(gitea_names)
#             except (GiteaAPIError, Exception) as e:
#                 logger.warning(
#                     f"Could not fetch Gitea repos for {self.user.username}: {e}"
#                 )
#                 gitea_names = {}
#
#             # Check each Django project
#             for project in django_projects:
#                 issue = self._check_django_project(project, gitea_names)
#                 issues.append(issue)
#                 if issue.is_healthy:
#                     stats["healthy_count"] += 1
#                 elif issue.is_critical:
#                     stats["critical_issues"] += 1
#                 else:
#                     stats["warnings"] += 1
#
#             # Check for orphaned Gitea repos
#             for gitea_name in gitea_names.keys():
#                 if gitea_name not in django_slugs:
#                     issue = RepositoryHealthIssue(
#                         "orphaned_in_gitea",
#                         gitea_name=gitea_name,
#                         message=f"Repository exists in Gitea but no Django project found",
#                     )
#                     issues.append(issue)
#                     stats["critical_issues"] += 1
#
#         except Exception as e:
#             logger.error(f"Error checking repository health: {e}")
#             raise
#
#         return issues, stats
#
#     def _check_django_project(
#         self, project: Project, gitea_names: Dict
#     ) -> RepositoryHealthIssue:
#         """Check health of a single Django project"""
#
#         # Check if Gitea repo exists
#         if project.slug not in gitea_names:
#             return RepositoryHealthIssue(
#                 "missing_in_gitea",
#                 project_slug=project.slug,
#                 message=f"Django project exists but Gitea repository not found",
#             )
#
#         # Check if local directory exists
#         if project.git_clone_path:
#             git_dir = Path(project.git_clone_path)
#             if not git_dir.exists():
#                 return RepositoryHealthIssue(
#                     "missing_directory",
#                     project_slug=project.slug,
#                     message=f"Local git directory missing: {project.git_clone_path}",
#                 )
#
#         # All checks passed
#         return RepositoryHealthIssue(
#             "healthy",
#             project_slug=project.slug,
#             message=f"Repository healthy and in sync",
#         )
#
#     def delete_orphaned_repository(self, gitea_name: str) -> Tuple[bool, str]:
#         """
#         Delete an orphaned Gitea repository.
#
#         Returns:
#             Tuple of (success: bool, message: str)
#         """
#         try:
#             self.client.delete_repository(self.user.username, gitea_name)
#             message = f"✓ Deleted Gitea repository: {self.user.username}/{gitea_name}"
#             logger.info(message)
#             return True, message
#         except Exception as e:
#             message = f"✗ Failed to delete: {str(e)}"
#             logger.error(
#                 f"Failed to delete orphaned repo {self.user.username}/{gitea_name}: {e}"
#             )
#             return False, message
#
#     def sync_repository(self, project_slug: str) -> Tuple[bool, str]:
#         """
#         Sync a project's local directory with Gitea.
#
#         Returns:
#             Tuple of (success: bool, message: str)
#         """
#         try:
#             project = Project.objects.get(owner=self.user, slug=project_slug)
#
#             # Check if Gitea repo exists
#             try:
#                 self.client.get_repository(self.user.username, project_slug)
#             except GiteaAPIError:
#                 # Repo doesn't exist in Gitea - would need to recreate it
#                 return (
#                     False,
#                     f"Gitea repository doesn't exist for {project_slug}. Manual intervention needed.",
#                 )
#
#             # Re-clone from Gitea if directory is missing
#             if not project.git_clone_path or not Path(project.git_clone_path).exists():
#                 from apps.infra.project_app.signals import _clone_gitea_repo_to_data_dir
#
#                 _clone_gitea_repo_to_data_dir(project)
#                 return True, f"✓ Re-cloned repository to: {project.git_clone_path}"
#
#             return True, f"✓ Repository {project_slug} is in sync"
#
#         except Project.DoesNotExist:
#             return False, f"Project {project_slug} not found"
#         except Exception as e:
#             logger.error(f"Failed to sync repository {project_slug}: {e}")
#             return False, f"✗ Error during sync: {str(e)}"
#
#     def restore_orphaned_repository(
#         self, gitea_name: str, project_name: str
#     ) -> Tuple[bool, str, int]:
#         """
#         Restore an orphaned Gitea repository by creating a new Django project.
#
#         An orphaned repository exists in Gitea but has no corresponding Django project.
#         This creates the missing Django project and restores the 1:1:1 mapping.
#
#         Args:
#             gitea_name: Name of the Gitea repository
#             project_name: Name for the new Django project
#
#         Returns:
#             Tuple of (success: bool, message: str, project_id: int or None)
#         """
#         try:
#             # Verify the Gitea repository exists
#             try:
#                 repo = self.client.get_repository(self.user.username, gitea_name)
#             except GiteaAPIError:
#                 return False, f"Gitea repository '{gitea_name}' not found", None
#
#             # Create Django project linked to the existing Gitea repo
#             from django.utils.text import slugify
#
#             slug = slugify(project_name)
#
#             # Check if project with this slug already exists
#             if Project.objects.filter(owner=self.user, slug=slug).exists():
#                 return False, f"Project with slug '{slug}' already exists", None
#
#             # Create the project without triggering Gitea creation signal
#             # (because repo already exists)
#             project = Project.objects.create(
#                 name=project_name,
#                 slug=slug,
#                 description=f"Restored from Gitea repository: {gitea_name}",
#                 owner=self.user,
#                 visibility="private",  # Default to private
#             )
#
#             # Update with Gitea information
#             project.gitea_repo_url = repo.get("html_url", "")
#             project.gitea_clone_url = repo.get("clone_url", "")
#             project.gitea_ssh_url = repo.get("ssh_url", "")
#             project.gitea_repo_id = repo.get("id")
#             project.gitea_repo_name = repo.get("name", gitea_name)
#             project.gitea_enabled = True
#             project.save(
#                 update_fields=[
#                     "gitea_repo_url",
#                     "gitea_clone_url",
#                     "gitea_ssh_url",
#                     "gitea_repo_id",
#                     "gitea_repo_name",
#                     "gitea_enabled",
#                 ]
#             )
#
#             # Clone the repository to local filesystem
#             from apps.infra.project_app.signals import _clone_gitea_repo_to_data_dir
#
#             _clone_gitea_repo_to_data_dir(project)
#
#             logger.info(
#                 f"✓ Restored project {project.name} (slug: {slug}) from Gitea repository {gitea_name}"
#             )
#             return (
#                 True,
#                 f"✓ Successfully restored project '{project_name}' from Gitea repository",
#                 project.id,
#             )
#
#         except Exception as e:
#             logger.error(f"Failed to restore repository {gitea_name}: {e}")
#             logger.exception("Full traceback:")
#             return False, f"✗ Error restoring repository: {str(e)}", None
#
#
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: apps/project_app/services/repository_health_service.py
# --------------------------------------------------------------------------------
