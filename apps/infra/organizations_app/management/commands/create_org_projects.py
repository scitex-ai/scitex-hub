"""
Management command to create projects for the scitex-ai organization.

This command creates Django Project records and sets up git repositories
with multiple remotes for flexible source management.

Remotes:
- origin: ywatanabe1989 personal GitHub (primary)
- github-scitex-ai: scitex-ai organization on GitHub
- scitex-ai-local: Local Gitea server
"""

import subprocess
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.infra.organizations_app.models import Organization
from apps.infra.project_app.models import Project

# Gitea server URL (will be set dynamically based on environment)
GITEA_BASE_URL = "http://gitea:3000"  # Docker internal URL

# Define the organization projects with multiple remote sources
SCITEX_PROJECTS = [
    {
        "name": "scitex-cloud",
        "slug": "scitex-cloud",
        "description": "SciTeX Cloud - Web platform for scientific research workflow management",
        "source_url": "https://github.com/scitex-ai/scitex-cloud",
        "primary_language": "Python",
    },
    {
        "name": "scitex-python",
        "slug": "scitex-python",
        "description": "Core SciTeX Python package for scientific computing and research automation",
        "source_url": "https://github.com/scitex-ai/scitex-python",
        "primary_language": "Python",
    },
    {
        "name": "scitex-writer",
        "slug": "scitex-writer",
        "description": "Scientific manuscript writing and LaTeX document generation",
        "source_url": "https://github.com/scitex-ai/scitex-writer",
        "primary_language": "Python",
    },
    {
        "name": "scitex-dataset",
        "slug": "scitex-dataset",
        "description": "Research dataset management and versioning",
        "source_url": "https://github.com/scitex-ai/scitex-dataset",
        "primary_language": "Python",
    },
    {
        "name": "figrecipe",
        "slug": "figrecipe",
        "description": "Scientific figure generation recipes and visualization tools",
        "source_url": "https://github.com/scitex-ai/figrecipe",
        "primary_language": "Python",
    },
    {
        "name": "crossref-local",
        "slug": "crossref-local",
        "description": "Local CrossRef database for academic paper metadata and citations",
        "source_url": "https://github.com/scitex-ai/crossref-local",
        "primary_language": "Python",
    },
    {
        "name": "openalex-local",
        "slug": "openalex-local",
        "description": "Local OpenAlex database for open academic metadata",
        "source_url": "https://github.com/scitex-ai/openalex-local",
        "primary_language": "Python",
    },
]


def get_remotes_for_project(slug: str, gitea_org: str = "scitex-ai") -> dict:
    """Generate remote URLs for a project."""
    return {
        "origin": f"https://github.com/ywatanabe1989/{slug}.git",
        "github-scitex-ai": f"https://github.com/scitex-ai/{slug}.git",
        "scitex-ai-local": f"{GITEA_BASE_URL}/{gitea_org}/{slug}.git",
    }


