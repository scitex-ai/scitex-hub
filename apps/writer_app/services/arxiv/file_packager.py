"""
File Packaging for arXiv Submission

Provides functionality to package manuscript files into
arXiv-compatible zip archives with validation.
"""

import zipfile
from pathlib import Path
from typing import List, Tuple

from ...models import ArxivSubmission


class ArxivFilePackager:
    """Package files for arXiv submission."""

    def __init__(self):
        self.max_file_size = 50 * 1024 * 1024  # 50MB limit
        self.allowed_extensions = {
            ".tex",
            ".bib",
            ".bbl",
            ".cls",
            ".sty",
            ".eps",
            ".ps",
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
        }

    def package_submission(self, submission: ArxivSubmission, work_dir: Path) -> Path:
        """
        Package all files for arXiv submission.

        Args:
            submission: ArxivSubmission to package
            work_dir: Working directory containing files

        Returns:
            Path to created submission package (zip file)
        """
        package_path = work_dir / f"arxiv_submission_{submission.submission_id}.zip"

        with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Add main LaTeX file
            if (work_dir / "main.tex").exists():
                zipf.write(work_dir / "main.tex", "main.tex")

            # Add bibliography
            if (work_dir / "references.bib").exists():
                zipf.write(work_dir / "references.bib", "references.bib")

            # Add figures
            figures_dir = work_dir / "figures"
            if figures_dir.exists():
                for figure_file in figures_dir.iterdir():
                    if (
                        figure_file.is_file()
                        and figure_file.suffix.lower() in self.allowed_extensions
                    ):
                        zipf.write(figure_file, f"figures/{figure_file.name}")

            # Add any additional files
            for file_path in work_dir.iterdir():
                if (
                    file_path.is_file()
                    and file_path.suffix.lower() in self.allowed_extensions
                    and file_path.name not in ["main.tex", "references.bib"]
                ):
                    zipf.write(file_path, file_path.name)

        # Check file size
        if package_path.stat().st_size > self.max_file_size:
            raise ValueError(
                f"Submission package exceeds {self.max_file_size / (1024 * 1024):.1f}MB limit"
            )

        return package_path

    def validate_file_types(self, work_dir: Path) -> Tuple[List[str], List[str]]:
        """
        Validate file types in submission.

        Args:
            work_dir: Directory to validate

        Returns:
            Tuple of (valid_files, invalid_files)
        """
        valid_files = []
        invalid_files = []

        for file_path in work_dir.rglob("*"):
            if file_path.is_file():
                if file_path.suffix.lower() in self.allowed_extensions:
                    valid_files.append(str(file_path.relative_to(work_dir)))
                else:
                    invalid_files.append(str(file_path.relative_to(work_dir)))

        return valid_files, invalid_files
