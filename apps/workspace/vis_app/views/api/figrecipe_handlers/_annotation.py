"""Annotation and caption figrecipe handlers."""

import json
import logging

from django.http import JsonResponse

logger = logging.getLogger(__name__)


def handle_update_annotation_position(request, editor):
    """Move panel labels and text annotations. WORKFLOW 4."""
    from figrecipe._editor._helpers import render_with_overrides

    data = json.loads(request.body) if request.body else {}
    ax_index = data.get("ax_index", 0)
    annotation_type = data.get("annotation_type", "text")
    text_index = data.get("text_index", 0)
    new_x = data.get("x")
    new_y = data.get("y")

    if new_x is None or new_y is None:
        return JsonResponse({"error": "Missing x or y coordinate"}, status=400)

    try:
        mpl_fig = editor.fig.fig if hasattr(editor.fig, "fig") else editor.fig
        axes_list = mpl_fig.get_axes()
        if ax_index >= len(axes_list):
            return JsonResponse(
                {"error": f"Invalid axis index: {ax_index}"}, status=400
            )

        ax = axes_list[ax_index]

        if annotation_type in ("panel_label", "text"):
            if text_index >= len(ax.texts):
                return JsonResponse(
                    {"error": f"Invalid text index: {text_index}"}, status=400
                )

            text_obj = ax.texts[text_index]
            if text_obj.get_transform() == ax.transAxes:
                text_obj.set_position((new_x, new_y))
            else:
                xlim, ylim = ax.get_xlim(), ax.get_ylim()
                text_obj.set_position(
                    (
                        xlim[0] + new_x * (xlim[1] - xlim[0]),
                        ylim[0] + new_y * (ylim[1] - ylim[0]),
                    )
                )

            override_key = f"annotation_pos_ax{ax_index}_text{text_index}"
            editor.style_overrides.manual_overrides[override_key] = {
                "x": new_x,
                "y": new_y,
                "type": annotation_type,
            }

        elif annotation_type == "arrow":
            return JsonResponse({"error": "Arrow drag not yet implemented"}, status=501)

        img, bboxes, size = render_with_overrides(
            editor.fig, editor.get_effective_style(), editor.dark_mode
        )
        return JsonResponse(
            {
                "success": True,
                "image": img,
                "bboxes": bboxes,
                "img_size": {"width": size[0], "height": size[1]},
            }
        )

    except Exception as e:
        logger.exception("[Vis] update_annotation_position failed")
        return JsonResponse({"error": str(e)}, status=500)


def handle_get_captions(request, editor):
    captions = {"figure_caption": "", "panel_captions": {}}
    if hasattr(editor.fig, "record") and editor.fig.record:
        record = editor.fig.record
        captions["figure_caption"] = getattr(record, "caption", "") or ""
        for ax_key, ax_record in getattr(record, "axes", {}).items():
            captions["panel_captions"][ax_key] = getattr(ax_record, "caption", "") or ""
    return JsonResponse(captions)


def handle_update_caption(request, editor):
    """Update figure or panel caption. WORKFLOW 4."""
    data = json.loads(request.body) if request.body else {}
    caption_type = data.get("type")

    if not caption_type:
        return JsonResponse({"error": "Missing caption type"}, status=400)

    try:
        if caption_type == "figure":
            figure_number = data.get("figure_number", 1)
            text = data.get("text", "")
            editor.style_overrides.manual_overrides["caption_figure_number"] = (
                figure_number
            )
            editor.style_overrides.manual_overrides["caption_figure_text"] = text
            if hasattr(editor.fig, "_recipe_metadata"):
                editor.fig._recipe_metadata.caption = text
                editor.fig._recipe_metadata.figure_number = figure_number
            return JsonResponse(
                {
                    "success": True,
                    "caption_type": "figure",
                    "figure_number": figure_number,
                    "text": text,
                }
            )

        elif caption_type == "panel":
            panel_index = data.get("panel_index", 0)
            text = data.get("text", "")
            editor.style_overrides.manual_overrides[
                f"caption_panel_{panel_index}_text"
            ] = text
            editor.style_overrides.manual_overrides["caption_panel_text"] = text
            return JsonResponse(
                {
                    "success": True,
                    "caption_type": "panel",
                    "panel_index": panel_index,
                    "text": text,
                }
            )

        return JsonResponse(
            {"error": f"Unknown caption type: {caption_type}"}, status=400
        )

    except Exception as e:
        logger.exception("[Vis] update_caption failed")
        return JsonResponse({"error": str(e)}, status=500)
