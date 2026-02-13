"""figrecipe API handler functions.

Thin wrappers around figrecipe Python functions, called by the
catch-all dispatcher in figrecipe.py.
"""

import json

from django.http import JsonResponse

# ─── Core handlers ──────────────────────────────────────────────


def handle_preview(request, editor):
    from figrecipe._editor._helpers import render_with_overrides

    img, bboxes, size = render_with_overrides(
        editor.fig,
        editor.get_effective_style(),
        editor.dark_mode,
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
        editor.fig,
        editor.get_effective_style(),
        editor.dark_mode,
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
        {
            "image": editor._hitmap_base64,
            "color_map": editor._color_map,
        }
    )


# ─── Style handlers ─────────────────────────────────────────────


def handle_style(request, editor):
    return JsonResponse(
        {
            "base_style": editor.style_overrides.base_style,
            "programmatic_style": editor.style_overrides.programmatic_style,
            "manual_overrides": editor.style_overrides.manual_overrides,
            "effective_style": editor.get_effective_style(),
            "has_overrides": editor.style_overrides.has_manual_overrides(),
            "manual_timestamp": editor.style_overrides.manual_timestamp,
        }
    )


def handle_overrides(request, editor):
    return JsonResponse(editor.style_overrides.manual_overrides)


def handle_list_themes(request, editor):
    from figrecipe.styles._style_loader import list_presets

    presets = list_presets()
    current = editor.get_effective_style().get("_name", "SCITEX")
    return JsonResponse({"themes": presets, "current": current})


def handle_switch_theme(request, editor):
    from figrecipe._editor._helpers import (
        get_form_values_from_style,
        render_with_overrides,
    )
    from figrecipe._reproducer import reproduce_from_record
    from figrecipe.styles._style_loader import load_preset

    data = json.loads(request.body) if request.body else {}
    theme_name = data.get("theme")
    if not theme_name:
        return JsonResponse({"error": "No theme specified"}, status=400)

    new_style = load_preset(theme_name)
    if new_style is None:
        return JsonResponse({"error": f"Theme '{theme_name}' not found"}, status=404)

    flat_style = dict(new_style)
    flat_style["_name"] = theme_name

    if "colors" in new_style and isinstance(new_style["colors"], dict):
        colors_dict = new_style["colors"]
        if "palette" in colors_dict and colors_dict["palette"] is not None:
            flat_style["color_palette"] = list(colors_dict["palette"])

    if "theme" in flat_style and isinstance(flat_style["theme"], dict):
        flat_style["theme"]["mode"] = "dark" if editor.dark_mode else "light"
    elif editor.dark_mode:
        flat_style["theme"] = {"mode": "dark"}

    editor.style_overrides.base_style = flat_style

    if hasattr(editor.fig, "record") and editor.fig.record is not None:
        editor.fig.record.style = flat_style
        new_fig, _ = reproduce_from_record(editor.fig.record)
        editor.fig = new_fig

    mpl_fig = editor.fig.fig if hasattr(editor.fig, "fig") else editor.fig
    behavior = new_style.get("behavior", {})
    for ax in mpl_fig.get_axes():
        for side, default in [
            ("top", True),
            ("right", True),
            ("bottom", False),
            ("left", False),
        ]:
            ax.spines[side].set_visible(not behavior.get(f"hide_{side}_spine", default))
        ax.grid(behavior.get("grid", False), alpha=0.3)

    img, bboxes, size = render_with_overrides(
        editor.fig,
        editor.get_effective_style(),
        editor.dark_mode,
    )
    form_values = get_form_values_from_style(editor.get_effective_style())

    return JsonResponse(
        {
            "success": True,
            "theme": theme_name,
            "image": img,
            "bboxes": bboxes,
            "img_size": {"width": size[0], "height": size[1]},
            "values": form_values,
        }
    )


def handle_save(request, editor):
    from figrecipe._editor._overrides import save_overrides

    data = json.loads(request.body) if request.body else {}
    editor.style_overrides.update_manual_overrides(data.get("overrides", {}))

    if editor.recipe_path:
        path = save_overrides(editor.style_overrides, editor.recipe_path)
        return JsonResponse(
            {
                "success": True,
                "path": str(path),
                "has_overrides": editor.style_overrides.has_manual_overrides(),
                "timestamp": editor.style_overrides.manual_timestamp,
            }
        )

    return JsonResponse(
        {
            "success": True,
            "overrides": editor.overrides,
            "has_overrides": editor.style_overrides.has_manual_overrides(),
        }
    )


