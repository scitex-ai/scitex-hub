"""
Template handling for Writer sections.

Provides access to original template content for sections.
"""

from typing import Optional
from scitex import logging

logger = logging.getLogger(__name__)


class TemplatesMixin:
    """Mixin for template operations."""

    def get_template_content(
        self, section_name: str, doc_type: str = "manuscript"
    ) -> Optional[str]:
        """Get original template content for a section.

        This retrieves the clean template content from scitex.writer.Writer,
        which can be used to reset a section to its original state.

        Args:
            section_name: Section name (e.g., 'introduction', 'abstract', 'title', 'authors')
            doc_type: 'shared', 'manuscript', 'supplementary', or 'revision'

        Returns:
            Template content string, or None if template not found
        """
        try:
            # Get the appropriate document tree
            if doc_type == "shared":
                doc = self.writer.shared
                section = getattr(doc, section_name, None)
            elif doc_type == "manuscript":
                doc = self.writer.manuscript
                section = getattr(doc.contents, section_name, None)
            elif doc_type == "supplementary":
                doc = self.writer.supplementary
                section = getattr(doc.contents, section_name, None)
            elif doc_type == "revision":
                doc = self.writer.revision
                section = getattr(doc.contents, section_name, None)
            else:
                raise ValueError(f"Unknown document type: {doc_type}")

            if section is None:
                logger.warning(f"Section '{section_name}' not found in {doc_type}")
                return None

            # Get template content from the section's template
            # The Writer class should have a method or property to access template content
            if hasattr(section, "template"):
                return section.template
            elif hasattr(section, "get_template"):
                return section.get_template()
            else:
                # Fallback: return empty string with comment
                logger.warning(f"No template method found for section '{section_name}'")
                return f"% Template for {section_name}\n\n"

        except Exception as e:
            logger.error(
                f"Error getting template content for {section_name}: {e}", exc_info=True
            )
            return None
