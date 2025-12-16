"""
Bundle Download API Views - GET-based download endpoints.

Provides direct download endpoints for figz and pltz bundles as ZIP files.
"""

import io
import logging
import zipfile
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def download_figz_bundle(request):
    """
    Download a figz bundle as a ZIP file (.figz format).

    Query params:
        path: Filesystem path to .figz.d directory or .figz file

    Returns:
        ZIP file download (.figz)
    """
    bundle_path = request.GET.get("path")
    if not bundle_path:
        return JsonResponse({"error": "path parameter required"}, status=400)

    bundle_path = Path(bundle_path)

    # Handle both .figz.d directory and .figz ZIP
    if bundle_path.suffix == ".figz" and bundle_path.is_file():
        with open(bundle_path, 'rb') as f:
            content = f.read()
        response = HttpResponse(content, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{bundle_path.name}"'
        return response

    # Handle .figz.d directory
    if not str(bundle_path).endswith('.figz.d'):
        bundle_path = Path(str(bundle_path) + '.d') if not bundle_path.exists() else bundle_path

    if not bundle_path.exists():
        return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)

    try:
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in bundle_path.rglob('*'):
                if file_path.is_file():
                    rel_path = file_path.relative_to(bundle_path)
                    zf.write(file_path, rel_path)

        zip_buffer.seek(0)
        bundle_name = bundle_path.name.replace('.figz.d', '')

        response = HttpResponse(zip_buffer.read(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{bundle_name}.figz"'
        return response

    except Exception as e:
        logger.exception(f"Failed to download figz bundle: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def download_figz_d_bundle(request):
    """
    Download a figz.d bundle as a ZIP file preserving directory structure.

    The downloaded ZIP will contain the full .figz.d directory structure,
    suitable for extracting as a working directory bundle.

    Query params:
        path: Filesystem path to .figz.d directory or .figz file

    Returns:
        ZIP file download with .figz.d.zip filename
    """
    bundle_path = request.GET.get("path")
    logger.info(f"[download_figz_d_bundle] Requested path: {bundle_path}")

    if not bundle_path:
        return JsonResponse({"error": "path parameter required"}, status=400)

    bundle_path = Path(bundle_path)
    logger.info(f"[download_figz_d_bundle] Path object: {bundle_path}, exists={bundle_path.exists()}")

    # Find the .figz.d directory
    if bundle_path.suffix == ".figz" and bundle_path.is_file():
        figz_d_path = Path(str(bundle_path) + '.d')
        if figz_d_path.exists():
            bundle_path = figz_d_path
        else:
            return JsonResponse({"error": "No .figz.d directory found, only .figz ZIP"}, status=404)

    # Handle .figz.d directory
    if not str(bundle_path).endswith('.figz.d'):
        bundle_path = Path(str(bundle_path) + '.d') if not bundle_path.exists() else bundle_path

    if not bundle_path.exists():
        logger.error(f"[download_figz_d_bundle] Bundle not found: {bundle_path}")
        return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)

    logger.info(f"[download_figz_d_bundle] Final bundle_path: {bundle_path}")

    try:
        zip_buffer = io.BytesIO()
        bundle_dir_name = bundle_path.name

        file_count = 0
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in bundle_path.rglob('*'):
                if file_path.is_file():
                    rel_path = file_path.relative_to(bundle_path.parent)
                    zf.write(file_path, rel_path)
                    file_count += 1
                    if file_count <= 20:
                        logger.debug(f"[download_figz_d_bundle] Added: {rel_path}")

        logger.info(f"[download_figz_d_bundle] Total files in ZIP: {file_count}")
        zip_buffer.seek(0)

        response = HttpResponse(zip_buffer.read(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{bundle_dir_name}.zip"'
        return response

    except Exception as e:
        logger.exception(f"Failed to download figz.d bundle: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def download_pltz_bundle(request):
    """
    Download a pltz bundle as a ZIP file.

    Query params:
        path: Filesystem path to .pltz.d directory or .pltz file

    Returns:
        ZIP file download (.pltz)
    """
    bundle_path = request.GET.get("path")
    if not bundle_path:
        return JsonResponse({"error": "path parameter required"}, status=400)

    bundle_path = Path(bundle_path)

    # Handle both .pltz.d directory and .pltz ZIP
    if bundle_path.suffix == ".pltz" and bundle_path.is_file():
        with open(bundle_path, 'rb') as f:
            content = f.read()
        response = HttpResponse(content, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{bundle_path.name}"'
        return response

    # Handle .pltz.d directory
    if not str(bundle_path).endswith('.pltz.d'):
        bundle_path = Path(str(bundle_path) + '.d') if not bundle_path.exists() else bundle_path

    if not bundle_path.exists():
        return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)

    try:
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in bundle_path.rglob('*'):
                if file_path.is_file():
                    rel_path = file_path.relative_to(bundle_path)
                    zf.write(file_path, rel_path)

        zip_buffer.seek(0)
        bundle_name = bundle_path.name.replace('.pltz.d', '')

        response = HttpResponse(zip_buffer.read(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{bundle_name}.pltz"'
        return response

    except Exception as e:
        logger.exception(f"Failed to download pltz bundle: {e}")
        return JsonResponse({"error": str(e)}, status=500)
