"""
Compliance Checking for arXiv Submission

Delegates core logic to scitex_writer.export._arxiv_compliance.
"""

from typing import Dict

from scitex_writer.export import check_compliance as _check_compliance

from ...models import Manuscript


class ArxivComplianceChecker:
    """Check manuscript compliance with arXiv requirements.

    Thin wrapper that reads Django model fields and delegates
    to scitex_writer.export.check_compliance().
    """

    def check_compliance(
        self, manuscript: Manuscript, latex_content: str
    ) -> Dict[str, any]:
        """Check manuscript compliance with arXiv requirements."""
        result = _check_compliance(manuscript.title, manuscript.abstract, latex_content)

        # Django-specific: check categories via ORM
        category_check = self._check_categories(manuscript)
        result["checks"]["categories"] = category_check
        if not category_check["passed"]:
            result["errors"].extend(category_check["errors"])
            result["is_compliant"] = False

        return result

    def _check_categories(self, manuscript: Manuscript) -> Dict:
        """Check category requirements (Django-specific)."""
        errors = []
        warnings = []

        if (
            not hasattr(manuscript, "arxiv_submissions")
            or not manuscript.arxiv_submissions.exists()
        ):
            warnings.append("No arXiv category selected")

        return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings}
