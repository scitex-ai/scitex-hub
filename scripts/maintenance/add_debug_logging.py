#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-06 07:15:01 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/scripts/add_debug_logging.py
# ----------------------------------------
from __future__ import annotations
import os

__FILE__ = "./scripts/add_debug_logging.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------
"""
Add DEBUG console.log statements to TypeScript files that don't have them.
"""

import re
from pathlib import Path


def has_debug_logging(content: str) -> bool:
    """Check if file already has DEBUG loaded statement."""
    return bool(re.search(r'console\.log\(["\']?\[DEBUG\].*loaded["\']?\)', content))


def add_debug_logging(file_path: Path) -> bool:
    """Add DEBUG logging to a TypeScript file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Skip if already has debug logging
        if has_debug_logging(content):
            return False

        # Create debug statement
        debug_line = f'console.log("[DEBUG] {file_path} loaded");\n'

        lines = content.split("\n")
        insert_position = 0

        # Find position after imports and comments
        in_comment_block = False
        for i, line in enumerate(lines):
            stripped = line.strip()

            # Track multi-line comments
            if "/*" in stripped:
                in_comment_block = True
            if "*/" in stripped:
                in_comment_block = False
                insert_position = i + 1
                continue

            # Skip single-line comments at top
            if stripped.startswith("//"):
                insert_position = i + 1
                continue

            # Skip import statements
            if stripped.startswith("import ") or stripped.startswith("import{"):
                insert_position = i + 1
                continue

            # Skip type-only imports
            if stripped.startswith("import type"):
                insert_position = i + 1
                continue

            # Skip empty lines at top
            if not stripped and i < 20:
                insert_position = i + 1
                continue

            # Stop at first real code
            if stripped and not in_comment_block:
                break

        # Add blank line before debug statement if needed
        if insert_position > 0 and lines[insert_position - 1].strip():
            lines.insert(insert_position, "")
            insert_position += 1

        # Insert debug statement
        lines.insert(insert_position, debug_line.rstrip())

        # Write back
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to add debug logging to all TypeScript files."""
    base_dir = Path.cwd()

    # Find all .ts files (excluding .d.ts)
    ts_files = []
    for pattern in ["apps/*/static/*/ts/**/*.ts", "static/shared/ts/**/*.ts"]:
        for file_path in base_dir.glob(pattern):
            if file_path.suffix == ".ts" and not file_path.name.endswith(".d.ts"):
                ts_files.append(file_path)

    print(f"Found {len(ts_files)} TypeScript files")

    added_count = 0
    skipped_count = 0

    for file_path in sorted(ts_files):
        if add_debug_logging(file_path):
            print(f"✅ Added: {file_path}")
            added_count += 1
        else:
            skipped_count += 1

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Added DEBUG logging:  {added_count} files")
    print(f"  Already had logging:  {skipped_count} files")
    print(f"  Total:                {len(ts_files)} files")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

# EOF
