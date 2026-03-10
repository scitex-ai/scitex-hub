#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-12-10 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/scripts/maintenance/_regenerate_gallery_worker.py
#
# Worker script for gallery regeneration.
# Called by regenerate_gallery.sh
# Path resolution in stx.io.save is relative to THIS script's location.

import sys

sys.path.insert(0, "/home/ywatanabe/proj/scitex-code/src")
sys.path.insert(0, "/app")

import matplotlib

matplotlib.use("Agg")
import warnings

warnings.filterwarnings("ignore")

import json
import os
from pathlib import Path
import scitex as stx

# Output paths - use static directory as single source of truth
OUTPUT_DIR = "/app/static/shared/images/gallery"


def add_element_bboxes_to_json(json_path, png_path, csv_path=None):
    """Re-render plot from recipe and extract element bboxes."""
    from PIL import Image
    import pandas as pd

    try:
        # Load existing metadata
        with open(json_path, "r") as f:
            metadata = json.load(f)

        # Get actual image dimensions
        img = Image.open(png_path)
        img_width, img_height = img.size

        # Load CSV data if available
        csv_data = None
        if csv_path and os.path.exists(csv_path):
            try:
                csv_data = pd.read_csv(csv_path)
            except Exception:
                pass

        # Re-create the figure to extract element bboxes
        # This requires re-rendering the plot with the same parameters
        fig, ax = stx.plt.subplots(figsize=(4, 3), dpi=150)

        # Get axes info from metadata
        axes_info = metadata.get("axes", {})
        ax_info = axes_info.get("ax_00", {})
        calls = ax_info.get("calls", [])

        # Get underlying mpl axes for consistent extraction
        mpl_ax = ax._axis_mpl if hasattr(ax, "_axis_mpl") else ax

        # Try to re-render each call
        for call in calls:
            method = call.get("method", "")
            data_ref = call.get("data_ref", {})

            try:
                # Try to extract data from CSV based on method
                if csv_data is not None and len(csv_data.columns) > 0:
                    if method == "boxplot" and "data" in data_ref:
                        # Boxplot - get data columns
                        data_cols = [c for c in csv_data.columns if "data" in c.lower()]
                        if data_cols:
                            data = [csv_data[c].dropna().values for c in data_cols]
                            mpl_ax.boxplot(data)
                            continue
                    elif method in ["stx_mean_std", "stx_mean_ci", "stx_median_iqr"]:
                        # Time series with error bands
                        x_col = [c for c in csv_data.columns if "_x" in c.lower()]
                        y_cols = [c for c in csv_data.columns if "y_" in c.lower()]
                        if x_col and y_cols:
                            x = csv_data[x_col[0]].values
                            y = csv_data[y_cols[0]].values if y_cols else None
                            if y is not None:
                                mpl_ax.plot(x, y)
                                continue

                # Handle simple plot types - with or without CSV data
                if method in [
                    "plot",
                    "scatter",
                    "bar",
                    "stx_bar",
                    "stx_barh",
                    "barh",
                    "stx_scatter",
                    "stx_line",
                    "step",
                ]:
                    # Get label from call kwargs if available
                    call_kwargs = call.get("kwargs", {})
                    label = call_kwargs.get(
                        "label", call.get("id", f"trace_{len(calls)}")
                    )

                    # Try to get data from CSV or generate dummy data
                    # Look for columns matching this call's data_ref
                    x, y = None, None
                    if csv_data is not None and len(csv_data.columns) >= 2:
                        x_ref = data_ref.get("x", "")
                        y_ref = data_ref.get("y", "")
                        # Find matching columns
                        for col in csv_data.columns:
                            if x_ref and x_ref in col:
                                x = csv_data[col].dropna().values
                            elif y_ref and y_ref in col:
                                y = csv_data[col].dropna().values
                        # Fallback to positional columns
                        if x is None or y is None:
                            x = csv_data.iloc[:, 0].values
                            y = csv_data.iloc[:, 1].values

                    if x is None or y is None:
                        # Generate dummy data for plots without CSV
                        # Use 4 data points as typical for bar plots
                        x = list(range(4))
                        y = [10, 20, 30, 40]

                    if method in ["scatter", "stx_scatter"]:
                        mpl_ax.scatter(x, y, label=label)
                    elif method in ["bar", "stx_bar"]:
                        mpl_ax.bar(x, y, label=label)
                    elif method in ["barh", "stx_barh"]:
                        mpl_ax.barh(x, y, label=label)
                    elif method == "step":
                        mpl_ax.step(x, y, label=label)
                    else:
                        mpl_ax.plot(x, y, label=label)
            except Exception as e:
                print(f"  Warning: Could not re-render {method}: {e}")

        # Extract element bboxes - use underlying matplotlib axes for consistency
        from apps.workspace.vis_app.services.plot_renderer.element_bboxes import (
            extract_element_bboxes,
        )

        mpl_ax = ax._axis_mpl if hasattr(ax, "_axis_mpl") else ax
        mpl_fig = fig.figure if hasattr(fig, "figure") else fig
        renderer = mpl_fig.canvas.get_renderer()
        element_bboxes = extract_element_bboxes(
            mpl_fig, mpl_ax, renderer, img_width, img_height
        )

        stx.plt.close(fig)

        if element_bboxes:
            # Add element_bboxes to metadata
            metadata["element_bboxes"] = element_bboxes

            # Write updated metadata
            with open(json_path, "w") as f:
                json.dump(metadata, f, indent=4)

            return True, len(element_bboxes)
        return False, 0

    except Exception as e:
        print(f"  Error processing {json_path}: {e}")
        return False, 0


def main():
    print(f"Generating gallery to: {OUTPUT_DIR}")

    result = stx.plt.gallery.generate(
        output_dir=OUTPUT_DIR,
        figsize=(4, 3),
        dpi=150,
        save_csv=True,
        save_png=True,
        save_svg=True,
        save_pltz=True,
        verbose=False,
    )

    print(
        f"Generated {len(result['png'])} PNG, {len(result.get('pltz', []))} PLTZ bundles"
    )
    if result["errors"]:
        print(f"Errors: {len(result['errors'])}")
        for err in result["errors"]:
            print(f"  - {err}")

    # Post-process: add element_bboxes to JSON files
    print("\nAdding element_bboxes to JSON metadata...")
    gallery_path = Path(OUTPUT_DIR)
    success_count = 0
    total_count = 0

    for json_path in gallery_path.rglob("*.json"):
        total_count += 1
        png_path = json_path.with_suffix(".png")
        csv_path = json_path.with_suffix(".csv")

        if png_path.exists():
            success, num_elements = add_element_bboxes_to_json(
                str(json_path),
                str(png_path),
                str(csv_path) if csv_path.exists() else None,
            )
            if success:
                success_count += 1
                print(f"  Added {num_elements} element bboxes to {json_path.name}")

    print(f"\nElement bboxes added to {success_count}/{total_count} JSON files")

    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
