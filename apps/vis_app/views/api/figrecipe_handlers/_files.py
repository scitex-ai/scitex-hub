"""File management figrecipe handlers: list/switch/new/delete/rename/duplicate/download.

WORKFLOW 1: File selection → data & canvas.
"""

import json
import logging
from pathlib import Path

from django.http import FileResponse, JsonResponse

logger = logging.getLogger(__name__)


def handle_api_files(request, editor):
    """List recipe files in working dir as tree + flat list."""
    working_dir = getattr(editor, "working_dir", Path.cwd())

    def build_tree(directory, relative_base=None):
        if relative_base is None:
            relative_base = directory
        items = []
        try:
            entries = sorted(
                directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
            )
        except PermissionError:
            return items
        for entry in entries:
            skip = (
                entry.name.startswith(".")
                or entry.name.endswith(".overrides.yaml")
                or entry.name == "__pycache__"
            )
            if skip:
                continue
            rel_path = str(entry.relative_to(relative_base))
            if entry.is_dir():
                children = build_tree(entry, relative_base)
                if children:
                    items.append(
                        {
                            "path": rel_path,
                            "name": entry.name,
                            "type": "directory",
                            "children": children,
                        }
                    )
            elif entry.suffix.lower() in (".yaml", ".yml"):
                items.append(
                    {
                        "path": rel_path,
                        "name": entry.name,
                        "type": "file",
                        "has_image": entry.with_suffix(".png").exists(),
                        "is_current": bool(
                            editor.recipe_path
                            and entry.resolve() == editor.recipe_path.resolve()
                        ),
                    }
                )
        return items

    tree = build_tree(working_dir)

    flat_files = []

    def flatten(items):
        for item in items:
            if item["type"] == "directory":
                flatten(item.get("children", []))
            else:
                flat_files.append(item)

    flatten(tree)
    return JsonResponse(
        {
            "tree": tree,
            "files": flat_files,
            "working_dir": str(working_dir),
            "current_file": (
                str(editor.recipe_path.name) if editor.recipe_path else None
            ),
        }
    )


def handle_api_switch(request, editor):
    """Switch to a different recipe file."""
    from figrecipe._editor._helpers import render_with_overrides
    from figrecipe._reproducer import reproduce

    data = json.loads(request.body) if request.body else {}
    file_path = data.get("path")
    if not file_path:
        return JsonResponse({"error": "No file path provided"}, status=400)

    working_dir = getattr(editor, "working_dir", Path.cwd())
    full_path = working_dir / file_path
    if not full_path.exists():
        return JsonResponse({"error": f"File not found: {file_path}"}, status=404)

    try:
        fig, _ = reproduce(full_path)
        editor.fig = fig
        editor.recipe_path = full_path
        editor._hitmap_generated = False
        editor._color_map = {}
        editor._init_style_overrides(None)

        img, bboxes, size = render_with_overrides(
            editor.fig, editor.get_effective_style(), editor.dark_mode
        )
        editor._hitmap_generated = False
        editor._color_map = {}

        return JsonResponse(
            {
                "success": True,
                "image": img,
                "bboxes": bboxes,
                "color_map": {},
                "img_size": {"width": size[0], "height": size[1]},
                "file": file_path,
            }
        )
    except Exception as e:
        logger.exception("[Vis] api_switch failed")
        return JsonResponse({"error": str(e)}, status=500)


def handle_api_new(request, editor):
    """Create a new blank figure file."""
    from figrecipe import reproduce, save, subplots
    from figrecipe._editor._helpers import render_with_overrides

    try:
        fig, ax = subplots()
        ax.set_title("New Figure")

        working_dir = getattr(editor, "working_dir", Path.cwd())
        counter = 1
        while True:
            file_path = working_dir / f"new_figure_{counter:03d}.yaml"
            if not file_path.exists():
                break
            counter += 1

        save(fig, file_path.with_suffix(".png"), validate=False, verbose=False)
        reproduced_fig, _ = reproduce(file_path)

        editor.fig = reproduced_fig
        editor.recipe_path = file_path
        editor._hitmap_generated = False
        editor._color_map = {}
        editor._init_style_overrides(None)

        img, bboxes, size = render_with_overrides(
            editor.fig, editor.get_effective_style(), editor.dark_mode
        )
        editor._hitmap_generated = False
        editor._color_map = {}

        return JsonResponse(
            {
                "success": True,
                "image": img,
                "bboxes": bboxes,
                "color_map": {},
                "img_size": {"width": size[0], "height": size[1]},
                "file": str(file_path.relative_to(working_dir)),
                "file_name": file_path.stem,
            }
        )
    except Exception as e:
        logger.exception("[Vis] api_new failed")
        return JsonResponse({"error": str(e)}, status=500)