def handle_restore(request, editor):
    from figrecipe._editor._helpers import render_with_overrides

    editor.style_overrides.clear_manual_overrides()
    editor.restore_axes_positions()
    editor.restore_annotation_positions()

    img, bboxes, size = render_with_overrides(
        editor.fig,
        None,
        editor.dark_mode,
    )
    return JsonResponse(
        {
            "success": True,
            "image": img,
            "bboxes": bboxes,
            "img_size": {"width": size[0], "height": size[1]},
            "original_style": editor.style,
        }
    )


def handle_diff(request, editor):
    return JsonResponse(
        {
            "diff": editor.style_overrides.get_diff(),
            "has_overrides": editor.style_overrides.has_manual_overrides(),
        }
    )


# ─── Axis/label handlers ────────────────────────────────────────


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
        editor.fig,
        editor.get_effective_style(),
        editor.dark_mode,
    )
    return JsonResponse(
        {
            "success": True,
            "image": img,
            "bboxes": bboxes,
            "img_size": {"width": size[0], "height": size[1]},
        }
    )


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
    return JsonResponse(info)


# ─── Data/record handlers ───────────────────────────────────────


def handle_get_captions(request, editor):
    mpl_fig = editor.fig.fig if hasattr(editor.fig, "fig") else editor.fig
    captions = {"figure_caption": "", "panel_captions": {}}
    if hasattr(editor.fig, "record") and editor.fig.record:
        record = editor.fig.record
        captions["figure_caption"] = getattr(record, "caption", "") or ""
        for ax_key, ax_record in getattr(record, "axes", {}).items():
            captions["panel_captions"][ax_key] = getattr(ax_record, "caption", "") or ""
    return JsonResponse(captions)


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


def handle_calls(request, editor):
    from figrecipe._editor._helpers import to_json_serializable

    if not hasattr(editor.fig, "record") or not editor.fig.record:
        return JsonResponse({})

    calls = {}
    record = editor.fig.record
    for ax_key, ax_record in record.axes.items():
        for call in getattr(ax_record, "calls", []):
            call_id = getattr(call, "call_id", None) or f"{ax_key}_{id(call)}"
            calls[call_id] = to_json_serializable(
                {
                    "function": getattr(call, "function", "unknown"),
                    "ax_key": ax_key,
                    "args": getattr(call, "args", []),
                    "kwargs": getattr(call, "kwargs", {}),
                }
            )
    return JsonResponse(calls)


def handle_datatable_data(request, editor):
    from figrecipe._editor._helpers import to_json_serializable

    if not hasattr(editor.fig, "record") or not editor.fig.record:
        return JsonResponse({"columns": [], "data": [], "source": "empty"})

    record = editor.fig.record
    columns = []
    data_rows = []

    for ax_key, ax_record in record.axes.items():
        for call in getattr(ax_record, "calls", []):
            kwargs = getattr(call, "kwargs", {})
            args = getattr(call, "args", [])
            func = getattr(call, "function", "")

            x_data = kwargs.get("x") or (args[0] if len(args) > 0 else None)
            y_data = kwargs.get("y") or (args[1] if len(args) > 1 else None)

            if x_data is not None and y_data is not None:
                call_id = getattr(call, "call_id", func)
                x_col = f"{call_id}_x"
                y_col = f"{call_id}_y"
                if x_col not in columns:
                    columns.extend([x_col, y_col])
                x_list = to_json_serializable(x_data)
                y_list = to_json_serializable(y_data)
                if isinstance(x_list, list) and isinstance(y_list, list):
                    for i, (xv, yv) in enumerate(zip(x_list, y_list)):
                        while len(data_rows) <= i:
                            data_rows.append({})
                        data_rows[i][x_col] = xv
                        data_rows[i][y_col] = yv

    return JsonResponse({"columns": columns, "data": data_rows, "source": "record"})


# ─── Handler dispatch table ─────────────────────────────────────

HANDLERS = {
    "preview": handle_preview,
    "ping": handle_ping,
    "update": handle_update,
    "hitmap": handle_hitmap,
    "style": handle_style,
    "overrides": handle_overrides,
    "list_themes": handle_list_themes,
    "switch_theme": handle_switch_theme,
    "save": handle_save,
    "restore": handle_restore,
    "diff": handle_diff,
    "get_labels": handle_get_labels,
    "update_label": handle_update_label,
    "get_axis_info": handle_get_axis_info,
    "get_legend_info": handle_get_legend_info,
    "get_captions": handle_get_captions,
    "get_axes_positions": handle_get_axes_positions,
    "calls": handle_calls,
    "datatable/data": handle_datatable_data,
}
