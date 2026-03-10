"""API endpoints for Overleaf import/export in SciTeX Writer.

Delegates all logic to scitex_writer.migration.from_overleaf() and to_overleaf().
"""

import logging
import tempfile
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.services.project_utils import get_current_project

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def api_import_overleaf(request):
    """Import Overleaf ZIP into current writer project."""
    uploaded_file = request.FILES.get("zip_file")
    if not uploaded_file:
        return JsonResponse(
            {"success": False, "error": "No ZIP file uploaded."}, status=400
        )
    if not uploaded_file.name.endswith(".zip"):
        return JsonResponse(
            {"success": False, "error": "File must be a .zip archive."}, status=400
        )

    project = get_current_project(request)
    if not project:
        return JsonResponse(
            {"success": False, "error": "No active project."}, status=400
        )

    # Save uploaded ZIP to temp file
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        from scitex_writer.migration import from_overleaf

        from ...services import WriterService

        writer_service = WriterService(project.id, request.user.id)
        writer_dir = writer_service.writer_dir

        result = from_overleaf(tmp_path, output_dir=str(writer_dir), force=True)
        logger.info(
            "Overleaf import completed for project %s (user: %s)",
            project.id,
            request.user.username,
        )
        return JsonResponse(
            {
                "success": True,
                "message": "Overleaf project imported successfully.",
                "details": result,
            }
        )
    except ImportError:
        logger.error("scitex_writer.migration module not available")
        return JsonResponse(
            {
                "success": False,
                "error": "Overleaf migration support is not installed.",
            },
            status=500,
        )
    except Exception as e:
        logger.error("Overleaf import failed: %s", e, exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@login_required
@require_http_methods(["POST"])
def api_export_overleaf(request):
    """Export current writer project as Overleaf-compatible ZIP."""
    project = get_current_project(request)
    if not project:
        return JsonResponse(
            {"success": False, "error": "No active project."}, status=400
        )

    from ...services import WriterService

    writer_service = WriterService(project.id, request.user.id)
    writer_dir = writer_service.writer_dir

    if not writer_dir.exists():
        return JsonResponse(
            {"success": False, "error": "No writer content found."}, status=400
        )

    tmp_zip = tempfile.mktemp(suffix=".zip")

    try:
        from scitex_writer.migration import to_overleaf

        to_overleaf(str(writer_dir), output_path=tmp_zip)
        logger.info(
            "Overleaf export completed for project %s (user: %s)",
            project.id,
            request.user.username,
        )

        response = FileResponse(open(tmp_zip, "rb"), content_type="application/zip")
        response["Content-Disposition"] = (
            f'attachment; filename="{project.name}_overleaf.zip"'
        )
        return response
    except ImportError:
        Path(tmp_zip).unlink(missing_ok=True)
        logger.error("scitex_writer.migration module not available")
        return JsonResponse(
            {
                "success": False,
                "error": "Overleaf migration support is not installed.",
            },
            status=500,
        )
    except Exception as e:
        Path(tmp_zip).unlink(missing_ok=True)
        logger.error("Overleaf export failed: %s", e, exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)
