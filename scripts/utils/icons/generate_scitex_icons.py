#!/usr/bin/env python3
"""
Generate SciTeX icon variants with different colors and backgrounds.

Usage:
    python scripts/generate_scitex_icons.py [--output-dir PATH] [--list-colors]

This script generates SVG icon variants with the naming convention:
    scitex-icon-{fill_color}-bg-{bg_color}.svg

Special backgrounds:
    - transparent: No background circle
    - camo: Camouflage pattern background
"""

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path

# SciTeX color palette
COLORS = {
    "navy": "#1a2a40",      # --_scitex-01
    "navy-mid": "#34495e",  # --_scitex-02
    "slate": "#506b7a",     # --_scitex-03
    "steel": "#6c8ba0",     # --_scitex-04
    "green": "#4a9b7e",     # --workspace-icon-primary
    "white": "#ffffff",
    "black": "#000000",
    # Gray variations
    "gray": "#6b7280",      # Medium gray
    "gray-100": "#f3f4f6",  # Lightest
    "gray-200": "#e5e7eb",
    "gray-300": "#d1d5db",
    "gray-400": "#9ca3af",
    "gray-500": "#6b7280",  # Same as gray
    "gray-600": "#4b5563",
    "gray-700": "#374151",
    "gray-800": "#1f2937",
    "gray-900": "#111827",  # Darkest
    # Dark color variations
    "dark-navy": "#0f1a2a",
    "dark-green": "#2d5f4d",
    "dark-gray": "#1f2937",  # Same as gray-800
}

# Define which combinations to generate
COMBINATIONS = [
    # (fill_color, bg_color)
    # White icon variants
    ("white", "navy"),
    ("white", "green"),
    ("white", "black"),
    ("white", "transparent"),
    ("white", "camo"),
    # Navy icon variants
    ("navy", "white"),
    ("navy", "transparent"),
    # Green icon variants
    ("green", "white"),
    ("green", "navy"),
    ("green", "transparent"),
    # Black icon variants
    ("black", "white"),
    ("black", "transparent"),
    ("black", "camo"),
    # Transparent (cutout) icon variants - snake is transparent, background is solid
    ("transparent", "white"),
    ("transparent", "navy"),
    ("transparent", "green"),
    ("transparent", "black"),
    # Camo snake variants (green/orig)
    ("camo-green", "white"),
    ("camo-green", "navy"),
    ("camo-green", "black"),
    ("camo-green", "transparent"),
    # Camo snake variants (navy)
    ("camo-navy", "white"),
    ("camo-navy", "green"),
    ("camo-navy", "transparent"),
    # Camo snake variants (desert)
    ("camo-desert", "white"),
    ("camo-desert", "navy"),
    ("camo-desert", "transparent"),
    # Camo snake variants (arctic)
    ("camo-arctic", "navy"),
    ("camo-arctic", "black"),
    ("camo-arctic", "transparent"),
    # Camo snake variants (urban)
    ("camo-urban", "white"),
    ("camo-urban", "transparent"),
    # Camo background variants (green/orig)
    ("white", "camo-green"),
    ("black", "camo-green"),
    # Camo background variants (navy)
    ("white", "camo-navy"),
    # Camo background variants (desert)
    ("black", "camo-desert"),
    # Camo background variants (arctic)
    ("navy", "camo-arctic"),
    # Camo background variants (urban)
    ("white", "camo-urban"),
    # Camo gray snake variants
    ("camo-gray-light", "navy"),
    ("camo-gray-light", "black"),
    ("camo-gray-light", "transparent"),
    ("camo-gray", "white"),
    ("camo-gray", "navy"),
    ("camo-gray", "transparent"),
    ("camo-gray-dark", "white"),
    ("camo-gray-dark", "transparent"),
    # Camo gray background variants
    ("white", "camo-gray-light"),
    ("navy", "camo-gray-light"),
    ("white", "camo-gray"),
    ("black", "camo-gray"),
    ("white", "camo-gray-dark"),
    ("green", "camo-gray-dark"),
    # Gray snake variants
    ("gray", "white"),
    ("gray", "transparent"),
    ("gray-300", "navy"),
    ("gray-300", "transparent"),
    ("gray-600", "white"),
    ("gray-600", "transparent"),
    ("gray-800", "white"),
    ("gray-800", "transparent"),
    # Gray background variants
    ("white", "gray"),
    ("white", "gray-600"),
    ("white", "gray-800"),
    ("navy", "gray-300"),
    ("green", "gray-800"),
    # Dark variants
    ("dark-navy", "white"),
    ("dark-navy", "transparent"),
    ("dark-green", "white"),
    ("dark-green", "transparent"),
    ("dark-gray", "white"),
    ("dark-gray", "transparent"),
    ("white", "dark-navy"),
    ("white", "dark-green"),
    ("white", "dark-gray"),
    ("green", "dark-navy"),
]

