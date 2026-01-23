#!/usr/bin/env python3
"""Jupyter notebook validation and sanitization."""
import json
from typing import Dict, List, Tuple


class NotebookValidator:
    """Validates and sanitizes Jupyter notebooks."""

    @staticmethod
    def validate_notebook(notebook_content: dict) -> Tuple[bool, List[str]]:
        """
        Validate notebook structure and content.

        Returns:
            (is_valid, errors)
        """
        errors = []

        # Basic structure validation
        required_fields = ["cells", "metadata", "nbformat", "nbformat_minor"]
        for field in required_fields:
            if field not in notebook_content:
                errors.append(f"Missing required field: {field}")

        # Check nbformat version
        if notebook_content.get("nbformat", 0) < 4:
            errors.append("Unsupported notebook format version")

        # Validate cells
        cells = notebook_content.get("cells", [])
        if not isinstance(cells, list):
            errors.append("Cells must be a list")

        for i, cell in enumerate(cells):
            if not isinstance(cell, dict):
                errors.append(f"Cell {i} must be a dictionary")
                continue

            if "cell_type" not in cell:
                errors.append(f"Cell {i} missing cell_type")

            if cell.get("cell_type") not in ["code", "markdown", "raw"]:
                errors.append(f"Cell {i} has invalid cell_type")

            if "source" not in cell:
                errors.append(f"Cell {i} missing source")

        return len(errors) == 0, errors

    @staticmethod
    def sanitize_notebook(notebook_content: dict) -> dict:
        """Remove potentially dangerous content from notebook."""
        # Create a copy to avoid modifying original
        sanitized = json.loads(json.dumps(notebook_content))

        # Remove outputs that might contain sensitive data
        for cell in sanitized.get("cells", []):
            if cell.get("cell_type") == "code":
                # Clear outputs but preserve execution count
                cell["outputs"] = []
                if "execution_count" in cell:
                    cell["execution_count"] = None

        # Remove potentially sensitive metadata
        metadata = sanitized.get("metadata", {})
        sensitive_keys = ["kernelspec", "language_info"]
        for key in sensitive_keys:
            if key in metadata:
                if key == "kernelspec":
                    # Keep basic kernelspec but remove paths
                    metadata[key] = {
                        "display_name": metadata[key].get("display_name", "Python 3"),
                        "language": "python",
                        "name": "python3",
                    }
                elif key == "language_info":
                    # Keep basic language info but remove paths
                    metadata[key] = {
                        "name": "python",
                        "version": metadata[key].get("version", "3.11.0"),
                    }

        return sanitized


# EOF
