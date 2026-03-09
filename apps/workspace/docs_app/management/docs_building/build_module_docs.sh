#!/bin/bash
# Build Sphinx documentation for SciTeX modules
set -e

echo "Building SciTeX module documentation..."

# Code module (symlinked to scitex_repo)
if [ -d "externals/code" ]; then
    echo "Building Code docs..."
    cd ~/proj/scitex_repo
    if [ -f "docs/conf.py" ]; then
        sphinx-build -b html docs docs/_build/html
        echo "  ✓ Code docs built"
    else
        echo "  ! No Sphinx config found, initializing..."
        cd docs
        sphinx-quickstart -q -p "SciTeX Code" -a "Yusuke Watanabe" -v "2.0" --ext-autodoc --ext-viewcode --makefile --no-batchfile
        sphinx-build -b html . _build/html
        echo "  ✓ Code docs initialized and built"
    fi
    cd -
fi

# Scholar (part of Code)
echo "  → Scholar docs included in Code"

# Writer module
if [ -d "externals/paper" ]; then
    echo "Building Writer docs..."
    cd ~/proj/neurovista/paper
    if [ -f "docs/conf.py" ]; then
        sphinx-build -b html docs docs/_build/html
        echo "  ✓ Writer docs built"
    else
        echo "  ! No Sphinx config - needs setup"
    fi
    cd -
fi

# Viz module
if [ -d "externals/viz" ]; then
    echo "Building Viz docs..."
    cd ~/win/documents/SciTeX-Viz
    if [ -f "docs/conf.py" ]; then
        sphinx-build -b html docs docs/_build/html
        echo "  ✓ Viz docs built"
    else
        echo "  ! No Sphinx config - needs setup"
    fi
    cd -
fi

echo ""
echo "✓ Documentation build complete"
echo "  Access at: http://scitex.ai/docs/"
