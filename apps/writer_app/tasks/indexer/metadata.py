#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Metadata extraction utilities for figures and tables."""
import hashlib
from pathlib import Path


def compute_file_hash(file_path: Path) -> str:
    """
    Compute SHA256 hash of file for change detection.

    Args:
        file_path: Path to file

    Returns:
        SHA256 hex digest
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def extract_figure_metadata(file_path: Path, project_path: Path) -> dict:
    """
    Extract metadata from figure file.

    Args:
        file_path: Absolute path to figure
        project_path: Project root path

    Returns:
        Dictionary with figure metadata
    """
    stat = file_path.stat()
    relative_path = str(file_path.relative_to(project_path))

    return {
        'file_path': relative_path,
        'file_name': file_path.name,
        'file_hash': compute_file_hash(file_path),
        'file_size': stat.st_size,
        'file_type': file_path.suffix[1:].lower(),
        'last_modified': stat.st_mtime,
        'source': detect_source(relative_path),
        'location': str(file_path.parent.relative_to(project_path)),
        'tags': extract_tags(file_path, relative_path),
    }


def extract_table_metadata(file_path: Path, project_path: Path) -> dict:
    """
    Extract metadata from table file (CSV, Excel).

    Args:
        file_path: Absolute path to table
        project_path: Project root path

    Returns:
        Dictionary with table metadata
    """
    stat = file_path.stat()
    relative_path = str(file_path.relative_to(project_path))

    # Try to extract caption from filename or parent directory
    caption = file_path.stem.replace('_', ' ').replace('-', ' ').title()

    return {
        'file_path': relative_path,
        'file_name': file_path.name,
        'file_hash': compute_file_hash(file_path),
        'caption': caption,
        'last_modified': stat.st_mtime,
        'source': detect_source(relative_path),
        'location': str(file_path.parent.relative_to(project_path)),
        'tags': extract_tags(file_path, relative_path),
    }


def detect_source(relative_path: str) -> str:
    """
    Detect source category from file path.

    Args:
        relative_path: Relative path from project root

    Returns:
        Source category: 'paper', 'pool', 'data', 'scripts', 'other'
    """
    if 'scitex/writer/00_shared/figures_pool' in relative_path:
        return 'pool'
    elif 'scitex/writer/00_shared/tables_pool' in relative_path:
        return 'pool'
    elif 'scitex/writer/' in relative_path:
        return 'paper'
    elif 'data/' in relative_path:
        return 'data'
    elif 'scripts/' in relative_path:
        return 'scripts'
    else:
        return 'other'


def extract_tags(file_path: Path, relative_path: str) -> list:
    """
    Auto-extract tags from file path and name.

    Args:
        file_path: Path object
        relative_path: Relative path string

    Returns:
        List of tags
    """
    tags = []

    # Document type tags
    if '01_manuscript' in relative_path:
        tags.append('manuscript')
    elif '02_supplementary' in relative_path:
        tags.append('supplementary')
    elif '03_revision' in relative_path:
        tags.append('revision')

    # Source type tags
    if 'data/' in relative_path:
        tags.append('data-analysis')
        # Extract dataset name (e.g., mnist, imagenet)
        parts = relative_path.split('data/')[1].split('/')
        if parts:
            tags.append(f'dataset:{parts[0]}')

    if 'scripts/' in relative_path:
        tags.append('script-output')

    if 'pool' in relative_path:
        tags.append('curated')

    # File type tags
    if file_path.suffix.lower() == '.pptx':
        tags.append('needs-conversion')

    if file_path.suffix.lower() == '.mmd':
        tags.append('diagram')

    if file_path.suffix.lower() in ['.svg']:
        tags.append('vector')

    if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
        tags.append('raster')

    if file_path.suffix.lower() in ['.pdf']:
        tags.append('pdf')

    return tags


# EOF
