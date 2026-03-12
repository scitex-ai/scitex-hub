"""Style/theme figrecipe handlers."""

import json

from django.http import JsonResponse


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


def handle_get_theme(request, editor):
    """Get current effective style as YAML content."""
    import io as _io

    from ruamel.yaml import YAML

    style = editor.get_effective_style()
    style_name = style.get("_name", "SCITEX")

    yaml = YAML()
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    stream = _io.StringIO()
    yaml.dump(style, stream)
    return JsonResponse({"name": style_name, "content": stream.getvalue()})


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
        colors = new_style["colors"]
        if "palette" in colors and colors["palette"] is not None:
            flat_style["color_palette"] = list(colors["palette"])

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
        editor.fig, editor.get_effective_style(), editor.dark_mode
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

    img, bboxes, size = render_with_overrides(editor.fig, None, editor.dark_mode)
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
