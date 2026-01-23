"""
SciTeX Cloud - Project Scanner

Project directory scanning and structured views.
No database dependencies - pure filesystem scanning.
"""

from pathlib import Path
from typing import List, Dict

from .file_handler import NativeFileHandler
from .file_operations import read_file_content


class ProjectFileScanner:
    """
    Scan project directories and provide structured views.
    No database dependencies - pure filesystem scanning.
    """

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.handler = NativeFileHandler()

    def scan_structure(self, max_depth: int = 3) -> Dict:
        """
        Scan project and return structured tree.

        Args:
            max_depth: Maximum depth to scan

        Returns:
            Nested dictionary representing directory structure
        """

        def scan_dir(path: Path, depth: int = 0) -> Dict:
            if depth > max_depth:
                return {"truncated": True}

            try:
                items = self.handler.list_directory(path, recursive=False)

                result = {
                    "name": path.name,
                    "path": str(path.relative_to(self.project_path)),
                    "files": [],
                    "directories": [],
                }

                for item in items:
                    if item["is_dir"]:
                        sub_path = Path(item["path"])
                        sub_tree = scan_dir(sub_path, depth + 1)
                        result["directories"].append(sub_tree)
                    else:
                        result["files"].append(
                            {
                                "name": item["name"],
                                "size": item["size"],
                                "size_human": item["size_human"],
                                "modified": item["modified"].isoformat(),
                                "extension": item["extension"],
                            }
                        )

                return result

            except Exception as e:
                return {"error": str(e)}

        return scan_dir(self.project_path)

    def get_recent_files(self, limit: int = 10) -> List[Dict]:
        """
        Get most recently modified files.

        Args:
            limit: Maximum number of files to return

        Returns:
            List of file info dictionaries sorted by modification time
        """
        all_files = self.handler.list_directory(self.project_path, recursive=True)

        # Filter to files only
        files = [f for f in all_files if f["is_file"]]

        # Sort by modification time
        files.sort(key=lambda x: x["modified_timestamp"], reverse=True)

        return files[:limit]

    def search_content(
        self, query: str, file_patterns: List[str] = ["*.py", "*.md", "*.txt"]
    ) -> List[Dict]:
        """
        Search file contents for query string.

        Args:
            query: Search string
            file_patterns: File patterns to search

        Returns:
            List of matches with context
        """
        results = []

        for pattern in file_patterns:
            files = self.handler.find_files(self.project_path, pattern)

            for file_path in files:
                try:
                    success, content = read_file_content(file_path)
                    if not success:
                        continue

                    # Search for query
                    lines = content.split("\n")
                    for line_no, line in enumerate(lines, 1):
                        if query.lower() in line.lower():
                            results.append(
                                {
                                    "file": str(
                                        file_path.relative_to(self.project_path)
                                    ),
                                    "line": line_no,
                                    "content": line.strip(),
                                    "context": self._get_context(lines, line_no - 1),
                                }
                            )
                except (UnicodeDecodeError, OSError, IOError):
                    # Unable to read or decode file, skip it
                    continue

        return results

    @staticmethod
    def _get_context(
        lines: List[str], line_idx: int, context_lines: int = 2
    ) -> List[str]:
        """
        Get surrounding lines for context.

        Args:
            lines: All lines from file
            line_idx: Index of target line
            context_lines: Number of lines before/after to include

        Returns:
            List of context lines
        """
        start = max(0, line_idx - context_lines)
        end = min(len(lines), line_idx + context_lines + 1)
        return lines[start:end]
