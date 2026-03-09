"""
LaTeX Content Formatters for arXiv Submission

Provides formatters for manuscript metadata such as authors,
keywords, figures, and tables.
"""

from ...models import Manuscript


class ArxivContentFormatter:
    """Format manuscript content elements for LaTeX."""

    def format_authors(self, manuscript: Manuscript) -> str:
        """Format author list for LaTeX."""
        authors = []

        # Primary author
        primary_author = manuscript.owner
        authors.append(primary_author.get_full_name() or primary_author.username)

        # Collaborators
        for collaborator in manuscript.collaborators.all():
            authors.append(collaborator.get_full_name() or collaborator.username)

        return " \\and ".join(authors)

    def format_keywords(self, manuscript: Manuscript) -> str:
        """Format keywords section."""
        if manuscript.keywords:
            return f"\\textbf{{Keywords:}} {manuscript.keywords}"
        return "% Keywords: Add relevant keywords here"

    def format_figures(self, manuscript: Manuscript) -> str:
        """Format figures for LaTeX."""
        if not manuscript.figures.exists():
            return "% No figures"

        figures_latex = []
        for figure in manuscript.figures.all():
            figure_latex = f"""\\begin{{figure}}[{figure.position}]
\\centering
\\includegraphics[width={figure.width}\\textwidth]{{figures/{figure.file.name.split("/")[-1]}}}
\\caption{{{figure.caption}}}
\\label{{fig:{figure.label}}}
\\end{{figure}}"""
            figures_latex.append(figure_latex)

        return "\n\n".join(figures_latex)

    def format_tables(self, manuscript: Manuscript) -> str:
        """Format tables for LaTeX."""
        if not manuscript.tables.exists():
            return "% No tables"

        tables_latex = []
        for table in manuscript.tables.all():
            table_latex = f"""\\begin{{table}}[{table.position}]
\\centering
\\caption{{{table.caption}}}
\\label{{tab:{table.label}}}
{table.content}
\\end{{table}}"""
            tables_latex.append(table_latex)

        return "\n\n".join(tables_latex)
