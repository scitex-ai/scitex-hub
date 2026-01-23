#!/usr/bin/env python3
"""
Django Template Tag Checker

Finds broken Django template tags that have been split across lines by formatters.
This is a common issue when Python formatters like Black or Ruff are run on .html files.

Usage:
    python scripts/check_django_templates.py
    python scripts/check_django_templates.py --fix
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def find_broken_template_tags(file_path: Path) -> List[Tuple[int, str]]:
    """
    Find Django template tags that are split across lines.

    Returns:
        List of (line_number, issue_description) tuples
    """
    issues = []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove <script> and <style> blocks to avoid false positives
    content_no_js = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content_no_js = re.sub(r'<style[^>]*>.*?</style>', '', content_no_js, flags=re.DOTALL | re.IGNORECASE)

    lines = content_no_js.split('\n')

    for i, line in enumerate(lines, start=1):
        # Check for incomplete opening tags
        if re.search(r'{%\s*$', line):
            issues.append((i, f"Incomplete opening tag: {line.strip()}"))

        # Check for lines starting with Django template tag keywords (not inside tags)
        # Only check for Django-specific keywords
        if re.search(r'^\s*(include|extends|load|block|endblock|for|endfor|if|elif|else|endif|with|endwith|url|static)\s', line):
            if not re.search(r'{%.*%}', line):
                issues.append((i, f"Orphaned Django tag content: {line.strip()}"))

        # Check for closing tag fragments
        if re.search(r'^\s*%}', line):
            issues.append((i, f"Orphaned closing tag: {line.strip()}"))

        # Check for variable fragments
        if re.search(r'{{\s*$', line):
            issues.append((i, f"Incomplete variable opening: {line.strip()}"))

        if re.search(r'^\s*}}', line):
            issues.append((i, f"Orphaned variable closing: {line.strip()}"))

    return issues


def find_all_templates(base_path: Path = None) -> List[Path]:
    """Find all Django template files (.html)"""
    if base_path is None:
        base_path = Path(__file__).parent.parent

    template_files = []

    # Search in apps/*/templates directories
    for template_file in base_path.glob('apps/*/templates/**/*.html'):
        template_files.append(template_file)

    return template_files


def main():
    """Main entry point"""
    base_path = Path(__file__).parent.parent
    template_files = find_all_templates(base_path)

    print(f"Checking {len(template_files)} template files...")
    print("=" * 80)

    total_issues = 0
    files_with_issues = 0

    for template_file in sorted(template_files):
        issues = find_broken_template_tags(template_file)

        if issues:
            files_with_issues += 1
            total_issues += len(issues)

            rel_path = template_file.relative_to(base_path)
            print(f"\n{rel_path}")
            print("-" * 80)

            for line_num, description in issues:
                print(f"  Line {line_num}: {description}")

    print("\n" + "=" * 80)
    print(f"Summary: Found {total_issues} issues in {files_with_issues} files")

    if total_issues > 0:
        print("\n⚠️  Broken Django template tags detected!")
        print("These are usually caused by running Python formatters on .html files.")
        print("\nRecommendations:")
        print("1. Exclude .html files from Python formatters (Black, Ruff, etc.)")
        print("2. Use Django-specific formatters like djlint instead")
        print("3. Add this script to your pre-commit hooks")
        return 1
    else:
        print("\n✅ All template tags look good!")
        return 0


if __name__ == '__main__':
    sys.exit(main())
