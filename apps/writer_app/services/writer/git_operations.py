"""
Git version control operations for Writer sections.

Handles history, diff, checkout, and commit operations.
"""

from scitex import logging

logger = logging.getLogger(__name__)


class GitOperationsMixin:
    """Mixin for git version control operations."""

    def commit_section(
        self, section_name: str, message: str, doc_type: str = "manuscript"
    ) -> bool:
        """Commit changes to a section.

        Args:
            section_name: Section name
            message: Commit message
            doc_type: 'shared', 'manuscript', 'supplementary', or 'revision'

        Returns:
            True if successful
        """
        try:
            # Get the appropriate document tree
            if doc_type == "shared":
                doc = self.writer.shared
                if not hasattr(doc, section_name):
                    logger.warning(
                        f"Cannot commit non-existent section {section_name} in shared tree"
                    )
                    return False
                section = getattr(doc, section_name)
            elif doc_type == "manuscript":
                doc = self.writer.manuscript
                if not hasattr(doc.contents, section_name):
                    logger.warning(
                        f"Cannot commit non-existent section {section_name} for {doc_type}"
                    )
                    return False
                section = getattr(doc.contents, section_name)
            elif doc_type == "supplementary":
                doc = self.writer.supplementary
                if not hasattr(doc.contents, section_name):
                    logger.warning(
                        f"Cannot commit non-existent section {section_name} for {doc_type}"
                    )
                    return False
                section = getattr(doc.contents, section_name)
            elif doc_type == "revision":
                doc = self.writer.revision
                if not hasattr(doc.contents, section_name):
                    logger.warning(
                        f"Cannot commit non-existent section {section_name} for {doc_type}"
                    )
                    return False
                section = getattr(doc.contents, section_name)
            else:
                raise ValueError(f"Unknown document type: {doc_type}")

            logger.info(f"Committing section {section_name} with message: {message}")

            # Check if section has commit method
            if not hasattr(section, "commit"):
                logger.error(f"Section {section_name} does not have commit method")
                raise AttributeError(
                    f"Section {section_name} does not support git commits"
                )

            result = section.commit(message)
            logger.info(f"Commit result for {section_name}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error committing section {section_name}: {e}", exc_info=True)
            raise

    def get_section_history(
        self, section_name: str, doc_type: str = "manuscript"
    ) -> list:
        """Get git history for a section.

        Args:
            section_name: Section name
            doc_type: 'shared', 'manuscript', 'supplementary', or 'revision'

        Returns:
            List of commit messages
        """
        try:
            # Get the appropriate document tree
            if doc_type == "shared":
                doc = self.writer.shared
                if not hasattr(doc, section_name):
                    logger.warning(
                        f"Cannot get history for non-existent section {section_name} in shared tree"
                    )
                    return []
                section = getattr(doc, section_name)
            elif doc_type == "manuscript":
                doc = self.writer.manuscript
                if not hasattr(doc.contents, section_name):
                    logger.warning(
                        f"Cannot get history for non-existent section {section_name}"
                    )
                    return []
                section = getattr(doc.contents, section_name)
            elif doc_type == "supplementary":
                doc = self.writer.supplementary
                if not hasattr(doc.contents, section_name):
                    logger.warning(
                        f"Cannot get history for non-existent section {section_name}"
                    )
                    return []
                section = getattr(doc.contents, section_name)
            elif doc_type == "revision":
                doc = self.writer.revision
                if not hasattr(doc.contents, section_name):
                    logger.warning(
                        f"Cannot get history for non-existent section {section_name}"
                    )
                    return []
                section = getattr(doc.contents, section_name)
            else:
                raise ValueError(f"Unknown document type: {doc_type}")

            return section.history()
        except Exception as e:
            logger.error(f"Error getting history for {section_name}: {e}")
            return []

    def get_section_diff(
        self, section_name: str, ref: str = "HEAD", doc_type: str = "manuscript"
    ) -> str:
        """Get uncommitted changes for a section.

        Args:
            section_name: Section name
            ref: Git reference (default: HEAD)
            doc_type: 'shared', 'manuscript', 'supplementary', or 'revision'

        Returns:
            Diff string (empty if no changes)
        """
        try:
            # Get the appropriate document tree
            if doc_type == "shared":
                doc = self.writer.shared
                if not hasattr(doc, section_name):
                    logger.warning(
                        f"Cannot get diff for non-existent section {section_name} in shared tree"
                    )
                    return ""
                section = getattr(doc, section_name)
            elif doc_type == "manuscript":
                doc = self.writer.manuscript
                if not hasattr(doc.contents, section_name):
                    logger.warning(
                        f"Cannot get diff for non-existent section {section_name}"
                    )
                    return ""
                section = getattr(doc.contents, section_name)
            elif doc_type == "supplementary":
                doc = self.writer.supplementary
                if not hasattr(doc.contents, section_name):
                    logger.warning(
                        f"Cannot get diff for non-existent section {section_name}"
                    )
                    return ""
                section = getattr(doc.contents, section_name)
            elif doc_type == "revision":
                doc = self.writer.revision
                if not hasattr(doc.contents, section_name):
                    logger.warning(
                        f"Cannot get diff for non-existent section {section_name}"
                    )
                    return ""
                section = getattr(doc.contents, section_name)
            else:
                raise ValueError(f"Unknown document type: {doc_type}")

            return section.diff(ref=ref)
        except Exception as e:
            logger.error(f"Error getting diff for {section_name}: {e}")
            return ""

    def checkout_section(
        self, section_name: str, ref: str = "HEAD", doc_type: str = "manuscript"
    ) -> bool:
        """Restore a section from git history.

        Args:
            section_name: Section name
            ref: Git reference (commit hash, branch, tag, etc.)
            doc_type: 'shared', 'manuscript', 'supplementary', or 'revision'

        Returns:
            True if successful
        """
        try:
            # Get the appropriate document tree
            if doc_type == "shared":
                doc = self.writer.shared
                if not hasattr(doc, section_name):
                    logger.warning(
                        f"Cannot checkout non-existent section {section_name} in shared tree"
                    )
                    return False
                section = getattr(doc, section_name)
            elif doc_type == "manuscript":
                doc = self.writer.manuscript
                if not hasattr(doc.contents, section_name):
                    logger.warning(
                        f"Cannot checkout non-existent section {section_name}"
                    )
                    return False
                section = getattr(doc.contents, section_name)
            elif doc_type == "supplementary":
                doc = self.writer.supplementary
                if not hasattr(doc.contents, section_name):
                    logger.warning(
                        f"Cannot checkout non-existent section {section_name}"
                    )
                    return False
                section = getattr(doc.contents, section_name)
            elif doc_type == "revision":
                doc = self.writer.revision
                if not hasattr(doc.contents, section_name):
                    logger.warning(
                        f"Cannot checkout non-existent section {section_name}"
                    )
                    return False
                section = getattr(doc.contents, section_name)
            else:
                raise ValueError(f"Unknown document type: {doc_type}")

            return section.checkout(ref)
        except Exception as e:
            logger.error(f"Error checking out {section_name}: {e}")
            raise