# Snake SVG paths (extracted from original)
SNAKE_PATHS = [
    "m934.04,1199.85c-.1-.02-.22-.05-.34-.05-.34-.02-.8-.05-1.33-.05-.19-.29-.34-.49-.44-.63-.44-.63-.02-.24.8.17.46.24.97.44,1.31.56Z",
    "m1733.04,862.1c-1.25-10.54-3.55-19.84-6.08-28.08-2.58-8.26-5.45-15.48-8.33-21.77-5.83-12.56-11.51-21.35-15.67-27.01-2.07-2.83-3.74-4.87-4.87-6.24-.98-1.12-1.53-1.79-1.72-1.95.07.16.46.93,1.14,2.32.77,1.58,1.86,3.95,3.11,7.15,2.55,6.36,5.78,16.06,8.1,28.9,2.27,12.76,3.76,28.94,1.23,46.65-1.25,8.77-3.67,17.87-7.75,26.04-4.02,8.17-9.84,14.99-17.01,19.19-3.53,2.13-7.52,3.6-11.81,4.67-4.34,1-9.07,1.46-14.18,1.44-10.19-.02-21.82-2.2-34.05-6.01-3.04-.97-5.31-1.81-9.33-3.16l-2.74-.93c.12.02.19.02.23.02-.09-.09-.42-.16-.44-.19l-.63-.26-1.25-.51c-1.72-.67-3.41-1.35-5.11-2.02-6.8-2.79-13.6-5.78-20.31-8.98-13.39-6.55-26.62-13.97-38.74-22.68-12.12-8.66-23.33-18.29-32.05-28.99-8.87-10.63-15.27-21.93-18.94-33.21-1.86-5.66-3.06-11.3-3.64-17.06-.7-5.71-.79-11.51-.46-17.5.58-11.93,3.2-24.86,7.22-38.88,4.15-14.02,9.89-29.1,17.17-44.89,1.88-3.92,3.67-7.94,5.66-11.95.95-2.02,2-4.04,3.02-6.08l1.55-3.02c.51-1.02,1-1.86,1.51-2.79l1.46-2.72,1.69-3.27,1.95-3.81.97-1.9.49-.95.02-.02c-.02.14-.16.53.28-.51,4.39-9.59,8.4-20.21,11.49-32.1,3.02-11.86,5.06-25.02,5.41-39.04.35-13.99-1.02-28.8-4.53-43.28-3.46-14.44-8.87-28.36-15.5-40.92-6.61-12.51-14.39-23.6-22.54-33.28-16.39-19.45-33.82-33.21-50.62-44.28-16.85-11.05-33.4-19.24-49.53-26.11-32.26-13.44-63.38-21.33-94.18-26.62-30.8-5.22-61.25-7.47-91.68-7.77-60.85-.23-121.66,7.06-183.28,23.05-30.8,8.03-61.78,18.5-92.79,32.33-15.53,6.89-31.01,14.78-46.44,23.74-15.41,9.03-30.8,19.03-45.84,30.77-14.99,11.7-29.78,24.83-43.68,39.97-6.94,7.61-13.62,15.67-20.05,24.21-1.6,2.14-3.18,4.29-4.69,6.52-1.55,2.18-3.11,4.41-4.6,6.71-1.53,2.27-2.9,4.36-4.76,7.33l-2.58,4.18-1.11,1.88-.65,1.14-3.57,6.41-3.37,6.38c-2.25,4.22-4.39,8.7-6.5,13.18-2.14,4.41-4.13,9.07-6.1,13.79-2,4.62-3.81,9.54-5.59,14.41-7.1,19.66-12.7,41.22-15.13,64.38-2.46,23.09-1.97,47.6,2.67,71.39l1.79,8.87,2.25,8.75c1.42,5.87,3.39,11.44,5.25,17.13,3.99,11.07,8.54,21.91,13.86,31.89,10.42,20.21,23,37.78,36.25,53.13,13.28,15.39,27.27,28.71,41.47,40.43,28.43,23.46,57.51,41.43,86.52,56.86,29.03,15.34,58,28.11,86.92,39.46,57.84,22.58,115.37,39.83,172.6,54.68,14.32,3.64,28.52,7.5,42.59,11.63,14.06,4.15,28.01,8.59,41.94,13.02,7.06,2.18,14.09,4.36,21.12,6.52l10.19,3.04,5.08,1.51,1.44.42,1.07.35,2.11.67c11.37,3.64,22.37,7.59,32.77,12.09,20.86,8.96,39.73,19.66,54.98,31.63,7.59,5.94,14.32,12.14,19.87,18.43,5.55,6.27,9.98,12.53,13.3,18.43,3.2,5.94,5.38,11.51,6.45,16.48.6,2.51.79,4.85,1,7.03.02,2.23.09,4.25-.09,6.22-.46,3.9-1.16,7.4-2.46,10.98-1.16,3.5-2.81,7.22-4.94,11.19-4.15,8.01-10.82,17.41-20.08,27.36-9.33,9.93-21.21,20.15-35,29.73l-2.51,1.76-2.02,1.35-2,1.37-4.02,2.53-6.03,3.78c-2.18,1.35-4.34,2.72-6.55,3.99-8.77,5.25-17.52,10.28-26.27,15.09-17.52,9.59-35,18.29-52.17,25.92-17.17,7.61-34.07,14.25-50.22,19.29-16.15,5.13-31.59,8.7-45.14,10.42-6.78.88-13.07,1.28-18.75,1.35-5.64.09-10.61-.3-14.9-.88-8.59-1.28-14.23-3.04-19.54-6.8-5.36-3.71-10.4-10.65-13.97-21.03-1.74-5.13-3.11-11-3.99-17.34l-.32-2.41-.16-1.18-.09-.98c-.14-1.28-.28-2.53-.44-3.85-.07-2.46-.12-4.9-.21-7.36l-.05-1.81c-.02.53-.02.84-.05,1v-1.67l-.02-4.08c-.14-21.79-1.3-43.54-3.76-65.59-2.48-22.05-6.43-44.33-13.65-67.68-3.57-11.65-8.19-23.58-14.25-35.67-6.2-12.07-13.76-24.41-23.86-36.18-9.98-11.72-22.49-22.77-36.65-31.22-14.13-8.52-29.52-14.41-44.12-17.59-14.65-3.27-28.41-4.06-40.8-3.67-5.22.14-10.21.51-15.02,1.04-6.64.72-12.9,1.74-18.85,2.93-20.4,4.25-37.18,10.24-52.08,16.36-4.32,1.83-8.49,3.67-12.51,5.52-9.79,4.48-18.71,9-26.95,13.53-11.67,6.36-22.14,12.53-31.56,18.52-16.41,10.26-29.96,19.66-41.22,27.71l-28.25,8.66c-56.07,17.22-98.73,63.45-110.85,120.11l-24.97,117.02c-4.87,22.84,2.09,46.21,18.38,62.27-1.3,1.9-2.58,3.85-3.92,5.8-39.39,57.95-83.04,77.8-108.62,84.6-4.78,1.28-4.36,8.12.53,8.91,33.26,5.22,62.92-1.11,76.54-4.92,3.5-.97,7.03,1.72,6.87,5.34-1.07,26.18,18.1,57.12,31.38,75.27,2.44,3.3,7.57.86,6.66-3.13-12.74-53.89,4.22-107.32,25.51-148.47,25.6,10.19,55.24,9.28,81.37-3.57l86.57-42.59c58.65-28.85,97.45-86.76,101.1-150.84l3.04-53.15,5.52-3.74c1.88-.93,3.76-1.81,5.66-2.67,7.94-3.62,15.97-6.55,22.47-7.91,3.2-.67,6.01-1.07,7.94-1.14h.88c-.21-.3-.35-.49-.44-.63-.44-.63-.02-.26.79.16.46.25.97.44,1.32.56-.09-.02-.23-.05-.35-.05-.35-.02-.79-.05-1.32-.05.53.88,1.39,2.44,2.34,4.64,1.25,2.97,2.72,7.03,3.97,12,.7,2.44,1.28,5.2,1.86,7.98.49,2.92,1,5.89,1.42,9.1.84,6.36,1.46,13.25,1.83,20.59.79,14.62.32,30.8-.77,47.83l-.23,3.2-.05.81c-.02.14-.02.21-.02.25,0,0-.02.21-.07,1.93l-.09,1.83c-.16,2.44-.3,4.9-.44,7.36-.05,3.64-.09,7.29-.14,10.96l-.02,2.74.05,2.51.09,5.06c.39,13.55,1.58,27.71,4.15,42.5,2.53,14.81,6.52,30.22,12.44,45.88,5.96,15.6,13.88,31.45,24.18,46.49,10.24,15.04,22.74,29.15,36.76,41.45,14.02,12.25,29.5,22.74,45.42,31.24,15.94,8.45,32.35,15.06,48.74,20.17,16.34,5.01,32.68,8.59,48.83,10.98,32.33,4.87,63.8,5.13,94.51,2.6,30.64-2.67,60.55-8.22,89.59-16.36,29.06-8.1,57.28-18.75,84.6-31.56,13.65-6.43,27.06-13.39,40.22-20.91,3.32-1.86,6.59-3.81,9.86-5.73l2.44-1.46,1.23-.7,2.46-1.53,4.06-2.55,4.09-2.6,5.99-3.92,5.94-4.02,5.34-3.76c28.06-20.01,55.35-44.42,79.49-74.8,12-15.2,23.16-32.01,32.89-50.34,9.75-18.31,17.75-38.48,23.79-59.81,2.85-10.75,5.27-21.72,6.87-33.05.91-5.59,1.42-11.37,2-17.06.42-5.8.81-11.53.81-17.38.37-23.21-2.46-46.88-8.42-69.42-2.99-11.33-6.73-22.3-11.09-32.93-4.5-10.51-9.45-20.82-15.06-30.43-11.14-19.38-24.39-36.62-38.62-51.83-14.3-15.11-29.59-28.17-45.28-39.48-15.74-11.3-31.82-20.82-48.02-29.1-32.4-16.48-65.03-27.9-97.32-36.39-16.15-4.25-32.19-7.78-48.18-10.58-13.65-2.32-27.34-4.64-41.06-6.99-6.73-1.11-13.41-2.37-20.12-3.64-6.64-1.35-13.35-2.67-19.94-4.25-13.23-3.09-26.3-6.82-39.18-11-51.5-16.62-101.98-35.63-148.47-58.25-23.16-11.35-45.42-23.46-65.47-36.69-20.03-13.14-38.11-27.2-52.01-41.36-13.9-14.11-23.16-28.22-26.48-38.67-1.02-2.62-1.42-4.99-1.93-7.22-.05-1.09-.42-2.16-.37-3.2-.02-.51-.07-1.02-.14-1.53.02-.49.05-1,.02-1.49-.09-3.92.67-7.78,1.86-12.37,1.18-4.6,3.34-10.07,6.38-16.36.79-1.55,1.51-3.13,2.48-4.8.9-1.65,1.79-3.3,2.9-5.06,1.02-1.69,2.04-3.41,3.27-5.2l1.65-2.55c-.05.07-.09.16-.14.26l.51-.74,1.42-2.18.74-1.07c.28-.44.16-.16.26-.3.12-.07.21-.12.28-.19.07,0,.65-.7,1.11-1.23.44-.58.97-1.16,1.49-1.74.49-.56,1.02-1.14,1.58-1.72,2.14-2.3,4.53-4.67,7.15-7.01,5.2-4.73,11.47-9.52,18.47-14.14,7.01-4.59,14.85-9.1,23.26-13.32,8.45-4.2,17.43-8.08,26.83-11.74,18.82-7.24,39.22-13.18,60.13-17.85,41.94-9.28,86.1-13.39,127.81-12.88,20.84.18,41.1,1.53,59.9,3.76,18.73,2.21,36.09,5.62,49.55,9.4,5.62,1.51,10.44,3.2,14.09,4.53l-.93,3.74c-.84,3.25-1.63,6.52-2.37,9.84-1.53,6.61-2.97,13.28-4.2,19.98-4.94,26.83-7.8,54.63-6.94,83.14.84,28.45,5.38,57.7,15.25,85.55,9.68,27.83,24.95,53.71,43.31,74.36,18.31,20.8,39.22,36.41,59.79,47.83,20.66,11.49,40.94,19.26,60.39,24.88,19.43,5.52,37.97,9.14,55.63,11.6,8.82,1.28,17.43,2.23,25.83,2.95,2.09.19,4.18.35,6.27.51l1.56.14.77.05c.46.07.05-.05,1.21.16l2.92.16c3.44.23,8.66.6,13,.79,17.38.53,34.86-.65,51.78-5.41,8.45-2.41,16.69-5.71,24.28-10.05,7.61-4.46,14.55-9.89,20.17-16.11,5.66-6.2,10.1-13.02,13.23-19.87,3.2-6.85,5.25-13.65,6.52-20.15,2.48-13.02,2.2-24.83.95-35.32Zm-891.34,427.81l-2.74,14.18c-3.23,16.78-14.6,31.1-30.36,38.29l-19.82,9.05c-9.4,4.27-19.82-2.55-19.33-12.67l.19-4.18c1.16-25.27,17.15-47.97,40.87-58.07l9.14-3.9c11.93-5.08,24.44,4.73,22.05,17.29Z",
]


