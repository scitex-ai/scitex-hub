#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bundle CRUD operations for FigzBundle."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Union

from django.conf import settings
from django.utils.text import slugify

from .constants import (
    BUNDLE_EXTENSIONS,
    FIGZ_EXTENSION,
    STX_EXTENSION,
    get_bundle_module,
    get_figz_class,
)


def get_bundle_base_path(user_id: int) -> Path:
    """Get base path for user's figz bundles."""
    return Path(settings.MEDIA_ROOT) / "vis" / "bundles" / "figz" / str(user_id)


def is_figz_bundle(path: Union[str, Path]) -> bool:
    """Check if path is a valid figz bundle (legacy, also checks .stx)."""
    return is_figure_bundle(path)


def is_figure_bundle(path: Union[str, Path]) -> bool:
    """Check if path is a valid figure bundle (.stx or .figz)."""
    bundle = get_bundle_module()
    path = Path(path)

    if path.suffix not in BUNDLE_EXTENSIONS:
        return False

    if not path.is_file():
        return False

    try:
        with bundle.ZipBundle(path, mode="r") as zb:
            spec = zb.read_json("spec.json")
            if path.suffix == STX_EXTENSION:
                content_type = bundle.get_stx_type(spec)
                return content_type == "figure"
            return True
    except Exception:
        return False


def load_bundle(bundle_path: Union[str, Path]) -> Dict[str, Any]:
    """Load a figure bundle (.stx or .figz) using scitex.fig.Figz."""
    Figz = get_figz_class()
    path = Path(bundle_path)

    if not path.exists():
        raise FileNotFoundError(f"Bundle not found: {path}")

    figz = Figz(path)

    content_type = "figure"
    if path.suffix == STX_EXTENSION:
        content_type = figz.spec.get("type", "figure")

    return {
        "path": str(path),
        "is_zip": path.suffix in BUNDLE_EXTENSIONS,
        "format": "stx" if path.suffix == STX_EXTENSION else "figz",
        "content_type": content_type,
        "bundle_id": figz.spec.get("bundle_id"),
        "spec": figz.spec,
        "style": figz.style,
        "panels": figz.panels,
    }


def save_bundle(
    spec: Dict,
    style: Dict,
    panels: Optional[Dict[str, Union[str, Path, Dict]]] = None,
    output_path: Optional[Union[str, Path]] = None,
    user_id: Optional[int] = None,
    name: Optional[str] = None,
    as_zip: bool = True,
    generate_exports: bool = True,
    use_stx: bool = False,
) -> Dict[str, Any]:
    """Save a new figure bundle using scitex.fig.Figz."""
    Figz = get_figz_class()
    ext = STX_EXTENSION if use_stx else FIGZ_EXTENSION

    if output_path:
        path = Path(output_path)
    elif user_id and name:
        base_path = get_bundle_base_path(user_id)
        base_path.mkdir(parents=True, exist_ok=True)
        path = base_path / f"{slugify(name)}{ext}"
    else:
        raise ValueError("Either output_path or (user_id, name) required")

    figure_name = spec.get("figure", {}).get("id", name or "Figure")
    size_mm = spec.get("size_mm")
    figz = Figz.create(path, figure_name, size_mm)
    if style:
        figz.style = style
    figz.save()

    return {
        "path": str(path),
        "is_zip": True,
        "format": "stx" if use_stx else "figz",
        "bundle_id": figz.spec.get("bundle_id"),
        "spec": figz.spec,
    }


def delete_bundle(bundle_path: Union[str, Path]) -> bool:
    """Delete a figz bundle."""
    path = Path(bundle_path)
    if not path.exists():
        return False
    if path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)
    return True


# EOF
