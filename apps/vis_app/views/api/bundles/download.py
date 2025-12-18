"""
Bundle Download API Views - GET-based download endpoints.

Provides direct download endpoints for figz and pltz bundles as ZIP files.
Also provides figure export generation from bundle components.
"""

import io
import json
import logging
import zipfile
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

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


@login_required
@require_http_methods(["GET"])
def export_figz_image(request):
    """
    Generate and download a composite figure image from figz bundle.

    Delegates to scitex.fig.io for actual compositing logic.

    Query params:
        path: Filesystem path to .figz or .figz.d bundle
        format: Output format (png, jpg, pdf) - default: png
        dpi: Resolution in DPI (default: 300)
        project_owner: (optional) Project owner for path resolution
        project_slug: (optional) Project slug for path resolution

    Returns:
        Image file download
    """
    from ._path_helpers import resolve_bundle_path

    bundle_path = request.GET.get("path")
    output_format = request.GET.get("format", "png").lower()
    dpi = int(request.GET.get("dpi", 300))

    if not bundle_path:
        return JsonResponse({"error": "path parameter required"}, status=400)

    logger.info(f"[export_figz_image] Requested path: {bundle_path}")

    # Resolve relative paths using project context
    resolved_path = resolve_bundle_path(
        bundle_path,
        project_owner=request.GET.get("project_owner"),
        project_slug=request.GET.get("project_slug"),
        user=request.user,
    )
    bundle_path = resolved_path

    logger.info(f"[export_figz_image] Resolved path: {bundle_path}")

    # Check if path exists (try both .figz and .figz.d)
    if not bundle_path.exists():
        # Try .figz.d variant
        figz_d_path = Path(str(bundle_path) + ".d")
        if figz_d_path.exists():
            bundle_path = figz_d_path
        else:
            logger.error(f"[export_figz_image] Bundle not found: {bundle_path}")
            return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)

    logger.info(f"[export_figz_image] Final path: {bundle_path}, format={output_format}, dpi={dpi}")

    try:
        # Delegate to scitex.fig.io for compositing
        from scitex.fig.io import export_figz_bundle

        image_bytes = export_figz_bundle(str(bundle_path), output_format=output_format, dpi=dpi)

        if not image_bytes:
            logger.error("[export_figz_image] export_figz_bundle returned empty bytes")
            return JsonResponse({"error": "Export returned empty result"}, status=500)

        bundle_name = bundle_path.name.replace('.figz.d', '').replace('.figz', '')
        ext = "jpg" if output_format in ("jpg", "jpeg") else output_format
        content_types = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "pdf": "application/pdf"}

        response = HttpResponse(image_bytes, content_type=content_types.get(output_format, "image/png"))
        response['Content-Disposition'] = f'attachment; filename="{bundle_name}.{ext}"'
        logger.info(f"[export_figz_image] Successfully exported {len(image_bytes)} bytes as {output_format}")
        return response

    except ImportError as e:
        logger.error(f"[export_figz_image] scitex.fig.io.export_figz_bundle not available: {e}")
        return JsonResponse({"error": "scitex.fig.io.export_figz_bundle not available"}, status=500)
    except FileNotFoundError as e:
        logger.error(f"[export_figz_image] File not found: {e}")
        return JsonResponse({"error": str(e)}, status=404)
    except ValueError as e:
        logger.error(f"[export_figz_image] Invalid input: {e}")
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        logger.exception(f"[export_figz_image] Failed to export figz image: {e}")
        return JsonResponse({"error": str(e)}, status=500)
