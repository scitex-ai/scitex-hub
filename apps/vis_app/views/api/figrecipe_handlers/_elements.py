"""Element/call figrecipe handlers: calls, update_call, update_element_color."""

import json
import logging

from django.http import JsonResponse

logger = logging.getLogger(__name__)


def _get_call_id(call):
    return getattr(call, "id", None) or getattr(call, "call_id", None)


def handle_calls(request, editor):
    from figrecipe._editor._helpers import to_json_serializable

    if not hasattr(editor.fig, "record") or not editor.fig.record:
        return JsonResponse({})

    calls = {}
    for ax_key, ax_record in editor.fig.record.axes.items():
        for call in getattr(ax_record, "calls", []):
            cid = _get_call_id(call) or f"{ax_key}_{id(call)}"
            try:
                from figrecipe._signatures import get_signature

                sig = get_signature(getattr(call, "function", ""))
            except Exception:
                sig = {}

            calls[cid] = to_json_serializable(
                {
                    "function": getattr(call, "function", "unknown"),
                    "ax_key": ax_key,
                    "args": getattr(call, "args", []),
                    "kwargs": getattr(call, "kwargs", {}),
                    "signature": {
                        "args": sig.get("args", []),
                        "kwargs": {
                            k: v
                            for k, v in sig.get("kwargs", {}).items()
                            if k != "**kwargs"
                        },
                    },
                }
            )
    return JsonResponse(calls)


def handle_single_call(request, editor, call_id):
    """GET /call/<call_id> — get one recorded call's data."""
    from figrecipe._editor._helpers import to_json_serializable

    if hasattr(editor.fig, "record"):
        for ax_key, ax_record in editor.fig.record.axes.items():
            for call in getattr(ax_record, "calls", []):
                if _get_call_id(call) == call_id:
                    try:
                        from figrecipe._signatures import get_signature

                        sig = get_signature(getattr(call, "function", ""))
                    except Exception:
                        sig = {}

                    return JsonResponse(
                        {
                            "call_id": call_id,
                            "function": getattr(call, "function", "unknown"),
                            "ax_key": ax_key,
                            "args": to_json_serializable(getattr(call, "args", [])),
                            "kwargs": to_json_serializable(getattr(call, "kwargs", {})),
                            "signature": {
                                "args": sig.get("args", []),
                                "kwargs": {
                                    k: v
                                    for k, v in sig.get("kwargs", {}).items()
                                    if k != "**kwargs"
                                },
                            },
                        }
                    )

    return JsonResponse({"error": f"Call {call_id} not found"}, status=404)


def handle_update_call(request, editor):
    """POST /update_call — change a call parameter and re-render. WORKFLOW 3."""
    from figrecipe._editor._helpers import render_with_overrides, to_json_serializable

    from ._core import _regen_hitmap

    data = json.loads(request.body) if request.body else {}
    call_id = data.get("call_id")
    param = data.get("param")
    value = data.get("value")

    if not call_id or not param:
        return JsonResponse({"error": "Missing call_id or param"}, status=400)

    updated = False
    if hasattr(editor.fig, "record"):
        for ax_key, ax_record in editor.fig.record.axes.items():
            for call in getattr(ax_record, "calls", []):
                if _get_call_id(call) == call_id:
                    editor.style_overrides.set_call_override(call_id, param, value)

                    is_diagram = getattr(call, "function", "") in (
                        "diagram",
                        "schematic",
                    )
                    if not is_diagram:
                        if value is None or value == "" or value == "null":
                            call.kwargs.pop(param, None)
                        else:
                            call.kwargs[param] = value

                    updated = True
                    break
            if updated:
                break

    if not updated:
        return JsonResponse({"error": f"Call {call_id} not found"}, status=404)

    if editor.recipe_path and hasattr(editor.fig, "save_recipe"):
        try:
            editor.fig.save_recipe(editor.recipe_path)
        except Exception as save_err:
            logger.warning("[Vis] Auto-save failed: %s", save_err)

    try:
        img, bboxes, size = render_with_overrides(
            editor.fig, editor.get_effective_style(), editor.dark_mode
        )
        _regen_hitmap(editor, size)
    except Exception as e:
        logger.exception("[Vis] update_call re-render failed")
        return JsonResponse({"error": f"Re-render failed: {str(e)}"}, status=500)

    updated_call = None
    if hasattr(editor.fig, "record"):
        for ax_key, ax_record in editor.fig.record.axes.items():
            for call in getattr(ax_record, "calls", []):
                if _get_call_id(call) == call_id:
                    updated_call = {"kwargs": to_json_serializable(call.kwargs)}
                    break
            if updated_call:
                break

    return JsonResponse(
        {
            "success": True,
            "image": img,
            "bboxes": bboxes,
            "img_size": {"width": size[0], "height": size[1]},
            "call_id": call_id,
            "param": param,
            "value": value,
            "has_call_overrides": editor.style_overrides.has_call_overrides(),
            "updated_call": updated_call,
        }
    )


