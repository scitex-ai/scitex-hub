#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-28 21:31:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/apps/public_app/views/api.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/public_app/views/api.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
API and Developer Pages Views

Handles API documentation, API key management, and release notes.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


def _interface_docs_context(request):
    from django.http import Http404
    from apps.infra.public_app.services.interface_catalog import build_interface_catalog

    try:
        return {
            "interface_catalog": build_interface_catalog(request.GET.get("package"))
        }
    except ValueError as exc:
        raise Http404("Invalid package identifier") from exc


def _hub_version():
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("scitex-hub")
    except PackageNotFoundError:
        return "unknown"


def api_docs_catalog(request):
    """Public inert provider metadata, not domain API execution or admission."""
    from django.http import Http404, JsonResponse

    if request.method != "GET":
        response = JsonResponse(
            {
                "error": {
                    "code": "method_not_allowed",
                    "message": "Use GET for provider metadata.",
                }
            },
            status=405,
        )
        response["Allow"] = "GET"
        return response
    try:
        catalog = _interface_docs_context(request)["interface_catalog"]
    except Http404:
        return JsonResponse(
            {
                "error": {
                    "code": "invalid_package",
                    "message": "Use a valid package distribution name.",
                }
            },
            status=400,
        )
    return JsonResponse(catalog)


def _get_user_api_key(user):
    """Get user's first active API key (masked for display)."""
    try:
        from apps.infra.accounts_app.models import APIKey

        api_key = APIKey.objects.filter(user=user, is_active=True).first()
        if api_key:
            # Return masked key for display (show prefix only)
            return api_key.key_prefix + "..." if api_key.key_prefix else "sk_..."
    except Exception:
        pass
    return None


def _render_api_docs(request, section=None):
    """Compose provider-backed pages; historical section URLs stay unverified."""
    from django.conf import settings
    from apps.infra.public_app.config import (
        API_DOC_DEFAULT_SECTION,
        get_all_sections,
        get_section,
    )

    current = section if get_section(section) else API_DOC_DEFAULT_SECTION
    info = get_section(current)
    legacy = current != "interfaces"
    return render(
        request,
        "public_app/pages/api_docs_section.html",
        {
            "section_title": info["title"],
            "section_template": "public_app/pages/api-docs-partials/legacy_reference.html"
            if legacy
            else info["template"],
            "current_section": current,
            "sections": get_all_sections(),
            "version": _hub_version(),
            "debug": settings.DEBUG,
            "legacy_reference": legacy,
            **_interface_docs_context(request),
        },
    )


def api_docs(request):
    """Documentation dispatcher landing; never executes a leaf API."""
    return _render_api_docs(request)


def api_docs_section(request, section):
    """Preserve old section URLs without certifying their historical examples."""
    return _render_api_docs(request, section)


def releases_view(request):
    """Release Notes page showing comprehensive development history."""
    return render(request, "public_app/release_note.html")


def api_docs_download(request, fmt="pdf"):
    """Serve API documentation as markdown or PDF."""
    import subprocess
    import tempfile
    from pathlib import Path

    from django.conf import settings
    from django.http import FileResponse, HttpResponse

    import json

    version = _hub_version()
    catalog = _interface_docs_context(request)["interface_catalog"]
    md_content = "# SciTeX interface provider catalog\n\n" + (
        "Installed declarations only. Host admission is not observed and live APIs were not probed.\n\n"
        "```json\n" + json.dumps(catalog, indent=2) + "\n```\n"
    )

    if fmt == "md":
        response = HttpResponse(md_content, content_type="text/markdown; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="scitex-api-docs-v{version}.md"'
        )
        return response

    # Generate PDF using pandoc
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path = Path(tmpdir) / "api-docs.md"
        pdf_path = Path(tmpdir) / "api-docs.pdf"

        md_path.write_text(md_content)

        try:
            # Try different PDF engines in order of preference
            pdf_engines = ["pdflatex", "xelatex", "wkhtmltopdf", None]
            success = False

            for engine in pdf_engines:
                cmd = ["pandoc", str(md_path), "-o", str(pdf_path)]
                if engine:
                    cmd.extend(["--pdf-engine", engine])

                result = subprocess.run(cmd, capture_output=True)
                if result.returncode == 0 and pdf_path.exists():
                    success = True
                    break

            if success:
                response = FileResponse(
                    open(pdf_path, "rb"),
                    content_type="application/pdf",
                )
                response["Content-Disposition"] = (
                    f'attachment; filename="scitex-api-docs-v{version}.pdf"'
                )
                return response
            else:
                # Return error message if no PDF engine works
                return HttpResponse(
                    "PDF generation unavailable. Please download Markdown instead.",
                    status=503,
                )
        except FileNotFoundError:
            return HttpResponse(
                "pandoc not installed. Please download Markdown instead.",
                status=503,
            )


@login_required
def scitex_api_keys(request):
    """
    SciTeX API Key Management Page

    Allows users to create, view, and manage their SciTeX API keys
    for programmatic access to Scholar, Code, Viz, and Writer services.
    """
    from apps.infra.accounts_app.models import APIKey

    # Handle POST requests (create new API key)
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create":
            name = request.POST.get("name", "").strip()
            if not name:
                messages.error(request, "Please provide a name for your API key")
                return redirect("public_app:scitex_api_keys")

            # Create new API key
            api_key, full_key = APIKey.create_key(
                user=request.user,
                name=name,
                scopes=["scholar:read", "scholar:write"],  # Default scopes
            )

            # Store the full key in session to show once
            request.session["new_api_key"] = full_key
            messages.success(request, f'API key "{name}" created successfully!')
            return redirect("public_app:scitex_api_keys")

        elif action == "delete":
            key_id = request.POST.get("key_id")
            try:
                api_key = APIKey.objects.get(id=key_id, user=request.user)
                key_name = api_key.name
                api_key.delete()
                messages.success(request, f'API key "{key_name}" deleted')
            except APIKey.DoesNotExist:
                messages.error(request, "API key not found")
            return redirect("public_app:scitex_api_keys")

        elif action == "toggle":
            key_id = request.POST.get("key_id")
            try:
                api_key = APIKey.objects.get(id=key_id, user=request.user)
                api_key.is_active = not api_key.is_active
                api_key.save()
                status = "activated" if api_key.is_active else "deactivated"
                messages.success(request, f'API key "{api_key.name}" {status}')
            except APIKey.DoesNotExist:
                messages.error(request, "API key not found")
            return redirect("public_app:scitex_api_keys")

    # Get user's API keys
    api_keys = APIKey.objects.filter(user=request.user).order_by("-created_at")

    # Get newly created key from session (show once)
    new_api_key = request.session.pop("new_api_key", None)

    context = {
        "api_keys": api_keys,
        "new_api_key": new_api_key,
    }

    return render(request, "public_app/pages/api_keys.html", context)


# EOF
