#!/usr/bin/env python3
"""Jupyter notebook conversion utilities."""
import logging

import nbformat
from nbconvert import HTMLExporter, PythonExporter, MarkdownExporter

from ..models import Notebook

logger = logging.getLogger(__name__)


class NotebookConverter:
    """Converts notebooks to different formats."""

    @staticmethod
    def to_html(notebook: Notebook) -> str:
        """Convert notebook to HTML."""
        try:
            nb = nbformat.from_dict(notebook.content)
            html_exporter = HTMLExporter()
            html_content, _ = html_exporter.from_notebook_node(nb)
            return html_content
        except Exception as e:
            logger.error(f"Error converting notebook to HTML: {e}")
            return f"<p>Error converting notebook: {e}</p>"

    @staticmethod
    def to_python(notebook: Notebook) -> str:
        """Convert notebook to Python script."""
        try:
            nb = nbformat.from_dict(notebook.content)
            python_exporter = PythonExporter()
            python_content, _ = python_exporter.from_notebook_node(nb)
            return python_content
        except Exception as e:
            logger.error(f"Error converting notebook to Python: {e}")
            return f"# Error converting notebook: {e}"

    @staticmethod
    def to_markdown(notebook: Notebook) -> str:
        """Convert notebook to Markdown."""
        try:
            nb = nbformat.from_dict(notebook.content)
            md_exporter = MarkdownExporter()
            md_content, _ = md_exporter.from_notebook_node(nb)
            return md_content
        except Exception as e:
            logger.error(f"Error converting notebook to Markdown: {e}")
            return f"Error converting notebook: {e}"


# EOF