class Command(BaseCommand):
    help = "Create projects for the scitex-ai organization with multiple git remotes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--org",
            type=str,
            default="scitex-ai",
            help="Organization slug (default: scitex-ai)",
        )
        parser.add_argument(
            "--owner",
            type=str,
            default="ywatanabe",
            help="Project owner username (default: ywatanabe)",
        )
        parser.add_argument(
            "--setup-git",
            action="store_true",
            help="Initialize git repos and configure remotes",
        )
        parser.add_argument(
            "--clone-from",
            type=str,
            choices=["origin", "github-scitex-ai"],
            default=None,
            help="Clone from specified remote (origin=ywatanabe1989, github-scitex-ai)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-setup even if directory exists",
        )

    def _get_project_path(self, owner_username: str, slug: str) -> Path:
        """Get the local path for a project."""
        return Path(settings.BASE_DIR) / "data" / "users" / owner_username / slug

    def _run_git(self, args: list, cwd: Path) -> tuple[bool, str]:
        """Run a git command and return (success, output)."""
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                cwd=str(cwd),
                timeout=300,
            )
            output = result.stdout + result.stderr
            return result.returncode == 0, output.strip()
        except Exception as e:
            return False, str(e)

    def _setup_git_repo(
        self,
        project_path: Path,
        remotes: dict,
        clone_from: str = None,
        force: bool = False,
    ) -> tuple[bool, str]:
        """Set up git repository with multiple remotes."""
        import shutil

        git_dir = project_path / ".git"

        # Handle existing directory
        if project_path.exists():
            if git_dir.exists() and not force:
                # Already a git repo - just update remotes
                return self._update_remotes(project_path, remotes)
            elif force:
                shutil.rmtree(project_path)

        # Create directory
        project_path.mkdir(parents=True, exist_ok=True)

        # Clone or init
        if clone_from and clone_from in remotes:
            # Clone from specified remote
            clone_url = remotes[clone_from]
            success, output = self._run_git(
                ["clone", clone_url, str(project_path)], project_path.parent
            )
            if not success:
                return False, f"Clone failed: {output}"

            # Rename origin if we cloned from github-scitex-ai
            if clone_from != "origin":
                self._run_git(["remote", "rename", "origin", clone_from], project_path)
                # Add the actual origin
                self._run_git(
                    ["remote", "add", "origin", remotes["origin"]], project_path
                )
        else:
            # Just initialize empty repo
            success, output = self._run_git(["init"], project_path)
            if not success:
                return False, f"Git init failed: {output}"

        # Add/update all remotes
        return self._update_remotes(project_path, remotes)

    def _update_remotes(self, project_path: Path, remotes: dict) -> tuple[bool, str]:
        """Add or update git remotes."""
        messages = []

        for name, url in remotes.items():
            # Check if remote exists
            success, existing = self._run_git(["remote", "get-url", name], project_path)

            if success:
                # Remote exists - update URL if different
                if existing.strip() != url:
                    self._run_git(["remote", "set-url", name, url], project_path)
                    messages.append(f"Updated {name}")
            else:
                # Remote doesn't exist - add it
                self._run_git(["remote", "add", name, url], project_path)
                messages.append(f"Added {name}")

        return True, ", ".join(messages) if messages else "Remotes unchanged"

    def handle(self, *args, **options):
        org_slug = options["org"]
        owner_username = options["owner"]
        setup_git = options["setup_git"]
        clone_from = options["clone_from"]
        force = options["force"]

        # Get organization
        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"Organization '{org_slug}' not found. Run setup_scitex_org first."
                )
            )
            return

        # Get owner user
        try:
            owner = User.objects.get(username=owner_username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User '{owner_username}' not found."))
            return

        self.stdout.write(f"Creating projects for organization: {org.name}")
        self.stdout.write(f"Owner: {owner.username}")
        if setup_git:
            self.stdout.write("Git setup: ENABLED")
            if clone_from:
                self.stdout.write(f"Clone from: {clone_from}")
        self.stdout.write("")

        created_count = 0
        updated_count = 0
        git_setup_count = 0
        errors = []

        for project_data in SCITEX_PROJECTS:
            slug = project_data["slug"]

            project, created = Project.objects.get_or_create(
                slug=slug,
                organization=org,
                defaults={
                    "name": project_data["name"],
                    "description": project_data["description"],
                    "owner": owner,
                    "visibility": "public",
                    "source": "github",
                    "source_url": project_data.get("source_url", ""),
                    "primary_language": project_data.get("primary_language", ""),
                },
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"  Created: {project.name} ({slug})")
                )
                created_count += 1
            else:
                if project.organization != org:
                    project.organization = org
                    project.save()
                    self.stdout.write(
                        self.style.WARNING(f"  Updated: {project.name} (linked to org)")
                    )
                    updated_count += 1
                else:
                    self.stdout.write(f"  Exists: {project.name}")

            # Set up git repository with remotes
            if setup_git:
                project_path = self._get_project_path(owner_username, slug)
                remotes = get_remotes_for_project(slug, org_slug)

                success, message = self._setup_git_repo(
                    project_path, remotes, clone_from=clone_from, force=force
                )

                if success:
                    self.stdout.write(
                        self.style.SUCCESS(f"    -> Git: {message} at {project_path}")
                    )
                    git_setup_count += 1
                else:
                    self.stdout.write(self.style.ERROR(f"    -> Git failed: {message}"))
                    errors.append((slug, message))

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Created: {created_count}, Updated: {updated_count}"
            )
        )
        if setup_git:
            self.stdout.write(f"Git setup: {git_setup_count}, Errors: {len(errors)}")
            if errors:
                self.stdout.write("\nErrors:")
                for slug, error in errors:
                    self.stdout.write(f"  {slug}: {error}")

        self.stdout.write("")
        self.stdout.write("Remotes configured:")
        self.stdout.write("  origin          -> github.com/ywatanabe1989/{slug}")
        self.stdout.write("  github-scitex-ai -> github.com/scitex-ai/{slug}")
        self.stdout.write("  scitex-ai-local  -> gitea:3000/scitex-ai/{slug}")
        self.stdout.write("")
        self.stdout.write("Project URLs:")
        for project_data in SCITEX_PROJECTS:
            self.stdout.write(f"  /{org_slug}/{project_data['slug']}/")
