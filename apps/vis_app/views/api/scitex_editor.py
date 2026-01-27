"""
SciTeX Visual Editor API - Real-time figure editing endpoints.

Integrates scitex.vis functionality into the Django /vis/ page:
- Load figure from JSON/CSV files
- Render preview with overrides
- Save manual edits to .manual.json
"""

import json
from pathlib import Path

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .editor_render import render_export_figure, render_figure_preview
from .editor_styles import (
    compute_file_hash,
    extract_defaults_from_metadata,
    get_scitex_defaults,
)


@require_http_methods(["POST"])
@csrf_exempt
def load_figure_json(request):
    """Load a figure from JSON file and return metadata + defaults."""
    try:
        data = json.loads(request.body)
        json_path = Path(data.get("json_path", ""))

        if not json_path.exists():
            return JsonResponse(
                {"error": f"JSON file not found: {json_path}"}, status=404
            )

        with open(json_path, "r") as f:
            metadata = json.load(f)

        csv_path, csv_data, csv_columns = _load_csv_data(
            json_path, data.get("csv_path")
        )

        overrides = get_scitex_defaults()
        overrides.update(extract_defaults_from_metadata(metadata))

        manual_path = json_path.with_suffix(".manual.json")
        if manual_path.exists():
            with open(manual_path, "r") as f:
                manual_overrides = json.load(f).get("overrides", {})
            overrides.update(manual_overrides)

        preview = render_figure_preview(metadata, csv_data, overrides)

        return JsonResponse(
            {
                "success": True,
                "metadata": metadata,
                "overrides": overrides,
                "csv_columns": csv_columns,
                "csv_path": str(csv_path) if csv_path else None,
                "json_path": str(json_path),
                "preview": preview,
            }
        )
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Failed to load figure: {str(e)}"}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def update_preview(request):
    """Update figure preview with new overrides."""
    try:
        data = json.loads(request.body)
        json_path_str = data.get("json_path", "")
        json_path = Path(json_path_str) if json_path_str else None
        overrides = data.get("overrides", {})
        sample_data_str = data.get("sample_data")

        metadata = {}
        if json_path and json_path.exists():
            with open(json_path, "r") as f:
                metadata = json.load(f)

        csv_data = None
        if sample_data_str:
            from io import StringIO

            import pandas as pd

            csv_data = pd.read_csv(StringIO(sample_data_str))
        elif data.get("csv_path"):
            import pandas as pd

            csv_path = Path(data.get("csv_path"))
            if csv_path.exists():
                csv_data = pd.read_csv(csv_path)

        full_overrides = get_scitex_defaults()
        full_overrides.update(extract_defaults_from_metadata(metadata))
        full_overrides.update(overrides)

        preview = render_figure_preview(metadata, csv_data, full_overrides)
        return JsonResponse({"preview": preview, "status": "updated"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def save_manual_overrides(request):
    """Save manual overrides to .manual.json file."""
    try:
        data = json.loads(request.body)
        json_path = Path(data.get("json_path", ""))
        overrides = data.get("overrides", {})

        if not json_path.exists():
            return JsonResponse(
                {"error": f"JSON file not found: {json_path}"}, status=404
            )

        manual_data = {
            "base_file": json_path.name,
            "base_hash": compute_file_hash(json_path),
            "overrides": overrides,
        }

        manual_path = json_path.with_suffix(".manual.json")
        with open(manual_path, "w") as f:
            json.dump(manual_data, f, indent=2)

        return JsonResponse({"status": "saved", "path": str(manual_path)})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def export_figure(request):
    """Export figure in specified format."""
    try:
        data = json.loads(request.body)
        json_path = Path(data.get("json_path", ""))
        overrides = data.get("overrides", {})
        export_format = data.get("format", "png").lower()
        export_dpi = data.get("dpi", 300)

        valid_formats = ["png", "pdf", "svg", "tiff"]
        if export_format not in valid_formats:
            return JsonResponse(
                {"error": f"Invalid format. Valid: {', '.join(valid_formats)}"},
                status=400,
            )

        metadata = {}
        if json_path.exists():
            with open(json_path, "r") as f:
                metadata = json.load(f)

        csv_data = None
        if data.get("csv_path"):
            import pandas as pd

            csv_path = Path(data.get("csv_path"))
            if csv_path.exists():
                csv_data = pd.read_csv(csv_path)

        full_overrides = get_scitex_defaults()
        full_overrides.update(extract_defaults_from_metadata(metadata))
        full_overrides.update(overrides)
        full_overrides["dpi"] = export_dpi

        export_data = render_export_figure(
            csv_data, full_overrides, export_format, export_dpi
        )

        content_types = {
            "png": "image/png",
            "pdf": "application/pdf",
            "svg": "image/svg+xml",
            "tiff": "image/tiff",
        }
        response = HttpResponse(export_data, content_type=content_types[export_format])
        response["Content-Disposition"] = (
            f'attachment; filename="{json_path.stem}.{export_format}"'
        )
        return response
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_scitex_style(request):
    """Get SCITEX_STYLE configuration for the frontend."""
    try:
        defaults = get_scitex_defaults()
        return JsonResponse({"style": defaults, "defaults": defaults})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def _load_csv_data(json_path, csv_path_str):
    """Load CSV data from path or auto-detect."""
    import pandas as pd

    csv_path = None
    csv_data = None
    csv_columns = []

    if csv_path_str:
        csv_path = Path(csv_path_str)
    else:
        csv_sibling = json_path.with_suffix(".csv")
        if csv_sibling.exists():
            csv_path = csv_sibling
        elif json_path.parent.name == "json":
            csv_organized = json_path.parent.parent / "csv" / f"{json_path.stem}.csv"
            if csv_organized.exists():
                csv_path = csv_organized

    if csv_path and csv_path.exists():
        csv_data = pd.read_csv(csv_path)
        csv_columns = csv_data.columns.tolist()

    return csv_path, csv_data, csv_columns
