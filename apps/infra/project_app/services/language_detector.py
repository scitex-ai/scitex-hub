"""
Language detection for projects based on file extensions and content.

Maps file extensions to programming languages and provides utilities
to auto-detect the primary language of a project.
"""

from pathlib import Path
from typing import Optional, List
from collections import defaultdict

# Language color mapping from GitHub/GitLab
LANGUAGE_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Java": "#b07219",
    "C": "#555555",
    "C++": "#f34b7d",
    "C#": "#239120",
    "Go": "#00ADD8",
    "Rust": "#CE422B",
    "Ruby": "#CC342D",
    "PHP": "#777BB4",
    "Swift": "#FA7343",
    "Kotlin": "#7F52FF",
    "R": "#198CE7",
    "MATLAB": "#0E7490",
    "Julia": "#9558B2",
    "Scala": "#DC322F",
    "Haskell": "#5E5086",
    "Clojure": "#DB5855",
    "Perl": "#0298C3",
    "Shell": "#89E051",
    "HTML": "#E34C26",
    "CSS": "#563D7C",
    "SCSS": "#c6538c",
    "Markdown": "#083fa1",
    "LaTeX": "#3D6117",
    "BibTeX": "#2D5F3F",
    "JSON": "#292929",
    "YAML": "#CB171E",
    "XML": "#0D8C55",
    "SQL": "#336791",
    "Other": "#858585",
}

# File extension to language mapping
FILE_EXTENSION_MAP = {
    # Python
    ".py": "Python",
    ".pyw": "Python",
    # JavaScript/TypeScript
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    # Java
    ".java": "Java",
    ".class": "Java",
    # C/C++
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    # C#
    ".cs": "C#",
    # Go
    ".go": "Go",
    # Rust
    ".rs": "Rust",
    # Ruby
    ".rb": "Ruby",
    ".erb": "Ruby",
    # PHP
    ".php": "PHP",
    # Swift
    ".swift": "Swift",
    # Kotlin
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    # R
    ".r": "R",
    ".R": "R",
    # MATLAB
    ".m": "MATLAB",
    # Julia
    ".jl": "Julia",
    # Scala
    ".scala": "Scala",
    # Haskell
    ".hs": "Haskell",
    # Clojure
    ".clj": "Clojure",
    ".cljs": "Clojure",
    # Perl
    ".pl": "Perl",
    # Shell
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    # Markup
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "SCSS",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".tex": "LaTeX",
    ".latex": "LaTeX",
    ".bib": "BibTeX",
    # Data/Config
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".sql": "SQL",
}

# Files to ignore when detecting language
IGNORE_PATTERNS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".env",
    ".idea",
    ".vscode",
    "dist",
    "build",
    ".DS_Store",
    "scitex",
    "docs",
    "data",
    "results",
    "temp",
}


def detect_language_from_files(
    project_path: Path, max_files: int = 1000
) -> Optional[str]:
    """
    Detect the primary programming language of a project by analyzing file extensions.

    Args:
        project_path: Path to the project root directory
        max_files: Maximum number of files to scan (for performance)

    Returns:
        The detected primary language, or None if no source files found
    """
    if not project_path.exists() or not project_path.is_dir():
        return None

    language_count = defaultdict(int)
    file_count = 0

    try:
        for path in project_path.rglob("*"):
            if file_count >= max_files:
                break

            # Skip ignored directories
            if any(ignored in path.parts for ignored in IGNORE_PATTERNS):
                continue

            if path.is_file():
                file_count += 1
                ext = path.suffix.lower()

                if ext in FILE_EXTENSION_MAP:
                    language = FILE_EXTENSION_MAP[ext]
                    language_count[language] += 1

    except (PermissionError, OSError):
        return None

    # Return the language with the most files
    if language_count:
        primary_language = max(language_count, key=language_count.get)
        return primary_language

    return None


def get_language_color(language: Optional[str]) -> str:
    """Get the color hex code for a language."""
    if language is None:
        language = "Other"
    return LANGUAGE_COLORS.get(language, LANGUAGE_COLORS["Other"])


def get_all_languages() -> List[tuple]:
    """Get all supported languages as tuples for Django choices."""
    return sorted(set(LANGUAGE_COLORS.keys()), key=lambda x: (x == "Other", x))
