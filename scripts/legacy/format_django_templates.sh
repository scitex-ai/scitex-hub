#!/bin/bash
# Auto-format Django templates with djhtml
# Usage: ./scripts/format_django_templates.sh [directory]

set -e

DIR="${1:-.}"

# Check if djhtml is installed
if ! command -v djhtml &> /dev/null; then
    echo "Installing djhtml..."
    pip install djhtml
fi

echo "Formatting Django templates in: $DIR"
djhtml -i -t 2 "$DIR"

echo "✓ Templates formatted with 2-space indentation"
