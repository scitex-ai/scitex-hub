"""
File read/write operations for Writer sections.

Handles reading and writing content to LaTeX sections.
"""

from pathlib import Path
from typing import Optional
from scitex import logging

logger = logging.getLogger(__name__)


class FileOperationsMixin:
    """Mixin for file I/O operations."""

    def read_section(self, section_name: str, doc_type: str = "manuscript") -> str:
        """Read a section from shared/manuscript/supplementary/revision.

        Args:
            section_name: Section name (e.g., 'introduction', 'abstract', 'title', 'authors')
            doc_type: 'shared', 'manuscript', 'supplementary', or 'revision'

        Returns:
            Section content as string
        """
        try:
            logger.info(
                f"[ReadSection] section_name={section_name}, doc_type={doc_type}"
            )

            # Special handling for compiled sections (not applicable to shared)
            if section_name == "compiled_pdf" or section_name == "compiled_tex":
                if doc_type == "shared":
                    logger.warning(
                        "[ReadSection] Compiled sections not available for 'shared' doc_type"
                    )
                    return ""
                logger.info(f"[ReadSection] Reading compiled tex for {doc_type}")
                content = self._read_compiled_tex(doc_type)
                logger.info(
                    f"[ReadSection] Compiled tex length: {len(content)}, first 100 chars: {content[:100]}"
                )
                return content

            # Get the appropriate document tree
            if doc_type == "shared":
                doc = self.writer.shared
                # For shared, sections are at the root level (no .contents)
                # shared has: title, authors, keywords, journal_name
                if not hasattr(doc, section_name):
                    logger.info(f"Section {section_name} not found in shared tree")
                    return ""
                section = getattr(doc, section_name)
            elif doc_type == "manuscript":
                doc = self.writer.manuscript
                if not hasattr(doc.contents, section_name):
                    logger.info(
                        f"Section {section_name} not found for {doc_type}: ManuscriptContents does not have attribute '{section_name}'"
                    )
                    return ""
                section = getattr(doc.contents, section_name)
            elif doc_type == "supplementary":
                doc = self.writer.supplementary
                if not hasattr(doc.contents, section_name):
                    logger.info(f"Section {section_name} not found for {doc_type}")
                    return ""
                section = getattr(doc.contents, section_name)
            elif doc_type == "revision":
                doc = self.writer.revision
                if not hasattr(doc.contents, section_name):
                    logger.info(f"Section {section_name} not found for {doc_type}")
                    return ""
                section = getattr(doc.contents, section_name)
            else:
                raise ValueError(f"Unknown document type: {doc_type}")

            content = section.read()

            # Convert to string if it's a list (from scitex.io.load)
            if isinstance(content, list):
                content = "\n".join(content)
            elif content is None:
                content = ""

            return content
        except Exception as e:
            logger.error(f"Error reading section {section_name}: {e}")
            raise

    def _read_compiled_tex(self, doc_type: str = "manuscript") -> str:
        """Read the compiled TeX file (merged document).

        Args:
            doc_type: 'manuscript', 'supplementary', or 'revision'

        Returns:
            Compiled TeX content or helpful message if not compiled yet
        """
        # Map document type to directory
        dir_map = {
            "manuscript": "01_manuscript",
            "supplementary": "02_supplementary",
            "revision": "03_revision",
        }

        if doc_type not in dir_map:
            raise ValueError(f"Unknown document type: {doc_type}")

        # Path to compiled tex file (e.g., manuscript.tex, supplementary.tex, revision.tex)
        compiled_tex_path = self.writer_dir / dir_map[doc_type] / f"{doc_type}.tex"

        # Check if file exists
        if not compiled_tex_path.exists():
            # Return helpful message
            doc_type_label = doc_type.capitalize()
            return f"""% Compiled {doc_type_label} TeX not yet generated
%
% This file will be created after compilation.
% Click the "Compile {doc_type_label} PDF" button to generate it.
%
% The compiled TeX file merges all sections into a single document
% that can be compiled to PDF.
"""

        # Read and return the compiled TeX
        try:
            with open(compiled_tex_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading compiled TeX: {e}")
            return f"% Error reading compiled TeX file: {str(e)}"

    def write_section(
        self, section_name: str, content: str, doc_type: str = "manuscript", auto_commit: bool = True
    ) -> bool:
        """Write content to a section.

        Args:
            section_name: Section name
            content: Section content
            doc_type: 'shared', 'manuscript', 'supplementary', or 'revision'
            auto_commit: Automatically commit changes after write (default: True)

        Returns:
            True if successful

        Raises:
            ValueError: If section doesn't exist or doc_type is invalid
            IOError: If file write fails
        """
        try:
            # Get the appropriate document tree
            if doc_type == "shared":
                doc = self.writer.shared
                # For shared, sections are at the root level (no .contents)
                if not hasattr(doc, section_name):
                    available_sections = [
                        attr
                        for attr in dir(doc)
                        if not attr.startswith("_")
                        and hasattr(getattr(doc, attr), "path")
                    ]
                    raise ValueError(
                        f"Section '{section_name}' not found in shared tree. "
                        f"Available sections: {', '.join(available_sections)}"
                    )
                section = getattr(doc, section_name)
            elif doc_type == "manuscript":
                doc = self.writer.manuscript
                if not hasattr(doc.contents, section_name):
                    available_sections = [
                        attr
                        for attr in dir(doc.contents)
                        if not attr.startswith("_")
                        and hasattr(getattr(doc.contents, attr), "path")
                    ]
                    raise ValueError(
                        f"Section '{section_name}' not found in manuscript.contents. "
                        f"Available sections: {', '.join(available_sections)}"
                    )
                section = getattr(doc.contents, section_name)
            elif doc_type == "supplementary":
                doc = self.writer.supplementary
                if not hasattr(doc.contents, section_name):
                    available_sections = [
                        attr
                        for attr in dir(doc.contents)
                        if not attr.startswith("_")
                        and hasattr(getattr(doc.contents, attr), "path")
                    ]
                    raise ValueError(
                        f"Section '{section_name}' not found in supplementary.contents. "
                        f"Available sections: {', '.join(available_sections)}"
                    )
                section = getattr(doc.contents, section_name)
            elif doc_type == "revision":
                doc = self.writer.revision
                if not hasattr(doc.contents, section_name):
                    available_sections = [
                        attr
                        for attr in dir(doc.contents)
                        if not attr.startswith("_")
                        and hasattr(getattr(doc.contents, attr), "path")
                    ]
                    raise ValueError(
                        f"Section '{section_name}' not found in revision.contents. "
                        f"Available sections: {', '.join(available_sections)}"
                    )
                section = getattr(doc.contents, section_name)
            else:
                raise ValueError(f"Unknown document type: {doc_type}")

            # Write content to section
            write_result = section.write(content)

            # Verify write succeeded
            if not write_result:
                expected_path = (
                    section.path
                    if hasattr(section, "path")
                    else f"{doc_type}/contents/{section_name}.tex"
                )
                raise IOError(
                    f"Failed to write to {section_name} (expected at: {expected_path})"
                )

            logger.info(
                f"Successfully wrote {len(content)} chars to {doc_type}/{section_name}"
            )

            # Auto-commit if requested
            if auto_commit:
                commit_message = f"Update {doc_type}/{section_name}"
                commit_sha = self.git_service.commit(
                    message=commit_message,
                    auto_stage=True
                )
                if commit_sha:
                    logger.info(
                        f"[WriterService] Auto-committed changes: {commit_sha[:8]} - {commit_message}"
                    )

            return True

        except Exception as e:
            logger.error(
                f"Error writing section {doc_type}/{section_name}: {e}", exc_info=True
            )
            raise

    def read_tex_file(self, file_path: str) -> str:
        """Read content of a .tex file from the writer workspace.

        Args:
            file_path: Relative path to the .tex file (e.g., "main.tex" or "chapters/intro.tex")

        Returns:
            Content of the file

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        full_path = self.writer_dir / file_path

        # Security check: ensure the path is within the project directory
        try:
            full_path.resolve().relative_to(self.writer_dir.resolve())
        except ValueError:
            raise PermissionError(f"Access denied: path outside project directory")

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not full_path.is_file():
            raise ValueError(f"Not a file: {file_path}")

        try:
            return full_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise
