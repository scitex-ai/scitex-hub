"""Plots Files - File upload and handling utilities."""

import tempfile
import uuid
from pathlib import Path
from typing import Dict


def save_uploaded_file(uploaded_file) -> Dict:
    """Save uploaded data file to temporary directory."""
    allowed_extensions = [".csv", ".xlsx", ".xls"]
    file_ext = "." + uploaded_file.name.split(".")[-1].lower()

    if file_ext not in allowed_extensions:
        raise ValueError(f"Invalid file type. Allowed: {', '.join(allowed_extensions)}")

    temp_dir = Path(tempfile.gettempdir()) / "scitex_plot_data"
    temp_dir.mkdir(exist_ok=True)

    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = temp_dir / unique_filename

    with open(file_path, "wb+") as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    return {
        "success": True,
        "file_path": str(file_path),
        "filename": uploaded_file.name,
        "size": uploaded_file.size,
    }
