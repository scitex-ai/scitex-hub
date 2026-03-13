"""
Scientific Figure Editor - Journal Preset API Views

Serves journal presets from the figrecipe package (no ORM).
Presets are static reference data defined in figrecipe.presets.
"""

from django.http import Http404, JsonResponse
from django.views.decorators.http import require_http_methods
from figrecipe.presets import get_journals, mm_to_pixels
from figrecipe.presets._journals import get_journal_by_id


@require_http_methods(["GET"])
def get_journal_presets(request):
    """Get all available journal presets."""
    presets = get_journals(active_only=True)
    return JsonResponse({"presets": presets})


@require_http_methods(["GET"])
def get_preset_detail(request, preset_id):
    """Get details of a specific journal preset."""
    preset = get_journal_by_id(str(preset_id))
    if not preset:
        raise Http404("Journal preset not found")

    # Enforce maximum canvas dimensions (180mm x 215mm @ 300dpi)
    MAX_WIDTH_PX = 2126  # 180mm @ 300dpi
    MAX_HEIGHT_PX = 2539  # 215mm @ 300dpi

    width_px = min(mm_to_pixels(preset["width_mm"], preset["dpi"]), MAX_WIDTH_PX)
    height_px = (
        min(mm_to_pixels(preset["height_mm"], preset["dpi"]), MAX_HEIGHT_PX)
        if preset["height_mm"]
        else None
    )

    return JsonResponse(
        {
            "id": preset["id"],
            "name": preset["name"],
            "column_type": preset["column_type"],
            "width_mm": preset["width_mm"],
            "height_mm": preset["height_mm"],
            "width_px": width_px,
            "height_px": height_px,
            "dpi": preset["dpi"],
            "font_family": preset["font_family"],
            "font_size_pt": preset["font_size_pt"],
            "line_width_pt": preset["line_width_pt"],
        }
    )
