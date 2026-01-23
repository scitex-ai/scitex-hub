"""
LaTeX compilation operations for Writer.

Handles preview compilation, manuscript/supplementary/revision compilation.
"""

from pathlib import Path
from typing import Optional, Callable
from scitex import logging

logger = logging.getLogger(__name__)


class CompilationMixin:
    """Mixin for compilation-related operations."""

    def _apply_color_mode_to_latex(self, latex_content: str, color_mode: str) -> str:
        """Apply color mode to LaTeX content by injecting color commands.

        Args:
            latex_content: Original LaTeX content
            color_mode: 'light', 'dark', 'sepia', or 'paper'

        Returns:
            Modified LaTeX content with color commands
        """
        # Skip color injection for light mode (default LaTeX colors)
        if color_mode == "light":
            return latex_content

        # Define dark mode colors - Eye-friendly warm dark background with soft text
        # Following modern dark mode best practices (Material Design, GitHub, VS Code)
        # Background: #1c2128 (rgb 0.11, 0.129, 0.157) - darker warm gray with slight blue tint
        # Text: #c9d1d9 (rgb 0.788, 0.82, 0.851) - soft off-white with warm tone
        # These colors reduce eye strain and prevent "halation" effect of pure white on pure black
        # The darker background is more comfortable while avoiding pure black
        # Must be after \documentclass but before \begin{document}
        color_commands = """\\usepackage{xcolor}
\\pagecolor[rgb]{0.11,0.129,0.157}
\\color[rgb]{0.788,0.82,0.851}
"""

        # Find the position to inject
        if "\\begin{document}" in latex_content:
            # Insert right before \begin{document}
            latex_content = latex_content.replace(
                "\\begin{document}", f"{color_commands}\\begin{{document}}", 1
            )
        else:
            # Just prepend if no \begin{document} found
            latex_content = color_commands + latex_content

        return latex_content

    def compile_preview(
        self,
        latex_content: str,
        timeout: int = 60,
        color_mode: str = "light",
        section_name: str = "preview",
        doc_type: str = "manuscript",
    ) -> dict:
        """Compile a quick preview of provided LaTeX content (not from workspace).

        This is used for live preview of the current section being edited.

        Args:
            latex_content: Complete LaTeX document content to compile
            timeout: Compilation timeout in seconds (default: 60 for quick preview)
            color_mode: PDF color mode - 'light', 'dark', 'sepia', or 'paper'
            section_name: Section name for output filename (e.g., 'introduction')
            doc_type: Document type - 'manuscript', 'supplementary', or 'revision'

        Returns:
            Compilation result dict with keys:
                - success: bool
                - output_pdf: str (path if successful)
                - log: str (compilation log)
                - error: str (error message if failed)
        """
        # Import at method start to avoid UnboundLocalError in except clauses
        import subprocess
        import shutil

        try:
            # Apply color mode to LaTeX content
            latex_content = self._apply_color_mode_to_latex(latex_content, color_mode)

            # Create .preview directory in scitex/writer for compiled previews
            # This directory stores temporary compiled PDFs for quick preview
            # Structure: scitex/writer/.preview/
            preview_dir = self.writer_dir / ".preview"
            preview_dir.mkdir(parents=True, exist_ok=True)

            # Ensure bibliography is accessible for citations
            # Link bibliography from 00_shared/bib_files to preview directory
            bib_source = (
                self.writer_dir / "00_shared" / "bib_files" / "bibliography.bib"
            )
            bib_link = preview_dir / "bibliography.bib"
            if bib_source.exists() and not bib_link.exists():
                try:
                    bib_link.symlink_to(bib_source)
                    logger.info(
                        f"[CompilePreview] Created bibliography symlink for citations"
                    )
                except Exception as e:
                    logger.warning(
                        f"[CompilePreview] Could not create bibliography symlink: {e}"
                    )

            # Write content to temporary .tex file in .preview directory
            # Include theme in temp filename to avoid conflicts with parallel compilations
            temp_tex = preview_dir / f"preview-{section_name}-{color_mode}-temp.tex"
            logger.info(
                f"[CompilePreview] Creating preview file: {temp_tex} for section: {section_name}, theme: {color_mode}"
            )
            temp_tex.write_text(latex_content, encoding="utf-8")

            logger.info(
                f"[CompilePreview] Compiling {color_mode} preview with latexmk ({len(latex_content)} chars) timeout={timeout}s"
            )

            # Use latexmk for intelligent multi-pass compilation (handles citations automatically)
            # This matches the behavior of full manuscript compilation
            result = subprocess.run(
                [
                    "latexmk",
                    "-pdf",  # Generate PDF output
                    "-interaction=nonstopmode",  # Don't stop on errors
                    f"-output-directory={preview_dir}",  # Output to preview directory
                    "-silent",  # Reduce verbosity
                    str(temp_tex),
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(preview_dir),  # Run from preview directory for relative paths
            )

            log_content = result.stdout + result.stderr

            # Expected PDF output: .preview/preview-{section_name}-{color_mode}-temp.pdf
            temp_pdf = preview_dir / f"preview-{section_name}-{color_mode}-temp.pdf"
            # Final PDF name: .preview/preview-{section_name}-{color_mode}.pdf
            output_pdf = preview_dir / f"preview-{section_name}-{color_mode}.pdf"

            # latexmk creates preview-{section_name}-{color_mode}-temp.pdf from preview-{section_name}-{color_mode}-temp.tex
            logger.info(f"[CompilePreview] Looking for compiled PDF: {temp_pdf}")

            # Check if compilation succeeded by looking for the PDF file
            # Note: latexmk return code may be non-zero even on successful compilation
            # with -interaction=nonstopmode, so we check for the PDF file instead
            if temp_pdf.exists():
                logger.info(
                    f"[CompilePreview] {color_mode} PDF compiled successfully with citations at {temp_pdf}"
                )

                # Clean up auxiliary files to keep preview directory tidy
                # Keep: .pdf, .tex, bibliography.bib (symlink)
                # Remove: .aux, .log, .fls, .fdb_latexmk, .bbl, .blg, .out, .toc
                aux_extensions = [
                    ".aux",
                    ".log",
                    ".fls",
                    ".fdb_latexmk",
                    ".bbl",
                    ".blg",
                    ".out",
                    ".toc",
                    ".nav",
                    ".snm",
                ]
                base_name = temp_tex.stem
                for ext in aux_extensions:
                    aux_file = preview_dir / f"{base_name}{ext}"
                    if aux_file.exists():
                        try:
                            aux_file.unlink()
                        except Exception as e:
                            logger.debug(
                                f"[CompilePreview] Could not remove auxiliary file {aux_file.name}: {e}"
                            )

                # Rename from temp filename to final filename
                if temp_pdf != output_pdf:
                    shutil.move(str(temp_pdf), str(output_pdf))

                logger.info(
                    f"WriterService: Preview compilation succeeded for {section_name} ({color_mode}): {output_pdf}"
                )

                return {
                    "success": True,
                    "output_pdf": str(output_pdf),
                    "log": log_content,
                    "error": None,
                }
            else:
                logger.error(
                    f"WriterService: Preview compilation failed - PDF not found at {temp_pdf}"
                )
                logger.error(f"latexmk return code: {result.returncode}")
                logger.error(f"latexmk output:\n{log_content}")
                return {
                    "success": False,
                    "output_pdf": None,
                    "log": log_content,
                    "error": f"PDF compilation failed - no output PDF generated",
                }

        except subprocess.TimeoutExpired:
            logger.error(f"WriterService: Preview compilation timeout after {timeout}s")
            return {
                "success": False,
                "output_pdf": None,
                "log": f"Compilation timeout after {timeout} seconds",
                "error": f"Compilation timeout",
            }
        except Exception as e:
            logger.error(
                f"WriterService: Preview compilation error: {e}", exc_info=True
            )
            return {
                "success": False,
                "output_pdf": None,
                "log": str(e),
                "error": str(e),
            }

    def compile_manuscript(
        self,
        timeout: int = 300,
        log_callback: Optional[Callable] = None,
        progress_callback: Optional[Callable] = None,
        no_figs: bool = False,
        ppt2tif: bool = False,
        crop_tif: bool = False,
        quiet: bool = False,
        verbose: bool = False,
        force: bool = False,
        **kwargs,  # Catch any unexpected arguments
    ) -> dict:
        """Compile manuscript with optional callbacks for live updates.

        Args:
            timeout: Compilation timeout in seconds
            log_callback: Optional callback for real-time log streaming
            progress_callback: Optional callback for progress updates
            no_figs: Exclude figures for quick compilation
            ppt2tif: Convert PowerPoint to TIF on WSL
            crop_tif: Crop TIF images to remove excess whitespace
            quiet: Suppress detailed logs for LaTeX compilation
            verbose: Show detailed logs for LaTeX compilation
            force: Force full recompilation, ignore cache

        Returns:
            Compilation result dict with keys:
                - success: bool
                - output_pdf: str (path if successful)
                - log: str (compilation log)
                - error: str (error message if failed)
        """
        try:
            # Use standalone compile function from scitex.writer._compile
            from scitex.writer._compile import compile_manuscript

            result = compile_manuscript(
                project_dir=self.writer_dir,
                timeout=timeout,
                no_figs=no_figs,
                ppt2tif=ppt2tif,
                crop_tif=crop_tif,
                quiet=quiet,
                verbose=verbose,
                force=force,
                log_callback=log_callback,
                progress_callback=progress_callback,
            )
            # Build log from stdout/stderr
            log_content = ""
            if hasattr(result, "stdout") and result.stdout:
                log_content += result.stdout
            if hasattr(result, "stderr") and result.stderr:
                if log_content:
                    log_content += "\n"
                log_content += result.stderr

            return {
                "success": result.success,
                "output_pdf": str(result.output_pdf) if result.output_pdf else None,
                "log": log_content,
                "error": None,  # No error if compilation completed
            }
        except Exception as e:
            logger.error(f"Compilation error: {e}", exc_info=True)
            return {
                "success": False,
                "output_pdf": None,
                "log": str(e),
                "error": str(e),
            }

    def compile_supplementary(
        self,
        timeout: int = 300,
        log_callback: Optional[Callable] = None,
        progress_callback: Optional[Callable] = None,
        no_figs: bool = False,
        ppt2tif: bool = False,
        crop_tif: bool = False,
        quiet: bool = False,
        **kwargs,  # Catch any unexpected arguments
    ) -> dict:
        """Compile supplementary material.

        Args:
            timeout: Compilation timeout in seconds
            log_callback: Optional callback for real-time log streaming
            progress_callback: Optional callback for progress updates
            no_figs: Exclude figures (default includes figures)
            ppt2tif: Convert PowerPoint to TIF on WSL
            crop_tif: Crop TIF images to remove excess whitespace
            quiet: Suppress detailed logs for LaTeX compilation
        """
        try:
            # Use standalone compile function from scitex.writer._compile
            from scitex.writer._compile import compile_supplementary

            result = compile_supplementary(
                project_dir=self.writer_dir,
                timeout=timeout,
                no_figs=no_figs,
                ppt2tif=ppt2tif,
                crop_tif=crop_tif,
                quiet=quiet,
                log_callback=log_callback,
                progress_callback=progress_callback,
            )
            # Build log from stdout/stderr
            log_content = ""
            if hasattr(result, "stdout") and result.stdout:
                log_content += result.stdout
            if hasattr(result, "stderr") and result.stderr:
                if log_content:
                    log_content += "\n"
                log_content += result.stderr

            return {
                "success": result.success,
                "output_pdf": str(result.output_pdf) if result.output_pdf else None,
                "log": log_content,
                "error": None,  # No error if compilation completed
            }
        except Exception as e:
            logger.error(f"Supplementary compilation error: {e}", exc_info=True)
            return {
                "success": False,
                "output_pdf": None,
                "log": str(e),
                "error": str(e),
            }

    def compile_revision(
        self,
        timeout: int = 300,
        log_callback: Optional[Callable] = None,
        progress_callback: Optional[Callable] = None,
        track_changes: bool = False,
        **kwargs,  # Catch any unexpected arguments
    ) -> dict:
        """Compile revision response document.

        Args:
            timeout: Compilation timeout in seconds
            log_callback: Optional callback for real-time log streaming
            progress_callback: Optional callback for progress updates
            track_changes: Whether to enable change tracking (diff highlighting)
        """
        try:
            # Use standalone compile function from scitex.writer._compile
            from scitex.writer._compile import compile_revision

            result = compile_revision(
                project_dir=self.writer_dir,
                timeout=timeout,
                track_changes=track_changes,
                log_callback=log_callback,
                progress_callback=progress_callback,
            )
            # Build log from stdout/stderr
            log_content = ""
            if hasattr(result, "stdout") and result.stdout:
                log_content += result.stdout
            if hasattr(result, "stderr") and result.stderr:
                if log_content:
                    log_content += "\n"
                log_content += result.stderr

            return {
                "success": result.success,
                "output_pdf": str(result.output_pdf) if result.output_pdf else None,
                "log": log_content,
                "error": None,  # No error if compilation completed
            }
        except Exception as e:
            logger.error(f"Revision compilation error: {e}", exc_info=True)
            return {
                "success": False,
                "output_pdf": None,
                "log": str(e),
                "error": str(e),
            }
