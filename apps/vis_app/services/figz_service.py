"""
FigzBundle Service - Business logic for .figz bundle operations.

Handles:
- Loading and saving .figz bundles (multi-panel figures)
- Panel composition and layout
- Nested .pltz bundle management
- Integration with scitex.fig for figure composition
"""

import base64
import json
import logging
import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from django.conf import settings
from django.utils.text import slugify

from .pltz_service import PltzService

logger = logging.getLogger(__name__)

# Ensure scitex is importable
SCITEX_CODE_PATH = os.environ.get(
    'SCITEX_CODE_PATH',
    '/home/ywatanabe/proj/scitex-code'
)
if SCITEX_CODE_PATH not in sys.path:
    sys.path.insert(0, f"{SCITEX_CODE_PATH}/src")


class FigzService:
    """Service for figz bundle operations."""

    # Bundle structure constants
    SPEC_FILE = "spec.json"
    STYLE_FILE = "style.json"
    EXPORTS_DIR = "exports"
    CACHE_DIR = "cache"
    GEOMETRY_FILE = "geometry_px.json"

    # Panel labels
    PANEL_LABELS = "ABCDEFGH"

    @staticmethod
    def get_bundle_base_path(user_id: int) -> Path:
        """Get base path for user's figz bundles."""
        return Path(settings.MEDIA_ROOT) / "vis" / "bundles" / "figz" / str(user_id)

    @staticmethod
    def is_figz_bundle(path: Union[str, Path]) -> bool:
        """
        Check if path is a valid figz bundle.

        Args:
            path: Path to check

        Returns:
            True if valid figz bundle
        """
        path = Path(path)

        # Check ZIP format
        if path.suffix == ".figz" and path.is_file():
            try:
                with zipfile.ZipFile(path, 'r') as zf:
                    return FigzService.SPEC_FILE in zf.namelist()
            except zipfile.BadZipFile:
                return False

        # Check directory format
        if str(path).endswith(".figz.d") and path.is_dir():
            return (path / FigzService.SPEC_FILE).exists()

        return False

    @staticmethod
    def load_bundle(bundle_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load a figz bundle from disk.

        Args:
            bundle_path: Path to .figz.d directory or .figz ZIP file

        Returns:
            Dictionary with spec, style, panels, and metadata

        Raises:
            FileNotFoundError: If bundle not found
            ValueError: If invalid bundle format
        """
        bundle_path = Path(bundle_path)

        if not bundle_path.exists():
            raise FileNotFoundError(f"Bundle not found: {bundle_path}")

        if not FigzService.is_figz_bundle(bundle_path):
            raise ValueError(f"Invalid figz bundle: {bundle_path}")

        result = {
            "path": str(bundle_path),
            "is_zip": bundle_path.suffix == ".figz",
        }

        # Load from ZIP or directory
        if result["is_zip"]:
            result.update(FigzService._load_from_zip(bundle_path))
        else:
            result.update(FigzService._load_from_directory(bundle_path))

        return result

    @staticmethod
    def _load_from_directory(bundle_dir: Path) -> Dict[str, Any]:
        """Load bundle contents from directory."""
        result = {}

        # Load spec.json
        spec_path = bundle_dir / FigzService.SPEC_FILE
        if spec_path.exists():
            with open(spec_path, 'r') as f:
                result["spec"] = json.load(f)

        # Load style.json
        style_path = bundle_dir / FigzService.STYLE_FILE
        if style_path.exists():
            with open(style_path, 'r') as f:
                result["style"] = json.load(f)

        # Find and load nested pltz bundles
        panels = {}
        for label in FigzService.PANEL_LABELS:
            pltz_dir = bundle_dir / f"{label}.pltz.d"
            pltz_zip = bundle_dir / f"{label}.pltz"

            if pltz_dir.exists() and PltzService.is_pltz_bundle(pltz_dir):
                panels[label] = PltzService.load_bundle(pltz_dir)
            elif pltz_zip.exists() and PltzService.is_pltz_bundle(pltz_zip):
                panels[label] = PltzService.load_bundle(pltz_zip)

        if panels:
            result["panels"] = panels

        # Check exports
        exports_dir = bundle_dir / FigzService.EXPORTS_DIR
        if exports_dir.exists():
            result["exports"] = {
                f.stem: str(f) for f in exports_dir.iterdir()
                if f.is_file()
            }

        # Load combined geometry cache
        cache_dir = bundle_dir / FigzService.CACHE_DIR
        geometry_path = cache_dir / FigzService.GEOMETRY_FILE
        if geometry_path.exists():
            with open(geometry_path, 'r') as f:
                result["geometry"] = json.load(f)

        return result

    @staticmethod
    def _load_from_zip(zip_path: Path) -> Dict[str, Any]:
        """Load bundle contents from ZIP file."""
        result = {}

        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Load spec.json
            if FigzService.SPEC_FILE in zf.namelist():
                with zf.open(FigzService.SPEC_FILE) as f:
                    result["spec"] = json.load(f)

            # Load style.json
            if FigzService.STYLE_FILE in zf.namelist():
                with zf.open(FigzService.STYLE_FILE) as f:
                    result["style"] = json.load(f)

            # Find nested pltz bundles in ZIP
            panels = {}
            for label in FigzService.PANEL_LABELS:
                pltz_spec = f"{label}.pltz.d/{PltzService.SPEC_FILE}"
                if pltz_spec in zf.namelist():
                    # Extract panel spec
                    with zf.open(pltz_spec) as f:
                        panel_spec = json.load(f)

                    pltz_style = f"{label}.pltz.d/{PltzService.STYLE_FILE}"
                    panel_style = {}
                    if pltz_style in zf.namelist():
                        with zf.open(pltz_style) as f:
                            panel_style = json.load(f)

                    panels[label] = {
                        "spec": panel_spec,
                        "style": panel_style,
                        "is_zip": True,
                    }

            if panels:
                result["panels"] = panels

            # List exports
            exports = {}
            for name in zf.namelist():
                if name.startswith(f"{FigzService.EXPORTS_DIR}/"):
                    stem = Path(name).stem
                    exports[stem] = name
            if exports:
                result["exports"] = exports

        return result

    @staticmethod
    def save_bundle(
        spec: Dict,
        style: Dict,
        panels: Optional[Dict[str, Union[str, Path, Dict]]] = None,
        output_path: Optional[Union[str, Path]] = None,
        user_id: Optional[int] = None,
        name: Optional[str] = None,
        as_zip: bool = False,
        generate_exports: bool = True,
    ) -> Dict[str, Any]:
        """
        Save a new figz bundle.

        Args:
            spec: FigureSpec dictionary
            style: FigureStyle dictionary
            panels: Dict mapping labels (A, B, C, ...) to:
                    - Path to existing .pltz bundle
                    - Dict with 'spec' and 'style' for new panel
            output_path: Custom output path (optional)
            user_id: User ID for default path generation
            name: Bundle name (used for slug if output_path not provided)
            as_zip: If True, save as .figz ZIP instead of .figz.d directory
            generate_exports: If True, generate composed figure images

        Returns:
            Dictionary with bundle info and path

        Raises:
            ValueError: If neither output_path nor user_id provided
        """
        # Determine output path
        if output_path:
            bundle_path = Path(output_path)
        elif user_id and name:
            base_path = FigzService.get_bundle_base_path(user_id)
            slug = slugify(name)
            suffix = ".figz" if as_zip else ".figz.d"
            bundle_path = base_path / f"{slug}{suffix}"
        else:
            raise ValueError("Either output_path or (user_id, name) required")

        # Ensure parent directory exists
        bundle_path.parent.mkdir(parents=True, exist_ok=True)

        if as_zip:
            return FigzService._save_as_zip(
                spec, style, panels, bundle_path, generate_exports
            )
        else:
            return FigzService._save_as_directory(
                spec, style, panels, bundle_path, generate_exports
            )

    @staticmethod
    def _save_as_directory(
        spec: Dict,
        style: Dict,
        panels: Optional[Dict],
        bundle_dir: Path,
        generate_exports: bool,
    ) -> Dict[str, Any]:
        """Save bundle as directory structure."""
        # Create directory structure
        bundle_dir.mkdir(parents=True, exist_ok=True)
        exports_dir = bundle_dir / FigzService.EXPORTS_DIR
        cache_dir = bundle_dir / FigzService.CACHE_DIR
        exports_dir.mkdir(exist_ok=True)
        cache_dir.mkdir(exist_ok=True)

        # Save spec.json
        spec_path = bundle_dir / FigzService.SPEC_FILE
        with open(spec_path, 'w') as f:
            json.dump(spec, f, indent=2)

        # Save style.json
        style_path = bundle_dir / FigzService.STYLE_FILE
        with open(style_path, 'w') as f:
            json.dump(style, f, indent=2)

        # Copy or create panel pltz bundles
        panel_info = {}
        if panels:
            for label, panel_source in panels.items():
                panel_path = bundle_dir / f"{label}.pltz.d"

                if isinstance(panel_source, (str, Path)):
                    # Copy existing pltz bundle
                    source_path = Path(panel_source)
                    if source_path.is_dir():
                        shutil.copytree(source_path, panel_path)
                    elif source_path.suffix == ".pltz":
                        # Extract ZIP
                        with zipfile.ZipFile(source_path, 'r') as zf:
                            zf.extractall(panel_path)
                elif isinstance(panel_source, dict):
                    # Create new pltz bundle
                    PltzService.save_bundle(
                        spec=panel_source.get("spec", {}),
                        style=panel_source.get("style", {}),
                        data_csv=panel_source.get("data_csv"),
                        output_path=panel_path,
                    )

                panel_info[label] = str(panel_path)

        result = {
            "path": str(bundle_dir),
            "is_zip": False,
            "spec": spec,
            "style": style,
            "panels": panel_info,
        }

        # Generate composed figure exports
        if generate_exports:
            try:
                export_result = FigzService._generate_exports(
                    bundle_dir, spec, style, panels
                )
                result["exports"] = export_result.get("exports", {})
            except Exception as e:
                logger.warning(f"Failed to generate exports: {e}")

        return result

    @staticmethod
    def _save_as_zip(
        spec: Dict,
        style: Dict,
        panels: Optional[Dict],
        zip_path: Path,
        generate_exports: bool,
    ) -> Dict[str, Any]:
        """Save bundle as ZIP file."""
        # First create as directory, then zip
        temp_dir = zip_path.with_suffix(".figz.d.tmp")
        try:
            result = FigzService._save_as_directory(
                spec, style, panels, temp_dir, generate_exports
            )

            # Create ZIP
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in temp_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(temp_dir)
                        zf.write(file_path, arcname)

            result["path"] = str(zip_path)
            result["is_zip"] = True
            return result

        finally:
            # Clean up temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    @staticmethod
    def _generate_exports(
        bundle_dir: Path,
        spec: Dict,
        style: Dict,
        panels: Optional[Dict],
    ) -> Dict[str, Any]:
        """
        Generate composed figure images using scitex.fig.

        Args:
            bundle_dir: Bundle directory path
            spec: FigureSpec dictionary
            style: FigureStyle dictionary
            panels: Panel definitions

        Returns:
            Dictionary with export paths
        """
        os.environ['MPLBACKEND'] = 'Agg'

        try:
            import scitex as stx
        except ImportError:
            logger.warning("scitex not available, skipping export generation")
            return {}

        exports_dir = bundle_dir / FigzService.EXPORTS_DIR
        result = {"exports": {}}

        try:
            # Use scitex.fig.save_figz to generate composed figure
            figure_name = spec.get("figure_id", "Figure")

            # Collect panel paths
            panel_paths = {}
            for label in FigzService.PANEL_LABELS:
                pltz_dir = bundle_dir / f"{label}.pltz.d"
                if pltz_dir.exists():
                    panel_paths[label] = str(pltz_dir)

            if panel_paths:
                # Generate composed figure
                composed_path = exports_dir / f"{figure_name}.png"

                # Use stx.fig.save_figz for proper composition
                stx.fig.save_figz(panel_paths, str(bundle_dir / f"{figure_name}.figz"))

                result["exports"]["png"] = str(composed_path)

        except Exception as e:
            logger.exception(f"Failed to generate composed figure: {e}")

        return result

    @staticmethod
    def add_panel(
        bundle_path: Union[str, Path],
        label: str,
        panel_source: Union[str, Path, Dict],
    ) -> Dict[str, Any]:
        """
        Add or update a panel in an existing figz bundle.

        Args:
            bundle_path: Path to figz bundle
            label: Panel label (A, B, C, ...)
            panel_source: Path to pltz bundle or dict with spec/style

        Returns:
            Updated bundle info
        """
        bundle_path = Path(bundle_path)

        if label not in FigzService.PANEL_LABELS:
            raise ValueError(f"Invalid panel label: {label}")

        if bundle_path.suffix == ".figz":
            # ZIP format - extract, add panel, repack
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Extract
                with zipfile.ZipFile(bundle_path, 'r') as zf:
                    zf.extractall(temp_path)

                # Add panel
                panel_path = temp_path / f"{label}.pltz.d"
                FigzService._copy_panel_source(panel_source, panel_path)

                # Update spec
                FigzService._update_spec_panels(temp_path, label)

                # Repack
                with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for file in temp_path.rglob("*"):
                        if file.is_file():
                            arcname = file.relative_to(temp_path)
                            zf.write(file, arcname)
        else:
            # Directory format
            panel_path = bundle_path / f"{label}.pltz.d"
            FigzService._copy_panel_source(panel_source, panel_path)
            FigzService._update_spec_panels(bundle_path, label)

        return FigzService.load_bundle(bundle_path)

    @staticmethod
    def _copy_panel_source(
        panel_source: Union[str, Path, Dict],
        target_path: Path
    ) -> None:
        """Copy panel source to target path."""
        if isinstance(panel_source, (str, Path)):
            source_path = Path(panel_source)
            if source_path.is_dir():
                if target_path.exists():
                    shutil.rmtree(target_path)
                shutil.copytree(source_path, target_path)
            elif source_path.suffix == ".pltz":
                target_path.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(source_path, 'r') as zf:
                    zf.extractall(target_path)
        elif isinstance(panel_source, dict):
            PltzService.save_bundle(
                spec=panel_source.get("spec", {}),
                style=panel_source.get("style", {}),
                data_csv=panel_source.get("data_csv"),
                output_path=target_path,
            )

    @staticmethod
    def _update_spec_panels(bundle_dir: Path, new_label: str) -> None:
        """Update spec.json to include new panel."""
        spec_path = bundle_dir / FigzService.SPEC_FILE
        if spec_path.exists():
            with open(spec_path, 'r') as f:
                spec = json.load(f)
        else:
            spec = {"panels": {}}

        # Ensure panels dict exists
        if "panels" not in spec:
            spec["panels"] = {}

        # Add panel reference
        spec["panels"][new_label] = {
            "source": f"{new_label}.pltz.d",
            "label": new_label,
        }

        with open(spec_path, 'w') as f:
            json.dump(spec, f, indent=2)

    @staticmethod
    def remove_panel(
        bundle_path: Union[str, Path],
        label: str,
    ) -> Dict[str, Any]:
        """
        Remove a panel from a figz bundle.

        Args:
            bundle_path: Path to figz bundle
            label: Panel label to remove

        Returns:
            Updated bundle info
        """
        bundle_path = Path(bundle_path)

        if bundle_path.suffix == ".figz":
            # ZIP format
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Extract
                with zipfile.ZipFile(bundle_path, 'r') as zf:
                    zf.extractall(temp_path)

                # Remove panel
                panel_path = temp_path / f"{label}.pltz.d"
                if panel_path.exists():
                    shutil.rmtree(panel_path)

                # Update spec
                spec_path = temp_path / FigzService.SPEC_FILE
                if spec_path.exists():
                    with open(spec_path, 'r') as f:
                        spec = json.load(f)
                    if "panels" in spec and label in spec["panels"]:
                        del spec["panels"][label]
                    with open(spec_path, 'w') as f:
                        json.dump(spec, f, indent=2)

                # Repack
                with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for file in temp_path.rglob("*"):
                        if file.is_file():
                            arcname = file.relative_to(temp_path)
                            zf.write(file, arcname)
        else:
            # Directory format
            panel_path = bundle_path / f"{label}.pltz.d"
            if panel_path.exists():
                shutil.rmtree(panel_path)

            spec_path = bundle_path / FigzService.SPEC_FILE
            if spec_path.exists():
                with open(spec_path, 'r') as f:
                    spec = json.load(f)
                if "panels" in spec and label in spec["panels"]:
                    del spec["panels"][label]
                with open(spec_path, 'w') as f:
                    json.dump(spec, f, indent=2)

        return FigzService.load_bundle(bundle_path)

    @staticmethod
    def get_preview_image(
        bundle_path: Union[str, Path],
        image_type: str = "png"
    ) -> Optional[bytes]:
        """
        Get composed figure preview image from bundle exports.

        Args:
            bundle_path: Path to bundle
            image_type: Type of image (png, svg, overview)

        Returns:
            Image bytes or None if not found
        """
        bundle_path = Path(bundle_path)

        if bundle_path.suffix == ".figz":
            with zipfile.ZipFile(bundle_path, 'r') as zf:
                for name in zf.namelist():
                    if name.startswith(f"{FigzService.EXPORTS_DIR}/") and image_type in name:
                        with zf.open(name) as f:
                            return f.read()
        else:
            exports_dir = bundle_path / FigzService.EXPORTS_DIR
            if exports_dir.exists():
                for file in exports_dir.iterdir():
                    if file.is_file() and image_type in file.stem:
                        with open(file, 'rb') as f:
                            return f.read()

        return None

    @staticmethod
    def get_preview_base64(
        bundle_path: Union[str, Path],
        image_type: str = "png"
    ) -> Optional[str]:
        """Get preview image as base64 data URL."""
        image_data = FigzService.get_preview_image(bundle_path, image_type)
        if image_data:
            b64 = base64.b64encode(image_data).decode('utf-8')
            return f"data:image/png;base64,{b64}"
        return None

    @staticmethod
    def get_panel_previews(
        bundle_path: Union[str, Path]
    ) -> Dict[str, Optional[str]]:
        """
        Get preview images for all panels as base64.

        Args:
            bundle_path: Path to bundle

        Returns:
            Dict mapping panel labels to base64 data URLs
        """
        bundle_data = FigzService.load_bundle(bundle_path)
        panels = bundle_data.get("panels", {})

        previews = {}
        for label, panel_data in panels.items():
            if isinstance(panel_data, dict) and "path" in panel_data:
                previews[label] = PltzService.get_preview_base64(panel_data["path"])
            else:
                previews[label] = None

        return previews

    @staticmethod
    def get_layout_positions(layout: str) -> Dict[str, Dict]:
        """
        Get default panel positions for a layout.

        Args:
            layout: Layout string (1x1, 2x1, 2x2, etc.)

        Returns:
            Dict mapping panel labels to position info
        """
        layouts = {
            "1x1": {"A": {"x": 0, "y": 0, "width": 1, "height": 1}},
            "2x1": {
                "A": {"x": 0, "y": 0, "width": 0.5, "height": 1},
                "B": {"x": 0.5, "y": 0, "width": 0.5, "height": 1},
            },
            "1x2": {
                "A": {"x": 0, "y": 0, "width": 1, "height": 0.5},
                "B": {"x": 0, "y": 0.5, "width": 1, "height": 0.5},
            },
            "2x2": {
                "A": {"x": 0, "y": 0, "width": 0.5, "height": 0.5},
                "B": {"x": 0.5, "y": 0, "width": 0.5, "height": 0.5},
                "C": {"x": 0, "y": 0.5, "width": 0.5, "height": 0.5},
                "D": {"x": 0.5, "y": 0.5, "width": 0.5, "height": 0.5},
            },
            "1x3": {
                "A": {"x": 0, "y": 0, "width": 0.333, "height": 1},
                "B": {"x": 0.333, "y": 0, "width": 0.333, "height": 1},
                "C": {"x": 0.666, "y": 0, "width": 0.334, "height": 1},
            },
            "3x1": {
                "A": {"x": 0, "y": 0, "width": 1, "height": 0.333},
                "B": {"x": 0, "y": 0.333, "width": 1, "height": 0.333},
                "C": {"x": 0, "y": 0.666, "width": 1, "height": 0.334},
            },
            "2x3": {
                "A": {"x": 0, "y": 0, "width": 0.333, "height": 0.5},
                "B": {"x": 0.333, "y": 0, "width": 0.333, "height": 0.5},
                "C": {"x": 0.666, "y": 0, "width": 0.334, "height": 0.5},
                "D": {"x": 0, "y": 0.5, "width": 0.333, "height": 0.5},
                "E": {"x": 0.333, "y": 0.5, "width": 0.333, "height": 0.5},
                "F": {"x": 0.666, "y": 0.5, "width": 0.334, "height": 0.5},
            },
        }

        return layouts.get(layout, layouts["1x1"])

    @staticmethod
    def delete_bundle(bundle_path: Union[str, Path]) -> bool:
        """
        Delete a figz bundle.

        Args:
            bundle_path: Path to bundle

        Returns:
            True if deleted successfully
        """
        bundle_path = Path(bundle_path)

        if not bundle_path.exists():
            return False

        if bundle_path.is_file():
            bundle_path.unlink()
        else:
            shutil.rmtree(bundle_path)

        return True

    @staticmethod
    def save_canvas_as_bundle(
        project_owner: Optional[str],
        project_slug: Optional[str],
        figure_name: str,
        panels: List[Dict],
        canvas_size: Dict,
        theme: str = "light",
        user: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Auto-save canvas state as a figz bundle.

        This is called when the canvas changes to persist the figure state
        as a figz bundle. Supports both project-based and user-based storage.

        Args:
            project_owner: Project owner username (optional)
            project_slug: Project slug (optional)
            figure_name: Figure name (e.g., "Figure1")
            panels: List of panel definitions with:
                - label: Panel label (A, B, C, etc.)
                - pltz_path: Path to pltz bundle
                - position: {x_mm, y_mm}
                - size: {width_mm, height_mm}
            canvas_size: {width_mm, height_mm}
            theme: "light" or "dark"
            user: Django user object (for user-based storage fallback)

        Returns:
            Dictionary with bundle path and info

        Raises:
            ValueError: If neither project context nor user provided
        """
        # Determine output directory
        if project_owner and project_slug:
            # Save to project's scitex/vis/figures directory
            from apps.project_app.models import Project
            try:
                project = Project.objects.get(owner__username=project_owner, slug=project_slug)
                project_root = project.get_local_path()
            except Project.DoesNotExist:
                raise ValueError(f"Project not found: {project_owner}/{project_slug}")
            figures_dir = project_root / "scitex" / "vis" / "figures"
        elif user:
            # Save to user's bundle directory
            figures_dir = FigzService.get_bundle_base_path(user.id)
        else:
            raise ValueError("Either project context or user required")

        figures_dir.mkdir(parents=True, exist_ok=True)

        # Create figz bundle directory
        bundle_dir = figures_dir / f"{figure_name}.figz.d"
        bundle_dir.mkdir(parents=True, exist_ok=True)

        exports_dir = bundle_dir / FigzService.EXPORTS_DIR
        cache_dir = bundle_dir / FigzService.CACHE_DIR
        exports_dir.mkdir(exist_ok=True)
        cache_dir.mkdir(exist_ok=True)

        # Build spec.json
        spec = {
            "schema": {"name": "scitex.fig.figure", "version": "1.0.0"},
            "figure": {
                "id": figure_name,
                "title": figure_name,
                "caption": "",
            },
            "panels": [],
        }

        # Build style.json
        style = {
            "schema": {"name": "scitex.fig.style", "version": "1.0.0"},
            "size": {
                "width_mm": canvas_size.get("width_mm", 170),
                "height_mm": canvas_size.get("height_mm", 120),
            },
            "theme": {
                "mode": theme,
            },
            "panel_labels": {
                "visible": True,
                "font_size": 12,
                "position": "top-left",
            },
        }

        # Process panels
        for panel in panels:
            label = panel.get("label", "A")
            pltz_path = panel.get("pltz_path")
            position = panel.get("position", {})
            size = panel.get("size", {})

            # Determine plot reference
            if pltz_path:
                # Check if pltz bundle is already inside figz directory
                pltz_full_path = Path(pltz_path)
                if pltz_full_path.is_relative_to(bundle_dir):
                    plot_ref = str(pltz_full_path.relative_to(bundle_dir))
                else:
                    # Copy pltz bundle into figz directory
                    target_pltz_path = bundle_dir / f"{label}.pltz.d"
                    if pltz_full_path.exists() and pltz_full_path.is_dir():
                        if target_pltz_path.exists():
                            shutil.rmtree(target_pltz_path)
                        shutil.copytree(pltz_full_path, target_pltz_path)
                    plot_ref = f"{label}.pltz.d"
            else:
                plot_ref = f"{label}.pltz.d"

            # Add panel to spec
            spec["panels"].append({
                "id": label,
                "label": label,
                "plot": plot_ref,
                "position": {
                    "x_mm": position.get("x_mm", 0),
                    "y_mm": position.get("y_mm", 0),
                },
                "size": {
                    "width_mm": size.get("width_mm", 80),
                    "height_mm": size.get("height_mm", 68),
                },
            })

        # Save spec.json
        spec_path = bundle_dir / FigzService.SPEC_FILE
        with open(spec_path, 'w') as f:
            json.dump(spec, f, indent=2)

        # Save style.json
        style_path = bundle_dir / FigzService.STYLE_FILE
        with open(style_path, 'w') as f:
            json.dump(style, f, indent=2)

        # Save {figure_name}.json - combined spec+style for backward compatibility
        # This is needed for local GUI editor (stx.fig.edit) compatibility
        compat_spec = dict(spec)
        compat_spec["figure"]["styles"] = {
            "size": style["size"],
            "background": style.get("background", "#ffffff"),
        }
        compat_spec_path = bundle_dir / f"{figure_name}.json"
        with open(compat_spec_path, 'w') as f:
            json.dump(compat_spec, f, indent=2)

        logger.info(f"Saved figz bundle: {bundle_dir}")

        # Also create .figz ZIP file for cleaner tree view
        zip_path = figures_dir / f"{figure_name}.figz"
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in bundle_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(bundle_dir)
                        zf.write(file_path, arcname)
            logger.info(f"Created figz ZIP: {zip_path}")
        except Exception as e:
            logger.warning(f"Failed to create figz ZIP: {e}")

        return {
            "bundle_path": str(zip_path),  # Return ZIP path as primary
            "directory_path": str(bundle_dir),  # Keep directory path for editing
            "figure_name": figure_name,
            "panel_count": len(panels),
            "spec": spec,
            "style": style,
        }
