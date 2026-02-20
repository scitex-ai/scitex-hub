"""
File Packaging for arXiv Submission

Delegates to scitex_writer.export._arxiv_packager.
"""

from pathlib import Path
from typing import List, Tuple

from scitex_writer.export import package_submission as _package_submission
from scitex_writer.export import validate_file_types as _validate_file_types

from ...models import ArxivSubmission


class ArxivFilePackager:
    """Package files for arXiv submission.

    Thin wrapper that extracts submission_id from Django model
    and delegates to scitex_writer.export functions.
    """

    def package_submission(self, submission: ArxivSubmission, work_dir: Path) -> Path:
        """Package all files for arXiv submission."""
        return _package_submission(work_dir, submission_id=submission.submission_id)

    def validate_file_types(self, work_dir: Path) -> Tuple[List[str], List[str]]:
        """Validate file types in submission."""
        return _validate_file_types(work_dir)