def handle_update_element_color(request, editor):
    """POST /update_element_color — direct color edit for un-recorded elements."""
    from figrecipe._editor._helpers import render_with_overrides

    from ._core import _regen_hitmap

    data = json.loads(request.body) if request.body else {}
    element_key = data.get("element_key")
    color = data.get("color")
    ax_index = data.get("ax_index")
    element_type = data.get("element_type")
    layer_index = data.get("layer_index")

    if not element_key or not color:
        return JsonResponse({"error": "Missing element_key or color"}, status=400)

    try:
        mpl_fig = editor.fig.fig if hasattr(editor.fig, "fig") else editor.fig
        axes = mpl_fig.get_axes()

        if ax_index is not None and ax_index < len(axes):
            ax = axes[ax_index]
            updated = False

            if "scatter" in element_key or element_type == "scatter":
                from matplotlib.collections import PathCollection

                for coll in ax.collections:
                    if isinstance(coll, PathCollection):
                        coll.set_facecolors([color])
                        coll.set_edgecolors([color])
                        updated = True
                        break

            elif "line" in element_key or element_type in ("line", "step"):
                for line in ax.get_lines():
                    if line.get_visible():
                        line.set_color(color)
                        line.set_markerfacecolor(color)
                        line.set_markeredgecolor(color)
                        updated = True
                        break

            elif "stackplot" in element_key or element_type == "stackplot":
                from matplotlib.collections import PolyCollection

                poly_idx = 0
                for coll in ax.collections:
                    if isinstance(coll, PolyCollection):
                        if layer_index is None or poly_idx == layer_index:
                            coll.set_facecolors([color])
                            coll.set_edgecolors([color])
                            updated = True
                            if layer_index is not None:
                                break
                        poly_idx += 1

            elif "fill" in element_key or element_type == "fill":
                from matplotlib.collections import PolyCollection

                for coll in ax.collections:
                    if isinstance(coll, PolyCollection):
                        coll.set_facecolors([color])
                        coll.set_edgecolors([color])
                        updated = True
                        break

            elif "bar" in element_key or element_type == "bar":
                for patch in ax.patches:
                    patch.set_facecolor(color)
                    patch.set_edgecolor(color)
                    updated = True

            if not updated:
                return JsonResponse(
                    {"error": f"Could not find element: {element_key}"}, status=404
                )

        img, bboxes, size = render_with_overrides(
            editor.fig, editor.get_effective_style(), editor.dark_mode
        )
        _regen_hitmap(editor, size)
        return JsonResponse(
            {
                "success": True,
                "image": img,
                "bboxes": bboxes,
                "img_size": {"width": size[0], "height": size[1]},
            }
        )
    except Exception as e:
        logger.exception("[Vis] update_element_color failed")
        return JsonResponse({"error": str(e)}, status=500)
