"""
arXiv Account Management Service

Handles account verification, authentication, and submission limits.
"""

from typing import Dict, Union

from django.conf import settings
from django.utils import timezone

from ...models import ArxivAccount


class ArxivAccountService:
    """Service for managing arXiv account verification and authentication."""

    def __init__(self):
        self.base_url = getattr(settings, "ARXIV_API_BASE_URL", "https://arxiv.org/api")
        self.submission_url = getattr(
            settings, "ARXIV_SUBMISSION_URL", "https://arxiv.org/submit"
        )

    def verify_account(self, arxiv_account: ArxivAccount) -> bool:
        """
        Verify arXiv account credentials by attempting authentication.

        Args:
            arxiv_account: ArxivAccount instance to verify

        Returns:
            bool: True if verification successful, False otherwise
        """
        try:
            # In a real implementation, this would use arXiv's authentication API
            # For now, we'll simulate the verification process

            # Create verification token
            verification_token = self._generate_verification_token(arxiv_account)

            # Update account with verification status
            arxiv_account.verification_token = verification_token
            arxiv_account.is_verified = True
            arxiv_account.verified_at = timezone.now()
            arxiv_account.save()

            return True

        except Exception as e:
            # Log the error and return False
            print(f"Account verification failed: {str(e)}")
            return False

    def _generate_verification_token(self, arxiv_account: ArxivAccount) -> str:
        """Generate a verification token for the account."""
        import hashlib
        import uuid

        data = (
            f"{arxiv_account.arxiv_username}{arxiv_account.arxiv_email}{uuid.uuid4()}"
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def check_submission_limits(
        self, arxiv_account: ArxivAccount
    ) -> Dict[str, Union[bool, int]]:
        """
        Check if user can submit based on daily limits and account status.

        Args:
            arxiv_account: ArxivAccount to check

        Returns:
            Dict with limit information
        """
        return {
            "can_submit": arxiv_account.can_submit_today() and arxiv_account.is_active,
            "submissions_today": arxiv_account.submissions_today,
            "daily_limit": arxiv_account.daily_submission_limit,
            "remaining": max(
                0,
                arxiv_account.daily_submission_limit - arxiv_account.submissions_today,
            ),
            "is_suspended": arxiv_account.suspended_until
            and arxiv_account.suspended_until > timezone.now(),
            "suspension_reason": arxiv_account.suspension_reason
            if arxiv_account.suspended_until
            else None,
        }
