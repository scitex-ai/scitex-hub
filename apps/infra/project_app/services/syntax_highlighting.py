#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Syntax Highlighting Language Detection Service

Provides centralized language detection for syntax highlighting in code viewers.
Uses Pygments library to detect languages based on file extensions and names.
Maps Pygments lexer aliases to highlight.js language identifiers.

This service should be used by:
- File viewers for syntax highlighting
- Code blocks for language detection
- Design galleries for testing
"""

from typing import Optional
import logging

from pygments.lexers import guess_lexer_for_filename
from pygments.util import ClassNotFound

logger = logging.getLogger(__name__)

# Mapping of Pygments lexer aliases to highlight.js language identifiers
# Used when Pygments doesn't directly match highlight.js naming conventions
PYGMENTS_TO_HIGHLIGHTJS = {
    "text": "plaintext",
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "csharp": "csharp",
    "go": "go",
    "rust": "rust",
    "ruby": "ruby",
    "php": "php",
    "swift": "swift",
    "kotlin": "kotlin",
    "r": "r",
    "matlab": "matlab",
    "julia": "julia",
    "scala": "scala",
    "haskell": "haskell",
    "clojure": "clojure",
    "perl": "perl",
    "bash": "bash",
    "shell": "bash",
    "sh": "bash",
    "html": "html",
    "css": "css",
    "scss": "scss",
    "sass": "scss",
    "markdown": "markdown",
    "latex": "latex",
    "bibtex": "bibtex",
    "json": "json",
    "yaml": "yaml",
    "xml": "xml",
    "sql": "sql",
    "toml": "toml",
    "ini": "ini",
    "dockerfile": "dockerfile",
    "makefile": "makefile",
}

# Special case: filename-based detection for files without extensions
FILENAME_TO_LANGUAGE = {
    "dockerfile": "dockerfile",
    "makefile": "makefile",
    "rakefile": "makefile",
    "gemfile": "ruby",
}


def detect_language(file_ext: str, file_name: str = "") -> Optional[str]:
    """
    Detect the highlight.js language identifier using Pygments.

    Args:
        file_ext: File extension (e.g., '.py', '.js')
        file_name: Full filename (used for extension-less files like Dockerfile)

    Returns:
        Language identifier for highlight.js, or 'plaintext' if unknown

    Examples:
        >>> detect_language('.py')
        'python'
        >>> detect_language('.bib')
        'bibtex'
        >>> detect_language('', 'Dockerfile')
        'dockerfile'
    """
    try:
        # Try filename-based detection first (for files without extensions)
        if file_name:
            file_name_lower = file_name.lower()
            if file_name_lower in FILENAME_TO_LANGUAGE:
                return FILENAME_TO_LANGUAGE[file_name_lower]

        # Try Pygments guess_lexer_for_filename if we have a filename
        if file_name:
            try:
                lexer = guess_lexer_for_filename(file_name, "")
                lexer_name = lexer.name.lower()

                # Map Pygments lexer aliases to highlight.js identifiers
                for alias in lexer.aliases:
                    if alias in PYGMENTS_TO_HIGHLIGHTJS:
                        return PYGMENTS_TO_HIGHLIGHTJS[alias]

                # Fallback: use first alias
                if lexer.aliases:
                    return PYGMENTS_TO_HIGHLIGHTJS.get(lexer.aliases[0], "plaintext")
            except ClassNotFound:
                pass

        # Try extension-based detection
        if file_ext:
            file_ext_lower = file_ext.lower()
            # Ensure extension starts with dot
            if not file_ext_lower.startswith("."):
                file_ext_lower = "." + file_ext_lower

            try:
                # Create dummy filename with the extension to use Pygments
                dummy_filename = f"file{file_ext_lower}"
                lexer = guess_lexer_for_filename(dummy_filename, "")

                # Map Pygments lexer aliases to highlight.js identifiers
                for alias in lexer.aliases:
                    if alias in PYGMENTS_TO_HIGHLIGHTJS:
                        return PYGMENTS_TO_HIGHLIGHTJS[alias]

                # Fallback: use first alias
                if lexer.aliases:
                    return PYGMENTS_TO_HIGHLIGHTJS.get(lexer.aliases[0], "plaintext")
            except ClassNotFound:
                pass

    except Exception as e:
        logger.debug(f"Error detecting language for {file_name}{file_ext}: {e}")

    # Default to plaintext if no match found
    return "plaintext"


def get_all_supported_languages() -> dict:
    """
    Get all supported highlight.js languages and their metadata.

    Returns:
        Dictionary mapping language identifiers to their info
    """
    from pygments.lexers import get_all_lexers

    languages = {}

    # Populate from Pygments lexers
    for name, aliases, filetypes, mimetypes in get_all_lexers():
        for alias in aliases:
            if alias in PYGMENTS_TO_HIGHLIGHTJS:
                lang_id = PYGMENTS_TO_HIGHLIGHTJS[alias]
                if lang_id not in languages:
                    languages[lang_id] = {
                        "identifier": lang_id,
                        "name": name,
                        "aliases": aliases,
                        "filetypes": list(filetypes),
                        "mimetypes": list(mimetypes),
                        "custom": False,
                    }

    return languages


def get_language_info(language: str) -> Optional[dict]:
    """
    Get information about a specific language.

    Args:
        language: Language identifier (highlight.js format)

    Returns:
        Language info dictionary, or None if not found
    """
    languages = get_all_supported_languages()
    return languages.get(language)


def is_supported_language(language: str) -> bool:
    """Check if a language is supported by highlight.js."""
    return language in PYGMENTS_TO_HIGHLIGHTJS.values()


def is_custom_language(language: str) -> bool:
    """Check if a language has special handling."""
    return language in ["bibtex"]  # Add custom languages here if needed
