"""
Project Validation Methods
Contains: Name validation, slug generation, and uniqueness checks
"""

import re


class ProjectValidationMixin:
    """Mixin containing validation and name generation methods for Project model"""

    # ----------------------------------------
    # Class Methods for Name/Slug Generation
    # ----------------------------------------

    @classmethod
    def generate_unique_slug(cls, name, owner=None):
        """
        Generate a unique slug from project name (unique per owner, not globally)

        Follows GitHub repository naming rules:
        - Only alphanumeric, hyphens, underscores, periods
        - Cannot start or end with special characters
        - Max 100 characters
        """
        from django.utils.text import slugify

        # Use Django's slugify (handles unicode, converts to ASCII)
        base_slug = slugify(name)

        # Further sanitize for GitHub compatibility
        # GitHub allows: alphanumeric, hyphens, underscores, periods
        base_slug = re.sub(r"[^a-z0-9._-]", "-", base_slug.lower())

        # Remove leading/trailing special chars
        base_slug = re.sub(r"^[._-]+|[._-]+$", "", base_slug)

        # Ensure not empty
        if not base_slug:
            base_slug = "project"

        # Limit to 100 chars (GitHub limit)
        base_slug = base_slug[:100]

        # Check if slug is unique for this owner (if owner provided)
        if owner:
            if not cls.objects.filter(slug=base_slug, owner=owner).exists():
                return base_slug

            # If base slug exists for this owner, try with numbers
            counter = 1
            while True:
                unique_slug = f"{base_slug}-{counter}"
                if not cls.objects.filter(slug=unique_slug, owner=owner).exists():
                    return unique_slug
                counter += 1
        else:
            # Legacy behavior: check globally (for backward compatibility)
            if not cls.objects.filter(slug=base_slug).exists():
                return base_slug

            # If base slug exists globally, try with numbers
            counter = 1
            while True:
                unique_slug = f"{base_slug}-{counter}"
                if not cls.objects.filter(slug=unique_slug).exists():
                    return unique_slug
                counter += 1

    @classmethod
    def generate_unique_name(cls, base_name, owner):
        """Generate a unique project name for the given owner"""
        # First try the base name
        if not cls.objects.filter(name=base_name, owner=owner).exists():
            return base_name

        # If base name exists, try with numbers
        counter = 1
        while True:
            unique_name = f"{base_name}_{counter}"
            if not cls.objects.filter(name=unique_name, owner=owner).exists():
                return unique_name
            counter += 1

    # ----------------------------------------
    # Validation Methods
    # ----------------------------------------

    @classmethod
    def validate_name_uniqueness(cls, name, owner, exclude_id=None):
        """Validate that project name is unique for the user"""
        queryset = cls.objects.filter(name=name, owner=owner)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return not queryset.exists()

    @classmethod
    def validate_repository_name(cls, name):
        """
        Validate repository name according to GitHub/Gitea naming rules

        Returns:
            Tuple of (is_valid: bool, error_message: str or None)

        Rules:
        - Cannot contain spaces
        - Must be 1-100 characters
        - Can only contain: alphanumeric, hyphens, underscores, periods
        - Cannot start or end with special characters (-, _, .)
        - Cannot be empty or whitespace only
        """
        # Check if empty or whitespace only
        if not name or not name.strip():
            return False, "Repository name cannot be empty"

        # Check length
        if len(name) > 100:
            return False, "Repository name must be 100 characters or less"

        # Check for spaces
        if " " in name:
            return (
                False,
                "Repository name cannot contain spaces. Use hyphens (-) or underscores (_) instead.",
            )

        # Check for valid characters (alphanumeric, hyphens, underscores, periods)
        if not re.match(r"^[a-zA-Z0-9._-]+$", name):
            return (
                False,
                "Repository name can only contain letters, numbers, hyphens (-), underscores (_), and periods (.)",
            )

        # Check that it doesn't start or end with special characters
        if re.match(r"^[._-]", name) or re.match(r"[._-]$", name):
            return (
                False,
                "Repository name cannot start or end with hyphens, underscores, or periods",
            )

        return True, None

    @classmethod
    def validate_name_using_scitex(cls, name):
        """
        Validate project name using scitex.project validator.

        Raises:
            ValidationError: If name is invalid
            ImportError: If scitex package is not installed
        """
        from django.core.exceptions import ValidationError

        try:
            from scitex.project import validate_name
        except ImportError:
            # Fall back to existing validator
            return cls.validate_repository_name(name)

        is_valid, error = validate_name(name)
        if not is_valid:
            raise ValidationError(error)

    # ----------------------------------------
    # Name Conversion Methods
    # ----------------------------------------

    def get_github_safe_name(self):
        """Get a GitHub-safe repository name"""
        # GitHub repo names: alphanumeric, hyphens, underscores, periods
        # Cannot start/end with special chars, max 100 chars
        safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", self.name.lower())
        safe_name = re.sub(r"^[._-]+|[._-]+$", "", safe_name)
        safe_name = safe_name[:100]  # GitHub limit
        return safe_name or "scitex_project"

    def get_filesystem_safe_name(self):
        """Get a filesystem-safe directory name"""
        # Remove/replace characters that are problematic for filesystems
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", self.name)
        safe_name = re.sub(r"\s+", "_", safe_name)  # Replace spaces with underscores
        safe_name = safe_name[:255]  # Filesystem limit
        return safe_name or "scitex_project"

    @staticmethod
    def extract_repo_name_from_url(git_url: str) -> str:
        """
        Extract repository name from Git URL, preserving the original name.

        Examples:
            https://github.com/user/my-repo.git -> my-repo
            https://github.com/user/MyRepo -> MyRepo
            git@github.com:user/awesome_project.git -> awesome_project

        Args:
            git_url: Git repository URL

        Returns:
            Repository name extracted from URL (preserves original case and valid characters)
        """
        git_url = git_url.strip()

        # Remove .git suffix if present
        if git_url.endswith(".git"):
            git_url = git_url[:-4]

        # Extract repo name (last part of path)
        # Works for both HTTPS and SSH formats
        repo_name = git_url.rstrip("/").split("/")[-1]

        # Only decode URL encoding if present, but keep original name otherwise
        try:
            from urllib.parse import unquote

            repo_name = unquote(repo_name)
        except (ValueError, TypeError, AttributeError):
            pass

        return repo_name or "imported-repo"
