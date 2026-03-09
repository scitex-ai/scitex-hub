"""
Pull Request mixins - methods for PullRequest model.
"""

from django.utils import timezone


class PullRequestMergeMixin:
    """Mixin providing merge-related methods for PullRequest."""

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


class PullRequestStateMixin:
    """Mixin providing state-related methods for PullRequest."""

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


class PullRequestReviewMixin:
    """Mixin providing review-related methods for PullRequest."""

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
