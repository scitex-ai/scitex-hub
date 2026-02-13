#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared CSV upload and parsing helpers for Plot and Stats APIs."""

import logging  # noqa: STX-I007 — Django context, no @stx.session
import os
import tempfile
from pathlib import Path

logger = logging.getLogger("scitex")

__all__ = ["parse_csv_upload", "cleanup_csv_temp", "extract_columns"]

ALLOWED_EXTENSIONS = {".csv", ".tsv"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def parse_csv_upload(request) -> tuple[Path, dict]:
    """Save uploaded CSV to temp file, return (path, form_params).

    Validates file presence, extension, and size.

    Returns
    -------
    tuple[Path, dict]
        (temp_file_path, dict_of_non_file_form_fields)

    Raises
    ------
    ValueError
        If file is missing, wrong extension, or too large.
    """
    if "csv_file" not in request.FILES:
        raise ValueError("'csv_file' field is required in multipart upload")

    csv_file = request.FILES["csv_file"]
    ext = Path(csv_file.name).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Only .csv and .tsv files accepted, got: {ext}")

    if csv_file.size > MAX_FILE_SIZE:
        raise ValueError(
            f"File too large ({csv_file.size} bytes). Max: {MAX_FILE_SIZE}"
        )

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    for chunk in csv_file.chunks():
        tmp.write(chunk)
    tmp.close()

    # Collect non-file form fields
    params = {k: v for k, v in request.POST.items()}

    return Path(tmp.name), params


def cleanup_csv_temp(path: Path):
    """Remove temporary CSV file."""
    if path and path.exists():
        os.unlink(path)


def extract_columns(csv_path: Path, columns: list[str]) -> dict[str, list]:
    """Load CSV and extract named columns as lists.

    Parameters
    ----------
    csv_path : Path
        Path to the CSV file.
    columns : list[str]
        Column names to extract.

    Returns
    -------
    dict[str, list]
        Mapping of column_name → values as list.

    Raises
    ------
    ValueError
        If a requested column doesn't exist in the CSV.
    """
    import scitex as stx

    df = stx.io.load(str(csv_path))

    result = {}
    for col in columns:
        if col not in df.columns:
            available = ", ".join(df.columns.tolist())
            raise ValueError(f"Column '{col}' not found. Available: {available}")
        result[col] = df[col].dropna().tolist()

    return result


# EOF
