"""
Output file handling for Writer.

Manages PDF output and watch mode operations.
"""

from pathlib import Path
from typing import Optional
from scitex import logging

logger = logging.getLogger(__name__)


class OutputMixin:
    """Mixin for output operations."""

    def get_pdf(self, doc_type: str = "manuscript") -> Optional[str]:
        """Get path to compiled PDF.

        Args:
            doc_type: 'manuscript', 'supplementary', or 'revision'

        Returns:
            Path to PDF if exists, None otherwise
        """
        try:
            pdf_path = self.writer.get_pdf(doc_type=doc_type)
            return str(pdf_path) if pdf_path else None
        except Exception as e:
            logger.error(f"Error getting PDF: {e}")
            return None

    def watch(self, on_compile=None):
        """Start watching for changes and auto-compile.

        Args:
            on_compile: Optional callback function on successful compilation
        """
        try:
            self.writer.watch(on_compile=on_compile)
        except Exception as e:
            logger.error(f"Error starting watch mode: {e}")
            raise
