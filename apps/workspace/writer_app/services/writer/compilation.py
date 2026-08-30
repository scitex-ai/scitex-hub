"""
LaTeX compilation operations for Writer.

Thin wrapper delegating to scitex.writer.compile for all compilation.
Django imports from scitex_writer._compile for compilation functions.
"""

import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from scitex import logging

# The failure-to-reason translation lives in ``compile_error`` so the
# FULL-compile view (views/editor/api/compilation_full_job.py) can apply
# the SAME precedence without importing scitex at module scope.
# Re-exported here because callers and tests already import these names
# from this module.
from .compile_error import (
    _TEX_EPILOGUE,
    _TEX_ERROR_PREFIX,
    _ensure_error_and_log,
    _first_tex_error,
)

__all__ = [
    "_TEX_EPILOGUE",
    "_TEX_ERROR_PREFIX",
    "_ensure_error_and_log",
    "_first_tex_error",
    "CompilationMixin",
]

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Lazy import helper
_sw_compile = None


def _get_sw_compile():
    global _sw_compile
    if _sw_compile is None:
        from scitex.writer import compile as _compile

        _sw_compile = _compile
    return _sw_compile


def _coerce_compile_result_to_dict(result: Any) -> dict:
    """Normalise a ``scitex.writer.compile.content()`` return value to a dict.

    scitex-writer >= 2.17.5 (G1, schema unification) returns a
    ``CompilationResult`` dataclass. Older releases returned a raw ``dict``.
    The downstream Django view (``compile_api``) and the UI's TypeScript
    ``CompilationResult`` interface both consume the response as JSON, so we
    flatten the dataclass with ``dataclasses.asdict`` and coerce any
    ``Path`` fields (``output_pdf`` / ``diff_pdf`` / ``log_file`` /
    ``temp_dir``) to strings so ``django.http.JsonResponse`` can serialise
    the result without a custom encoder.

    Passing through a plain dict (pre-2.17.5 shape) is a no-op so this
    helper is safe to call unconditionally.
    """
    if dataclasses.is_dataclass(result) and not isinstance(result, type):
        raw = dataclasses.asdict(result)
    elif isinstance(result, dict):
        raw = dict(result)
    else:  # pragma: no cover — defensive: scitex.writer.compile.content
        # always returns one of the two shapes above.
        return {
            "success": False,
            "error": f"unexpected result shape: {type(result).__name__}",
        }

    for key in ("output_pdf", "diff_pdf", "log_file", "temp_dir"):
        value = raw.get(key)
        if isinstance(value, Path):
            raw[key] = str(value)
    return raw


class CompilationMixin:
    """Mixin for compilation-related operations.

    Delegates to scitex.writer.compile (single source of truth).
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

        Delegates to scitex.writer.compile.content(). The upstream return
        type changed from a raw dict to a ``CompilationResult`` dataclass
        in scitex-writer 2.17.5 (G1); we normalise both back to a dict so
        ``compile_api`` and the UI keep their existing JSON contract.
        """
        try:
            # Sanitize section_name: strip .tex extension if present
            if section_name.endswith(".tex"):
                section_name = section_name[:-4]

            # Delegate to scitex.writer (single source of truth)
            sw_compile = _get_sw_compile()
            result = sw_compile.content(
                latex_content=latex_content,
                project_dir=str(self.writer_dir),
                color_mode=color_mode,
                name=f"preview-{section_name}-{color_mode}",
                timeout=timeout,
                keep_aux=False,
            )
            return _ensure_error_and_log(_coerce_compile_result_to_dict(result))
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
            from scitex_writer._compile import compile_manuscript

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
            from scitex_writer._compile import compile_supplementary

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
            from scitex_writer._compile import compile_revision

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
