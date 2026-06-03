#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2026-02-13
# Author: ywatanabe (with Claude Code)
# File: /home/ywatanabe/proj/scitex-hub/scripts/maintenance/_check_contrast_static.py
#
# Static CSS analysis for WCAG AA contrast anti-patterns.
# Parses CSS files and the color system to find text/background pairs
# that violate contrast ratio requirements. No running server needed.

import math
import re
import sys
from pathlib import Path

# ── WCAG contrast utilities ──────────────────────────────────────


def hex_to_rgb(hex_str):
    """Convert #RRGGBB or #RGB to (r, g, b) tuple."""
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = h[0] * 2 + h[1] * 2 + h[2] * 2
    if len(h) != 6:
        return None
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return None


def parse_rgba(val):
    """Parse rgb(r,g,b) or rgba(r,g,b,a) to (r,g,b,a) tuple."""
    m = re.match(
        r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?\s*\)",
        val.strip(),
    )
    if m:
        a = float(m.group(4)) if m.group(4) else 1.0
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)), a)
    return None


def srgb_to_linear(c):
    s = c / 255.0
    return s / 12.92 if s <= 0.04045 else math.pow((s + 0.055) / 1.055, 2.4)


def relative_luminance(r, g, b):
    return (
        0.2126 * srgb_to_linear(r)
        + 0.7152 * srgb_to_linear(g)
        + 0.0722 * srgb_to_linear(b)
    )


def contrast_ratio(fg_rgb, bg_rgb):
    l_fg = relative_luminance(*fg_rgb[:3])
    l_bg = relative_luminance(*bg_rgb[:3])
    lighter = max(l_fg, l_bg)
    darker = min(l_fg, l_bg)
    return (lighter + 0.05) / (darker + 0.05)


# ── Color system parser ──────────────────────────────────────────


def parse_color_system(project_root):
    """Parse colors.css to build resolved variable -> hex color map for each theme."""
    colors_path = (
        project_root / "static" / "shared" / "css" / "primitives" / "colors.css"
    )
    if not colors_path.exists():
        print(f"WARN: Color system file not found: {colors_path}")
        return {}, {}

    content = colors_path.read_text()

    # Split into theme blocks
    light_vars = {}
    dark_vars = {}

    # Extract :root/[data-theme="light"] block
    light_match = re.search(
        r'(?::root|data-theme="light"\])\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}',
        content,
        re.DOTALL,
    )
    dark_match = re.search(
        r'\[data-theme="dark"\]\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}',
        content,
        re.DOTALL,
    )

    def extract_vars(block):
        """Extract --var: value pairs from a CSS block."""
        pairs = {}
        for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+);", block):
            name = m.group(1).strip()
            value = m.group(2).strip()
            pairs[name] = value
        return pairs

    if light_match:
        light_vars = extract_vars(light_match.group(1))
    if dark_match:
        dark_vars = extract_vars(dark_match.group(1))

    def resolve(var_map, name, depth=0):
        """Recursively resolve var() references."""
        if depth > 10 or name not in var_map:
            return None
        val = var_map[name]
        var_ref = re.match(r"var\((--[\w-]+)\)", val)
        if var_ref:
            return resolve(var_map, var_ref.group(1), depth + 1)
        rgb = hex_to_rgb(val)
        if rgb:
            return rgb
        rgba = parse_rgba(val)
        if rgba:
            return rgba[:3]
        return None

    light_resolved = {}
    for name in light_vars:
        rgb = resolve(light_vars, name)
        if rgb:
            light_resolved[name] = rgb

    dark_resolved = {}
    # Dark inherits light, then overrides
    merged_dark = {**light_vars, **dark_vars}
    for name in merged_dark:
        rgb = resolve(merged_dark, name)
        if rgb:
            dark_resolved[name] = rgb

    return light_resolved, dark_resolved


# ── Known text/background pairings to check ──────────────────────

