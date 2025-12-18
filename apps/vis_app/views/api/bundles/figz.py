"""
FigzBundle API Views - CRUD endpoints for figz bundle operations.

Provides REST operations for multi-panel figure bundles (.figz).
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods

from ....models import PltzBundle, FigzBundle, FigzPanel
from ....services.figz import FigzService

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def list_figz_bundles(request):
    """
    List all figz bundles for current user.

    Query params:
        layout: Filter by layout (1x1, 2x2, etc.)
        search: Search in name/description

    Returns:
        JSON array of bundle summaries
    """
    bundles = FigzBundle.objects.filter(owner=request.user)

    layout = request.GET.get("layout")
    if layout:
        bundles = bundles.filter(layout=layout)

    search = request.GET.get("search")
    if search:
        bundles = bundles.filter(name__icontains=search)

    bundle_list = []
    for bundle in bundles:
        bundle_list.append({
            "id": str(bundle.id),
            "name": bundle.name,
            "slug": bundle.slug,
            "layout": bundle.layout,
            "panel_count": bundle.get_panel_count(),
            "width_mm": bundle.width_mm,
            "height_mm": bundle.height_mm,
            "description": bundle.description,
            "preview_url": f"/vis/api/bundles/figz/{bundle.id}/preview/",
            "created_at": bundle.created_at.isoformat(),
            "updated_at": bundle.updated_at.isoformat(),
        })

    return JsonResponse({"bundles": bundle_list})


@login_required
@require_http_methods(["POST"])
def create_figz_bundle(request):
    """
    Create a new figz bundle.

    Request body:
        name: Figure title
        layout: Layout string (1x1, 2x1, 2x2, etc.)
        spec: FigureSpec dictionary
        style: FigureStyle dictionary
        panels: Dict mapping labels to pltz bundle IDs or inline specs
        width_mm: Figure width in mm (optional)
        height_mm: Figure height in mm (optional)
        description: Description text (optional)

    Returns:
        Created bundle info
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = data.get("name")
    if not name:
        return JsonResponse({"error": "name is required"}, status=400)

    spec = data.get("spec", {})
    style = data.get("style", {})
    layout = data.get("layout", "1x1")

    # Resolve panel sources
    panels = {}
    panel_data = data.get("panels", {})
    for label, panel_ref in panel_data.items():
        if isinstance(panel_ref, str):
            try:
                pltz_bundle = PltzBundle.objects.get(id=panel_ref, owner=request.user)
                panels[label] = pltz_bundle.bundle_path
            except PltzBundle.DoesNotExist:
                return JsonResponse(
                    {"error": f"Panel {label}: pltz bundle {panel_ref} not found"},
                    status=400
                )
        else:
            panels[label] = panel_ref

    try:
        result = FigzService.save_bundle(
            spec=spec,
            style=style,
            panels=panels,
            user_id=request.user.id,
            name=name,
        )

        bundle = FigzBundle.objects.create(
            owner=request.user,
            name=name,
            slug=slugify(name),
            bundle_path=result["path"],
            is_zip=result.get("is_zip", False),
            spec=spec,
            style=style,
            layout=layout,
            width_mm=data.get("width_mm", 170.0),
            height_mm=data.get("height_mm"),
            description=data.get("description", ""),
            tags=data.get("tags", []),
        )

        # Create panel relationships
        for label, panel_ref in panel_data.items():
            if isinstance(panel_ref, str):
                try:
                    pltz_bundle = PltzBundle.objects.get(id=panel_ref)
                    positions = FigzService.get_layout_positions(layout)
                    pos = positions.get(label, {"x": 0, "y": 0, "width": 1, "height": 1})

                    FigzPanel.objects.create(
                        figure=bundle,
                        plot=pltz_bundle,
                        label=label,
                        order=ord(label) - ord("A"),
                        x=pos["x"],
                        y=pos["y"],
                        width=pos["width"],
                        height=pos["height"],
                    )
                except PltzBundle.DoesNotExist:
                    pass

        return JsonResponse({
            "id": str(bundle.id),
            "name": bundle.name,
            "slug": bundle.slug,
            "path": result["path"],
            "layout": bundle.layout,
            "panel_count": bundle.get_panel_count(),
        }, status=201)

    except Exception as e:
        logger.exception(f"Failed to create figz bundle: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_figz_bundle(request, bundle_id):
    """Get figz bundle details including spec, style, panels, and metadata."""
    try:
        bundle = FigzBundle.objects.get(id=bundle_id, owner=request.user)
    except FigzBundle.DoesNotExist:
        return JsonResponse({"error": "Bundle not found"}, status=404)

    try:
        bundle_data = FigzService.load_bundle(bundle.bundle_path)
    except Exception as e:
        logger.warning(f"Failed to load bundle from disk: {e}")
        bundle_data = {}

    panels = []
    for figz_panel in bundle.figz_panels.all():
        panels.append({
            "label": figz_panel.label,
            "plot_id": str(figz_panel.plot.id),
            "plot_name": figz_panel.plot.name,
            "x": figz_panel.x,
            "y": figz_panel.y,
            "width": figz_panel.width,
            "height": figz_panel.height,
            "style_overrides": figz_panel.style_overrides,
        })

    return JsonResponse({
        "id": str(bundle.id),
        "name": bundle.name,
        "slug": bundle.slug,
        "layout": bundle.layout,
        "width_mm": bundle.width_mm,
        "height_mm": bundle.height_mm,
        "description": bundle.description,
        "tags": bundle.tags,
        "spec": bundle_data.get("spec", bundle.spec),
        "style": bundle_data.get("style", bundle.style),
        "panels": panels,
        "panel_data": bundle_data.get("panels", {}),
        "exports": bundle_data.get("exports"),
        "created_at": bundle.created_at.isoformat(),
        "updated_at": bundle.updated_at.isoformat(),
    })


@login_required
@require_http_methods(["PUT", "PATCH"])
def update_figz_bundle(request, bundle_id):
    """Update figz bundle spec, style, or metadata."""
    try:
        bundle = FigzBundle.objects.get(id=bundle_id, owner=request.user)
    except FigzBundle.DoesNotExist:
        return JsonResponse({"error": "Bundle not found"}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if "name" in data:
        bundle.name = data["name"]
        bundle.slug = slugify(data["name"])
    if "spec" in data:
        bundle.spec = data["spec"]
    if "style" in data:
        bundle.style = data["style"]
    if "layout" in data:
        bundle.layout = data["layout"]
    if "width_mm" in data:
        bundle.width_mm = data["width_mm"]
    if "height_mm" in data:
        bundle.height_mm = data["height_mm"]
    if "description" in data:
        bundle.description = data["description"]
    if "tags" in data:
        bundle.tags = data["tags"]

    bundle.save()

    return JsonResponse({
        "id": str(bundle.id),
        "name": bundle.name,
        "updated": True,
    })


@login_required
@require_http_methods(["DELETE"])
def delete_figz_bundle(request, bundle_id):
    """Delete a figz bundle."""
    try:
        bundle = FigzBundle.objects.get(id=bundle_id, owner=request.user)
    except FigzBundle.DoesNotExist:
        return JsonResponse({"error": "Bundle not found"}, status=404)

    FigzService.delete_bundle(bundle.bundle_path)
    bundle.delete()

    return JsonResponse({"deleted": True})


@login_required
@require_http_methods(["GET"])
def get_figz_preview(request, bundle_id):
    """Get figz bundle composed figure preview."""
    try:
        bundle = FigzBundle.objects.get(id=bundle_id, owner=request.user)
    except FigzBundle.DoesNotExist:
        return JsonResponse({"error": "Bundle not found"}, status=404)

    image_type = request.GET.get("type", "png")
    image_data = FigzService.get_preview_image(bundle.bundle_path, image_type)

    if image_data:
        return HttpResponse(image_data, content_type="image/png")

    return JsonResponse({"error": "Preview not found"}, status=404)


@login_required
@require_http_methods(["POST"])
def add_figz_panel(request, bundle_id):
    """Add a panel to a figz bundle."""
    try:
        bundle = FigzBundle.objects.get(id=bundle_id, owner=request.user)
    except FigzBundle.DoesNotExist:
        return JsonResponse({"error": "Bundle not found"}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    label = data.get("label")
    if not label or label not in "ABCDEFGH":
        return JsonResponse({"error": "Valid label (A-H) required"}, status=400)

    if bundle.figz_panels.filter(label=label).exists():
        return JsonResponse({"error": f"Panel {label} already exists"}, status=400)

    pltz_id = data.get("pltz_id")
    if pltz_id:
        try:
            pltz_bundle = PltzBundle.objects.get(id=pltz_id, owner=request.user)
            panel_source = pltz_bundle.bundle_path
        except PltzBundle.DoesNotExist:
            return JsonResponse({"error": "Pltz bundle not found"}, status=404)
    else:
        panel_source = {
            "spec": data.get("spec", {}),
            "style": data.get("style", {}),
            "data_csv": data.get("data_csv"),
        }
        pltz_bundle = None

    FigzService.add_panel(bundle.bundle_path, label, panel_source)

    if pltz_bundle:
        positions = FigzService.get_layout_positions(bundle.layout)
        pos = positions.get(label, {"x": 0, "y": 0, "width": 1, "height": 1})

        FigzPanel.objects.create(
            figure=bundle,
            plot=pltz_bundle,
            label=label,
            order=ord(label) - ord("A"),
            x=pos["x"],
            y=pos["y"],
            width=pos["width"],
            height=pos["height"],
        )

    return JsonResponse({
        "label": label,
        "added": True,
        "panel_count": bundle.get_panel_count(),
    })


@login_required
@require_http_methods(["DELETE"])
def remove_figz_panel(request, bundle_id, label):
    """Remove a panel from a figz bundle."""
    try:
        bundle = FigzBundle.objects.get(id=bundle_id, owner=request.user)
    except FigzBundle.DoesNotExist:
        return JsonResponse({"error": "Bundle not found"}, status=404)

    FigzService.remove_panel(bundle.bundle_path, label)
    bundle.figz_panels.filter(label=label).delete()

    return JsonResponse({
        "label": label,
        "removed": True,
        "panel_count": bundle.get_panel_count(),
    })


@login_required
@require_http_methods(["GET"])
def get_figz_panel_previews(request, bundle_id):
    """Get preview images for all panels."""
    try:
        bundle = FigzBundle.objects.get(id=bundle_id, owner=request.user)
    except FigzBundle.DoesNotExist:
        return JsonResponse({"error": "Bundle not found"}, status=404)

    previews = FigzService.get_panel_previews(bundle.bundle_path)

    return JsonResponse({"panels": previews})


@login_required
@require_http_methods(["GET"])
def get_layout_options(request):
    """Get available layout options with panel positions."""
    layouts = {
        "1x1": {
            "name": "Single Panel",
            "positions": FigzService.get_layout_positions("1x1"),
        },
        "2x1": {
            "name": "Two Horizontal",
            "positions": FigzService.get_layout_positions("2x1"),
        },
        "1x2": {
            "name": "Two Vertical",
            "positions": FigzService.get_layout_positions("1x2"),
        },
        "2x2": {
            "name": "Four Panel Grid",
            "positions": FigzService.get_layout_positions("2x2"),
        },
        "1x3": {
            "name": "Three Horizontal",
            "positions": FigzService.get_layout_positions("1x3"),
        },
        "3x1": {
            "name": "Three Vertical",
            "positions": FigzService.get_layout_positions("3x1"),
        },
        "2x3": {
            "name": "Six Panel Grid",
            "positions": FigzService.get_layout_positions("2x3"),
        },
    }

    return JsonResponse({"layouts": layouts})
