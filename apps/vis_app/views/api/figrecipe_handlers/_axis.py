"""Axis/label/legend figrecipe handlers."""

import json
import logging

from django.http import JsonResponse

logger = logging.getLogger(__name__)


def handle_get_labels(request, editor):
    mpl_fig = editor.fig.fig if hasattr(editor.fig, "fig") else editor.fig
    axes = mpl_fig.get_axes()
    labels = {"title": "", "xlabel": "", "ylabel": "", "suptitle": ""}
    if axes:
        labels["title"] = axes[0].get_title()
        labels["xlabel"] = axes[0].get_xlabel()
        labels["ylabel"] = axes[0].get_ylabel()
    if mpl_fig._suptitle:
        labels["suptitle"] = mpl_fig._suptitle.get_text()
    return JsonResponse(labels)


def handle_update_label(request, editor):
    from figrecipe._editor._helpers import render_with_overrides

    data = json.loads(request.body) if request.body else {}
    label_type = data.get("label_type")
    text = data.get("text", "")
    ax_index = data.get("ax_index", 0)

    if not label_type:
        return JsonResponse({"error": "Missing label_type"}, status=400)

    mpl_fig = editor.fig.fig if hasattr(editor.fig, "fig") else editor.fig
    axes = mpl_fig.get_axes()
    if not axes:
        return JsonResponse({"error": "No axes found"}, status=400)

    ax = axes[min(ax_index, len(axes) - 1)]
    if label_type == "title":
        ax.set_title(text)
    elif label_type == "xlabel":
        ax.set_xlabel(text)
    elif label_type == "ylabel":
        ax.set_ylabel(text)
    elif label_type == "suptitle":
        if text:
            mpl_fig.suptitle(text)
        elif mpl_fig._suptitle:
            mpl_fig._suptitle.set_text("")
    else:
        return JsonResponse({"error": f"Unknown label_type: {label_type}"}, status=400)

    editor.style_overrides.manual_overrides[f"label_{label_type}"] = text
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


def handle_update_axis_type(request, editor):
    import matplotlib
    from figrecipe._editor._helpers import render_with_overrides

    data = json.loads(request.body) if request.body else {}
    axis = data.get("axis")
    axis_type = data.get("type")
    labels = data.get("labels", [])
    ax_index = data.get("ax_index", 0)

    if not axis or not axis_type:
        return JsonResponse({"error": "Missing axis or type"}, status=400)

    mpl_fig = editor.fig.fig if hasattr(editor.fig, "fig") else editor.fig
    axes_list = mpl_fig.get_axes()
    if not axes_list:
        return JsonResponse({"error": "No axes found"}, status=400)

    ax = axes_list[min(ax_index, len(axes_list) - 1)]

    try:
        if axis == "x":
            if axis_type == "categorical" and labels:
                ax.set_xticks(list(range(len(labels))))
                ax.set_xticklabels(labels)
            else:
                ax.xaxis.set_major_locator(matplotlib.ticker.AutoLocator())
                ax.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
        elif axis == "y":
            if axis_type == "categorical" and labels:
                ax.set_yticks(list(range(len(labels))))
                ax.set_yticklabels(labels)
            else:
                ax.yaxis.set_major_locator(matplotlib.ticker.AutoLocator())
                ax.yaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())

        editor.style_overrides.manual_overrides[f"axis_{axis}_type"] = axis_type
        if labels:
            editor.style_overrides.manual_overrides[f"axis_{axis}_labels"] = labels

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
        logger.exception("[Vis] update_axis_type failed")
        return JsonResponse({"error": str(e)}, status=500)


def handle_get_axis_info(request, editor):
    mpl_fig = editor.fig.fig if hasattr(editor.fig, "fig") else editor.fig
    axes = mpl_fig.get_axes()
    info = {
        "x_type": "numerical",
        "y_type": "numerical",
        "x_labels": [],
        "y_labels": [],
    }
    if axes:
        x_labels = [t.get_text() for t in axes[0].get_xticklabels()]
        if x_labels and any(t for t in x_labels):
            info["x_type"] = "categorical"
            info["x_labels"] = x_labels
        y_labels = [t.get_text() for t in axes[0].get_yticklabels()]
        if y_labels and any(t for t in y_labels):
            info["y_type"] = "categorical"
            info["y_labels"] = y_labels
    return JsonResponse(info)


def handle_update_legend_position(request, editor):
    from figrecipe._editor._helpers import render_with_overrides

    data = json.loads(request.body) if request.body else {}
    loc = data.get("loc")
    x = data.get("x")
    y = data.get("y")
    visible = data.get("visible")
    ax_index = data.get("ax_index", 0)

    mpl_fig = editor.fig.fig if hasattr(editor.fig, "fig") else editor.fig
    axes_list = mpl_fig.get_axes()
    if not axes_list:
        return JsonResponse({"error": "No axes found"}, status=400)

    ax = axes_list[min(ax_index, len(axes_list) - 1)]
    legend = ax.get_legend()
    if legend is None:
        return JsonResponse({"error": "No legend found on this axes"}, status=400)

    try:
        if visible is not None:
            legend.set_visible(visible)
            editor.style_overrides.manual_overrides["legend_visible"] = visible

        if loc is not None:
            if loc == "custom" and x is not None and y is not None:
                legend.set_bbox_to_anchor((float(x), float(y)))
                legend._loc = 2
            else:
                loc_map = {
                    "best": 0,
                    "upper right": 1,
                    "upper left": 2,
                    "lower left": 3,
                    "lower right": 4,
                    "right": 5,
                    "center left": 6,
                    "center right": 7,
                    "lower center": 8,
                    "upper center": 9,
                    "center": 10,
                }
                legend._loc = loc_map.get(loc, 0)
                legend.set_bbox_to_anchor(None)

            editor.style_overrides.manual_overrides["legend_loc"] = loc
            if loc == "custom":
                editor.style_overrides.manual_overrides["legend_x"] = x
                editor.style_overrides.manual_overrides["legend_y"] = y

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
        logger.exception("[Vis] update_legend_position failed")
        return JsonResponse({"error": str(e)}, status=500)


