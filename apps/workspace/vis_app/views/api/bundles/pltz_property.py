"""
PltzBundle Property Update API - Endpoint for updating individual properties.

Provides fine-grained property updates without full spec replacement.
"""

import json
import logging
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def update_pltz_property(request):
    """
    Update a single property in a pltz bundle without full spec replacement.

    Request body:
        path: Path to pltz bundle (absolute or relative to project)
        property_path: Dot-separated path (e.g., "spec.axes.xlabel")
        value: New value for the property
        project_owner: Project owner (optional, for path resolution)
        project_slug: Project slug (optional, for path resolution)

    Returns:
        Updated spec or style fragment
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    pltz_path = data.get("path")
    property_path = data.get("property_path")
    value = data.get("value")

    if not pltz_path or not property_path:
        return JsonResponse(
            {"error": "path and property_path are required"}, status=400
        )

    # Resolve path if project context provided
    if data.get("project_owner") and data.get("project_slug"):
        from apps.infra.project_app.models import Project

        try:
            project = Project.objects.get(
                owner__username=data["project_owner"], slug=data["project_slug"]
            )
            project_root = project.get_local_path()
            full_path = project_root / pltz_path
        except Project.DoesNotExist:
            return JsonResponse(
                {
                    "error": f"Project not found: {data['project_owner']}/{data['project_slug']}"
                },
                status=404,
            )
    else:
        full_path = Path(pltz_path)

    if not full_path.exists():
        return JsonResponse({"error": f"Bundle not found: {full_path}"}, status=404)

    try:
        import figrecipe

        pltz = figrecipe.Pltz(full_path)

        # Parse property path (e.g., "spec.axes.xlabel" → spec["axes"]["xlabel"])
        parts = property_path.split(".")
        if len(parts) == 0:
            return JsonResponse({"error": "Invalid property_path"}, status=400)

        # Determine which root object to modify (spec or style)
        root_key = parts[0]
        if root_key not in ["spec", "style"]:
            return JsonResponse(
                {
                    "error": f"Property path must start with 'spec' or 'style', got '{root_key}'"
                },
                status=400,
            )

        # Get root object
        root_obj = pltz.spec if root_key == "spec" else pltz.style

        # Navigate to parent and update property
        current = root_obj
        for part in parts[1:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the value
        final_key = parts[-1]
        current[final_key] = value

        # Save back to bundle
        if root_key == "spec":
            pltz.spec = root_obj
        else:
            pltz.style = root_obj
        pltz.save()

        logger.info(f"Updated {property_path} in {full_path}")

        return JsonResponse(
            {
                "success": True,
                "path": str(full_path),
                "property_path": property_path,
                "value": value,
                "updated_root": root_obj,
            }
        )

    except Exception as e:
        logger.exception(f"Failed to update pltz property: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def batch_update_pltz_properties(request):
    """
    Update multiple properties in a pltz bundle at once.

    Request body:
        path: Path to pltz bundle
        updates: List of {property_path, value} dicts
        project_owner: Project owner (optional)
        project_slug: Project slug (optional)

    Returns:
        Updated spec and style
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    pltz_path = data.get("path")
    updates = data.get("updates", [])

    if not pltz_path or not updates:
        return JsonResponse({"error": "path and updates are required"}, status=400)

    # Resolve path
    if data.get("project_owner") and data.get("project_slug"):
        from apps.infra.project_app.models import Project

        try:
            project = Project.objects.get(
                owner__username=data["project_owner"], slug=data["project_slug"]
            )
            project_root = project.get_local_path()
            full_path = project_root / pltz_path
        except Project.DoesNotExist:
            return JsonResponse({"error": "Project not found"}, status=404)
    else:
        full_path = Path(pltz_path)

    if not full_path.exists():
        return JsonResponse({"error": f"Bundle not found: {full_path}"}, status=404)

    try:
        import figrecipe

        pltz = figrecipe.Pltz(full_path)

        # Apply all updates
        for update in updates:
            property_path = update.get("property_path")
            value = update.get("value")

            if not property_path:
                continue

            parts = property_path.split(".")
            root_key = parts[0]

            if root_key not in ["spec", "style"]:
                continue

            root_obj = pltz.spec if root_key == "spec" else pltz.style
            current = root_obj

            # Navigate and update
            for part in parts[1:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            current[parts[-1]] = value

            # Save back
            if root_key == "spec":
                pltz.spec = root_obj
            else:
                pltz.style = root_obj

        pltz.save()

        logger.info(f"Batch updated {len(updates)} properties in {full_path}")

        return JsonResponse(
            {
                "success": True,
                "path": str(full_path),
                "updated_count": len(updates),
                "spec": pltz.spec,
                "style": pltz.style,
            }
        )

    except Exception as e:
        logger.exception(f"Failed to batch update pltz properties: {e}")
        return JsonResponse({"error": str(e)}, status=500)
