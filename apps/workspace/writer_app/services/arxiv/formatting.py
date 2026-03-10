"""
arXiv Formatting Service

Handles manuscript formatting for arXiv submission including LaTeX generation,
asset management, bibliography preparation, and PDF compilation.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from django.utils import timezone

from ...models import Manuscript


class ArxivFormattingException(Exception):
    """Exception raised during formatting operations."""

    pass


class ArxivFormattingService:
    """Service for formatting manuscripts for arXiv submission."""

    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "arxiv_formatting"
        self.temp_dir.mkdir(exist_ok=True)

    def format_manuscript_for_arxiv(self, manuscript: Manuscript) -> Tuple[Path, Path]:
        """
        Format manuscript for arXiv submission.

        Args:
            manuscript: Manuscript to format

        Returns:
            Tuple of (latex_file_path, pdf_file_path)
        """
        # Create temporary working directory
        work_dir = (
            self.temp_dir
            / f"manuscript_{manuscript.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        )
        work_dir.mkdir(exist_ok=True)

        try:
            # Generate arXiv-compatible LaTeX
            latex_content = self._generate_arxiv_latex(manuscript)
            latex_file = work_dir / "main.tex"

            with open(latex_file, "w", encoding="utf-8") as f:
                f.write(latex_content)

            # Copy figures and other assets
            self._copy_manuscript_assets(manuscript, work_dir)

            # Generate bibliography if needed
            bib_file = self._generate_bibliography(manuscript, work_dir)

            # Compile to PDF
            pdf_file = self._compile_latex_to_pdf(latex_file, work_dir)

            return latex_file, pdf_file

        except Exception as e:
            # Clean up on error
            shutil.rmtree(work_dir, ignore_errors=True)
            raise ArxivFormattingException(f"Failed to format manuscript: {str(e)}")

    def _generate_arxiv_latex(self, manuscript: Manuscript) -> str:
        """Generate arXiv-compatible LaTeX content."""
        # Basic arXiv template
        latex_template = r"""\documentclass[12pt]{{article}}

% arXiv recommended packages
\usepackage[utf8]{{inputenc}}
\usepackage[english]{{babel}}
\usepackage{{amsmath}}
\usepackage{{amsfonts}}
\usepackage{{amssymb}}
\usepackage{{graphicx}}
\usepackage{{cite}}
\usepackage{{url}}
\usepackage[margin=1in]{{geometry}}

% Metadata
\title{{{title}}}
\author{{{authors}}}
\date{{\today}}

\begin{{document}}

\maketitle

\begin{{abstract}}
{abstract}
\end{{abstract}}

% Keywords
\textbf{{Keywords:}} {keywords}

{content}

% Bibliography
\bibliographystyle{{plain}}
\bibliography{{references}}

\end{{document}}
"""

        # Prepare content
        if manuscript.is_modular:
            content = self._compile_modular_content(manuscript)
        else:
            content = manuscript.content

        # Format authors
        authors = self._format_authors(manuscript)

        # Generate LaTeX
        return latex_template.format(
            title=manuscript.title,
            authors=authors,
            abstract=manuscript.abstract or "Abstract content here.",
            keywords=manuscript.keywords or "keyword1, keyword2, keyword3",
            content=content,
        )

    def _compile_modular_content(self, manuscript: Manuscript) -> str:
        """Compile content from modular manuscript sections."""
        content = ""

        # Get paper path
        paper_path = manuscript.get_project_paper_path()
        if not paper_path:
            return "% Content could not be loaded"

        # Section files mapping
        section_files = [
            ("manuscript/src/introduction.tex", "Introduction"),
            ("manuscript/src/methods.tex", "Methods"),
            ("manuscript/src/results.tex", "Results"),
            ("manuscript/src/discussion.tex", "Discussion"),
            ("manuscript/src/conclusion.tex", "Conclusion"),
        ]

        for file_path, section_name in section_files:
            full_path = paper_path / file_path
            if full_path.exists():
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        section_content = f.read()
                        # Remove section commands if they exist
                        if not section_content.strip().startswith("\\section"):
                            content += f"\\section{{{section_name}}}\n"
                        content += section_content + "\n\n"
                except Exception:
                    content += f"% Error loading {section_name} section\n\n"

        return content

    def _format_authors(self, manuscript: Manuscript) -> str:
        """Format author list for arXiv."""
        authors = [manuscript.owner.get_full_name() or manuscript.owner.username]

        if manuscript.collaborators.exists():
            collaborator_names = [
                c.get_full_name() or c.username for c in manuscript.collaborators.all()
            ]
            authors.extend(collaborator_names)

        return " \\and ".join(authors)

    def _copy_manuscript_assets(self, manuscript: Manuscript, work_dir: Path):
        """Copy figures and other assets to working directory."""
        if not manuscript.is_modular:
            return

        paper_path = manuscript.get_project_paper_path()
        if not paper_path:
            return

        # Copy figures
        figures_src = paper_path / "manuscript" / "src" / "figures"
        if figures_src.exists():
            figures_dst = work_dir / "figures"
            figures_dst.mkdir(exist_ok=True)

            for figure_file in figures_src.glob("*"):
                if figure_file.is_file():
                    shutil.copy2(figure_file, figures_dst)

    def _generate_bibliography(
        self, manuscript: Manuscript, work_dir: Path
    ) -> Optional[Path]:
        """Generate bibliography file from manuscript citations."""
        bib_file = work_dir / "references.bib"

        # Get citations from manuscript
        citations = manuscript.citations.all()
        if not citations:
            # Try to copy from modular structure
            if manuscript.is_modular:
                paper_path = manuscript.get_project_paper_path()
                if paper_path:
                    ref_file = paper_path / "references" / "references.bib"
                    if ref_file.exists():
                        shutil.copy2(ref_file, bib_file)
                        return bib_file
            return None

        # Generate BibTeX content
        bib_content = "% Bibliography for arXiv submission\n\n"
        for citation in citations:
            bib_content += citation.bibtex_entry + "\n\n"

        with open(bib_file, "w", encoding="utf-8") as f:
            f.write(bib_content)

        return bib_file

    def _compile_latex_to_pdf(self, latex_file: Path, work_dir: Path) -> Path:
        """Compile LaTeX to PDF."""
        import subprocess

        pdf_file = work_dir / "main.pdf"

        try:
            # Change to working directory
            original_cwd = os.getcwd()
            os.chdir(work_dir)

            # Run pdflatex
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", latex_file.name],
                check=True,
                capture_output=True,
            )

            # Run bibtex if bibliography exists
            if (work_dir / "references.bib").exists():
                subprocess.run(
                    ["bibtex", latex_file.stem],
                    check=False,  # Don't fail if no citations
                    capture_output=True,
                )

                # Run pdflatex twice more for references
                subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", latex_file.name],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", latex_file.name],
                    check=True,
                    capture_output=True,
                )

            return pdf_file

        except subprocess.CalledProcessError as e:
            raise ArxivFormattingException(f"LaTeX compilation failed: {e}")
        except FileNotFoundError:
            raise ArxivFormattingException("pdflatex not found. Please install LaTeX.")
        finally:
            os.chdir(original_cwd)
