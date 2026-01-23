#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Indexing tasks for figures and tables."""
from pathlib import Path
import logging

from .constants import shared_task, CELERY_AVAILABLE
from .constants import SUPPORTED_FIGURE_EXTENSIONS, SUPPORTED_TABLE_EXTENSIONS
from .metadata import compute_file_hash, extract_figure_metadata, extract_table_metadata

logger = logging.getLogger(__name__)


@shared_task
def index_project_figures(project_id):
    """
    Index all figures in project to local SQLite DB.

    This task scans the project directory for figure files and stores
    their metadata in the project's SQLite database for fast querying.

    Args:
        project_id: Project ID
    """
    from apps.project_app.models import Project
    from ...utils.project_db import get_project_db
    from ...services import WriterService
    from .references import update_latex_references
    from .thumbnails import generate_thumbnail

    try:
        project = Project.objects.get(id=project_id)

        # Get project path
        if hasattr(project, 'git_clone_path') and project.git_clone_path:
            project_path = Path(project.git_clone_path)
        else:
            # Handle visitor projects
            from apps.project_app.services.project_filesystem import get_project_filesystem_manager
            if not hasattr(project, 'owner') or not project.owner:
                logger.error(f"[Indexer] Cannot determine user for project {project_id}")
                return
            manager = get_project_filesystem_manager(project.owner)
            project_path = manager.get_project_root_path(project)
            if not project_path:
                logger.error(f"[Indexer] Project path not found for project {project_id}")
                return

        db = get_project_db(project)

        logger.info(f"[Indexer] Starting indexing for project {project_id} at {project_path}")

        # Search patterns for figures
        search_patterns = [
            'scitex/writer/**/figures/**/*',
            'scitex/writer/**/tables/**/*',
            'scitex/writer/00_shared/figures_pool/*',
            'scitex/writer/00_shared/tables_pool/*',
            'scitex/writer/uploads/figures/*',  # User uploads
            'data/**/figures/**/*',
            'data/**/plots/**/*',
            'data/**/*.png',
            'data/**/*.jpg',
            'data/**/*.pdf',
            'scripts/**/*_out/**/*',
            'scripts/**/figures/**/*',
        ]

        indexed_count = 0
        skipped_count = 0

        for pattern in search_patterns:
            for file_path in project_path.glob(pattern):
                if not file_path.is_file():
                    continue

                if file_path.suffix.lower() in SUPPORTED_FIGURE_EXTENSIONS:
                    try:
                        # Check if already indexed with same hash
                        relative_path = str(file_path.relative_to(project_path))
                        file_hash = compute_file_hash(file_path)

                        if db.check_if_indexed(relative_path, file_hash):
                            skipped_count += 1
                            continue  # Skip unchanged files

                        # Check for duplicate content (same hash, different path)
                        existing = db.check_hash_exists(file_hash, table_type='figure')
                        if existing:
                            # Compare filenames - prefer longer, more descriptive names
                            current_name = file_path.name
                            existing_name = existing['file_name']

                            if len(current_name) <= len(existing_name):
                                # Current file has shorter/same length name - skip it as duplicate
                                logger.debug(f"[Indexer] Skipping duplicate: {current_name} (keeping {existing_name})")
                                skipped_count += 1
                                continue
                            else:
                                # Current file has longer name - remove old entry and index new one
                                logger.info(f"[Indexer] Replacing duplicate: {existing_name} -> {current_name}")
                                db.delete_figure(existing['file_path'])

                        # Extract metadata
                        metadata = extract_figure_metadata(file_path, project_path)
                        db.upsert_figure(metadata)
                        indexed_count += 1

                        # Generate thumbnail asynchronously
                        if CELERY_AVAILABLE:
                            generate_thumbnail.delay(project_id, relative_path)
                        else:
                            generate_thumbnail(project_id, relative_path)

                    except Exception as e:
                        logger.error(f"[Indexer] Error indexing {file_path}: {e}")
                        continue

        logger.info(f"[Indexer] Completed for project {project_id}: {indexed_count} indexed, {skipped_count} skipped")

        # Update LaTeX references
        if CELERY_AVAILABLE:
            update_latex_references.delay(project_id)
        else:
            update_latex_references(project_id)

    except Exception as e:
        logger.error(f"[Indexer] Error indexing project {project_id}: {e}")
        raise


