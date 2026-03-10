from django.db import models
from django.contrib.auth.models import User


class UserFollow(models.Model):
    """
    Model for user following relationships (GitHub-style).

    A user can follow other users to see their activity in their feed.
    """

    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="following",
        help_text="User who is following",
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="followers",
        help_text="User being followed",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "following")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["follower", "-created_at"]),
            models.Index(fields=["following", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"

    @classmethod
    def is_following(cls, follower, following):
        """Check if follower is following the user"""
        if not follower or not follower.is_authenticated:
            return False
        return cls.objects.filter(follower=follower, following=following).exists()

    @classmethod
    def get_followers_count(cls, user):
        """Get count of followers for a user"""
        return cls.objects.filter(following=user).count()

    @classmethod
    def get_following_count(cls, user):
        """Get count of users this user is following"""
        return cls.objects.filter(follower=user).count()


class RepositoryStar(models.Model):
    """
    Model for repository starring (GitHub-style).

    Users can star repositories to bookmark them and show appreciation.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="starred_repositories",
        help_text="User who starred the repository",
    )
    project = models.ForeignKey(
        "project_app.Project",
        on_delete=models.CASCADE,
        related_name="stars",
        help_text="Repository that was starred",
    )
    starred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "project")
        ordering = ["-starred_at"]
        indexes = [
            models.Index(fields=["user", "-starred_at"]),
            models.Index(fields=["project", "-starred_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} starred {self.project.name}"

    @classmethod
    def is_starred(cls, user, project):
        """Check if user has starred this project"""
        if not user or not user.is_authenticated:
            return False
        return cls.objects.filter(user=user, project=project).exists()

    @classmethod
    def get_star_count(cls, project):
        """Get count of stars for a project"""
        return cls.objects.filter(project=project).count()

    @classmethod
    def get_user_starred_count(cls, user):
        """Get count of repositories starred by user"""
        return cls.objects.filter(user=user).count()


class Activity(models.Model):
    """
    Model for tracking user activity (GitHub-style activity feed).

    Tracks actions like: follow, star, commit, create project, etc.
    """

    ACTIVITY_TYPES = [
        ("follow", "Followed user"),
        ("star", "Starred repository"),
        ("create_project", "Created repository"),
        ("fork", "Forked repository"),
        ("commit", "Committed to repository"),
        ("issue", "Created issue"),
        ("pr", "Created pull request"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="activities",
        help_text="User who performed the activity",
    )
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)

    # Polymorphic relationships - store related object info as JSON
    target_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="targeted_activities",
        help_text="Target user (for follow actions)",
    )
    target_project = models.ForeignKey(
        "project_app.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="project_activities",
        help_text="Target project (for star, fork, commit actions)",
    )

    # Additional metadata stored as JSON
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional activity metadata (commit message, issue title, etc.)",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["activity_type", "-created_at"]),
        ]
        verbose_name_plural = "Activities"

    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()} ({self.created_at.strftime('%Y-%m-%d')})"

    @classmethod
    def create_follow_activity(cls, follower, following):
        """Create activity for following a user"""
        return cls.objects.create(
            user=follower, activity_type="follow", target_user=following
        )

    @classmethod
    def create_star_activity(cls, user, project):
        """Create activity for starring a repository"""
        return cls.objects.create(
            user=user, activity_type="star", target_project=project
        )

    @classmethod
    def create_project_activity(cls, user, project):
        """Create activity for creating a repository"""
        return cls.objects.create(
            user=user, activity_type="create_project", target_project=project
        )
