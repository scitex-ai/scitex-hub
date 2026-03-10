"""
Compliance Checking for arXiv Submission

Provides validator to check manuscript compliance
with arXiv submission requirements.
"""

import re
from typing import Dict

from ...models import Manuscript


class ArxivComplianceChecker:
    """Check manuscript compliance with arXiv requirements."""

    def __init__(self):
        self.required_sections = ["title", "abstract", "introduction"]
        self.max_title_length = 256
        self.max_abstract_length = 1920
        self.min_abstract_length = 100

    def check_compliance(
        self, manuscript: Manuscript, latex_content: str
    ) -> Dict[str, any]:
        """
        Check manuscript compliance with arXiv requirements.

        Args:
            manuscript: Manuscript to check
            latex_content: LaTeX content

        Returns:
            Dictionary with compliance results
        """
        compliance_results = {
            "is_compliant": True,
            "errors": [],
            "warnings": [],
            "checks": {},
        }

        # Check title
        title_check = self._check_title(manuscript.title)
        compliance_results["checks"]["title"] = title_check
        if not title_check["passed"]:
            compliance_results["errors"].extend(title_check["errors"])
            compliance_results["is_compliant"] = False

        # Check abstract
        abstract_check = self._check_abstract(manuscript.abstract)
        compliance_results["checks"]["abstract"] = abstract_check
        if not abstract_check["passed"]:
            compliance_results["errors"].extend(abstract_check["errors"])
            compliance_results["is_compliant"] = False

        # Check LaTeX structure
        latex_check = self._check_latex_structure(latex_content)
        compliance_results["checks"]["latex"] = latex_check
        if not latex_check["passed"]:
            compliance_results["errors"].extend(latex_check["errors"])
            compliance_results["is_compliant"] = False

        # Check categories
        category_check = self._check_categories(manuscript)
        compliance_results["checks"]["categories"] = category_check
        if not category_check["passed"]:
            compliance_results["errors"].extend(category_check["errors"])
            compliance_results["is_compliant"] = False

        return compliance_results

    def _check_title(self, title: str) -> Dict:
        """Check title compliance."""
        errors = []
        warnings = []

        if not title or not title.strip():
            errors.append("Title is required")
        elif len(title) > self.max_title_length:
            errors.append(
                f"Title exceeds maximum length of {self.max_title_length} characters"
            )

        if title and len(title) < 10:
            warnings.append("Title is very short")

        return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _check_abstract(self, abstract: str) -> Dict:
        """Check abstract compliance."""
        errors = []
        warnings = []

        if not abstract or not abstract.strip():
            errors.append("Abstract is required")
        else:
            if len(abstract) > self.max_abstract_length:
                errors.append(
                    f"Abstract exceeds maximum length of {self.max_abstract_length} characters"
                )
            elif len(abstract) < self.min_abstract_length:
                warnings.append(
                    f"Abstract is shorter than recommended minimum of {self.min_abstract_length} characters"
                )

        return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _check_latex_structure(self, latex_content: str) -> Dict:
        """Check LaTeX structure compliance."""
        errors = []
        warnings = []

        # Check for document class
        if not re.search(r"\\documentclass", latex_content):
            errors.append("Missing \\documentclass declaration")

        # Check for document environment
        if not re.search(r"\\begin\{document\}", latex_content):
            errors.append("Missing \\begin{document}")
        if not re.search(r"\\end\{document\}", latex_content):
            errors.append("Missing \\end{document}")

        # Check for title and author
        if not re.search(r"\\title\{", latex_content):
            warnings.append("Missing \\title command")
        if not re.search(r"\\author\{", latex_content):
            warnings.append("Missing \\author command")

        return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _check_categories(self, manuscript: Manuscript) -> Dict:
        """Check category requirements."""
        errors = []
        warnings = []

        # This would check if the manuscript has arXiv submissions with categories
        # For now, just return a basic check
        if (
            not hasattr(manuscript, "arxiv_submissions")
            or not manuscript.arxiv_submissions.exists()
        ):
            warnings.append("No arXiv category selected")

        return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings}
