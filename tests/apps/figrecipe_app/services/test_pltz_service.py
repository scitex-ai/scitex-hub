#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/figrecipe_app/services/pltz_service.py"""

import pytest

# from apps.workspace.figrecipe_app.services.pltz_service import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/figrecipe_app/services/pltz_service.py
# --------------------------------------------------------------------------------
# """PltzBundle Service - Thin Django wrapper around scitex.plt.Pltz."""
#
# import logging
# import os
# import sys
# from pathlib import Path
# from typing import Any, Dict, Optional, Union
#
# from django.conf import settings
# from django.utils.text import slugify
#
# logger = logging.getLogger(__name__)
#
# # Ensure scitex is importable
# SCITEX_CODE_PATH = os.environ.get('SCITEX_CODE_PATH', '/home/ywatanabe/proj/scitex-code')
# if SCITEX_CODE_PATH not in sys.path:
#     sys.path.insert(0, f"{SCITEX_CODE_PATH}/src")
#
#
# def _get_pltz_class():
#     """Lazy import Pltz class."""
#     from scitex.plt import Pltz
#     return Pltz
#
#
# class PltzService:
#     """Thin service wrapper for pltz bundle operations."""
#
#     @staticmethod
#     def get_bundle_base_path(user_id: int) -> Path:
#         """Get base path for user's pltz bundles."""
#         return Path(settings.MEDIA_ROOT) / "vis" / "bundles" / "pltz" / str(user_id)
#
#     @staticmethod
#     def load_bundle(bundle_path: Union[str, Path]) -> Dict[str, Any]:
#         """Load a pltz bundle using scitex.plt.Pltz."""
#         Pltz = _get_pltz_class()
#         path = Path(bundle_path)
#         if not path.exists():
#             raise FileNotFoundError(f"Bundle not found: {path}")
#         pltz = Pltz(path)
#         return {
#             "path": str(path),
#             "is_zip": path.suffix == ".pltz",
#             "spec": pltz.spec,
#             "style": pltz.style,
#             "data": pltz.data,
#         }
#
#     @staticmethod
#     def save_bundle(
#         spec: Dict,
#         style: Dict,
#         data_csv: Optional[str] = None,
#         output_path: Optional[Union[str, Path]] = None,
#         user_id: Optional[int] = None,
#         name: Optional[str] = None,
#         as_zip: bool = True,
#     ) -> Dict[str, Any]:
#         """Save a new pltz bundle using scitex.plt.Pltz."""
#         Pltz = _get_pltz_class()
#         import pandas as pd
#         from io import StringIO
#
#         # Determine output path
#         if output_path:
#             path = Path(output_path)
#         elif user_id and name:
#             base_path = PltzService.get_bundle_base_path(user_id)
#             base_path.mkdir(parents=True, exist_ok=True)
#             path = base_path / f"{slugify(name)}.pltz"
#         else:
#             raise ValueError("Either output_path or (user_id, name) required")
#
#         # Parse CSV data
#         df = None
#         if data_csv:
#             if Path(data_csv).is_file():
#                 df = pd.read_csv(data_csv)
#             else:
#                 df = pd.read_csv(StringIO(data_csv))
#
#         # Create bundle
#         plot_type = spec.get("plot_type", "line")
#         pltz = Pltz.create(path, plot_type=plot_type, data=df, spec_overrides=spec)
#         if style:
#             pltz.style = style
#             pltz.save()
#
#         return {"path": str(path), "is_zip": True, "spec": pltz.spec, "style": pltz.style}
#
#     @staticmethod
#     def update_spec(bundle_path: Union[str, Path], spec: Dict) -> Dict[str, Any]:
#         """Update spec.json in bundle."""
#         Pltz = _get_pltz_class()
#         pltz = Pltz(bundle_path)
#         pltz.spec = spec
#         pltz.save()
#         return {"path": str(bundle_path), "spec": spec}
#
#     @staticmethod
#     def update_style(bundle_path: Union[str, Path], style: Dict) -> Dict[str, Any]:
#         """Update style.json in bundle."""
#         Pltz = _get_pltz_class()
#         pltz = Pltz(bundle_path)
#         pltz.style = style
#         pltz.save()
#         return {"path": str(bundle_path), "style": style}
#
#     @staticmethod
#     def get_preview_image(bundle_path: Union[str, Path], image_type: str = "png") -> Optional[bytes]:
#         """Get preview image from bundle."""
#         Pltz = _get_pltz_class()
#         try:
#             pltz = Pltz(bundle_path)
#             return pltz.get_preview() or pltz.render_preview()
#         except Exception as e:
#             logger.warning(f"Failed to get preview: {e}")
#             return None
#
#     @staticmethod
#     def get_data_csv(bundle_path: Union[str, Path]) -> Optional[str]:
#         """Get data CSV content from bundle."""
#         Pltz = _get_pltz_class()
#         try:
#             pltz = Pltz(bundle_path)
#             if pltz.data is not None:
#                 return pltz.data.to_csv(index=False)
#         except Exception as e:
#             logger.warning(f"Failed to get data: {e}")
#         return None
#
#     @staticmethod
#     def get_geometry(bundle_path: Union[str, Path]) -> Optional[Dict]:
#         """Get geometry cache from bundle."""
#         from scitex.io.bundle import ZipBundle
#         try:
#             with ZipBundle(bundle_path, mode="r") as zb:
#                 return zb.read_json("cache/geometry_px.json")
#         except (FileNotFoundError, Exception):
#             return None
#
#     @staticmethod
#     def delete_bundle(bundle_path: Union[str, Path]) -> bool:
#         """Delete a pltz bundle."""
#         import shutil
#         path = Path(bundle_path)
#         if not path.exists():
#             return False
#         if path.is_file():
#             path.unlink()
#         else:
#             shutil.rmtree(path)
#         return True
#
#     @staticmethod
#     def categorize_plot(spec: Dict) -> str:
#         """Determine plot category from spec."""
#         plot_type = spec.get("plot_type", "").lower()
#         if plot_type in ["line", "step", "stem"]:
#             return "line"
#         elif plot_type == "scatter":
#             return "scatter"
#         elif plot_type in ["bar", "barh"]:
#             return "bar"
#         elif plot_type in ["histogram", "kde", "ecdf"]:
#             return "distribution"
#         elif plot_type in ["boxplot", "violinplot"]:
#             return "statistical"
#         elif plot_type in ["heatmap", "imshow", "contour"]:
#             return "heatmap"
#         return "other"
#
#     @staticmethod
#     def create_from_gallery(
#         gallery_category: str,
#         gallery_plot_name: str,
#         output_path: Union[str, Path],
#         project_owner: Optional[str] = None,
#         project_slug: Optional[str] = None,
#     ) -> Dict[str, Any]:
#         """Create pltz bundle from gallery template."""
#         Pltz = _get_pltz_class()
#         path = Path(output_path)
#         path.parent.mkdir(parents=True, exist_ok=True)
#         pltz = Pltz.create_from_gallery(path, gallery_category, gallery_plot_name)
#         return {
#             "bundle_path": str(path),
#             "spec": pltz.spec,
#             "style": pltz.style,
#         }
#
#     @staticmethod
#     def create_from_plot(
#         plot_type: str, data_csv: Optional[str] = None, data: Optional[Any] = None,
#         name: Optional[str] = None, output_dir: Optional[str] = None,
#         project_owner: Optional[str] = None, project_slug: Optional[str] = None,
#         figure_name: Optional[str] = None, panel_label: Optional[str] = None,
#         user: Optional[Any] = None, gallery_category: Optional[str] = None,
#         gallery_plot_name: Optional[str] = None,
#     ) -> Dict[str, Any]:
#         """Create pltz bundle from gallery template, optionally with user data."""
#         if not gallery_category or not gallery_plot_name:
#             raise ValueError("gallery_category and gallery_plot_name required")
#         bundle_name = panel_label or name or "plot"
#         if output_dir:
#             bundle_path = Path(output_dir) / f"{bundle_name}.pltz"
#         elif project_owner and project_slug:
#             from apps.infra.project_app.models import Project
#             project = Project.objects.get(owner__username=project_owner, slug=project_slug)
#             figures_dir = project.get_local_path() / "scitex" / "vis" / "figures"
#             figz_path = figures_dir / f"{figure_name}.figz" if figure_name else figures_dir
#             figz_path.mkdir(parents=True, exist_ok=True)
#             bundle_path = figz_path / f"{bundle_name}.pltz"
#         elif user:
#             bundle_path = PltzService.get_bundle_base_path(user.id) / f"{bundle_name}.pltz"
#         else:
#             raise ValueError("output_dir, project info, or user required")
#         result = PltzService.create_from_gallery(gallery_category, gallery_plot_name, bundle_path)
#         # Update with user data if provided
#         if data_csv:
#             Pltz = _get_pltz_class()
#             import pandas as pd
#             from io import StringIO
#             pltz = Pltz(bundle_path)
#             df = pd.read_csv(StringIO(data_csv))
#             pltz.data = df
#             pltz.save()
#             result["data_updated"] = True
#         return result
#
#     @staticmethod
#     def is_pltz_bundle(path: Union[str, Path]) -> bool:
#         """Check if path is a valid pltz bundle."""
#         path = Path(path)
#         if path.suffix == ".pltz" and path.is_file():
#             from scitex.io.bundle import ZipBundle
#             try:
#                 with ZipBundle(path, mode="r") as zb:
#                     zb.read_json("spec.json")
#                 return True
#             except Exception:
#                 return False
#         return False
#
#     @staticmethod
#     def render_preview(bundle_path: Union[str, Path]) -> Dict[str, Any]:
#         """Re-render preview and update bundle."""
#         Pltz = _get_pltz_class()
#         pltz = Pltz(bundle_path)
#         pltz.update_preview()
#         return {"path": str(bundle_path), "rendered": True}
#
#     @staticmethod
#     def get_preview_base64(bundle_path: Union[str, Path], image_type: str = "png") -> Optional[str]:
#         """Get preview image as base64 data URL."""
#         import base64
#         data = PltzService.get_preview_image(bundle_path, image_type)
#         if data:
#             b64 = base64.b64encode(data).decode('utf-8')
#             return f"data:image/png;base64,{b64}"
#         return None

# --------------------------------------------------------------------------------
# End of Source Code from: apps/figrecipe_app/services/pltz_service.py
# --------------------------------------------------------------------------------
