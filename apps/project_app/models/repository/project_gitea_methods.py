"""
Project Gitea Integration Methods
Contains: Gitea-specific methods for Project model
"""

import logging
import subprocess


logger = logging.getLogger(__name__)


class ProjectGiteaMethodsMixin:
    """Mixin containing Gitea integration methods for Project model"""

    def create_gitea_repository(self, user_token: str = None):
        """
        Create repository in Gitea with one-to-one relationship validation

        Args:
            user_token: User's Gitea API token (optional, uses default if not provided)

        Returns:
            Gitea repository object

        Raises:
            Exception: If repository creation fails (including if it already exists)
        """
        from apps.gitea_app.api_client import GiteaClient
        from django.db.models import Q
        from .project import Project

        client = GiteaClient(token=user_token) if user_token else GiteaClient()

        # 1. Check if this project already has a Gitea repository
        if self.gitea_enabled and self.gitea_repo_id:
            logger.warning(
                f"Project {self.slug} already has Gitea repository {self.gitea_repo_id}"
            )
            raise Exception(f"Project already has a Gitea repository")

        # 2. Check if another Django project claims this Gitea repository
        existing_project = (
            Project.objects.filter(
                Q(owner=self.owner)
                & Q(gitea_repo_name=self.slug)
                & Q(gitea_enabled=True)
            )
            .exclude(id=self.id)
            .first()
        )

        if existing_project:
            raise Exception(
                f"A project named '{existing_project.name}' already uses Gitea repository '{self.slug}'"
            )

        # 3. Check if repository already exists in Gitea (enforce strict 1:1)
        try:
            existing_repo = client.get_repository(self.owner.username, self.slug)
            if existing_repo:
                # Repository exists - this violates 1:1 mapping
                logger.error(
                    f"Gitea repository {self.owner.username}/{self.slug} already exists (ID: {existing_repo.get('id')})"
                )
                raise Exception(
                    f"The repository '{self.slug}' already exists in Gitea (ID: {existing_repo.get('id')}). "
                    f"This is an orphaned repository. Please delete it manually or contact support."
                )
        except Exception as e:
            # If it's a 404, the repo doesn't exist (which is what we want for strict 1:1)
            if "404" not in str(e) and "not found" not in str(e).lower():
                # Some other error occurred - re-raise
                raise

        # 4. Create the repository in Gitea
        try:
            repo = client.create_repository(
                name=self.slug,
                description=self.description,
                private=(self.visibility == "private"),
                auto_init=True,
                gitignores="Python",
                readme="Default",
            )
        except Exception as create_error:
            logger.error(
                f"Failed to create Gitea repository {self.slug}: {create_error}"
            )
            raise Exception(f"Failed to create Gitea repository: {str(create_error)}")

        # 5. Update project with Gitea info (atomic operation)
        try:
            self.gitea_repo_id = repo["id"]
            self.gitea_repo_name = repo["name"]
            self.gitea_repo_url = repo.get("html_url", "")
            self.gitea_clone_url = repo.get("clone_url", "")
            self.gitea_ssh_url = repo.get("ssh_url", "")
            self.git_url = repo["clone_url"]  # HTTPS URL
            self.gitea_enabled = True
            self.save()

            logger.info(
                f"✓ Gitea repository created: {self.owner.username}/{self.slug} (ID: {repo['id']})"
            )
            return repo

        except Exception as e:
            # Rollback: delete the Gitea repository we just created
            logger.error(f"Failed to save project after Gitea creation: {e}")
            try:
                client.delete_repository(self.owner.username, self.slug)
                logger.info(f"✓ Rolled back Gitea repository {self.slug}")
            except Exception as cleanup_error:
                logger.error(
                    f"Failed to cleanup Gitea repository {self.slug}: {cleanup_error}"
                )
            raise Exception(f"Failed to link Gitea repository to project: {str(e)}")

    def clone_gitea_to_local(self):
        """
        Clone Gitea repository to local working directory

        Returns:
            Tuple of (success, path or error_message)
        """
        from apps.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        if not self.git_url:
            return False, "No git URL configured"

        manager = get_project_filesystem_manager(self.owner)
        clone_path = manager.base_path / self.slug

        # Remove existing directory if empty
        if clone_path.exists():
            if any(clone_path.iterdir()):
                return False, "Directory already exists and is not empty"
            else:
                clone_path.rmdir()

        try:
            result = subprocess.run(
                ["git", "clone", self.git_url, str(clone_path)],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                self.git_clone_path = str(clone_path)
                self.directory_created = True
                self.data_location = str(clone_path.relative_to(manager.base_path))
                self.save()
                return True, str(clone_path)
            else:
                return False, result.stderr

        except subprocess.TimeoutExpired:
            return False, "Clone operation timed out"
        except Exception as e:
            return False, str(e)

    def import_from_github(
        self,
        github_url: str,
        github_token: str = "",
        import_issues: bool = True,
        import_pulls: bool = True,
    ):
        """
        Import project from GitHub repository

        Args:
            github_url: GitHub repository URL
            github_token: GitHub personal access token (for private repos)
            import_issues: Import issues
            import_pulls: Import pull requests

        Returns:
            Tuple of (success, repo_object or error_message)
        """
        from apps.gitea_app.api_client import GiteaClient

        client = GiteaClient()

        try:
            repo = client.migrate_repository(
                clone_addr=github_url,
                repo_name=self.slug,
                service="github",
                auth_token=github_token,
                mirror=False,
                private=(self.visibility == "private"),
                description=self.description,
                issues=import_issues,
                pull_requests=import_pulls,
            )

            # Update project with Gitea info
            self.gitea_repo_id = repo["id"]
            self.gitea_repo_name = repo["name"]
            self.git_url = repo["clone_url"]
            self.gitea_enabled = True
            self.source = "github"
            self.source_url = github_url
            self.save()

            # Clone to local directory
            success, result = self.clone_gitea_to_local()

            return True, repo

        except Exception as e:
            return False, str(e)

    def delete_gitea_repository(self, user_token: str = None):
        """
        Delete the associated Gitea repository

        Args:
            user_token: User's Gitea API token (optional)

        Returns:
            Tuple of (success: bool, message: str)
        """
        from apps.gitea_app.api_client import GiteaClient

        if not self.gitea_enabled or not self.gitea_repo_name:
            return False, "No Gitea repository associated with this project"

        try:
            client = GiteaClient(token=user_token) if user_token else GiteaClient()
            client.delete_repository(self.owner.username, self.gitea_repo_name)

            # Clear Gitea integration fields
            self.gitea_repo_id = None
            self.gitea_repo_name = ""
            self.gitea_repo_url = ""
            self.gitea_clone_url = ""
            self.gitea_ssh_url = ""
            self.gitea_enabled = False
            self.save()

            logger.info(
                f"✓ Deleted Gitea repository: {self.owner.username}/{self.gitea_repo_name}"
            )
            return True, "Gitea repository deleted successfully"

        except Exception as e:
            logger.error(
                f"Failed to delete Gitea repository {self.gitea_repo_name}: {e}"
            )
            return False, str(e)

    @classmethod
    def cleanup_orphaned_gitea_repos(cls, user, user_token: str = None):
        """
        Find and optionally delete Gitea repositories that don't have corresponding Django projects

        Args:
            user: Django User object
            user_token: User's Gitea API token (optional)

        Returns:
            Dict with lists of orphaned repositories
        """
        from apps.gitea_app.api_client import GiteaClient

        client = GiteaClient(token=user_token) if user_token else GiteaClient()

        try:
            # Get all Gitea repositories for this user
            gitea_repos = client.list_repositories(user.username)

            # Get all Django projects with Gitea integration
            django_projects = cls.objects.filter(
                owner=user, gitea_enabled=True
            ).values_list("gitea_repo_name", "gitea_repo_id")

            django_repo_names = {name for name, _ in django_projects if name}
            django_repo_ids = {repo_id for _, repo_id in django_projects if repo_id}

            # Find orphaned repositories
            orphaned = []
            for repo in gitea_repos:
                repo_name = repo.get("name")
                repo_id = repo.get("id")

                if (
                    repo_name not in django_repo_names
                    and repo_id not in django_repo_ids
                ):
                    orphaned.append(
                        {
                            "id": repo_id,
                            "name": repo_name,
                            "url": repo.get("html_url", ""),
                            "created_at": repo.get("created_at", ""),
                        }
                    )

            return {
                "orphaned": orphaned,
                "total_gitea": len(gitea_repos),
                "total_django": len(django_repo_names),
            }

        except Exception as e:
            logger.error(f"Failed to check for orphaned repositories: {e}")
            return {"error": str(e)}
