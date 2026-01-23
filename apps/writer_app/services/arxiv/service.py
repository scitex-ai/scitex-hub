"""
arXiv Integration Main Service

Coordinates all arXiv-related services including account management,
category handling, validation, and submission workflow.
"""

from typing import Dict

from .account import ArxivAccountService
from .category import ArxivCategoryService
from .formatting import ArxivFormattingService
from .submission import ArxivSubmissionService
from .validation import ArxivValidationService


class ArxivAPIException(Exception):
    """Custom exception for arXiv API errors."""

    pass


class ArxivIntegrationService:
    """Main service class for arXiv integration coordination."""

    def __init__(self):
        self.account_service = ArxivAccountService()
        self.category_service = ArxivCategoryService()
        self.submission_service = ArxivSubmissionService()
        self.validation_service = ArxivValidationService()
        self.formatting_service = ArxivFormattingService()

    def initialize_arxiv_integration(self):
        """Initialize arXiv integration by populating categories."""
        return self.category_service.populate_categories()

    def get_user_submission_status(self, user) -> Dict:
        """Get comprehensive submission status for a user."""
        from ...models import ArxivAccount

        try:
            arxiv_account = user.arxiv_account
            submissions = user.arxiv_submissions.all()

            return {
                "account": {
                    "is_verified": arxiv_account.is_verified,
                    "username": arxiv_account.arxiv_username,
                    "email": arxiv_account.arxiv_email,
                },
                "limits": self.account_service.check_submission_limits(arxiv_account),
                "submissions": {
                    "total": submissions.count(),
                    "draft": submissions.filter(status="draft").count(),
                    "submitted": submissions.filter(status="submitted").count(),
                    "published": submissions.filter(status="published").count(),
                },
                "recent_submissions": submissions[:5],
            }
        except ArxivAccount.DoesNotExist:
            return {
                "account": None,
                "limits": None,
                "submissions": None,
                "recent_submissions": [],
            }
