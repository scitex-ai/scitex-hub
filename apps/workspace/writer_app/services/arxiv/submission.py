"""
arXiv Submission Service

Manages the complete submission workflow including creation, validation,
file preparation, submission to arXiv, status tracking, and version management.
"""

import shutil
from datetime import timedelta
from typing import Dict, Tuple

from django.core.files.base import ContentFile
from django.utils import timezone

from ...models import (
    ArxivAccount,
    ArxivSubmission,
    ArxivSubmissionHistory,
    ArxivValidationResult,
    Manuscript,
)
from .account import ArxivAccountService
from .formatting import ArxivFormattingService
from .validation import ArxivValidationService


class ArxivSubmissionException(Exception):
    """Exception raised during submission operations."""

    pass


class ArxivSubmissionService:
    """Service for managing arXiv submissions and status tracking."""

    def __init__(self):
        self.account_service = ArxivAccountService()
        self.validation_service = ArxivValidationService()
        self.formatting_service = ArxivFormattingService()

    def create_submission(
        self, manuscript: Manuscript, user, submission_data: Dict
    ) -> ArxivSubmission:
        """
        Create a new arXiv submission.

        Args:
            manuscript: Manuscript to submit
            user: User creating the submission
            submission_data: Submission metadata

        Returns:
            ArxivSubmission object
        """
        # Get or verify arXiv account
        try:
            arxiv_account = user.arxiv_account
            if not arxiv_account.is_verified:
                raise ArxivSubmissionException("arXiv account not verified")
        except ArxivAccount.DoesNotExist:
            raise ArxivSubmissionException("No arXiv account configured")

        # Check submission limits
        limits = self.account_service.check_submission_limits(arxiv_account)
        if not limits["can_submit"]:
            raise ArxivSubmissionException(
                "Daily submission limit exceeded or account suspended"
            )

        # Create submission
        submission = ArxivSubmission.objects.create(
            manuscript=manuscript,
            user=user,
            arxiv_account=arxiv_account,
            title=submission_data.get("title", manuscript.title),
            abstract=submission_data.get("abstract", manuscript.abstract),
            authors=submission_data.get("authors", ""),
            primary_category_id=submission_data["primary_category_id"],
            comments=submission_data.get("comments", ""),
            journal_reference=submission_data.get("journal_reference", ""),
            doi=submission_data.get("doi", ""),
        )

        # Add secondary categories
        if "secondary_categories" in submission_data:
            submission.secondary_categories.set(submission_data["secondary_categories"])

        # Create history entry
        ArxivSubmissionHistory.objects.create(
            submission=submission,
            new_status="draft",
            change_reason="Submission created",
            changed_by=user,
            is_automatic=False,
        )

        return submission

    def validate_submission(self, submission: ArxivSubmission) -> ArxivValidationResult:
        """Validate submission for arXiv requirements."""
        return self.validation_service.validate_submission(submission)

    def prepare_submission_files(self, submission: ArxivSubmission) -> Tuple[str, str]:
        """
        Prepare LaTeX and PDF files for submission.

        Args:
            submission: ArxivSubmission to prepare

        Returns:
            Tuple of (latex_file_path, pdf_file_path) in storage
        """
        # Format manuscript
        latex_file, pdf_file = self.formatting_service.format_manuscript_for_arxiv(
            submission.manuscript
        )

        # Save files to storage
        latex_name = f"arxiv_{submission.submission_id}_latex.tex"
        pdf_name = f"arxiv_{submission.submission_id}.pdf"

        with open(latex_file, "rb") as f:
            latex_content = ContentFile(f.read(), name=latex_name)
            submission.latex_source = latex_content

        with open(pdf_file, "rb") as f:
            pdf_content = ContentFile(f.read(), name=pdf_name)
            submission.pdf_file = pdf_content

        submission.save()

        # Clean up temporary files
        shutil.rmtree(latex_file.parent, ignore_errors=True)

        return submission.latex_source.path, submission.pdf_file.path

    def submit_to_arxiv(self, submission: ArxivSubmission) -> bool:
        """
        Submit to arXiv (simulated - would use real arXiv API).

        Args:
            submission: ArxivSubmission to submit

        Returns:
            bool: True if submission successful
        """
        try:
            # Update status
            submission.status = "submitted"
            submission.submitted_at = timezone.now()
            submission.save()

            # Increment daily submission count
            submission.arxiv_account.increment_daily_submissions()

            # Create history entry
            ArxivSubmissionHistory.objects.create(
                submission=submission,
                previous_status="draft",
                new_status="submitted",
                change_reason="Submitted to arXiv",
                arxiv_response={
                    "message": "Submission successful",
                    "timestamp": timezone.now().isoformat(),
                },
                is_automatic=True,
            )

            # In a real implementation, this would:
            # 1. Package files according to arXiv requirements
            # 2. Make API call to arXiv submission system
            # 3. Handle response and update submission status
            # 4. Store arXiv-assigned submission ID

            # Simulate successful submission
            submission.arxiv_id = f"2312.{str(submission.id).zfill(5)}"
            submission.arxiv_url = f"https://arxiv.org/abs/{submission.arxiv_id}"
            submission.save()

            return True

        except Exception as e:
            # Update status to indicate failure
            submission.status = "draft"
            submission.save()

            # Create error history entry
            ArxivSubmissionHistory.objects.create(
                submission=submission,
                previous_status="draft",
                new_status="draft",
                change_reason="Submission failed",
                error_details=str(e),
                is_automatic=True,
            )

            raise ArxivSubmissionException(f"Submission failed: {str(e)}")

    def check_submission_status(self, submission: ArxivSubmission) -> Dict:
        """
        Check submission status from arXiv (simulated).

        Args:
            submission: ArxivSubmission to check

        Returns:
            Dict with status information
        """
        if not submission.arxiv_id:
            return {
                "status": submission.status,
                "message": "Not yet submitted to arXiv",
            }

        # In a real implementation, this would query arXiv API
        # For now, simulate status progression

        # Simulate status progression based on time elapsed
        time_since_submission = (
            timezone.now() - submission.submitted_at
            if submission.submitted_at
            else timedelta(0)
        )

        if time_since_submission < timedelta(hours=1):
            new_status = "submitted"
        elif time_since_submission < timedelta(hours=24):
            new_status = "under_review"
        elif time_since_submission < timedelta(days=3):
            new_status = "approved"
        else:
            new_status = "published"
            if not submission.published_at:
                submission.published_at = timezone.now()

        # Update status if changed
        if new_status != submission.status:
            old_status = submission.status
            submission.status = new_status
            submission.last_status_check = timezone.now()
            submission.save()

            # Create history entry
            ArxivSubmissionHistory.objects.create(
                submission=submission,
                previous_status=old_status,
                new_status=new_status,
                change_reason="Status updated from arXiv",
                arxiv_response={
                    "status": new_status,
                    "timestamp": timezone.now().isoformat(),
                },
                is_automatic=True,
            )

        return {
            "status": submission.status,
            "arxiv_id": submission.arxiv_id,
            "arxiv_url": submission.arxiv_url,
            "message": submission.get_status_display_with_details(),
            "last_checked": submission.last_status_check,
        }

    def withdraw_submission(self, submission: ArxivSubmission, reason: str) -> bool:
        """
        Withdraw a submission from arXiv.

        Args:
            submission: ArxivSubmission to withdraw
            reason: Reason for withdrawal

        Returns:
            bool: True if withdrawal successful
        """
        if not submission.can_be_withdrawn():
            raise ArxivSubmissionException(
                "Submission cannot be withdrawn in current status"
            )

        try:
            # Update status
            old_status = submission.status
            submission.status = "withdrawn"
            submission.save()

            # Create history entry
            ArxivSubmissionHistory.objects.create(
                submission=submission,
                previous_status=old_status,
                new_status="withdrawn",
                change_reason=f"Withdrawn by user: {reason}",
                changed_by=submission.user,
                is_automatic=False,
            )

            return True

        except Exception as e:
            raise ArxivSubmissionException(f"Withdrawal failed: {str(e)}")

    def replace_submission(
        self,
        original_submission: ArxivSubmission,
        new_manuscript: Manuscript,
        replacement_data: Dict,
    ) -> ArxivSubmission:
        """
        Create a replacement submission for an existing arXiv paper.

        Args:
            original_submission: Original ArxivSubmission to replace
            new_manuscript: New manuscript for replacement
            replacement_data: Replacement metadata

        Returns:
            New ArxivSubmission object
        """
        if not original_submission.can_be_replaced():
            raise ArxivSubmissionException("Original submission cannot be replaced")

        # Create replacement submission
        replacement = ArxivSubmission.objects.create(
            manuscript=new_manuscript,
            user=original_submission.user,
            arxiv_account=original_submission.arxiv_account,
            submission_type="replacement",
            replaces_submission=original_submission,
            title=replacement_data.get("title", new_manuscript.title),
            abstract=replacement_data.get("abstract", new_manuscript.abstract),
            authors=replacement_data.get("authors", original_submission.authors),
            primary_category=original_submission.primary_category,
            comments=replacement_data.get("comments", ""),
            journal_reference=replacement_data.get("journal_reference", ""),
            doi=replacement_data.get("doi", ""),
            version=original_submission.version + 1,
        )

        # Copy secondary categories
        replacement.secondary_categories.set(
            original_submission.secondary_categories.all()
        )

        # Create history entry
        ArxivSubmissionHistory.objects.create(
            submission=replacement,
            new_status="draft",
            change_reason=f"Replacement created for {original_submission.arxiv_id}",
            changed_by=original_submission.user,
            is_automatic=False,
        )

        return replacement
