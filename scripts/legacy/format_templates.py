#!/usr/bin/env python3
"""
Auto-format Django templates with proper indentation.
Usage: python scripts/format_templates.py <file_or_directory>
"""

import re
import sys
from pathlib import Path


def format_django_template(content):
    """Format Django template with proper indentation."""
    lines = content.split('\n')
    formatted = []
    indent_level = 0
    indent_char = '  '  # 2 spaces

    # Block tags that increase indentation
    opening_tags = [
        'block', 'if', 'for', 'with', 'autoescape', 'filter', 'spaceless',
        'verbatim', 'comment', 'blocktrans', 'ifequal', 'ifnotequal',
        'ifchanged', 'regroup'
    ]

    # Block tags that decrease indentation
    closing_tags = [f'end{tag}' for tag in opening_tags]
    middle_tags = ['else', 'elif', 'empty']

    for line in lines:
        stripped = line.strip()

        # Check for closing tags
        if any(f'{{% {tag}' in stripped or f'{{%{tag}' in stripped for tag in closing_tags):
            indent_level = max(0, indent_level - 1)
            formatted.append(indent_char * indent_level + stripped)
            continue

        # Check for middle tags (else, elif, empty)
        if any(f'{{% {tag}' in stripped or f'{{%{tag}' in stripped for tag in middle_tags):
            formatted.append(indent_char * max(0, indent_level - 1) + stripped)
            continue

        # Add current line with current indentation
        if stripped:  # Only add indentation to non-empty lines
            formatted.append(indent_char * indent_level + stripped)
        else:
            formatted.append('')

        # Check for opening tags (increase indentation for next line)
        if any(f'{{% {tag}' in stripped or f'{{%{tag}' in stripped for tag in opening_tags):
            # Make sure it's not a self-closing tag like {% block %}{% endblock %}
            if not any(f'{{% end{tag}' in stripped or f'{{%end{tag}' in stripped for tag in opening_tags):
                indent_level += 1

        # Check for HTML opening tags
        if stripped.startswith('<') and not stripped.startswith('</') and not stripped.endswith('/>') and not '<!--' in stripped:
            # Simple heuristic: if tag doesn't close on same line
            tag_match = re.match(r'<(\w+)', stripped)
            if tag_match and f'</{tag_match.group(1)}>' not in stripped:
                indent_level += 1

        # Check for HTML closing tags
        if stripped.startswith('</'):
            indent_level = max(0, indent_level - 1)

    return '\n'.join(formatted)


def format_file(filepath):
    """Format a single template file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        formatted = format_django_template(content)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(formatted)

        print(f"✓ Formatted: {filepath}")
        return True
    except Exception as e:
        print(f"✗ Error formatting {filepath}: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/format_templates.py <file_or_directory>")
        sys.exit(1)

    path = Path(sys.argv[1])

    if path.is_file():
        format_file(path)
    elif path.is_dir():
        count = 0
        for html_file in path.rglob('*.html'):
            if format_file(html_file):
                count += 1
        print(f"\nFormatted {count} files")
    else:
        print(f"Path not found: {path}")
        sys.exit(1)


if __name__ == '__main__':
    main()
