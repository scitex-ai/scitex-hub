#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/docs_app/views.py

from django.shortcuts import render, redirect
from django.http import Http404, HttpResponse
from django.conf import settings
from pathlib import Path


# Documentation paths
DOC_PATHS = {
    "python": "../scitex-code/docs/sphinx/build/html",  # scitex PyPI package
}


def docs_index(request):
    """Documentation landing page."""
    context = {
        "modules": [
            {
                "name": "Python Package",
                "slug": "python",
                "description": "SciTeX Python package (pip install scitex)",
                "icon": "scitex_logos/scitex-icons/scitex-icon-navy.svg",
                "available": _check_docs_available("python"),
            },
            {
                "name": "REST API",
                "slug": "api",
                "description": "REST API reference for SciTeX Cloud",
                "icon": "scitex_logos/scitex-icons/scitex-icon-navy.svg",
                "available": True,  # Always available (static HTML)
            },
        ]
    }
    return render(request, "docs_app/docs_index.html", context)


def docs_python(request):
    """Serve SciTeX Python package documentation."""
    return _serve_module_docs(request, "python", "index.html")


def docs_api(request):
    """Serve REST API documentation page."""
    return render(request, "public_app/pages/api_docs.html")


def docs_page(request, module, page):
    """Serve a specific documentation page."""
    return _serve_module_docs(request, module, page)


def _check_docs_available(module):
    """Check if documentation is built and available for a module."""
    if module not in DOC_PATHS:
        return False

    doc_path = Path(settings.BASE_DIR) / DOC_PATHS[module]
    return doc_path.exists() and (doc_path / "index.html").exists()


def _serve_module_docs(request, module, page="index.html"):
    """Serve documentation files for a specific module."""
    if module not in DOC_PATHS:
        raise Http404("Module documentation not found")

    # Construct the full path to the documentation file
    doc_base = Path(settings.BASE_DIR) / DOC_PATHS[module]
    doc_file = doc_base / page

    # If docs not built, redirect to GitHub README
    if not doc_base.exists() or not doc_file.exists():
        github_urls = {
            "python": "https://github.com/ywatanabe1989/SciTeX-Code#readme",
        }
        return redirect(github_urls.get(module, "https://github.com/SciTeX-AI"))

    # Security: ensure the path is within the documentation directory
    try:
        doc_file = doc_file.resolve()
        doc_base = doc_base.resolve()
        if not str(doc_file).startswith(str(doc_base)):
            raise Http404("Invalid documentation path")
    except (ValueError, OSError):
        raise Http404("Invalid documentation path")

    # Read and serve the file
    if doc_file.suffix == ".html":
        with open(doc_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Wrap in SciTeX template
        context = {
            "module": module,
            "module_name": module.capitalize(),
            "doc_content": content,
            "page": page,
        }
        return render(request, "docs_app/docs_page.html", context)
    else:
        # Serve static files (CSS, JS, images) directly
        content_types = {
            ".css": "text/css",
            ".js": "application/javascript",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".woff": "font/woff",
            ".woff2": "font/woff2",
            ".ttf": "font/ttf",
        }
        content_type = content_types.get(doc_file.suffix, "application/octet-stream")

        with open(doc_file, "rb") as f:
            return HttpResponse(f.read(), content_type=content_type)
