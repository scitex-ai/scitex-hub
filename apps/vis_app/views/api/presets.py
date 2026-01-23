"""
Scientific Figure Editor - Journal Preset API Views
REST API endpoints for journal preset management
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404

from apps.vis_app.models import JournalPreset


@require_http_methods(["GET"])
def get_journal_presets(request):
    """Get all available journal presets"""
    presets = JournalPreset.objects.filter(is_active=True).values(
        "id",
        "name",
        "column_type",
        "width_mm",
        "height_mm",
        "dpi",
        "font_family",
        "font_size_pt",
        "line_width_pt",
    )

    return JsonResponse({"presets": list(presets)})


@require_http_methods(["GET"])
def get_preset_detail(request, preset_id):
    """Get details of a specific journal preset"""
    preset = get_object_or_404(JournalPreset, id=preset_id, is_active=True)

    # Calculate pixel dimensions
    def mm_to_pixels(mm, dpi):
        inches = mm / 25.4
        return int(inches * dpi)

    # Enforce maximum canvas dimensions (180mm × 215mm @ 300dpi)
    MAX_WIDTH_PX = 2126  # 180mm @ 300dpi
    MAX_HEIGHT_PX = 2539  # 215mm @ 300dpi

    width_px = min(mm_to_pixels(preset.width_mm, preset.dpi), MAX_WIDTH_PX)
    height_px = min(mm_to_pixels(preset.height_mm, preset.dpi), MAX_HEIGHT_PX) if preset.height_mm else None

    return JsonResponse({
        "id": preset.id,
        "name": preset.name,
        "column_type": preset.column_type,
        "width_mm": preset.width_mm,
        "height_mm": preset.height_mm,
        "width_px": width_px,
        "height_px": height_px,
        "dpi": preset.dpi,
        "font_family": preset.font_family,
        "font_size_pt": preset.font_size_pt,
        "line_width_pt": preset.line_width_pt,
    })