# These are the semantic token pairs that matter for readability.
PAIRINGS = [
    # (foreground_var, background_var, description)
    ("--text-primary", "--bg-page", "Primary text on page background"),
    ("--text-primary", "--bg-surface", "Primary text on surface"),
    ("--text-primary", "--bg-muted", "Primary text on muted background"),
    ("--text-secondary", "--bg-page", "Secondary text on page background"),
    ("--text-secondary", "--bg-surface", "Secondary text on surface"),
    ("--text-muted", "--bg-page", "Muted text on page background"),
    ("--text-muted", "--bg-surface", "Muted text on surface"),
    ("--text-inverse", "--bg-muted", "Inverse text on muted background"),
    ("--status-success", "--bg-page", "Success status on page"),
    ("--status-warning", "--bg-page", "Warning status on page"),
    ("--status-error", "--bg-page", "Error status on page"),
    ("--status-info", "--bg-page", "Info status on page"),
    ("--status-success-text", "--status-success-bg", "Success text on success bg"),
    ("--status-error-text", "--status-error-bg", "Error text on error bg"),
    ("--status-warning-text", "--status-warning-bg", "Warning text on warning bg"),
    ("--status-info-text", "--status-info-bg", "Info text on info bg"),
    ("--color-btn-primary-text", "--color-btn-primary-bg", "Button primary text"),
    ("--color-btn-text", "--color-btn-bg", "Button default text"),
    ("--terminal-fg", "--terminal-bg", "Terminal foreground on background"),
    ("--workspace-icon-primary", "--workspace-bg-primary", "Workspace icon on bg"),
    ("--workspace-icon-muted", "--workspace-bg-primary", "Workspace muted icon on bg"),
]

# Additional: direct hex pairings found in CSS files
DIRECT_HEX_PAIRS = [
    # (fg_hex, bg_hex, description, file_hint)
]


# ── CSS file scanner ─────────────────────────────────────────────


def scan_css_files(project_root, light_vars, dark_vars):
    """Scan CSS files for color/background-color patterns that may violate contrast."""
    violations = []
    css_dirs = [
        project_root / "static",
        project_root / "apps",
    ]

    for css_dir in css_dirs:
        if not css_dir.exists():
            continue
        for css_path in css_dir.rglob("*.css"):
            # Skip vendor/build artifacts
            rel = str(css_path.relative_to(project_root))
            if any(
                skip in rel for skip in ["node_modules", ".tsbuild", ".old", "legacy"]
            ):
                continue

            content = css_path.read_text(errors="replace")

            # Find rules that set both color and background-color
            # Simple heuristic: look for rule blocks
            blocks = re.findall(r"([^{}]+)\{([^{}]+)\}", content)
            for selector, body in blocks:
                selector = selector.strip().split("\n")[-1].strip()
                color_m = re.search(r"(?:^|\s)color\s*:\s*([^;]+);", body)
                bg_m = re.search(r"background(?:-color)?\s*:\s*([^;]+);", body)

                if not color_m:
                    continue

                fg_val = color_m.group(1).strip()
                bg_val = bg_m.group(1).strip() if bg_m else None

                # Resolve fg
                fg_rgb = _resolve_color_value(fg_val, light_vars)
                bg_rgb = _resolve_color_value(bg_val, light_vars) if bg_val else None

                if fg_rgb and bg_rgb:
                    cr = contrast_ratio(fg_rgb, bg_rgb)
                    if cr < 4.5:
                        violations.append(
                            {
                                "file": rel,
                                "selector": selector[:80],
                                "fg": fg_val,
                                "bg": bg_val,
                                "ratio": round(cr, 2),
                                "required": 4.5,
                                "theme": "light (inline)",
                            }
                        )

    return violations


def _resolve_color_value(val, resolved_vars):
    """Try to resolve a CSS value to an RGB tuple."""
    if not val:
        return None

    # Direct hex
    rgb = hex_to_rgb(val)
    if rgb:
        return rgb

    # rgba/rgb
    rgba = parse_rgba(val)
    if rgba:
        return rgba[:3]

    # var() reference
    var_m = re.match(r"var\((--[\w-]+)", val)
    if var_m:
        name = var_m.group(1)
        return resolved_vars.get(name)

    return None