def handle_api_delete(request, editor):
    """Delete a recipe file and associated files."""
    data = json.loads(request.body) if request.body else {}
    file_path = data.get("path")
    if not file_path:
        return JsonResponse({"error": "No file path provided"}, status=400)

    working_dir = getattr(editor, "working_dir", Path.cwd())
    full_path = working_dir / file_path
    if full_path.suffix.lower() not in (".yaml", ".yml", ".png"):
        return JsonResponse({"error": "Invalid file type"}, status=400)

    base_path = full_path.with_suffix("")
    is_current = bool(
        editor.recipe_path and base_path == editor.recipe_path.with_suffix("")
    )
    deleted_files, errors = [], []

    for ext in [".yaml", ".yml", ".png", ".overrides.yaml"]:
        target = base_path.with_suffix(ext)
        if target.exists():
            try:
                target.unlink()
                deleted_files.append(target.name)
            except Exception as e:
                errors.append(f"{target.name}: {e}")

    if not deleted_files:
        return JsonResponse({"error": "No files found to delete"}, status=404)

    switch_to = None
    if is_current:
        for f in sorted(working_dir.glob("*.yaml")):
            if not f.name.startswith(".") and not f.name.endswith(".overrides.yaml"):
                switch_to = str(f.relative_to(working_dir))
                break

    return JsonResponse(
        {
            "success": True,
            "deleted": deleted_files,
            "errors": errors or None,
            "was_current": is_current,
            "switch_to": switch_to,
        }
    )


def handle_api_rename(request, editor):
    """Rename a recipe file."""
    data = json.loads(request.body) if request.body else {}
    old_path = data.get("path")
    new_name = data.get("new_name")

    if not old_path:
        return JsonResponse({"error": "No file path provided"}, status=400)
    if not new_name:
        return JsonResponse({"error": "No new name provided"}, status=400)

    new_name = Path(new_name).stem
    if not new_name or "/" in new_name or "\\" in new_name:
        return JsonResponse({"error": "Invalid new name"}, status=400)

    working_dir = getattr(editor, "working_dir", Path.cwd())
    full_path = working_dir / old_path
    if full_path.suffix.lower() not in (".yaml", ".yml", ".png"):
        return JsonResponse({"error": "Invalid file type"}, status=400)

    old_base = full_path.with_suffix("")
    new_base = working_dir / new_name

    for ext in [".yaml", ".png"]:
        if new_base.with_suffix(ext).exists():
            return JsonResponse(
                {"error": f"File {new_name}{ext} already exists"}, status=400
            )

    renamed_files, errors = [], []
    for ext in [".yaml", ".yml", ".png", ".overrides.yaml"]:
        old_file = old_base.with_suffix(ext)
        new_file = new_base.with_suffix(ext)
        if old_file.exists():
            try:
                old_file.rename(new_file)
                renamed_files.append({"from": old_file.name, "to": new_file.name})
            except Exception as e:
                errors.append(f"{old_file.name}: {e}")

    if not renamed_files:
        return JsonResponse({"error": "No files found to rename"}, status=404)

    if editor.recipe_path and old_base == editor.recipe_path.with_suffix(""):
        editor.recipe_path = new_base.with_suffix(".yaml")

    return JsonResponse(
        {
            "success": True,
            "renamed": renamed_files,
            "new_name": new_name,
            "errors": errors or None,
        }
    )


def handle_api_duplicate(request, editor):
    """Duplicate a recipe file."""
    import shutil

    data = json.loads(request.body) if request.body else {}
    file_path = data.get("path")
    if not file_path:
        return JsonResponse({"error": "No file path provided"}, status=400)

    working_dir = getattr(editor, "working_dir", Path.cwd())
    full_path = working_dir / file_path
    if full_path.suffix.lower() not in (".yaml", ".yml", ".png"):
        return JsonResponse({"error": "Invalid file type"}, status=400)

    base_path = full_path.with_suffix("")
    original_name = base_path.stem
    counter = 1
    while True:
        new_name = f"{original_name}_copy_{counter:02d}"
        new_base = base_path.parent / new_name
        if not new_base.with_suffix(".yaml").exists():
            break
        counter += 1

    copied_files, errors = [], []
    for ext in [".yaml", ".yml", ".png", ".overrides.yaml"]:
        old_file = base_path.with_suffix(ext)
        new_file = new_base.with_suffix(ext)
        if old_file.exists():
            try:
                shutil.copy2(old_file, new_file)
                copied_files.append({"from": old_file.name, "to": new_file.name})
            except Exception as e:
                errors.append(f"{old_file.name}: {e}")

    if not copied_files:
        return JsonResponse({"error": "No files found to duplicate"}, status=404)

    return JsonResponse(
        {
            "success": True,
            "copied": copied_files,
            "new_name": new_name,
            "new_path": str(new_base.with_suffix(".yaml").relative_to(working_dir)),
            "errors": errors or None,
        }
    )


def handle_api_download_recipe(request, editor):
    """Download the current recipe YAML file."""
    file_path_str = request.GET.get("path", "")
    if not file_path_str and editor.recipe_path:
        full_path = editor.recipe_path
    elif file_path_str:
        working_dir = getattr(editor, "working_dir", Path.cwd())
        full_path = working_dir / file_path_str
        if not full_path.suffix:
            full_path = full_path.with_suffix(".yaml")
    else:
        return JsonResponse({"error": "No file path provided"}, status=400)

    if not full_path.exists():
        return JsonResponse({"error": "File not found"}, status=404)

    return FileResponse(
        open(full_path, "rb"),
        as_attachment=True,
        filename=full_path.name,
        content_type="application/x-yaml",
    )
