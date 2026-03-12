"""Core figrecipe handlers: preview, ping, update, hitmap."""

import json

from django.http import JsonResponse


def _regen_hitmap(editor, img_size):
    """Regenerate hitmap after any render that changes figure content."""
    from figrecipe._editor._hitmap import generate_hitmap, hitmap_to_base64

    editor._main_img_size = img_size
    hitmap_img, color_map = generate_hitmap(editor.fig, dpi=150, target_size=img_size)
    editor._color_map = color_map
    editor._hitmap_base64 = hitmap_to_base64(hitmap_img)
    editor._hitmap_generated = True


def handle_preview(request, editor):
    from figrecipe._editor._helpers import render_with_overrides

    img, bboxes, size = render_with_overrides(
        editor.fig, editor.get_effective_style(), editor.dark_mode
    )
    return JsonResponse(
        {
            "image": img,
            "bboxes": bboxes,
            "img_size": {"width": size[0], "height": size[1]},
        }
    )


def handle_ping(request, editor):
    return JsonResponse({"status": "ok"})


def handle_update(request, editor):
    from figrecipe._editor._helpers import render_with_overrides

    data = json.loads(request.body) if request.body else {}
    editor.overrides.update(data.get("overrides", {}))

    new_dark = data.get("dark_mode")
    if new_dark is not None and new_dark != editor.dark_mode:
        editor.dark_mode = new_dark

    img, bboxes, size = render_with_overrides(
        editor.fig, editor.get_effective_style(), editor.dark_mode
    )
    return JsonResponse(
        {
            "image": img,
            "bboxes": bboxes,
            "img_size": {"width": size[0], "height": size[1]},
        }
    )


def handle_hitmap(request, editor):
    if not editor._hitmap_generated:
        from figrecipe._editor._hitmap import generate_hitmap, hitmap_to_base64

        hitmap_img, editor._color_map = generate_hitmap(editor.fig)
        editor._hitmap_base64 = hitmap_to_base64(hitmap_img)
        editor._hitmap_generated = True

    return JsonResponse(
        {"image": editor._hitmap_base64, "color_map": editor._color_map}
    )
