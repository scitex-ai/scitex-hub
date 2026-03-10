"""
File read/write operations for Writer sections.

Thin Django wrapper delegating to scitex.writer.Writer for core logic.
"""

from scitex import logging

logger = logging.getLogger(__name__)


class FileOperationsMixin:
    """Mixin for file I/O operations. Delegates to Writer."""

    def read_section(self, section_name: str, doc_type: str = "manuscript") -> str:
        """Read a section's content.

        Delegates to Writer.read_section() for core logic.
        Handles compiled sections as a special case (app-level concern).

        Args:
            section_name: Section name (e.g., 'abstract', 'title')
            doc_type: 'shared', 'manuscript', 'supplementary', or 'revision'

        Returns:
            Section content as string
        """
        if section_name in ("compiled_pdf", "compiled_tex"):
            if doc_type == "shared":
                return ""
            return self._read_compiled_tex(doc_type)

        return self.writer.read_section(section_name, doc_type)

    def write_section(
        self,
        section_name: str,
        content: str,
        doc_type: str = "manuscript",
        auto_commit: bool = True,
    ) -> bool:
        """Write content to a section.

        Delegates to Writer.write_section() for core logic.
        Handles auto-commit as app-level concern.

        Args:
            section_name: Section name
            content: Section content
            doc_type: 'shared', 'manuscript', 'supplementary', or 'revision'
            auto_commit: Automatically commit changes after write

        Returns:
            True if successful
        """
        result = self.writer.write_section(section_name, content, doc_type)

        if not result:
            raise IOError(f"Failed to write to {doc_type}/{section_name}")

        logger.info(
            f"Successfully wrote {len(content)} chars to {doc_type}/{section_name}"
        )

        if auto_commit:
            commit_message = f"Update {doc_type}/{section_name}"
            commit_sha = self.git_service.commit(
                message=commit_message, auto_stage=True
            )
            if commit_sha:
                logger.info(
                    f"[WriterService] Auto-committed: {commit_sha[:8]} - {commit_message}"
                )

        return True

    def _read_compiled_tex(self, doc_type: str = "manuscript") -> str:
        """Read the compiled TeX file (merged document).

        App-level concern: returns helpful message if not yet compiled.

        Args:
            doc_type: 'manuscript', 'supplementary', or 'revision'

        Returns:
            Compiled TeX content or helpful message
        """
        dir_map = {
            "manuscript": "01_manuscript",
            "supplementary": "02_supplementary",
            "revision": "03_revision",
        }

        if doc_type not in dir_map:
            raise ValueError(f"Unknown document type: {doc_type}")

        compiled_tex_path = self.writer_dir / dir_map[doc_type] / f"{doc_type}.tex"

        if not compiled_tex_path.exists():
            doc_type_label = doc_type.capitalize()
            return (
                f"% Compiled {doc_type_label} TeX not yet generated\n"
                f"%\n"
                f'% Click the "Compile {doc_type_label} PDF" button to generate it.\n'
            )

        try:
            return compiled_tex_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Error reading compiled TeX: {e}")
            return f"% Error reading compiled TeX file: {e}"

    def read_tex_file(self, file_path: str) -> str:
        """Read a .tex file from the writer workspace.

        App-level concern: path security validation.

        Args:
            file_path: Relative path within writer workspace

        Returns:
            File content as string
        """
        full_path = self.writer_dir / file_path

        try:
            full_path.resolve().relative_to(self.writer_dir.resolve())
        except ValueError:
            raise PermissionError("Access denied: path outside project directory")

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not full_path.is_file():
            raise ValueError(f"Not a file: {file_path}")

        return full_path.read_text(encoding="utf-8")
