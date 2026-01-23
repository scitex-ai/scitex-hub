"""
Pull Request model - GitHub-style code review workflow.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class PullRequest(models.Model):
    """
    Model for Pull Requests - GitHub-style code review workflow.

    Represents a request to merge changes from source_branch into target_branch.
    """

    STATE_CHOICES = [
        ("open", "Open"),
        ("closed", "Closed"),
        ("merged", "Merged"),
        ("draft", "Draft"),
    ]

    # Core fields
    project = models.ForeignKey(
        "project_app.Project",
        on_delete=models.CASCADE,
        related_name="pull_requests",
        help_text="Project this PR belongs to",
    )
    number = models.IntegerField(help_text="PR number (auto-incremented per project)")
    title = models.CharField(
        max_length=255, help_text="PR title (e.g., 'Add neural decoder model')"
    )
    description = models.TextField(
        blank=True, help_text="PR description (supports Markdown)"
    )

    # Author
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="authored_pull_requests",
        help_text="User who created the PR",
    )

    # Branch information
    source_branch = models.CharField(
        max_length=255, help_text="Branch to merge from (e.g., 'feature/add-decoder')"
    )
    target_branch = models.CharField(
        max_length=255,
        default="main",
        help_text="Branch to merge into (e.g., 'main', 'develop')",
    )

    # State
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default="open",
        db_index=True,
        help_text="Current state of the PR",
    )
    is_draft = models.BooleanField(
        default=False, help_text="Whether this is a draft PR (work in progress)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    merged_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # Merge information
    merged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="merged_pull_requests",
        help_text="User who merged the PR",
    )
    merge_commit_sha = models.CharField(
        max_length=40, blank=True, help_text="SHA of the merge commit"
    )
    merge_strategy = models.CharField(
        max_length=20,
        blank=True,
        help_text="Merge strategy used (merge, squash, rebase)",
    )

    # Merge conflict detection
    has_conflicts = models.BooleanField(
        default=False, help_text="Whether PR has merge conflicts"
    )
    conflict_files = models.JSONField(
        default=list, blank=True, help_text="List of files with conflicts"
    )

    # Review requirements
    reviewers = models.ManyToManyField(
        User,
        related_name="review_requested_prs",
        blank=True,
        help_text="Users requested to review this PR",
    )
    required_approvals = models.IntegerField(
        default=0, help_text="Number of approvals required before merge"
    )

    # Labels and assignees
    labels = models.JSONField(
        default=list, blank=True, help_text="PR labels (e.g., ['bug', 'enhancement'])"
    )
    assignees = models.ManyToManyField(
        User,
        related_name="assigned_prs",
        blank=True,
        help_text="Users assigned to work on this PR",
    )

    # CI/CD status
    ci_status = models.CharField(
        max_length=20,
        blank=True,
        help_text="CI/CD check status (pending, success, failure)",
    )

    class Meta:
        unique_together = ("project", "number")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "state"]),
            models.Index(fields=["project", "number"]),
            models.Index(fields=["author", "created_at"]),
        ]
        verbose_name = "Pull Request"
        verbose_name_plural = "Pull Requests"

    def __str__(self):
        return f"PR #{self.number}: {self.title}"

    def save(self, *args, **kwargs):
        # Auto-increment PR number per project
        if not self.number:
            last_pr = (
                PullRequest.objects.filter(project=self.project)
                .order_by("-number")
                .first()
            )
            self.number = (last_pr.number + 1) if last_pr else 1
        super().save(*args, **kwargs)

    @property
    def is_open(self):
        """Check if PR is open"""
        return self.state == "open"

    @property
    def is_merged(self):
        """Check if PR is merged"""
        return self.state == "merged"

    @property
    def is_closed(self):
        """Check if PR is closed (but not merged)"""
        return self.state == "closed"

    def get_approval_status(self):
        """
        Get approval status for this PR.

        Returns:
            dict: {
                'approved_count': int,
                'changes_requested_count': int,
                'commented_count': int,
                'is_approved': bool
            }
        """
        reviews = self.reviews.all()

        # Get latest review from each reviewer
        latest_reviews = {}
        for review in reviews.order_by("created_at"):
            latest_reviews[review.reviewer_id] = review

        approved = sum(1 for r in latest_reviews.values() if r.state == "approved")
        changes_requested = sum(
            1 for r in latest_reviews.values() if r.state == "changes_requested"
        )
        commented = sum(1 for r in latest_reviews.values() if r.state == "commented")

        return {
            "approved_count": approved,
            "changes_requested_count": changes_requested,
            "commented_count": commented,
            "is_approved": approved >= self.required_approvals
            and changes_requested == 0,
        }

    def can_merge(self, user):
        """
        Check if user can merge this PR.

        Args:
            user: User attempting to merge

        Returns:
            tuple: (can_merge: bool, reason: str)
        """
        if not self.is_open:
            return False, "PR is not open"

        if not self.project.can_edit(user):
            return False, "User does not have permission to merge"

        if self.has_conflicts:
            return False, "PR has merge conflicts"

        approval_status = self.get_approval_status()
        if not approval_status["is_approved"]:
            return False, f"PR requires {self.required_approvals} approval(s)"

        if self.ci_status == "failure":
            return False, "CI/CD checks failed"

        if self.ci_status == "pending":
            return False, "CI/CD checks are still running"

        return True, "OK"

    def merge(self, user, strategy="merge", commit_message=None):
        """
        Merge this PR using the specified strategy.

        Args:
            user: User performing the merge
            strategy: Merge strategy ('merge', 'squash', 'rebase')
            commit_message: Optional custom commit message

        Returns:
            tuple: (success: bool, message: str)
        """
        can_merge, reason = self.can_merge(user)
        if not can_merge:
            return False, reason

        # TODO: Implement actual git merge logic here
        self.state = "merged"
        self.merged_at = timezone.now()
        self.merged_by = user
        self.merge_strategy = strategy
        self.save()

        return True, "PR merged successfully"

    def close(self, user):
        """
        Close this PR without merging.

        Args:
            user: User closing the PR

        Returns:
            tuple: (success: bool, message: str)
        """
        if not self.is_open:
            return False, "PR is not open"

        if not self.project.can_edit(user):
            return False, "User does not have permission to close"

        self.state = "closed"
        self.closed_at = timezone.now()
        self.save()

        return True, "PR closed successfully"

    def reopen(self, user):
        """
        Reopen a closed PR.

        Args:
            user: User reopening the PR

        Returns:
            tuple: (success: bool, message: str)
        """
        if self.is_merged:
            return False, "Cannot reopen merged PR"

        if not self.is_closed:
            return False, "PR is not closed"

        if not self.project.can_edit(user):
            return False, "User does not have permission to reopen"

        self.state = "open"
        self.closed_at = None
        self.save()

        return True, "PR reopened successfully"

    def get_absolute_url(self):
        """Get URL for this PR"""
        from django.urls import reverse

        return reverse(
            "user_projects:pr_detail",
            kwargs={
                "username": self.project.owner.username,
                "slug": self.project.slug,
                "pr_number": self.number,
            },
        )