def parse_path_coordinates(path_d: str) -> list[tuple[float, float]]:
    """Extract coordinates from SVG path d attribute."""
    coords = []
    # Match all coordinate pairs (handles m, l, c, z commands)
    # This is a simplified parser - extracts numeric pairs
    numbers = re.findall(r"[-+]?\d*\.?\d+", path_d)
    for i in range(0, len(numbers) - 1, 2):
        try:
            x, y = float(numbers[i]), float(numbers[i + 1])
            coords.append((x, y))
        except (ValueError, IndexError):
            continue
    return coords


def calculate_centroid(paths: list[str]) -> tuple[float, float]:
    """Calculate the centroid (center of gravity) of SVG paths."""
    all_coords = []
    for path in paths:
        all_coords.extend(parse_path_coordinates(path))

    if not all_coords:
        return 1080.0, 1080.0  # Default center

    x_sum = sum(c[0] for c in all_coords)
    y_sum = sum(c[1] for c in all_coords)
    n = len(all_coords)

    return x_sum / n, y_sum / n


def calculate_bounding_box(
    paths: list[str],
) -> tuple[float, float, float, float]:
    """Calculate bounding box of SVG paths."""
    all_coords = []
    for path in paths:
        all_coords.extend(parse_path_coordinates(path))

    if not all_coords:
        return 0, 0, 2160, 2160

    xs = [c[0] for c in all_coords]
    ys = [c[1] for c in all_coords]

    return min(xs), min(ys), max(xs), max(ys)


