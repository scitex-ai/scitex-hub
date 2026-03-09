"""
Bundle Download API Views - GET-based download endpoints for .fig.zip and .plt.zip bundles.

Supports unified .fig.zip (figure) and .plt.zip (plot) formats.
No directory formats (.figz.d, .pltz.d) are used.
"""

import logging
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def download_figz_bundle(request):
    """Download a .fig.zip figure bundle.

    Query params:
        path: Filesystem path to .fig.zip file

    Returns:
        ZIP file download
    """
    bundle_path = request.GET.get("path")
    if not bundle_path:
        return JsonResponse({"error": "path parameter required"}, status=400)

    bundle_path = Path(bundle_path)
    if not bundle_path.exists():
        return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)

    try:
        with open(bundle_path, "rb") as f:
            content = f.read()
        response = HttpResponse(content, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{bundle_path.name}"'
        return response
    except Exception as e:
        logger.exception(f"Failed to download figz bundle: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def download_figz_d_bundle(request):
    """Redirect: .fig.zip is already the canonical format.

    This endpoint exists for backward compatibility — .figz.d is no
    longer used. Serves the .fig.zip file directly.

    Query params:
        path: Filesystem path to .fig.zip file
    """
    return download_figz_bundle(request)


@login_required
@require_http_methods(["GET"])
def download_pltz_bundle(request):
    """Download a .plt.zip plot bundle.

    Query params:
        path: Filesystem path to .plt.zip file

    Returns:
        ZIP file download
    """
    bundle_path = request.GET.get("path")
    if not bundle_path:
        return JsonResponse({"error": "path parameter required"}, status=400)

    bundle_path = Path(bundle_path)
    if not bundle_path.exists():
        return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)

    try:
        with open(bundle_path, "rb") as f:
            content = f.read()
        response = HttpResponse(content, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{bundle_path.name}"'
        return response
    except Exception as e:
        logger.exception(f"Failed to download pltz bundle: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def export_figz_image(request):
    """Generate and download a composite figure image from .fig.zip bundle.

    Query params:
        path: Filesystem path to .fig.zip bundle
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

    if not bundle_path:
        return JsonResponse({"error": "path parameter required"}, status=400)

    resolved_path = resolve_bundle_path(
        bundle_path,
        project_owner=request.GET.get("project_owner"),
        project_slug=request.GET.get("project_slug"),
        user=request.user,
    )

    if not resolved_path.exists():
        return JsonResponse({"error": f"Bundle not found: {resolved_path}"}, status=404)

    try:
        import figrecipe

        figz = figrecipe.Figz(str(resolved_path))
        image_bytes = figz.render_preview()

        if not image_bytes:
            return JsonResponse({"error": "No preview available in bundle"}, status=500)

        bundle_name = resolved_path.stem
        ext = "jpg" if output_format in ("jpg", "jpeg") else output_format
        content_types = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "pdf": "application/pdf",
        }

        response = HttpResponse(
            image_bytes,
            content_type=content_types.get(output_format, "image/png"),
        )
        response["Content-Disposition"] = f'attachment; filename="{bundle_name}.{ext}"'
        return response

    except FileNotFoundError as e:
        return JsonResponse({"error": str(e)}, status=404)
    except Exception as e:
        logger.exception(f"[export_figz_image] Failed: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def download_stx_bundle(request):
    """Download a bundle file (.fig.zip or .plt.zip).

    Query params:
        path: Filesystem path to bundle

    Returns:
        ZIP file download
    """
    bundle_path = request.GET.get("path")
    if not bundle_path:
        return JsonResponse({"error": "path parameter required"}, status=400)

    bundle_path = Path(bundle_path)

    if not bundle_path.exists():
        return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)

    try:
        with open(bundle_path, "rb") as f:
            content = f.read()
        response = HttpResponse(content, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{bundle_path.name}"'
        return response
    except Exception as e:
        logger.exception(f"Failed to download bundle: {e}")
        return JsonResponse({"error": str(e)}, status=500)