@shared_task
def index_project_tables(project_id):
    """
    Index all table files (CSV, Excel) in project to local SQLite DB.

    Tables are discovered in:
    - scitex/writer/**/tables/**/* (manuscript tables)
    - scitex/writer/00_shared/tables_pool/* (shared pool)
    - data/**/tables/**/* (data tables)
    - data/**/*.{csv,xlsx,xls,tsv} (data files)
    - scripts/**/*_out/**/* (script outputs)

    Args:
        project_id: Project ID
    """
    from apps.project_app.models import Project
    from ...utils.project_db import get_project_db
    from .thumbnails import generate_table_thumbnail

    try:
        project = Project.objects.get(id=project_id)

        # Get project path
        if hasattr(project, 'git_clone_path') and project.git_clone_path:
            project_path = Path(project.git_clone_path)
        else:
            from apps.project_app.services.project_filesystem import get_project_filesystem_manager
            if not hasattr(project, 'owner') or not project.owner:
                logger.error(f"[TableIndexer] Cannot determine user for project {project_id}")
                return
            manager = get_project_filesystem_manager(project.owner)
            project_path = manager.get_project_root_path(project)
            if not project_path:
                logger.error(f"[TableIndexer] Project path not found for project {project_id}")
                return

        db = get_project_db(project)

        logger.info(f"[TableIndexer] Starting table indexing for project {project_id} at {project_path}")

        # Search patterns for tables
        search_patterns = [
            'scitex/writer/**/tables/**/*',
            'scitex/writer/00_shared/tables_pool/*',
            'scitex/writer/uploads/tables/*',  # User uploads
            'data/**/tables/**/*',
            'data/**/*.csv',
            'data/**/*.xlsx',
            'data/**/*.xls',
            'data/**/*.tsv',
            'scripts/**/*_out/**/*.csv',
            'scripts/**/*_out/**/*.xlsx',
        ]

        indexed_count = 0
        skipped_count = 0

        for pattern in search_patterns:
            for file_path in project_path.glob(pattern):
                if not file_path.is_file():
                    continue

                if file_path.suffix.lower() in SUPPORTED_TABLE_EXTENSIONS:
                    try:
                        # Check if already indexed with same hash
                        relative_path = str(file_path.relative_to(project_path))
                        file_hash = compute_file_hash(file_path)

                        if db.check_if_indexed(relative_path, file_hash, table_type='table'):
                            skipped_count += 1
                            continue  # Skip unchanged files

                        # Check for duplicate content (same hash, different path)
                        existing = db.check_hash_exists(file_hash, table_type='table')
                        if existing:
                            # Compare filenames - prefer longer, more descriptive names
                            current_name = file_path.name
                            existing_name = existing['file_name']

                            if len(current_name) <= len(existing_name):
                                # Current file has shorter/same length name - skip it as duplicate
                                logger.debug(f"[TableIndexer] Skipping duplicate: {current_name} (keeping {existing_name})")
                                skipped_count += 1
                                continue
                            else:
                                # Current file has longer name - remove old entry and index new one
                                logger.info(f"[TableIndexer] Replacing duplicate: {existing_name} -> {current_name}")
                                db.delete_table(existing['file_path'])

                        # Extract metadata
                        metadata = extract_table_metadata(file_path, project_path)
                        db.upsert_table(metadata)
                        indexed_count += 1

                        # Generate thumbnail asynchronously
                        if CELERY_AVAILABLE:
                            generate_table_thumbnail.delay(project_id, relative_path)
                        else:
                            generate_table_thumbnail(project_id, relative_path)

                    except Exception as e:
                        logger.error(f"[TableIndexer] Error indexing {file_path}: {e}")
                        continue

        logger.info(f"[TableIndexer] Completed for project {project_id}: {indexed_count} indexed, {skipped_count} skipped")

    except Exception as e:
        logger.error(f"[TableIndexer] Error indexing project {project_id}: {e}")
        raise


# EOF