def generate_camo_pattern(variant: str = "green") -> str:
    """Generate SVG camouflage pattern definition.

    Variants:
        - green (orig): Forest green camo
        - navy: Navy/dark blue camo
        - desert: Desert tan/brown camo
        - arctic: White/gray arctic camo
        - urban: Gray urban camo
    """
    camo_palettes = {
        "green": ("#4a5d23", "#3d4f1e", "#2d3a16", "#5a6f2a"),  # Original forest
        "navy": ("#1a2a40", "#263850", "#34495e", "#1e3a5f"),   # Navy blue
        "desert": ("#c2a678", "#a08050", "#8b7355", "#d4c4a8"), # Desert tan
        "arctic": ("#e8e8e8", "#c0c0c0", "#ffffff", "#d0d0d0"), # Arctic white
        "urban": ("#4a4a4a", "#606060", "#3a3a3a", "#707070"),  # Urban gray
        # Gray camo variants
        "gray-light": ("#d1d5db", "#e5e7eb", "#f3f4f6", "#9ca3af"),  # Light gray
        "gray": ("#6b7280", "#4b5563", "#9ca3af", "#374151"),        # Medium gray
        "gray-dark": ("#374151", "#1f2937", "#4b5563", "#111827"),   # Dark gray
    }

    colors = camo_palettes.get(variant, camo_palettes["green"])

    return f"""
  <defs>
    <pattern id="camo" patternUnits="userSpaceOnUse" width="200" height="200">
      <rect width="200" height="200" fill="{colors[0]}"/>
      <ellipse cx="50" cy="30" rx="60" ry="40" fill="{colors[1]}"/>
      <ellipse cx="150" cy="80" rx="50" ry="35" fill="{colors[2]}"/>
      <ellipse cx="30" cy="120" rx="45" ry="30" fill="{colors[3]}"/>
      <ellipse cx="120" cy="160" rx="55" ry="38" fill="{colors[1]}"/>
      <ellipse cx="180" cy="20" rx="40" ry="25" fill="{colors[2]}"/>
      <ellipse cx="80" cy="180" rx="48" ry="32" fill="{colors[0]}"/>
    </pattern>
  </defs>"""