# ── Main ─────────────────────────────────────────────────────────

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
WARN = "\033[33mWARN\033[0m"
HEADER = "\033[36m"
NC = "\033[0m"


def main():
    project_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    project_root = project_root.resolve()

    if not (project_root / "static").exists():
        print(f"ERROR: Not a valid project root: {project_root}")
        sys.exit(1)

    light_vars, dark_vars = parse_color_system(project_root)

    if not light_vars:
        print("ERROR: Could not parse color system. No variables found.")
        sys.exit(1)

    total_pass = 0
    total_fail = 0
    all_violations = []

    # Check semantic pairings for each theme
    for theme_name, resolved in [("light", light_vars), ("dark", dark_vars)]:
        print(f"\n{HEADER}--- Theme: {theme_name} (semantic token pairs) ---{NC}\n")

        for fg_var, bg_var, desc in PAIRINGS:
            fg_rgb = resolved.get(fg_var)
            bg_rgb = resolved.get(bg_var)

            if not fg_rgb or not bg_rgb:
                print(f"  {WARN}  {desc}: could not resolve {fg_var} or {bg_var}")
                continue

            cr = contrast_ratio(fg_rgb, bg_rgb)
            # Assume normal text (4.5:1) for semantic check
            required = 4.5

            if cr >= required:
                total_pass += 1
                print(
                    f"  {PASS}  {cr:5.2f}:1 >= {required}:1  {desc}  ({fg_var} on {bg_var})"
                )
            else:
                total_fail += 1
                fg_hex = "#{:02x}{:02x}{:02x}".format(*fg_rgb[:3])
                bg_hex = "#{:02x}{:02x}{:02x}".format(*bg_rgb[:3])
                print(
                    f"  {FAIL}  {cr:5.2f}:1 <  {required}:1  {desc}  ({fg_var}={fg_hex} on {bg_var}={bg_hex})"
                )
                all_violations.append(
                    {
                        "theme": theme_name,
                        "fg_var": fg_var,
                        "bg_var": bg_var,
                        "fg_hex": fg_hex,
                        "bg_hex": bg_hex,
                        "ratio": round(cr, 2),
                        "required": required,
                        "desc": desc,
                    }
                )

    # Scan CSS files for inline color/bg pairs
    print(f"\n{HEADER}--- CSS file scan (inline color pairs) ---{NC}\n")
    css_violations = scan_css_files(project_root, light_vars, dark_vars)

    if css_violations:
        for v in css_violations:
            total_fail += 1
            print(
                f"  {FAIL}  {v['ratio']:5.2f}:1 <  {v['required']}:1  {v['file']}  {v['selector']}"
            )
            print(f"          fg={v['fg']}  bg={v['bg']}")
            all_violations.append(v)
    else:
        print(f"  {PASS}  No inline color pair violations detected")
        total_pass += 1

    # Summary
    print(f"\n{HEADER}=== Summary ==={NC}")
    print(f"Total checks: {total_pass + total_fail}")
    print(f"  PASS: {total_pass}")
    print(f"  FAIL: {total_fail}")

    if all_violations:
        print(f"\n{HEADER}=== Violations requiring attention ==={NC}")
        for v in all_violations:
            if "desc" in v:
                print(
                    f"  [{v['theme']}] {v['desc']}: {v['ratio']}:1 ({v.get('fg_var', '')} on {v.get('bg_var', '')})"
                )
            else:
                print(
                    f"  [{v.get('theme', '?')}] {v.get('file', '?')}: {v['selector']} {v['ratio']}:1"
                )

    print()
    if total_fail > 0:
        print(
            f"\033[31mWCAG AA contrast check FAILED with {total_fail} violation(s).\033[0m"
        )
        sys.exit(1)
    else:
        print("\033[32mWCAG AA contrast check PASSED.\033[0m")
        sys.exit(0)


if __name__ == "__main__":
    main()
