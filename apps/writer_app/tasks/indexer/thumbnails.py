#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thumbnail generation for figures and tables."""
from pathlib import Path
import logging

from .constants import shared_task
from .metadata import compute_file_hash

logger = logging.getLogger(__name__)


@shared_task
def generate_thumbnail(project_id, file_path):
    """
    Generate thumbnail for figure.

    Supports: PNG, JPG, JPEG, TIFF, PDF
    TODO: Add support for SVG, PPTX, MMD

    Args:
        project_id: Project ID
        file_path: Relative path to figure
    """
    from apps.project_app.models import Project
    from ...utils.project_db import get_project_db

    try:
        from PIL import Image

        project = Project.objects.get(id=project_id)

        # Get project path
        if hasattr(project, 'git_clone_path') and project.git_clone_path:
            project_path = Path(project.git_clone_path)
        else:
            from apps.project_app.services.project_filesystem import get_project_filesystem_manager
            if not hasattr(project, 'owner') or not project.owner:
                logger.error(f"[Thumbnail] Cannot determine user for project {project_id}")
                return
            manager = get_project_filesystem_manager(project.owner)
            project_path = manager.get_project_root_path(project)
            if not project_path:
                logger.error(f"[Thumbnail] Project path not found for project {project_id}")
                return

        db = get_project_db(project)

        full_path = project_path / file_path
        if not full_path.exists():
            logger.warning(f"[Thumbnail] File not found: {file_path}")
            return

        # Generate thumbnail filename
        file_hash = compute_file_hash(full_path)
        thumb_name = f"{file_hash[:16]}_thumb.jpg"
        thumb_path = db.thumbnails_dir / thumb_name

        # Generate based on file type
        file_type = full_path.suffix.lower()

        if file_type in ['.png', '.jpg', '.jpeg', '.tiff', '.tif']:
            with Image.open(full_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                img.save(thumb_path, 'JPEG', quality=85)

        elif file_type == '.pdf':
            try:
                from pdf2image import convert_from_path
                images = convert_from_path(full_path, first_page=1, last_page=1, size=(200, 200))
                if images:
                    images[0].save(thumb_path, 'JPEG', quality=85)
            except ImportError:
                logger.warning("[Thumbnail] pdf2image not installed, skipping PDF thumbnail")
                return
            except Exception as e:
                logger.error(f"[Thumbnail] Error generating PDF thumbnail: {e}")
                return

        else:
            logger.debug(f"[Thumbnail] Unsupported file type: {file_type}")
            return

        # Update DB with thumbnail path
        relative_thumb_path = str(thumb_path.relative_to(project_path))

        with db.connection() as conn:
            conn.execute('''
                UPDATE figures SET thumbnail_path = ? WHERE file_path = ?
            ''', (relative_thumb_path, file_path))

        logger.debug(f"[Thumbnail] Generated for {file_path}")

    except Exception as e:
        logger.error(f"[Thumbnail] Error generating for {file_path}: {e}")


@shared_task
def generate_table_thumbnail(project_id, file_path):
    """
    Generate thumbnail preview for table files (CSV, Excel).

    Reads first few rows and renders as table image.

    Args:
        project_id: Project ID
        file_path: Relative path to table file
    """
    from apps.project_app.models import Project
    from ...utils.project_db import get_project_db

    try:
        import pandas as pd
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        from PIL import Image

        project = Project.objects.get(id=project_id)

        # Get project path
        if hasattr(project, 'git_clone_path') and project.git_clone_path:
            project_path = Path(project.git_clone_path)
        else:
            from apps.project_app.services.project_filesystem import get_project_filesystem_manager
            if not hasattr(project, 'owner') or not project.owner:
                logger.error(f"[TableThumbnail] Cannot determine user for project {project_id}")
                return
            manager = get_project_filesystem_manager(project.owner)
            project_path = manager.get_project_root_path(project)
            if not project_path:
                logger.error(f"[TableThumbnail] Project path not found for project {project_id}")
                return

        db = get_project_db(project)

        full_path = project_path / file_path
        if not full_path.exists():
            logger.warning(f"[TableThumbnail] File not found: {file_path}")
            return

        # Generate thumbnail filename
        file_hash = compute_file_hash(full_path)
        thumb_name = f"{file_hash[:16]}_thumb.jpg"
        thumb_path = db.thumbnails_dir / thumb_name

        # Read table data - show top-left corner only
        file_type = full_path.suffix.lower()
        df = None

        if file_type == '.csv':
            df = pd.read_csv(full_path, nrows=5)  # First 5 rows
        elif file_type in ['.xlsx', '.xls']:
            df = pd.read_excel(full_path, nrows=5)
        elif file_type == '.tsv':
            df = pd.read_csv(full_path, sep='\t', nrows=5)
        elif file_type == '.ods':
            df = pd.read_excel(full_path, engine='odf', nrows=5)
        else:
            logger.debug(f"[TableThumbnail] Unsupported file type: {file_type}")
            return

        if df is None or df.empty:
            logger.warning(f"[TableThumbnail] Empty table: {file_path}")
            return

        # Show only first 4 columns (top-left corner)
        if len(df.columns) > 4:
            df = df.iloc[:, :4]
            # Add ellipsis column to indicate more columns
            df['...'] = '...'

        # Truncate long values to fit in thumbnail
        df = df.map(lambda x: str(x)[:15] + '...' if len(str(x)) > 15 else str(x))

        # Create figure and render table - optimized for small thumbnail
        fig, ax = plt.subplots(figsize=(5, 3), facecolor='white')
        ax.axis('tight')
        ax.axis('off')

        # Create table with better spacing
        table = ax.table(
            cellText=df.values,
            colLabels=df.columns,
            cellLoc='center',
            loc='center',
            bbox=[0, 0, 1, 1]
        )

        # Style table for better readability
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)  # Increase row height for better readability

        # Header and cell styling
        for (i, j), cell in table.get_celld().items():
            cell.set_edgecolor('#cccccc')
            cell.set_linewidth(1)
            cell.PAD = 0.05

            if i == 0:  # Header row
                cell.set_facecolor('#4A90E2')
                cell.set_text_props(weight='bold', color='white', size=9)
            else:  # Data rows
                cell.set_facecolor('#f8f9fa' if i % 2 == 0 else 'white')
                cell.set_text_props(size=8)

        # Save to file with white background
        plt.savefig(thumb_path, format='jpeg', dpi=120, bbox_inches='tight',
                   pad_inches=0.15, facecolor='white', edgecolor='none')
        plt.close(fig)

        # Update DB with thumbnail path
        relative_thumb_path = str(thumb_path.relative_to(project_path))

        with db.connection() as conn:
            conn.execute('''
                UPDATE tables SET thumbnail_path = ? WHERE file_path = ?
            ''', (relative_thumb_path, file_path))

        logger.debug(f"[TableThumbnail] Generated for {file_path}")

    except ImportError as e:
        logger.warning(f"[TableThumbnail] Missing dependency for {file_path}: {e}")
    except Exception as e:
        logger.error(f"[TableThumbnail] Error generating for {file_path}: {e}")


# EOF
