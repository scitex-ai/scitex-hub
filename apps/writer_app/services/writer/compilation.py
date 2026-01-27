"""
LaTeX compilation operations for Writer.

Thin wrapper delegating to scitex_writer.compile for all compilation.
"""

from typing import Callable, Optional

from scitex_writer import compile as sw_compile

from scitex import logging

logger = logging.getLogger(__name__)


class CompilationMixin:
    """Mixin for compilation-related operations.

    Delegates to scitex_writer.compile (single source of truth).
    """

    def compile_preview(
        self,
        latex_content: str,
        timeout: int = 60,
        color_mode: str = "light",
        section_name: str = "preview",
        doc_type: str = "manuscript",
    ) -> dict:
        """Compile a quick preview of provided LaTeX content.

        Delegates to scitex_writer.compile.content().
        """
        try:
            # Delegate to scitex_writer (single source of truth)
            result = sw_compile.content(
                latex_content=latex_content,
                project_dir=str(self.writer_dir),
                color_mode=color_mode,
                name=f"preview-{section_name}-{color_mode}",
                timeout=timeout,
                keep_aux=False,
            )
            return result
        except Exception as e:
            logger.error(f"Preview compilation error: {e}", exc_info=True)
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
