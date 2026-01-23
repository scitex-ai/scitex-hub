"""
Project Custom Managers and QuerySets
Contains: Custom managers for Project model
"""

from django.db import models


class ProjectQuerySet(models.QuerySet):
    """Custom QuerySet for Project model"""

    def public(self):
        """Return only public projects"""
        return self.filter(visibility='public')

    def private(self):
        """Return only private projects"""
        return self.filter(visibility='private')

    def local_repos(self):
        """Return only local (Git-enabled) projects"""
        return self.filter(project_type='local')

    def remote_repos(self):
        """Return only remote (SSHFS mount) projects"""
        return self.filter(project_type='remote')

    def with_gitea(self):
        """Return only projects with Gitea integration enabled"""
        return self.filter(gitea_enabled=True)

    def with_github(self):
        """Return only projects with GitHub integration enabled"""
        return self.filter(github_integration_enabled=True)

    def for_user(self, user):
        """Return projects accessible to a user (owned or collaborated)"""
        if not user or not user.is_authenticated:
            return self.public()

        return self.filter(
            models.Q(owner=user) |
            models.Q(collaborators=user) |
            models.Q(visibility='public')
        ).distinct()

    def owned_by(self, user):
        """Return projects owned by a user"""
        return self.filter(owner=user)


class ProjectManager(models.Manager):
    """Custom manager for Project model"""

    def get_queryset(self):
        return ProjectQuerySet(self.model, using=self._db)

    def public(self):
        return self.get_queryset().public()

    def private(self):
        return self.get_queryset().private()

    def local_repos(self):
        return self.get_queryset().local_repos()

    def remote_repos(self):
        return self.get_queryset().remote_repos()

    def with_gitea(self):
        return self.get_queryset().with_gitea()

    def with_github(self):
        return self.get_queryset().with_github()

    def for_user(self, user):
        return self.get_queryset().for_user(user)

    def owned_by(self, user):
        return self.get_queryset().owned_by(user)