def generate_svg(
    fill_color: str,
    bg_color: str,
    viewbox: str = "0 0 2160 2160",
) -> str:
    """Generate SVG content with specified colors."""
    fill_hex = COLORS.get(fill_color, fill_color)
    bg_hex = COLORS.get(bg_color, bg_color) if bg_color != "transparent" else None

    # Build SVG
    svg_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg id="scitex-logo" xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}">',
    ]

    # Handle transparent fill (cutout effect) - snake shape is cut out from background
    if fill_color == "transparent":
        svg_parts.append("  <defs>")
        svg_parts.append('    <mask id="snake-cutout">')
        svg_parts.append('      <rect width="2160" height="2160" fill="white"/>')
        for path in SNAKE_PATHS:
            svg_parts.append(f'      <path fill="black" d="{path}"/>')
        svg_parts.append("    </mask>")
        svg_parts.append("  </defs>")
        svg_parts.append(f'  <circle cx="1080" cy="1080" r="1080" fill="{bg_hex}" mask="url(#snake-cutout)"/>')
        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    # Handle camo fill - snake is camo pattern
    if fill_color.startswith("camo-"):
        camo_variant = fill_color.replace("camo-", "")
        svg_parts.append(generate_camo_pattern(camo_variant))
        if bg_hex:
            svg_parts.append(f'  <circle cx="1080" cy="1080" r="1080" fill="{bg_hex}"/>')
        svg_parts.append("  <g>")
        for path in SNAKE_PATHS:
            svg_parts.append(f'    <path fill="url(#camo)" d="{path}"/>')
        svg_parts.append("  </g>")
        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    # Add defs with styles
    if bg_color.startswith("camo"):
        camo_variant = bg_color.replace("camo-", "") if "-" in bg_color else "green"
        # For camo background, we need pattern + style in same defs block
        camo_colors = {
            "green": ("#4a5d23", "#3d4f1e", "#2d3a16", "#5a6f2a"),
            "navy": ("#1a2a40", "#263850", "#34495e", "#1e3a5f"),
            "desert": ("#c2a678", "#a08050", "#8b7355", "#d4c4a8"),
            "arctic": ("#e8e8e8", "#c0c0c0", "#ffffff", "#d0d0d0"),
            "urban": ("#4a4a4a", "#606060", "#3a3a3a", "#707070"),
            "gray-light": ("#d1d5db", "#e5e7eb", "#f3f4f6", "#9ca3af"),
            "gray": ("#6b7280", "#4b5563", "#9ca3af", "#374151"),
            "gray-dark": ("#374151", "#1f2937", "#4b5563", "#111827"),
        }
        colors = camo_colors.get(camo_variant, camo_colors["green"])
        svg_parts.append("  <defs>")
        svg_parts.append(f'    <pattern id="camo" patternUnits="userSpaceOnUse" width="200" height="200">')
        svg_parts.append(f'      <rect width="200" height="200" fill="{colors[0]}"/>')
        svg_parts.append(f'      <ellipse cx="50" cy="30" rx="60" ry="40" fill="{colors[1]}"/>')
        svg_parts.append(f'      <ellipse cx="150" cy="80" rx="50" ry="35" fill="{colors[2]}"/>')
        svg_parts.append(f'      <ellipse cx="30" cy="120" rx="45" ry="30" fill="{colors[3]}"/>')
        svg_parts.append(f'      <ellipse cx="120" cy="160" rx="55" ry="38" fill="{colors[1]}"/>')
        svg_parts.append(f'      <ellipse cx="180" cy="20" rx="40" ry="25" fill="{colors[2]}"/>')
        svg_parts.append(f'      <ellipse cx="80" cy="180" rx="48" ry="32" fill="{colors[0]}"/>')
        svg_parts.append("    </pattern>")
        svg_parts.append("    <style>")
        svg_parts.append(f'      .snake-fill {{ fill: {fill_hex}; stroke-width: 0px; }}')
        svg_parts.append("    </style>")
        svg_parts.append("  </defs>")
        svg_parts.append('  <circle cx="1080" cy="1080" r="1080" fill="url(#camo)"/>')
    else:
        svg_parts.append("  <defs>")
        svg_parts.append("    <style>")
        if bg_hex:
            svg_parts.append(f"      .bg-fill {{ fill: {bg_hex}; }}")
        svg_parts.append(
            f'      .snake-fill {{ fill: {fill_hex}; stroke-width: 0px; }}'
        )
        svg_parts.append("    </style>")
        svg_parts.append("  </defs>")

        # Add background circle if not transparent
        if bg_hex:
            svg_parts.append('  <circle class="bg-fill" cx="1080" cy="1080" r="1080"/>')

    # Add snake paths
    svg_parts.append("  <g>")
    for path in SNAKE_PATHS:
        svg_parts.append(f'    <path class="snake-fill" d="{path}"/>')
    svg_parts.append("  </g>")
    svg_parts.append("</svg>")

    return "\n".join(svg_parts)