def handle_get_legend_info(request, editor):
    mpl_fig = editor.fig.fig if hasattr(editor.fig, "fig") else editor.fig
    axes = mpl_fig.get_axes()
    info = {"has_legend": False, "visible": True, "loc": "best", "x": None, "y": None}
    if axes:
        legend = axes[0].get_legend()
        if legend is not None:
            info["has_legend"] = True
            info["visible"] = legend.get_visible()
            loc_names = {
                0: "best",
                1: "upper right",
                2: "upper left",
                3: "lower left",
                4: "lower right",
                5: "right",
                6: "center left",
                7: "center right",
                8: "lower center",
                9: "upper center",
                10: "center",
            }
            info["loc"] = loc_names.get(legend._loc, "best")
            bbox = legend.get_bbox_to_anchor()
            if bbox is not None:
                try:
                    bounds = bbox.bounds
                    if bounds[0] != 0 or bounds[1] != 0:
                        info["loc"] = "custom"
                        info["x"] = bounds[0]
                        info["y"] = bounds[1]
                except Exception:
                    pass
    return JsonResponse(info)


def handle_get_axes_positions(request, editor):
    mpl_fig = editor.fig.fig if hasattr(editor.fig, "fig") else editor.fig
    axes = mpl_fig.get_axes()
    fig_w_mm = mpl_fig.get_size_inches()[0] * 25.4
    fig_h_mm = mpl_fig.get_size_inches()[1] * 25.4

    positions = {}
    for i, ax in enumerate(axes):
        bbox = ax.get_position()
        positions[f"ax_{i}"] = {
            "index": i,
            "left": round(bbox.x0 * fig_w_mm, 2),
            "top": round((1 - bbox.y1) * fig_h_mm, 2),
            "width": round(bbox.width * fig_w_mm, 2),
            "height": round(bbox.height * fig_h_mm, 2),
        }
    positions["_figsize"] = {
        "width_mm": round(fig_w_mm, 2),
        "height_mm": round(fig_h_mm, 2),
    }
    return JsonResponse(positions)


def handle_update_axes_position(request, editor):
    """Move or resize a panel (axes) on the canvas. WORKFLOW 4."""
    from figrecipe._editor._helpers import render_with_overrides

    from ._core import _regen_hitmap

    data = json.loads(request.body) if request.body else {}
    ax_index = data.get("ax_index", 0)
    left_mm = data.get("left")
    top_mm = data.get("top")
    width_mm = data.get("width")
    height_mm = data.get("height")

    if any(v is None for v in [left_mm, top_mm, width_mm, height_mm]):
        return JsonResponse({"error": "Missing position values"}, status=400)

    mpl_fig = editor.fig.fig if hasattr(editor.fig, "fig") else editor.fig
    fig_w_mm = mpl_fig.get_size_inches()[0] * 25.4
    fig_h_mm = mpl_fig.get_size_inches()[1] * 25.4

    if left_mm < 0 or left_mm + width_mm > fig_w_mm:
        return JsonResponse(
            {"error": f"Horizontal out of bounds (0-{fig_w_mm:.1f}mm)"}, status=400
        )
    if top_mm < 0 or top_mm + height_mm > fig_h_mm:
        return JsonResponse(
            {"error": f"Vertical out of bounds (0-{fig_h_mm:.1f}mm)"}, status=400
        )

    left = left_mm / fig_w_mm
    width = width_mm / fig_w_mm
    height = height_mm / fig_h_mm
    bottom = 1 - (top_mm + height_mm) / fig_h_mm

    axes = mpl_fig.get_axes()
    if ax_index >= len(axes):
        return JsonResponse({"error": f"Invalid ax_index: {ax_index}"}, status=400)

    try:
        ax = axes[ax_index]
        current_pos = ax.get_position()
        ax.set_position([left, bottom, width, height])

        editor.style_overrides.manual_overrides[f"axes_position_{ax_index}"] = {
            "left_mm": left_mm,
            "top_mm": top_mm,
            "width_mm": width_mm,
            "height_mm": height_mm,
        }

        if hasattr(editor.fig, "record"):
            ax_keys = sorted(editor.fig.record.axes.keys())
            matched = None
            for ak in ax_keys:
                ar = editor.fig.record.axes[ak]
                if hasattr(ar, "position_override") and ar.position_override:
                    rp = ar.position_override
                    if (
                        len(rp) >= 4
                        and abs(rp[0] - current_pos.x0) < 0.01
                        and abs(rp[1] - current_pos.y0) < 0.01
                        and abs(rp[2] - current_pos.width) < 0.01
                        and abs(rp[3] - current_pos.height) < 0.01
                    ):
                        matched = ak
                        break
            if matched is None and ax_index < len(ax_keys):
                matched = ax_keys[ax_index]
            if matched:
                editor.fig.record.axes[matched].position_override = [
                    left,
                    bottom,
                    width,
                    height,
                ]

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
        logger.exception("[Vis] update_axes_position failed")
        return JsonResponse({"error": str(e)}, status=500)
