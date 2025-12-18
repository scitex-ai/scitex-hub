"""
Style Preset API - User and project-level style configuration

Provides endpoints for:
- Managing user-level style presets (database)
- Loading/saving project-level YAML configs
- Merging SCITEX_STYLE with user preferences
"""

import json
import yaml
from pathlib import Path
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from apps.vis_app.models import UserStylePreset
from scitex.fig.editor._defaults import get_scitex_defaults
from scitex.plt.styles import SCITEX_STYLE


@require_http_methods(["GET"])
@login_required
def list_style_presets(request):
    """
    List all style presets for the current user.

    GET /vis/api/style-presets/

    Response:
    {
        "presets": [
            {
                "id": "uuid",
                "name": "My Custom Style",
                "description": "...",
                "is_active": true,
                "is_builtin": false,
                "created_at": "...",
                "updated_at": "..."
            },
            ...
        ],
        "active_preset_id": "uuid" or null
    }
    """
    try:
        presets = UserStylePreset.objects.filter(user=request.user)

        preset_list = [
            {
                "id": str(preset.id),
                "name": preset.name,
                "description": preset.description,
                "is_active": preset.is_active,
                "is_builtin": preset.is_builtin,
                "created_at": preset.created_at.isoformat(),
                "updated_at": preset.updated_at.isoformat(),
            }
            for preset in presets
        ]

        active_preset = presets.filter(is_active=True).first()
        active_preset_id = str(active_preset.id) if active_preset else None

        return JsonResponse(
            {"presets": preset_list, "active_preset_id": active_preset_id}
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
@login_required
def get_style_preset(request, preset_id):
    """
    Get a specific style preset.

    GET /vis/api/style-presets/<preset_id>/

    Response:
    {
        "preset": {...},
        "merged_style": {...}  // SCITEX_STYLE + user overrides
    }
    """
    try:
        preset = UserStylePreset.objects.get(id=preset_id, user=request.user)

        # Merge SCITEX_STYLE with user overrides
        merged_style = dict(SCITEX_STYLE) if SCITEX_STYLE else {}
        merged_style.update(preset.style_config)

        return JsonResponse(
            {
                "preset": {
                    "id": str(preset.id),
                    "name": preset.name,
                    "description": preset.description,
                    "style_config": preset.style_config,
                    "is_active": preset.is_active,
                    "is_builtin": preset.is_builtin,
                },
                "merged_style": merged_style,
            }
        )

    except UserStylePreset.DoesNotExist:
        return JsonResponse({"error": "Preset not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
@login_required
def create_style_preset(request):
    """
    Create a new style preset.

    POST /vis/api/style-presets/

    Request body:
    {
        "name": "My Custom Style",
        "description": "Optional description",
        "style_config": {...}  // YAML-compatible style overrides
    }

    Response:
    {
        "preset_id": "uuid",
        "message": "Preset created successfully"
    }
    """
    try:
        data = json.loads(request.body)

        name = data.get("name")
        if not name:
            return JsonResponse({"error": "Name is required"}, status=400)

        # Check for duplicate names
        if UserStylePreset.objects.filter(user=request.user, name=name).exists():
            return JsonResponse(
                {"error": f"Preset with name '{name}' already exists"}, status=400
            )

        preset = UserStylePreset.objects.create(
            user=request.user,
            name=name,
            description=data.get("description", ""),
            style_config=data.get("style_config", {}),
            is_active=False,
        )

        return JsonResponse(
            {
                "preset_id": str(preset.id),
                "message": "Preset created successfully",
            },
            status=201,
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["PUT", "PATCH"])
@csrf_exempt
@login_required
def update_style_preset(request, preset_id):
    """
    Update an existing style preset.

    PUT/PATCH /vis/api/style-presets/<preset_id>/

    Request body:
    {
        "name": "Updated Name",
        "description": "Updated description",
        "style_config": {...}
    }
    """
    try:
        preset = UserStylePreset.objects.get(id=preset_id, user=request.user)

        if preset.is_builtin:
            return JsonResponse(
                {"error": "Cannot modify built-in presets"}, status=403
            )

        data = json.loads(request.body)

        if "name" in data:
            # Check for duplicate names (excluding current preset)
            if (
                UserStylePreset.objects.filter(user=request.user, name=data["name"])
                .exclude(id=preset_id)
                .exists()
            ):
                return JsonResponse(
                    {"error": f"Preset with name '{data['name']}' already exists"},
                    status=400,
                )
            preset.name = data["name"]

        if "description" in data:
            preset.description = data["description"]

        if "style_config" in data:
            preset.style_config = data["style_config"]

        preset.save()

        return JsonResponse({"message": "Preset updated successfully"})

    except UserStylePreset.DoesNotExist:
        return JsonResponse({"error": "Preset not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["DELETE"])
@csrf_exempt
@login_required
def delete_style_preset(request, preset_id):
    """
    Delete a style preset.

    DELETE /vis/api/style-presets/<preset_id>/
    """
    try:
        preset = UserStylePreset.objects.get(id=preset_id, user=request.user)

        if preset.is_builtin:
            return JsonResponse(
                {"error": "Cannot delete built-in presets"}, status=403
            )

        preset.delete()

        return JsonResponse({"message": "Preset deleted successfully"})

    except UserStylePreset.DoesNotExist:
        return JsonResponse({"error": "Preset not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
@login_required
def activate_style_preset(request, preset_id):
    """
    Activate a style preset (sets as current).

    POST /vis/api/style-presets/<preset_id>/activate/
    """
    try:
        preset = UserStylePreset.objects.get(id=preset_id, user=request.user)
        preset.activate()

        return JsonResponse(
            {"message": f"Preset '{preset.name}' activated successfully"}
        )

    except UserStylePreset.DoesNotExist:
        return JsonResponse({"error": "Preset not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
@login_required
def export_preset_yaml(request, preset_id):
    """
    Export a style preset as YAML file.

    POST /vis/api/style-presets/<preset_id>/export/

    Response: YAML file download
    """
    try:
        preset = UserStylePreset.objects.get(id=preset_id, user=request.user)

        # Create YAML content
        yaml_content = yaml.dump(
            preset.style_config, default_flow_style=False, sort_keys=False
        )

        response = HttpResponse(yaml_content, content_type="application/x-yaml")
        filename = f"{preset.name.replace(' ', '_').lower()}.yaml"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except UserStylePreset.DoesNotExist:
        return JsonResponse({"error": "Preset not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
@login_required
def import_preset_yaml(request):
    """
    Import a style preset from YAML file.

    POST /vis/api/style-presets/import/

    Request: multipart/form-data with 'file' field

    Response:
    {
        "preset_id": "uuid",
        "message": "Preset imported successfully"
    }
    """
    try:
        if "file" not in request.FILES:
            return JsonResponse({"error": "No file provided"}, status=400)

        yaml_file = request.FILES["file"]
        yaml_content = yaml_file.read().decode("utf-8")

        # Parse YAML
        style_config = yaml.safe_load(yaml_content)

        if not isinstance(style_config, dict):
            return JsonResponse({"error": "Invalid YAML format"}, status=400)

        # Generate name from filename
        name = Path(yaml_file.name).stem.replace("_", " ").title()

        # Check for duplicate names
        counter = 1
        original_name = name
        while UserStylePreset.objects.filter(user=request.user, name=name).exists():
            name = f"{original_name} ({counter})"
            counter += 1

        # Create preset
        preset = UserStylePreset.objects.create(
            user=request.user,
            name=name,
            description=f"Imported from {yaml_file.name}",
            style_config=style_config,
            is_active=False,
        )

        return JsonResponse(
            {
                "preset_id": str(preset.id),
                "message": f"Preset '{name}' imported successfully",
            },
            status=201,
        )

    except yaml.YAMLError as e:
        return JsonResponse({"error": f"YAML parse error: {str(e)}"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_active_style(request):
    """
    Get the currently active style for the user.
    If no user or no active preset, returns default SCITEX_STYLE.

    GET /vis/api/style-presets/active/

    Response:
    {
        "preset_name": "SciTeX Default" or "My Custom Style",
        "style": {...},  // Merged SCITEX_STYLE + overrides
        "defaults": {...}  // Computed defaults for editor
    }
    """
    try:
        base_style = dict(SCITEX_STYLE) if SCITEX_STYLE else {}
        preset_name = "SciTeX Default"

        # If user is authenticated, check for active preset
        if request.user.is_authenticated:
            active_preset = UserStylePreset.objects.filter(
                user=request.user, is_active=True
            ).first()

            if active_preset:
                base_style.update(active_preset.style_config)
                preset_name = active_preset.name

        # Compute defaults
        defaults = get_scitex_defaults()

        return JsonResponse(
            {"preset_name": preset_name, "style": base_style, "defaults": defaults}
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
