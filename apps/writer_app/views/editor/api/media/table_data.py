#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Table data API views - preview and editing."""
from __future__ import annotations
import logging
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ...auth_utils import api_login_optional, get_user_for_request

logger = logging.getLogger(__name__)


@api_login_optional
@require_http_methods(["GET"])
def table_data_api(request, project_id, file_hash):
    """
    Get full table data for preview/editing.

    Args:
        project_id: Project ID
        file_hash: SHA256 hash of the table file (first 16 chars)

    Returns:
        JSON with:
            - success: bool
            - data: list of dictionaries (rows)
            - columns: list of column names
            - metadata: {file_name, file_path, file_type, rows, cols}
    """
    try:
        import pandas as pd
        from pathlib import Path
        from apps.project_app.models import Project
        from .....utils.project_db import get_project_db

        project = Project.objects.get(id=project_id)
        user, is_visitor = get_user_for_request(request, project_id)

        if not user:
            return JsonResponse(
                {"success": False, "error": "Invalid session"}, status=403
            )

        db = get_project_db(project)

        # Find table by hash
        tables = db.get_all_tables()
        table = None
        for t in tables:
            if t.get('file_hash', '').startswith(file_hash):
                table = t
                break

        if not table:
            return JsonResponse(
                {"success": False, "error": "Table not found"}, status=404
            )

        # Get project path
        if hasattr(project, 'git_clone_path') and project.git_clone_path:
            project_path = Path(project.git_clone_path)
        else:
            from apps.project_app.services.filesystem_manager import get_project_filesystem_manager
            manager = get_project_filesystem_manager(project.owner)
            project_path = manager.get_project_root_path(project)
            if not project_path:
                raise ValueError(f"Project path not found")

        # Read table file
        file_path = project_path / table['file_path']
        if not file_path.exists():
            return JsonResponse(
                {"success": False, "error": "Table file not found"}, status=404
            )

        file_type = file_path.suffix.lower()

        # Read data based on file type
        if file_type == '.csv':
            df = pd.read_csv(file_path)
        elif file_type in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        elif file_type == '.tsv':
            df = pd.read_csv(file_path, sep='\t')
        elif file_type == '.ods':
            df = pd.read_excel(file_path, engine='odf')
        else:
            return JsonResponse(
                {"success": False, "error": f"Unsupported file type: {file_type}"},
                status=400
            )

        # Convert to JSON-friendly format
        # Replace NaN with None for JSON serialization
        df = df.where(pd.notna(df), None)

        data = df.to_dict('records')
        columns = df.columns.tolist()

        logger.info(f"[Table Data API] Loaded {len(data)} rows × {len(columns)} cols from {table['file_name']}")

        return JsonResponse({
            'success': True,
            'data': data,
            'columns': columns,
            'metadata': {
                'file_name': table['file_name'],
                'file_path': table['file_path'],
                'file_type': file_type,
                'file_hash': table['file_hash'],
                'rows': len(data),
                'cols': len(columns),
            }
        })

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"[Table Data API] Error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@api_login_optional
@require_http_methods(["POST"])
def table_update_api(request, project_id, file_hash):
    """
    Update table data (save modifications).

    Expects JSON body with:
        - data: list of dictionaries (updated rows)
        - columns: list of column names

    Returns:
        JSON with success status and updated metadata
    """
    try:
        import pandas as pd
        from pathlib import Path
        from apps.project_app.models import Project
        from .....utils.project_db import get_project_db
        from .....tasks.indexer import index_project_tables, CELERY_AVAILABLE

        project = Project.objects.get(id=project_id)
        user, is_visitor = get_user_for_request(request, project_id)

        if not user:
            return JsonResponse(
                {"success": False, "error": "Invalid session"}, status=403
            )

        # Parse request body
        body = json.loads(request.body)
        data = body.get('data', [])
        columns = body.get('columns', [])

        if not data or not columns:
            return JsonResponse(
                {"success": False, "error": "Missing data or columns"}, status=400
            )

        db = get_project_db(project)

        # Find table by hash
        tables = db.get_all_tables()
        table = None
        for t in tables:
            if t.get('file_hash', '').startswith(file_hash):
                table = t
                break

        if not table:
            return JsonResponse(
                {"success": False, "error": "Table not found"}, status=404
            )

        # Get project path
        if hasattr(project, 'git_clone_path') and project.git_clone_path:
            project_path = Path(project.git_clone_path)
        else:
            from apps.project_app.services.filesystem_manager import get_project_filesystem_manager
            manager = get_project_filesystem_manager(project.owner)
            project_path = manager.get_project_root_path(project)
            if not project_path:
                raise ValueError(f"Project path not found")

        # Write data to file
        file_path = project_path / table['file_path']
        file_type = file_path.suffix.lower()

        # Create DataFrame from data
        df = pd.DataFrame(data, columns=columns)

        # Save based on file type
        if file_type == '.csv':
            df.to_csv(file_path, index=False)
        elif file_type in ['.xlsx', '.xls']:
            df.to_excel(file_path, index=False, engine='openpyxl')
        elif file_type == '.tsv':
            df.to_csv(file_path, sep='\t', index=False)
        elif file_type == '.ods':
            df.to_excel(file_path, index=False, engine='odf')
        else:
            return JsonResponse(
                {"success": False, "error": f"Unsupported file type: {file_type}"},
                status=400
            )

        logger.info(f"[Table Update API] Saved {len(data)} rows to {table['file_name']}")

        # Re-index to update thumbnail and metadata
        if CELERY_AVAILABLE:
            index_project_tables.delay(project_id)
        else:
            index_project_tables(project_id)

        return JsonResponse({
            'success': True,
            'message': 'Table updated successfully',
            'metadata': {
                'rows': len(data),
                'cols': len(columns),
            }
        })

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"[Table Update API] Error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# EOF
