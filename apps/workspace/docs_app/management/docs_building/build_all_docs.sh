#!/bin/bash
# Build Sphinx documentation for all SciTeX modules
# Each module has its own .env that auto-activates on cd

set -e

echo "========================================"
echo "Building SciTeX Documentation"
echo "========================================"

# Code module (includes Scholar)
echo ""
echo "📚 Building Code documentation..."
cd "$HOME/proj/scitex_repo/"
if [ -f "docs/conf.py" ]; then
    sphinx-build -b html docs docs/_build/html 2>&1 | grep -E "build succeeded|warning|error" | tail -5
    if [ -f "docs/_build/html/index.html" ]; then
        echo "  ✓ Code docs built successfully"
    else
        echo "  ✗ Code docs build failed"
    fi
else
    echo "  ! No Sphinx config found at docs/conf.py"
fi

# Writer module
echo ""
echo "📝 Building Writer documentation..."
cd "$HOME/proj/neurovista/paper"
if [ -f "docs/conf.py" ]; then
    sphinx-build -b html docs docs/_build/html 2>&1 | grep -E "build succeeded|warning|error" | tail -5
    if [ -f "docs/_build/html/index.html" ]; then
        echo "  ✓ Writer docs built successfully"
    else
        echo "  ✗ Writer docs build failed"
    fi
else
    echo "  ! No Sphinx config found"
fi

# Viz module
echo ""
echo "📊 Building Viz documentation..."
cd "$HOME/proj/SciTeX-Viz"
if [ -f "docs/conf.py" ]; then
    sphinx-build -b html docs docs/_build/html 2>&1 | grep -E "build succeeded|warning|error" | tail -5
    if [ -f "docs/_build/html/index.html" ]; then
        echo "  ✓ Viz docs built successfully"
    else
        echo "  ✗ Viz docs build failed"
    fi
else
    echo "  ! No Sphinx config found - using README.md as docs"
fi

# Return to cloud project
cd "$HOME/proj/scitex-cloud"

echo ""
echo "========================================"
echo "Documentation Build Summary"
echo "========================================"
echo "Access documentation at:"
echo "  - Code:   http://scitex.ai/docs/code/"
echo "  - Scholar: http://scitex.ai/docs/scholar/"
echo "  - Writer: http://scitex.ai/docs/writer/"
echo "  - Viz:    http://scitex.ai/docs/viz/"
echo ""
echo "If docs not built, buttons fallback to GitHub READMEs"
echo "========================================"