def generate_all_icons(output_dir: Path) -> list[Path]:
    """Generate all icon combinations."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = []

    for fill_color, bg_color in COMBINATIONS:
        filename = f"scitex-icon-{fill_color}-bg-{bg_color}.svg"
        filepath = output_dir / filename

        svg_content = generate_svg(fill_color, bg_color)
        filepath.write_text(svg_content)
        generated.append(filepath)
        print(f"Generated: {filename}")

    return generated


def print_centroid_info():
    """Print centroid and bounding box information."""
    centroid = calculate_centroid(SNAKE_PATHS)
    bbox = calculate_bounding_box(SNAKE_PATHS)

    print("\n=== Snake Icon Geometry ===")
    print(f"Centroid (center of gravity): ({centroid[0]:.2f}, {centroid[1]:.2f})")
    print(f"Bounding box: x={bbox[0]:.2f} to {bbox[2]:.2f}, y={bbox[1]:.2f} to {bbox[3]:.2f}")
    print(f"Width: {bbox[2] - bbox[0]:.2f}, Height: {bbox[3] - bbox[1]:.2f}")
    print(f"Canvas center: (1080, 1080)")
    print(f"Offset from center: ({centroid[0] - 1080:.2f}, {centroid[1] - 1080:.2f})")


def main():
    parser = argparse.ArgumentParser(
        description="Generate SciTeX icon variants"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("static/shared/images/scitex_logos/scitex-icon/generated"),
        help="Output directory for generated icons",
    )
    parser.add_argument(
        "--list-colors",
        action="store_true",
        help="List available colors and exit",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show centroid and geometry info",
    )
    parser.add_argument(
        "--fill",
        type=str,
        help="Generate single icon with this fill color",
    )
    parser.add_argument(
        "--bg",
        type=str,
        help="Generate single icon with this background color",
    )

    args = parser.parse_args()

    if args.list_colors:
        print("Available colors:")
        for name, hex_val in COLORS.items():
            print(f"  {name}: {hex_val}")
        print("\nSpecial backgrounds:")
        print("  transparent: No background")
        print("  camo: Camouflage pattern")
        return

    if args.info:
        print_centroid_info()
        return

    if args.fill and args.bg:
        # Generate single icon
        args.output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"scitex-icon-{args.fill}-bg-{args.bg}.svg"
        filepath = args.output_dir / filename
        svg_content = generate_svg(args.fill, args.bg)
        filepath.write_text(svg_content)
        print(f"Generated: {filepath}")
    else:
        # Generate all combinations
        generated = generate_all_icons(args.output_dir)
        print(f"\nGenerated {len(generated)} icons in {args.output_dir}")
        print_centroid_info()


if __name__ == "__main__":
    main()
