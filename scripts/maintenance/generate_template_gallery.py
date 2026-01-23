#!/usr/bin/env python3
"""
Generate gallery into static/shared/images/gallery/.

Run with appropriate permissions:
    sudo python3 scripts/maintenance/generate_template_gallery.py

This pre-generates all scitex.plt gallery examples into the static directory,
which serves as the single source of truth for gallery templates.

Note: Prefer using regenerate_gallery.sh which runs inside Docker.
"""

import os
import sys
from pathlib import Path

# Setup paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SCITEX_CODE_PATH = os.environ.get(
    'SCITEX_CODE_PATH',
    '/home/ywatanabe/proj/scitex-code'
)

# Add scitex to path
sys.path.insert(0, f"{SCITEX_CODE_PATH}/src")

# Set non-interactive backend
os.environ['MPLBACKEND'] = 'Agg'


def main():
    """Generate gallery into static directory."""
    # Single source of truth: static/shared/images/gallery/
    static_gallery_path = PROJECT_ROOT / "static" / "shared" / "images" / "gallery"

    print(f"Generating gallery to: {static_gallery_path}")

    try:
        import scitex as stx
    except ImportError as e:
        print(f"ERROR: Failed to import scitex: {e}")
        print(f"Make sure SCITEX_CODE_PATH is set correctly: {SCITEX_CODE_PATH}")
        sys.exit(1)

    # Create directory if needed
    static_gallery_path.mkdir(parents=True, exist_ok=True)

    # Generate all gallery plots
    result = stx.plt.gallery.generate(
        output_dir=str(static_gallery_path),
        figsize=(4, 3),
        dpi=150,
        save_csv=True,
        save_png=True,
        save_svg=True,
        save_pltz=True,
        verbose=True,
    )

    print()
    print("=" * 50)
    print("RESULTS")
    print("=" * 50)
    print(f"PNGs generated: {len(result.get('png', []))}")
    print(f"CSVs generated: {len(result.get('csv', []))}")
    print(f"PLTZs generated: {len(result.get('pltz', []))}")

    if result.get('errors'):
        print(f"\nErrors ({len(result['errors'])}):")
        for err in result['errors']:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("\nGallery generated successfully!")
        print(f"Location: {static_gallery_path}")


if __name__ == "__main__":
    main()
