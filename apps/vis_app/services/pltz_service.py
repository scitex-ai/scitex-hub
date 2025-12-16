"""
PltzBundle Service - Business logic for .pltz bundle operations.

Handles:
- Loading and saving .pltz bundles (directory and ZIP formats)
- Spec and style JSON management
- Data CSV operations
- Hitmap and geometry cache management
- Integration with scitex.io for bundle I/O
"""

import base64
import hashlib
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

logger = logging.getLogger(__name__)

# Ensure scitex is importable
SCITEX_CODE_PATH = os.environ.get(
    'SCITEX_CODE_PATH',
    '/home/ywatanabe/proj/scitex-code'
)
if SCITEX_CODE_PATH not in sys.path:
    sys.path.insert(0, f"{SCITEX_CODE_PATH}/src")


class PltzService:
    """Service for pltz bundle operations."""

    # Bundle structure constants
    SPEC_FILE = "spec.json"
    STYLE_FILE = "style.json"
    DATA_FILE = "data.csv"
    EXPORTS_DIR = "exports"
    CACHE_DIR = "cache"
    GEOMETRY_FILE = "geometry_px.json"
    MANIFEST_FILE = "render_manifest.json"

    @staticmethod
    def get_bundle_base_path(user_id: int) -> Path:
        """Get base path for user's pltz bundles."""
        return Path(settings.MEDIA_ROOT) / "vis" / "bundles" / "pltz" / str(user_id)

    @staticmethod
    def is_pltz_bundle(path: Union[str, Path]) -> bool:
        """
        Check if path is a valid pltz bundle.

        Args:
            path: Path to check

        Returns:
            True if valid pltz bundle
        """
        path = Path(path)

        # Check ZIP format
        if path.suffix == ".pltz" and path.is_file():
            try:
                with zipfile.ZipFile(path, 'r') as zf:
                    return PltzService.SPEC_FILE in zf.namelist()
            except zipfile.BadZipFile:
                return False

        # Check directory format
        if str(path).endswith(".pltz.d") and path.is_dir():
            return (path / PltzService.SPEC_FILE).exists()

        return False

    @staticmethod
    def load_bundle(bundle_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load a pltz bundle from disk.

        Supports:
        - Standalone bundles: A.pltz, A.pltz.d
        - Nested bundles: Figure1.figz/A.pltz.d, Figure1.figz.d/A.pltz.d

        Args:
            bundle_path: Path to .pltz.d directory, .pltz ZIP file, or nested path

        Returns:
            Dictionary with spec, style, data info, and metadata

        Raises:
            FileNotFoundError: If bundle not found
            ValueError: If invalid bundle format
        """
        bundle_path_str = str(bundle_path)

        # Check if this is a nested path (contains .figz or .figz.d in path)
        if '.figz/' in bundle_path_str or '.figz.d/' in bundle_path_str:
            return PltzService._load_nested_bundle(bundle_path_str)

        # Handle standalone bundles
        bundle_path = Path(bundle_path)

        if not bundle_path.exists():
            raise FileNotFoundError(f"Bundle not found: {bundle_path}")

        if not PltzService.is_pltz_bundle(bundle_path):
            raise ValueError(f"Invalid pltz bundle: {bundle_path}")

        result = {
            "path": str(bundle_path),
            "is_zip": bundle_path.suffix == ".pltz",
        }

        # Load from ZIP or directory
        if result["is_zip"]:
            result.update(PltzService._load_from_zip(bundle_path))
        else:
            result.update(PltzService._load_from_directory(bundle_path))

        return result

    @staticmethod
    def _load_nested_bundle(bundle_path: str) -> Dict[str, Any]:
        """
        Load a nested pltz bundle from inside a figz bundle.

        This handles paths like:
        - Figure1.figz/A.pltz.d
        - Figure1.figz.d/A.pltz.d

        Works transparently with both ZIP and directory formats.

        Args:
            bundle_path: Nested path to pltz bundle

        Returns:
            Dictionary with spec, style, data info, and metadata
        """
        try:
            from scitex.io.bundle import nested
        except ImportError:
            logger.warning("scitex.io.bundle not available")
            raise FileNotFoundError(f"Cannot load nested bundle without scitex: {bundle_path}")

        try:
            nested_data = nested.resolve(bundle_path)

            result = {
                "path": bundle_path,
                "is_nested": True,
                "is_zip": False,  # Nested bundles are accessed transparently
                "spec": nested_data.get("spec"),
                "style": nested_data.get("style"),
            }

            # Check for data
            if nested_data.get("data") is not None:
                import hashlib
                import pandas as pd
                df = nested_data["data"]
                if isinstance(df, pd.DataFrame):
                    csv_str = df.to_csv(index=False)
                    result["data_hash"] = hashlib.sha256(csv_str.encode()).hexdigest()

            # Get exports from file list
            exports = {}
            for f in nested_data.get("files", []):
                if "exports/" in f or f.endswith(".png") or f.endswith(".svg"):
                    stem = Path(f).stem
                    if "_hitmap" not in stem and "_overview" not in stem:
                        exports["png"] = f
                    elif "_hitmap" in stem:
                        exports["hitmap"] = f
                    elif "_overview" in stem:
                        exports["overview"] = f
            if exports:
                result["exports"] = exports

            return result

        except Exception as e:
            logger.warning(f"Failed to load nested bundle {bundle_path}: {e}")
            raise FileNotFoundError(f"Nested bundle not found: {bundle_path}")

    @staticmethod
    def _load_from_directory(bundle_dir: Path) -> Dict[str, Any]:
        """Load bundle contents from directory."""
        result = {}

        # Load spec.json
        spec_path = bundle_dir / PltzService.SPEC_FILE
        if spec_path.exists():
            with open(spec_path, 'r') as f:
                result["spec"] = json.load(f)

        # Load style.json
        style_path = bundle_dir / PltzService.STYLE_FILE
        if style_path.exists():
            with open(style_path, 'r') as f:
                result["style"] = json.load(f)

        # Check data.csv
        data_path = bundle_dir / PltzService.DATA_FILE
        if data_path.exists():
            result["data_path"] = str(data_path)
            result["data_hash"] = PltzService._compute_file_hash(data_path)

        # Check exports
        exports_dir = bundle_dir / PltzService.EXPORTS_DIR
        if exports_dir.exists():
            result["exports"] = {
                f.stem: str(f) for f in exports_dir.iterdir()
                if f.is_file()
            }

        # Load geometry cache
        cache_dir = bundle_dir / PltzService.CACHE_DIR
        geometry_path = cache_dir / PltzService.GEOMETRY_FILE
        if geometry_path.exists():
            with open(geometry_path, 'r') as f:
                result["geometry"] = json.load(f)

        # Load render manifest
        manifest_path = cache_dir / PltzService.MANIFEST_FILE
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                result["manifest"] = json.load(f)

        return result

    @staticmethod
    def _load_from_zip(zip_path: Path) -> Dict[str, Any]:
        """Load bundle contents from ZIP file."""
        result = {}

        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Load spec.json
            if PltzService.SPEC_FILE in zf.namelist():
                with zf.open(PltzService.SPEC_FILE) as f:
                    result["spec"] = json.load(f)

            # Load style.json
            if PltzService.STYLE_FILE in zf.namelist():
                with zf.open(PltzService.STYLE_FILE) as f:
                    result["style"] = json.load(f)

            # Check data.csv
            if PltzService.DATA_FILE in zf.namelist():
                result["data_in_zip"] = True
                with zf.open(PltzService.DATA_FILE) as f:
                    data = f.read()
                    result["data_hash"] = hashlib.sha256(data).hexdigest()

            # List exports
            exports = {}
            for name in zf.namelist():
                if name.startswith(f"{PltzService.EXPORTS_DIR}/"):
                    stem = Path(name).stem
                    exports[stem] = name
            if exports:
                result["exports"] = exports

            # Load geometry cache
            geometry_name = f"{PltzService.CACHE_DIR}/{PltzService.GEOMETRY_FILE}"
            if geometry_name in zf.namelist():
                with zf.open(geometry_name) as f:
                    result["geometry"] = json.load(f)

        return result

    @staticmethod
    def save_bundle(
        spec: Dict,
        style: Dict,
        data_csv: Optional[str] = None,
        output_path: Optional[Union[str, Path]] = None,
        user_id: Optional[int] = None,
        name: Optional[str] = None,
        as_zip: bool = False,
        generate_exports: bool = True,
    ) -> Dict[str, Any]:
        """
        Save a new pltz bundle.

        Args:
            spec: PltzSpec dictionary
            style: PltzStyle dictionary
            data_csv: CSV data string or path to CSV file
            output_path: Custom output path (optional)
            user_id: User ID for default path generation
            name: Bundle name (used for slug if output_path not provided)
            as_zip: If True, save as .pltz ZIP instead of .pltz.d directory
            generate_exports: If True, generate preview images

        Returns:
            Dictionary with bundle info and path

        Raises:
            ValueError: If neither output_path nor user_id provided
        """
        # Determine output path
        if output_path:
            bundle_path = Path(output_path)
        elif user_id and name:
            base_path = PltzService.get_bundle_base_path(user_id)
            slug = slugify(name)
            suffix = ".pltz" if as_zip else ".pltz.d"
            bundle_path = base_path / f"{slug}{suffix}"
        else:
            raise ValueError("Either output_path or (user_id, name) required")

        # Ensure parent directory exists
        bundle_path.parent.mkdir(parents=True, exist_ok=True)

        if as_zip:
            return PltzService._save_as_zip(
                spec, style, data_csv, bundle_path, generate_exports
            )
        else:
            return PltzService._save_as_directory(
                spec, style, data_csv, bundle_path, generate_exports
            )

    @staticmethod
    def _save_as_directory(
        spec: Dict,
        style: Dict,
        data_csv: Optional[str],
        bundle_dir: Path,
        generate_exports: bool,
    ) -> Dict[str, Any]:
        """Save bundle as directory structure."""
        # Create directory structure
        bundle_dir.mkdir(parents=True, exist_ok=True)
        exports_dir = bundle_dir / PltzService.EXPORTS_DIR
        cache_dir = bundle_dir / PltzService.CACHE_DIR
        exports_dir.mkdir(exist_ok=True)
        cache_dir.mkdir(exist_ok=True)

        # Save spec.json
        spec_path = bundle_dir / PltzService.SPEC_FILE
        with open(spec_path, 'w') as f:
            json.dump(spec, f, indent=2)

        # Save style.json
        style_path = bundle_dir / PltzService.STYLE_FILE
        with open(style_path, 'w') as f:
            json.dump(style, f, indent=2)

        # Save data.csv
        data_hash = None
        if data_csv:
            data_path = bundle_dir / PltzService.DATA_FILE
            if Path(data_csv).is_file():
                shutil.copy(data_csv, data_path)
            else:
                with open(data_path, 'w') as f:
                    f.write(data_csv)
            data_hash = PltzService._compute_file_hash(data_path)

        result = {
            "path": str(bundle_dir),
            "is_zip": False,
            "spec": spec,
            "style": style,
            "data_hash": data_hash,
        }

        # Generate exports using scitex
        if generate_exports:
            try:
                export_result = PltzService._generate_exports(bundle_dir, spec, style)
                result["exports"] = export_result.get("exports", {})
                result["geometry"] = export_result.get("geometry")
            except Exception as e:
                logger.warning(f"Failed to generate exports: {e}")

        return result

    @staticmethod
    def _save_as_zip(
        spec: Dict,
        style: Dict,
        data_csv: Optional[str],
        zip_path: Path,
        generate_exports: bool,
    ) -> Dict[str, Any]:
        """Save bundle as ZIP file."""
        # First create as directory, then zip
        temp_dir = zip_path.with_suffix(".pltz.d.tmp")
        try:
            result = PltzService._save_as_directory(
                spec, style, data_csv, temp_dir, generate_exports
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
    ) -> Dict[str, Any]:
        """
        Generate preview images and geometry cache using scitex.

        Args:
            bundle_dir: Bundle directory path
            spec: PltzSpec dictionary
            style: PltzStyle dictionary

        Returns:
            Dictionary with exports paths and geometry
        """
        os.environ['MPLBACKEND'] = 'Agg'

        try:
            import scitex as stx
        except ImportError:
            logger.warning("scitex not available, skipping export generation")
            return {}

        exports_dir = bundle_dir / PltzService.EXPORTS_DIR
        cache_dir = bundle_dir / PltzService.CACHE_DIR

        result = {"exports": {}}

        try:
            # Load data if available
            data_path = bundle_dir / PltzService.DATA_FILE
            df = None
            if data_path.exists():
                import pandas as pd
                df = pd.read_csv(data_path)

            # Get size from style
            size = style.get("size", {})
            width_mm = size.get("width_mm", 80)
            height_mm = size.get("height_mm", 68)

            # Create figure with scitex
            fig, ax = stx.plt.subplots(
                axes_width_mm=width_mm,
                axes_height_mm=height_mm,
            )

            # Render traces from spec
            traces = spec.get("traces", [])
            for trace in traces:
                PltzService._render_trace(ax, trace, df, style)

            # Apply axes labels
            axes_list = spec.get("axes", [])
            if axes_list:
                ax_spec = axes_list[0] if isinstance(axes_list, list) else axes_list.get("ax0", {})
                labels = ax_spec.get("labels", {})
                if labels.get("xlabel"):
                    ax.set_xlabel(labels["xlabel"])
                if labels.get("ylabel"):
                    ax.set_ylabel(labels["ylabel"])
                if labels.get("title"):
                    ax.set_title(labels["title"])

            # Save preview PNG
            plot_name = spec.get("plot_id", "plot")
            png_path = exports_dir / f"{plot_name}.png"
            stx.io.save(fig, png_path, dpi=150)
            result["exports"]["png"] = str(png_path)

            # Generate hitmap
            hitmap_path = exports_dir / f"{plot_name}_hitmap.png"
            # Hitmap generation would go here using element detection

            stx.plt.close(fig)

        except Exception as e:
            logger.exception(f"Failed to generate exports: {e}")

        return result

    @staticmethod
    def _render_trace(ax, trace: Dict, df, style: Dict) -> None:
        """Render a single trace on axes."""
        trace_type = trace.get("type", "line")
        x_col = trace.get("x_col")
        y_col = trace.get("y_col")

        if df is None or x_col is None or y_col is None:
            return

        x = df[x_col].values if x_col in df.columns else None
        y = df[y_col].values if y_col in df.columns else None

        if x is None or y is None:
            return

        # Get trace style
        trace_id = trace.get("id")
        trace_styles = style.get("traces", [])
        trace_style = next(
            (ts for ts in trace_styles if ts.get("trace_id") == trace_id),
            {}
        )

        color = trace_style.get("color")
        linewidth = trace_style.get("linewidth", 1.0)
        linestyle = trace_style.get("linestyle", "-")
        marker = trace_style.get("marker")
        label = trace.get("label")

        if trace_type == "line":
            ax.plot(x, y, color=color, linewidth=linewidth,
                   linestyle=linestyle, marker=marker, label=label)
        elif trace_type == "scatter":
            ax.scatter(x, y, c=color, s=trace_style.get("markersize", 20),
                      label=label)
        elif trace_type == "bar":
            ax.bar(x, y, color=color, label=label)

    @staticmethod
    def update_spec(bundle_path: Union[str, Path], spec: Dict) -> Dict[str, Any]:
        """
        Update spec.json in an existing bundle.

        Args:
            bundle_path: Path to bundle (can be nested: figz/pltz.d)
            spec: New spec dictionary

        Returns:
            Updated bundle info
        """
        bundle_path_str = str(bundle_path)

        # Check if this is a nested path (pltz inside figz)
        if '.figz/' in bundle_path_str or '.figz.d/' in bundle_path_str:
            try:
                from scitex.io.bundle import nested
                # Use scitex nested bundle write function
                file_path = f"{bundle_path_str}/{PltzService.SPEC_FILE}"
                nested.put_json(file_path, spec)
                logger.info(f"Updated nested spec via scitex: {file_path}")
                return {"path": bundle_path_str, "spec": spec}
            except Exception as e:
                logger.exception(f"Failed to update nested spec: {e}")
                raise

        bundle_path = Path(bundle_path)

        if bundle_path.suffix == ".pltz":
            # ZIP format - need to extract, update, repack
            return PltzService._update_zip_file(
                bundle_path, PltzService.SPEC_FILE, spec
            )
        else:
            # Directory format
            spec_path = bundle_path / PltzService.SPEC_FILE
            with open(spec_path, 'w') as f:
                json.dump(spec, f, indent=2)
            return {"path": str(bundle_path), "spec": spec}

    @staticmethod
    def update_style(bundle_path: Union[str, Path], style: Dict) -> Dict[str, Any]:
        """
        Update style.json in an existing bundle.

        Args:
            bundle_path: Path to bundle (can be nested: figz/pltz.d)
            style: New style dictionary

        Returns:
            Updated bundle info
        """
        bundle_path_str = str(bundle_path)

        # Check if this is a nested path (pltz inside figz)
        if '.figz/' in bundle_path_str or '.figz.d/' in bundle_path_str:
            try:
                from scitex.io.bundle import nested
                # Use scitex nested bundle write function
                file_path = f"{bundle_path_str}/{PltzService.STYLE_FILE}"
                nested.put_json(file_path, style)
                logger.info(f"Updated nested style via scitex: {file_path}")
                return {"path": bundle_path_str, "style": style}
            except Exception as e:
                logger.exception(f"Failed to update nested style: {e}")
                raise

        bundle_path = Path(bundle_path)

        if bundle_path.suffix == ".pltz":
            return PltzService._update_zip_file(
                bundle_path, PltzService.STYLE_FILE, style
            )
        else:
            style_path = bundle_path / PltzService.STYLE_FILE
            with open(style_path, 'w') as f:
                json.dump(style, f, indent=2)
            return {"path": str(bundle_path), "style": style}

    @staticmethod
    def _update_zip_file(zip_path: Path, filename: str, data: Dict) -> Dict[str, Any]:
        """Update a JSON file inside a ZIP archive."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Extract
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_path)

            # Update file
            file_path = temp_path / filename
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)

            # Repack
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file in temp_path.rglob("*"):
                    if file.is_file():
                        arcname = file.relative_to(temp_path)
                        zf.write(file, arcname)

        return {"path": str(zip_path), filename.replace(".json", ""): data}

    @staticmethod
    def get_preview_image(
        bundle_path: Union[str, Path],
        image_type: str = "png"
    ) -> Optional[bytes]:
        """
        Get preview image from bundle exports.

        Supports:
        - Standalone bundles: A.pltz, A.pltz.d
        - Nested bundles: Figure1.figz/A.pltz.d, Figure1.figz.d/A.pltz.d

        Args:
            bundle_path: Path to bundle (can include nested path)
            image_type: Type of image (png, svg, hitmap, overview)

        Returns:
            Image bytes or None if not found
        """
        bundle_path_str = str(bundle_path)

        logger.info(f"[get_preview_image] === Loading preview ===")
        logger.info(f"[get_preview_image] bundle_path: {bundle_path_str}")
        logger.info(f"[get_preview_image] image_type: {image_type}")

        # Check if this is a nested path (contains .figz or .figz.d in path)
        if '.figz/' in bundle_path_str or '.figz.d/' in bundle_path_str:
            logger.info(f"[get_preview_image] Detected nested bundle path")
            return PltzService._get_nested_preview_image(bundle_path_str, image_type)

        # Handle standalone bundles
        bundle_path = Path(bundle_path)

        logger.info(f"[get_preview_image] Standalone bundle, exists={bundle_path.exists()}")

        if bundle_path.suffix == ".pltz":
            # ZIP format
            logger.info(f"[get_preview_image] Loading from ZIP")
            return PltzService._get_preview_from_zip(bundle_path, image_type)
        else:
            # Directory format
            logger.info(f"[get_preview_image] Loading from directory")
            return PltzService._get_preview_from_directory(bundle_path, image_type)

    @staticmethod
    def _get_nested_preview_image(bundle_path: str, image_type: str = "png") -> Optional[bytes]:
        """
        Get preview image from a nested bundle using scitex.io.

        Delegates to scitex.io.get_nested_preview() which transparently handles:
        - Both ZIP (.pltz) and directory (.pltz.d) formats
        - Automatic .pltz → .pltz.d fallback via _find_bundle_path()
        - Nested paths (Figure1.figz.d/A.pltz.d)

        Args:
            bundle_path: Nested path to pltz bundle
            image_type: Type of image (png, hitmap, overview)

        Returns:
            Image bytes or None if not found
        """
        logger.info(f"[_get_nested_preview_image] Loading from nested path: {bundle_path}")

        try:
            from scitex.io.bundle import nested
        except ImportError:
            logger.warning("[_get_nested_preview_image] scitex.io.bundle not available")
            return None

        try:
            if image_type == "png":
                # nested.get_preview handles .pltz → .pltz.d fallback internally
                logger.info(f"[_get_nested_preview_image] Calling nested.get_preview({bundle_path})")
                result = nested.get_preview(bundle_path)
                if result:
                    logger.info(f"[_get_nested_preview_image] ✓ Got preview, size: {len(result)} bytes")
                else:
                    logger.warning(f"[_get_nested_preview_image] ✗ get_nested_preview returned None")
                return result
            else:
                # Get specific image type (hitmap, overview)
                files = nested.list_files(bundle_path)
                logger.info(f"[_get_nested_preview_image] Looking for {image_type} in files: {files}")
                for f in files:
                    if f.endswith('.png') and image_type in f:
                        logger.info(f"[_get_nested_preview_image] Found matching file: {f}")
                        return nested.get_file(f"{bundle_path}/{f}")
        except Exception as e:
            logger.warning(f"[_get_nested_preview_image] Failed to get nested preview from {bundle_path}: {e}")
            import traceback
            logger.debug(f"[_get_nested_preview_image] Traceback: {traceback.format_exc()}")

        return None

    @staticmethod
    def _get_preview_from_zip(zip_path: Path, image_type: str = "png") -> Optional[bytes]:
        """Get preview image from a ZIP bundle."""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                namelist = zf.namelist()

                # Handle ZIP files with .d directory structure inside
                # e.g., A.pltz contains A.pltz.d/exports/A.png
                d_prefix = f"{zip_path.stem}.pltz.d/"

                for name in namelist:
                    # Check both direct path and .d prefixed path
                    is_export = (
                        name.startswith(f"{PltzService.EXPORTS_DIR}/") or
                        name.startswith(f"{d_prefix}{PltzService.EXPORTS_DIR}/")
                    )

                    if not is_export:
                        continue

                    if image_type == "png":
                        if name.endswith('.png') and '_hitmap' not in name and '_overview' not in name:
                            with zf.open(name) as f:
                                return f.read()
                    elif image_type == "svg":
                        if name.endswith('.svg'):
                            with zf.open(name) as f:
                                return f.read()
                    elif image_type in name and name.endswith('.png'):
                        with zf.open(name) as f:
                            return f.read()
        except Exception as e:
            logger.warning(f"Failed to read preview from ZIP {zip_path}: {e}")

        return None

    @staticmethod
    def _get_preview_from_directory(bundle_dir: Path, image_type: str = "png") -> Optional[bytes]:
        """Get preview image from a directory bundle."""
        # Check both exports/ subdirectory AND bundle root (for different bundle formats)
        search_dirs = []

        exports_dir = bundle_dir / PltzService.EXPORTS_DIR
        if exports_dir.exists():
            search_dirs.append(exports_dir)

        # Also check bundle root for bundles with direct files (plot.png, plot.svg)
        search_dirs.append(bundle_dir)

        logger.info(f"[_get_preview_from_directory] Search dirs: {[str(d) for d in search_dirs]}")

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            files = list(search_dir.iterdir())
            logger.info(f"[_get_preview_from_directory] Files in {search_dir.name}: {[f.name for f in files if f.is_file()]}")

            for file in files:
                if not file.is_file():
                    continue

                # Match by image_type:
                # - "png": any .png file without _hitmap or _overview suffix
                # - "svg": any .svg file
                # - "hitmap": .png file with _hitmap in stem
                # - "overview": .png file with _overview in stem
                if image_type == "png":
                    if file.suffix == ".png" and "_hitmap" not in file.stem and "_overview" not in file.stem:
                        logger.info(f"[_get_preview_from_directory] ✓ Found preview: {file.name}")
                        with open(file, 'rb') as f:
                            data = f.read()
                            logger.info(f"[_get_preview_from_directory] Preview size: {len(data)} bytes")
                            return data
                elif image_type == "svg":
                    if file.suffix == ".svg":
                        logger.info(f"[_get_preview_from_directory] ✓ Found SVG preview: {file.name}")
                        with open(file, 'rb') as f:
                            return f.read()
                elif image_type in file.stem and file.suffix == ".png":
                    logger.info(f"[_get_preview_from_directory] ✓ Found {image_type} preview: {file.name}")
                    with open(file, 'rb') as f:
                        return f.read()

        logger.warning(f"[_get_preview_from_directory] ✗ No matching preview found for type: {image_type}")
        return None

    @staticmethod
    def get_preview_base64(
        bundle_path: Union[str, Path],
        image_type: str = "png"
    ) -> Optional[str]:
        """Get preview image as base64 data URL."""
        image_data = PltzService.get_preview_image(bundle_path, image_type)
        if image_data:
            b64 = base64.b64encode(image_data).decode('utf-8')
            return f"data:image/png;base64,{b64}"
        return None

    @staticmethod
    def get_geometry(bundle_path: Union[str, Path]) -> Optional[Dict]:
        """
        Get geometry cache from bundle.

        Supports:
        - Standalone bundles: A.pltz, A.pltz.d
        - Nested bundles: Figure1.figz/A.pltz.d, Figure1.figz.d/A.pltz.d

        Args:
            bundle_path: Path to bundle

        Returns:
            Geometry dictionary or None if not cached
        """
        bundle_path_str = str(bundle_path)

        # Check if this is a nested path (contains .figz or .figz.d in path)
        if '.figz/' in bundle_path_str or '.figz.d/' in bundle_path_str:
            return PltzService._get_nested_geometry(bundle_path_str)

        bundle_path = Path(bundle_path)

        if bundle_path.suffix == ".pltz":
            cache_name = f"{PltzService.CACHE_DIR}/{PltzService.GEOMETRY_FILE}"
            try:
                with zipfile.ZipFile(bundle_path, 'r') as zf:
                    if cache_name in zf.namelist():
                        with zf.open(cache_name) as f:
                            return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read geometry from ZIP {bundle_path}: {e}")
        else:
            geometry_path = bundle_path / PltzService.CACHE_DIR / PltzService.GEOMETRY_FILE
            if geometry_path.exists():
                with open(geometry_path, 'r') as f:
                    return json.load(f)

        return None

    @staticmethod
    def _get_nested_geometry(bundle_path: str) -> Optional[Dict]:
        """
        Get geometry from a nested bundle using scitex.io.

        Args:
            bundle_path: Nested path to pltz bundle

        Returns:
            Geometry dictionary or None if not found
        """
        logger.info(f"[_get_nested_geometry] Loading from nested path: {bundle_path}")

        try:
            from scitex.io.bundle import nested
        except ImportError:
            logger.warning("[_get_nested_geometry] scitex.io.bundle not available")
            return None

        try:
            geometry_file = f"cache/{PltzService.GEOMETRY_FILE}"
            result = nested.get_json(f"{bundle_path}/{geometry_file}")
            if result:
                logger.info(f"[_get_nested_geometry] ✓ Got geometry")
                return result
        except Exception as e:
            logger.warning(f"[_get_nested_geometry] Failed to get geometry from {bundle_path}: {e}")

        return None

    @staticmethod
    def get_data_csv(bundle_path: Union[str, Path]) -> Optional[str]:
        """
        Get data CSV content from bundle.

        Reads the CSV filename from spec.json["data"]["csv"] to support
        bundles with custom-named CSV files.

        Args:
            bundle_path: Path to bundle

        Returns:
            CSV content string or None if not found
        """
        bundle_path = Path(bundle_path)

        # First try to get CSV filename from spec.json
        csv_filename = None
        try:
            spec = PltzService.get_spec(bundle_path)
            if spec and "data" in spec and "csv" in spec["data"]:
                csv_filename = spec["data"]["csv"]
        except Exception:
            pass

        if bundle_path.suffix == ".pltz":
            with zipfile.ZipFile(bundle_path, 'r') as zf:
                # Try spec-referenced file first
                if csv_filename and csv_filename in zf.namelist():
                    with zf.open(csv_filename) as f:
                        return f.read().decode('utf-8')
                # Fall back to default data.csv
                if PltzService.DATA_FILE in zf.namelist():
                    with zf.open(PltzService.DATA_FILE) as f:
                        return f.read().decode('utf-8')
        else:
            # Directory-based bundle
            # Try spec-referenced file first
            if csv_filename:
                data_path = bundle_path / csv_filename
                if data_path.exists():
                    with open(data_path, 'r') as f:
                        return f.read()
            # Fall back to default data.csv
            data_path = bundle_path / PltzService.DATA_FILE
            if data_path.exists():
                with open(data_path, 'r') as f:
                    return f.read()
            # Fall back to any .csv file in the bundle
            csv_files = list(bundle_path.glob("*.csv"))
            if csv_files:
                with open(csv_files[0], 'r') as f:
                    return f.read()

        return None

    @staticmethod
    def _compute_file_hash(file_path: Path) -> str:
        """Compute SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def categorize_plot(spec: Dict) -> str:
        """
        Determine plot category from spec.

        Args:
            spec: PltzSpec dictionary

        Returns:
            Category string
        """
        traces = spec.get("traces", [])
        if not traces:
            return "other"

        trace_types = [t.get("type", "").lower() for t in traces]

        if any(t in ["line", "step", "stem"] for t in trace_types):
            return "line"
        elif "scatter" in trace_types:
            return "scatter"
        elif any(t in ["bar", "barh"] for t in trace_types):
            return "bar"
        elif any(t in ["histogram", "kde", "ecdf"] for t in trace_types):
            return "distribution"
        elif any(t in ["boxplot", "violinplot", "joyplot"] for t in trace_types):
            return "statistical"
        elif any(t in ["heatmap", "imshow", "contour"] for t in trace_types):
            return "heatmap"

        return "other"

    @staticmethod
    def render_preview(bundle_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Re-render preview images from bundle spec/style.

        Args:
            bundle_path: Path to pltz bundle (can be nested: figz/pltz.d)

        Returns:
            Dictionary with export paths and rendering info

        Raises:
            FileNotFoundError: If bundle not found
            ValueError: If invalid bundle format
        """
        bundle_path_str = str(bundle_path)

        # Check if this is a nested path (pltz inside figz)
        if '.figz/' in bundle_path_str or '.figz.d/' in bundle_path_str:
            return PltzService._render_nested_preview(bundle_path_str)

        bundle_path = Path(bundle_path)

        if not bundle_path.exists():
            raise FileNotFoundError(f"Bundle not found: {bundle_path}")

        if not PltzService.is_pltz_bundle(bundle_path):
            raise ValueError(f"Invalid pltz bundle: {bundle_path}")

        # Load current spec and style
        bundle_data = PltzService.load_bundle(bundle_path)
        spec = bundle_data.get("spec", {})
        style = bundle_data.get("style", {})

        # For ZIP format, extract to temp, render, repack
        if bundle_path.suffix == ".pltz":
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Extract
                with zipfile.ZipFile(bundle_path, 'r') as zf:
                    zf.extractall(temp_path)

                # Generate exports
                result = PltzService._generate_exports(temp_path, spec, style)

                # Repack
                with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for file in temp_path.rglob("*"):
                        if file.is_file():
                            arcname = file.relative_to(temp_path)
                            zf.write(file, arcname)

                return result
        else:
            # Directory format - render directly
            return PltzService._generate_exports(bundle_path, spec, style)

    @staticmethod
    def _render_nested_preview(bundle_path: str) -> Dict[str, Any]:
        """
        Re-render preview for a nested pltz bundle (inside figz).

        This extracts the nested bundle, renders, and writes results back.

        Args:
            bundle_path: Nested path like Figure1.figz/A.pltz.d

        Returns:
            Dictionary with export paths and rendering info
        """
        import tempfile
        from scitex.io.bundle import nested

        # Load bundle data using scitex
        bundle_data = nested.resolve(bundle_path)
        spec = bundle_data.get("spec", {})
        style = bundle_data.get("style", {})

        if not spec:
            raise ValueError(f"No spec found in nested bundle: {bundle_path}")

        # Create temp directory for rendering
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write spec and style to temp
            (temp_path / "spec.json").write_text(json.dumps(spec, indent=2))
            if style:
                (temp_path / "style.json").write_text(json.dumps(style, indent=2))

            # Copy data if exists
            if bundle_data.get("data") is not None:
                bundle_data["data"].to_csv(temp_path / "data.csv", index=False)

            # Generate exports in temp directory
            result = PltzService._generate_exports(temp_path, spec, style)

            # Write rendered files back to nested bundle
            exports_dir = temp_path / "exports"
            if exports_dir.exists():
                for export_file in exports_dir.iterdir():
                    if export_file.is_file():
                        file_data = export_file.read_bytes()
                        nested_path = f"{bundle_path}/exports/{export_file.name}"
                        nested.put_file(nested_path, file_data)
                        logger.info(f"Wrote export to nested bundle: {nested_path}")

            return result

    @staticmethod
    def delete_bundle(bundle_path: Union[str, Path]) -> bool:
        """
        Delete a pltz bundle.

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
    def create_from_plot(
        plot_type: str,
        data_csv: Optional[str] = None,
        data: Optional[Dict] = None,
        name: Optional[str] = None,
        output_dir: Optional[str] = None,
        project_owner: Optional[str] = None,
        project_slug: Optional[str] = None,
        figure_name: Optional[str] = None,
        panel_label: Optional[str] = None,
        user: Optional[Any] = None,
        gallery_category: Optional[str] = None,
        gallery_plot_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a pltz bundle from plot type and data using scitex.

        If gallery_category and gallery_plot_name are provided, copies from
        the gallery template instead of re-rendering (preserves exact plot).

        Args:
            plot_type: Type of plot (line, scatter, bar, histogram, etc.)
            data_csv: CSV data string
            data: Dictionary with data arrays (x, y, etc.)
            name: Bundle name
            output_dir: Custom output directory
            project_owner: Project owner username
            project_slug: Project slug
            figure_name: Figure name for organizing within project
            panel_label: Panel label (A, B, C, etc.)
            user: Django user object
            gallery_category: Gallery category (e.g., 'line', 'scatter')
            gallery_plot_name: Gallery plot name (e.g., 'plot', 'stx_line')

        Returns:
            Dictionary with bundle path, spec, style, geometry

        Raises:
            ValueError: If invalid plot type or missing data
        """
        import os
        os.environ['MPLBACKEND'] = 'Agg'

        try:
            import scitex as stx
            from scitex.io.bundle import copy
            from scitex.plt.io import save_layered_pltz_bundle
        except ImportError as e:
            logger.error(f"scitex not available: {e}")
            raise ValueError("scitex not available for rendering")

        import numpy as np
        import pandas as pd

        # Determine bundle name - use panel_label for consistency within figz bundles
        # For scientific rigor: consistent naming, no timestamps
        bundle_name = panel_label or name or "plot"

        # Determine output path
        if output_dir:
            bundle_dir = Path(output_dir) / f"{bundle_name}.pltz.d"
        elif project_owner and project_slug:
            # Save to project's scitex/vis/figures directory
            from apps.project_app.models import Project
            try:
                project = Project.objects.get(owner__username=project_owner, slug=project_slug)
                project_root = project.get_local_path()
            except Project.DoesNotExist:
                raise ValueError(f"Project not found: {project_owner}/{project_slug}")
            figures_dir = project_root / "scitex" / "vis" / "figures"

            if figure_name:
                # Create figz directory structure
                figz_dir = figures_dir / f"{figure_name}.figz.d"
                figz_dir.mkdir(parents=True, exist_ok=True)
                bundle_name = panel_label or 'A'
                bundle_dir = figz_dir / f"{bundle_name}.pltz.d"
            else:
                figures_dir.mkdir(parents=True, exist_ok=True)
                bundle_dir = figures_dir / f"{bundle_name}.pltz.d"
        elif user:
            # Fallback to user's bundle directory
            base_path = PltzService.get_bundle_base_path(user.id)
            bundle_dir = base_path / f"{bundle_name}.pltz.d"
        else:
            raise ValueError("Either output_dir, project info, or user required")

        bundle_dir.parent.mkdir(parents=True, exist_ok=True)

        # Clean up existing bundle if it exists (replace, don't accumulate)
        if bundle_dir.exists():
            import shutil
            shutil.rmtree(bundle_dir)
            logger.info(f"Cleaned up existing bundle: {bundle_dir}")

        # Try to copy from gallery template if category and plot name are provided
        # This preserves the exact pre-rendered plot instead of re-rendering
        copied_from_gallery = False
        if gallery_category and gallery_plot_name:
            try:
                from .gallery_generator import get_template_gallery_path
                gallery_path = get_template_gallery_path()
                source_bundle = gallery_path / gallery_category / f"{gallery_plot_name}.pltz.d"

                if source_bundle.exists():
                    copy(source_bundle, bundle_dir, overwrite=True)
                    copied_from_gallery = True
                    logger.info(f"Copied gallery bundle: {source_bundle} -> {bundle_dir}")
                else:
                    # Try .pltz format
                    source_zip = gallery_path / gallery_category / f"{gallery_plot_name}.pltz"
                    if source_zip.exists():
                        copy(source_zip, bundle_dir, overwrite=True)
                        copied_from_gallery = True
                        logger.info(f"Copied gallery bundle (ZIP): {source_zip} -> {bundle_dir}")
                    else:
                        logger.warning(f"Gallery bundle not found: {source_bundle} or {source_zip}")
            except Exception as e:
                logger.warning(f"Failed to copy from gallery, will re-render: {e}")

        # If not copied from gallery, generate the plot
        if not copied_from_gallery:
            # Prepare data
            df = None
            if data_csv:
                from io import StringIO
                df = pd.read_csv(StringIO(data_csv))
            elif data:
                df = pd.DataFrame(data)
            else:
                # Generate demo data based on plot type
                df = PltzService._generate_demo_data(plot_type)

            # Create figure using scitex
            fig, ax = stx.plt.subplots(axes_width_mm=80, axes_height_mm=68)

            # Render the plot based on type
            PltzService._render_plot_type(ax, plot_type, df)

            # Save as pltz bundle using scitex's layered bundle saver
            # Use bundle_name for consistent file naming (e.g., A.csv, A.png)
            save_layered_pltz_bundle(
                fig=fig,
                bundle_dir=bundle_dir,
                basename=bundle_name,
                dpi=150,
                csv_df=df,
            )

            stx.plt.close(fig)

        # Load the created bundle to return spec/style/geometry
        bundle_data = PltzService.load_bundle(bundle_dir)

        # Create .pltz ZIP file using scitex (Django is thin layer, logic in scitex)
        zip_path = None
        try:
            from scitex.io.bundle import zip_directory
            zip_path = zip_directory(bundle_dir)
            logger.info(f"Created pltz ZIP via scitex: {zip_path}")
        except ImportError:
            logger.warning("scitex.io.bundle.zip_directory not available")
        except Exception as e:
            logger.warning(f"Failed to create pltz ZIP: {e}")

        return {
            "bundle_path": str(zip_path) if zip_path else str(bundle_dir),
            "directory_path": str(bundle_dir),
            "name": bundle_name,
            "spec": bundle_data.get("spec"),
            "style": bundle_data.get("style"),
            "geometry": bundle_data.get("geometry"),
            "exports": bundle_data.get("exports"),
        }

    @staticmethod
    def _generate_demo_data(plot_type: str) -> "pd.DataFrame":
        """Generate demo data for a plot type."""
        import numpy as np
        import pandas as pd

        n = 50

        if plot_type in ["line", "scatter", "step", "stem"]:
            x = np.linspace(0, 10, n)
            y = np.sin(x) + np.random.normal(0, 0.1, n)
            return pd.DataFrame({"x": x, "y": y})

        elif plot_type in ["bar", "barh"]:
            categories = [f"Cat{i}" for i in range(8)]
            values = np.random.randint(10, 100, len(categories))
            return pd.DataFrame({"category": categories, "value": values})

        elif plot_type in ["histogram", "kde", "ecdf"]:
            data = np.random.normal(50, 15, 200)
            return pd.DataFrame({"value": data})

        elif plot_type in ["boxplot", "violinplot"]:
            groups = []
            values = []
            for g in ["A", "B", "C", "D"]:
                n_points = 30
                groups.extend([g] * n_points)
                values.extend(np.random.normal(50 + ord(g) * 5, 10, n_points))
            return pd.DataFrame({"group": groups, "value": values})

        elif plot_type == "heatmap":
            data = np.random.rand(8, 8)
            rows = [f"R{i}" for i in range(8)]
            cols = [f"C{i}" for i in range(8)]
            return pd.DataFrame(data, index=rows, columns=cols)

        elif plot_type == "pie":
            labels = ["A", "B", "C", "D", "E"]
            values = np.random.randint(10, 50, len(labels))
            return pd.DataFrame({"label": labels, "value": values})

        else:
            # Default: simple line data
            x = np.linspace(0, 10, n)
            y = x ** 2
            return pd.DataFrame({"x": x, "y": y})

    @staticmethod
    def _render_plot_type(ax, plot_type: str, df: "pd.DataFrame") -> None:
        """Render specific plot type on axes."""
        import numpy as np

        # Find x/y columns flexibly (handles both simple 'x','y' and complex column names)
        x_col = None
        y_col = None
        for col in df.columns:
            if col == 'x' or col.endswith('_x') or '_variable-x' in col:
                x_col = col
            elif col == 'y' or col.endswith('_y') or '_variable-y' in col:
                y_col = col

        if plot_type == "line":
            if x_col and y_col:
                ax.plot(df[x_col], df[y_col], label="Series 1")
                ax.set_xlabel("X")
                ax.set_ylabel("Y")
                ax.legend()
            elif "x" in df.columns and "y" in df.columns:
                ax.plot(df["x"], df["y"], label="Series 1")
                ax.set_xlabel("X")
                ax.set_ylabel("Y")
                ax.legend()

        elif plot_type == "scatter":
            if "x" in df.columns and "y" in df.columns:
                ax.scatter(df["x"], df["y"], label="Data")
                ax.set_xlabel("X")
                ax.set_ylabel("Y")
                ax.legend()

        elif plot_type == "bar":
            if "category" in df.columns and "value" in df.columns:
                ax.bar(df["category"], df["value"])
                ax.set_xlabel("Category")
                ax.set_ylabel("Value")
            elif "x" in df.columns and "y" in df.columns:
                ax.bar(df["x"], df["y"])

        elif plot_type == "barh":
            if "category" in df.columns and "value" in df.columns:
                ax.barh(df["category"], df["value"])
                ax.set_xlabel("Value")
                ax.set_ylabel("Category")

        elif plot_type == "histogram":
            if "value" in df.columns:
                ax.hist(df["value"], bins=20, edgecolor='white')
                ax.set_xlabel("Value")
                ax.set_ylabel("Frequency")
            elif "x" in df.columns:
                ax.hist(df["x"], bins=20, edgecolor='white')

        elif plot_type == "step":
            if "x" in df.columns and "y" in df.columns:
                ax.step(df["x"], df["y"], where='mid', label="Steps")
                ax.set_xlabel("X")
                ax.set_ylabel("Y")
                ax.legend()

        elif plot_type == "stem":
            if "x" in df.columns and "y" in df.columns:
                ax.stem(df["x"], df["y"])
                ax.set_xlabel("X")
                ax.set_ylabel("Y")

        elif plot_type == "boxplot":
            if "group" in df.columns and "value" in df.columns:
                groups = df["group"].unique()
                data = [df[df["group"] == g]["value"].values for g in groups]
                ax.boxplot(data, tick_labels=groups)
                ax.set_xlabel("Group")
                ax.set_ylabel("Value")

        elif plot_type == "violinplot":
            if "group" in df.columns and "value" in df.columns:
                groups = df["group"].unique()
                data = [df[df["group"] == g]["value"].values for g in groups]
                ax.violinplot(data, positions=range(len(groups)))
                ax.set_xticks(range(len(groups)))
                ax.set_xticklabels(groups)
                ax.set_xlabel("Group")
                ax.set_ylabel("Value")

        elif plot_type == "heatmap":
            # For heatmap, use all numeric columns as matrix
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                data = df[numeric_cols].values
                im = ax.imshow(data, cmap='viridis', aspect='auto')

        elif plot_type == "pie":
            if "label" in df.columns and "value" in df.columns:
                # Pie chart needs figure-level, use axes for simplicity
                ax.pie(df["value"], labels=df["label"], autopct='%1.1f%%')
                ax.axis('equal')

        elif plot_type == "area":
            if "x" in df.columns and "y" in df.columns:
                ax.fill_between(df["x"], df["y"], alpha=0.5, label="Area")
                ax.plot(df["x"], df["y"])
                ax.set_xlabel("X")
                ax.set_ylabel("Y")
                ax.legend()

        else:
            # Default fallback: try line plot
            if "x" in df.columns and "y" in df.columns:
                ax.plot(df["x"], df["y"], label="Data")
                ax.set_xlabel("X")
                ax.set_ylabel("Y")
                ax.legend()
            elif len(df.columns) >= 2:
                ax.plot(df.iloc[:, 0], df.iloc[:, 1], label="Data")
                ax.legend()
