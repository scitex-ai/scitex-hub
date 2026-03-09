"""
LaTeX Content Formatting for arXiv Submission

Provides specialized formatter for converting SciTeX manuscripts
to arXiv-compatible LaTeX formats.
"""

import re
from pathlib import Path
from typing import Dict

from ...models import Manuscript
from .latex_cleaner import ArxivLatexCleaner
from .latex_content_formatter import ArxivContentFormatter


class ArxivLatexFormatter:
    """Format LaTeX content for arXiv submission compliance."""

    def __init__(self):
        self.cleaner = ArxivLatexCleaner()
        self.content_formatter = ArxivContentFormatter()
        self.arxiv_class_options = {
            "article": r"\documentclass[12pt]{article}",
            "revtex": r"\documentclass[12pt,prd,aps]{revtex4-2}",  # For physics papers
            "neurips": r"\documentclass[final]{neurips_2023}",  # For ML papers
        }

    def format_for_arxiv(
        self, manuscript: Manuscript, document_class: str = "article"
    ) -> str:
        """
        Format manuscript LaTeX for arXiv submission.

        Args:
            manuscript: Manuscript to format
            document_class: LaTeX document class to use

        Returns:
            Formatted LaTeX content
        """
        if manuscript.is_modular:
            return self._format_modular_manuscript(manuscript, document_class)
        else:
            return self._format_standard_manuscript(manuscript, document_class)

    def _format_modular_manuscript(
        self, manuscript: Manuscript, document_class: str
    ) -> str:
        """Format modular manuscript structure for arXiv."""
        # Get paper path
        paper_path = manuscript.get_project_paper_path()
        if not paper_path:
            raise ValueError("Cannot access modular manuscript files")

        # Read main.tex and sections
        main_tex_path = paper_path / "manuscript" / "main.tex"
        if main_tex_path.exists():
            with open(main_tex_path, "r", encoding="utf-8") as f:
                main_content = f.read()
        else:
            main_content = self._generate_default_main_tex(manuscript, document_class)

        # Process and combine sections
        sections_content = self._compile_sections(paper_path / "manuscript" / "src")

        # Replace \\input commands with actual content
        latex_content = self._replace_input_commands(main_content, sections_content)

        # Clean and validate LaTeX
        return self._clean_latex_for_arxiv(latex_content)

    def _format_standard_manuscript(
        self, manuscript: Manuscript, document_class: str
    ) -> str:
        """Format standard (non-modular) manuscript for arXiv."""
        # Generate complete LaTeX document
        latex_content = self._generate_complete_latex(manuscript, document_class)

        # Clean and validate LaTeX
        return self._clean_latex_for_arxiv(latex_content)

    def _generate_default_main_tex(
        self, manuscript: Manuscript, document_class: str
    ) -> str:
        """Generate default main.tex structure."""
        template = self.arxiv_class_options.get(
            document_class, self.arxiv_class_options["article"]
        )

        return f"""{template}

% Essential packages for arXiv
\\usepackage[utf8]{{inputenc}}
\\usepackage[english]{{babel}}
\\usepackage{{amsmath}}
\\usepackage{{amsfonts}}
\\usepackage{{amssymb}}
\\usepackage{{graphicx}}
\\usepackage{{cite}}
\\usepackage{{url}}
\\usepackage[margin=1in]{{geometry}}

% Manuscript metadata
\\title{{{manuscript.title}}}
\\author{{{self._format_authors(manuscript)}}}
\\date{{\\today}}

\\begin{{document}}

\\maketitle

\\begin{{abstract}}
{manuscript.abstract or "Abstract content."}
\\end{{abstract}}

% Keywords
{self._format_keywords(manuscript)}

% Main content sections
\\input{{src/introduction}}
\\input{{src/methods}}
\\input{{src/results}}
\\input{{src/discussion}}
\\input{{src/conclusion}}

% Bibliography
\\bibliographystyle{{plain}}
\\bibliography{{references}}

\\end{{document}}
"""

    def _compile_sections(self, src_path: Path) -> Dict[str, str]:
        """Compile content from individual section files."""
        sections = {}

        section_files = [
            "abstract.tex",
            "introduction.tex",
            "methods.tex",
            "results.tex",
            "discussion.tex",
            "conclusion.tex",
        ]

        for section_file in section_files:
            file_path = src_path / section_file
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        sections[section_file] = self._clean_section_content(content)
                except Exception as e:
                    sections[section_file] = f"% Error reading {section_file}: {str(e)}"
            else:
                sections[section_file] = f"% Section {section_file} not found"

        return sections

    def _replace_input_commands(
        self, main_content: str, sections: Dict[str, str]
    ) -> str:
        """Replace \\input commands with actual section content."""
        # Pattern to match \\input{src/filename} or \\input{filename}
        input_pattern = r"\\input\{(?:src/)?([^}]+)\}"

        def replace_input(match):
            filename = match.group(1)
            if not filename.endswith(".tex"):
                filename += ".tex"

            return sections.get(filename, f"% Content for {filename} not found")

        return re.sub(input_pattern, replace_input, main_content)

    def _generate_complete_latex(
        self, manuscript: Manuscript, document_class: str
    ) -> str:
        """Generate complete LaTeX document from manuscript data."""
        template = self.arxiv_class_options.get(
            document_class, self.arxiv_class_options["article"]
        )

        # Build complete document
        latex_parts = [
            template,
            "",
            "% Essential packages for arXiv",
            "\\usepackage[utf8]{inputenc}",
            "\\usepackage[english]{babel}",
            "\\usepackage{amsmath}",
            "\\usepackage{amsfonts}",
            "\\usepackage{amssymb}",
            "\\usepackage{graphicx}",
            "\\usepackage{cite}",
            "\\usepackage{url}",
            "\\usepackage[margin=1in]{geometry}",
            "",
            "% Manuscript metadata",
            f"\\title{{{manuscript.title}}}",
            f"\\author{{{self._format_authors(manuscript)}}}",
            "\\date{\\today}",
            "",
            "\\begin{document}",
            "",
            "\\maketitle",
            "",
            "\\begin{abstract}",
            manuscript.abstract or "Abstract content.",
            "\\end{abstract}",
            "",
            self._format_keywords(manuscript),
            "",
            manuscript.content or "% Main content here",
            "",
            self._format_figures(manuscript),
            "",
            self._format_tables(manuscript),
            "",
            "% Bibliography",
            "\\bibliographystyle{plain}",
            "\\bibliography{references}",
            "",
            "\\end{document}",
        ]

        return "\n".join(latex_parts)

    def _clean_latex_for_arxiv(self, latex_content: str) -> str:
        """Clean LaTeX content for arXiv compliance."""
        return self.cleaner.clean_latex_for_arxiv(latex_content)

    def _clean_section_content(self, content: str) -> str:
        """Clean individual section content."""
        return self.cleaner.clean_section_content(content)

    def _format_authors(self, manuscript: Manuscript) -> str:
        """Format author list for LaTeX."""
        return self.content_formatter.format_authors(manuscript)

    def _format_keywords(self, manuscript: Manuscript) -> str:
        """Format keywords section."""
        return self.content_formatter.format_keywords(manuscript)

    def _format_figures(self, manuscript: Manuscript) -> str:
        """Format figures for LaTeX."""
        return self.content_formatter.format_figures(manuscript)

    def _format_tables(self, manuscript: Manuscript) -> str:
        """Format tables for LaTeX."""
        return self.content_formatter.format_tables(manuscript)
