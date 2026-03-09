#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-28 21:31:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/public_app/views/api.py
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


def api_docs(request):
    """Display the API documentation page - shows getting-started by default."""
    from django.conf import settings

    from apps.infra.public_app.config import (
        API_DOC_DEFAULT_SECTION,
        get_active_campaign_token,
        get_all_sections,
        get_section,
    )

    section_info = get_section(API_DOC_DEFAULT_SECTION)
    version = getattr(settings, "SCITEX_CLOUD_VERSION", "0.7.0-alpha")

    # Get user's API key if authenticated
    user_api_key = (
        _get_user_api_key(request.user) if request.user.is_authenticated else None
    )

    # Test password for dev mode only (for API docs examples)
    test_password = ""
    if settings.DEBUG and request.user.is_authenticated:
        test_password = getattr(settings, "TEST_USER_PASSWORD", "")

    return render(
        request,
        "public_app/pages/api_docs_section.html",
        {
            "section_title": section_info["title"],
            "section_template": section_info["template"],
            "current_section": API_DOC_DEFAULT_SECTION,
            "sections": get_all_sections(),
            "campaign_token": get_active_campaign_token(),
            "user_api_key": user_api_key,
            "version": version,
            "test_password": test_password,
            "debug": settings.DEBUG,
        },
    )


def api_docs_section(request, section):
    """Display a specific API documentation section."""
    from django.conf import settings

    from apps.infra.public_app.config import (
        API_DOC_DEFAULT_SECTION,
        get_active_campaign_token,
        get_all_sections,
        get_section,
    )

    section_info = get_section(section)
    if not section_info:
        # Fallback to default section
        section = API_DOC_DEFAULT_SECTION
        section_info = get_section(section)

    version = getattr(settings, "SCITEX_CLOUD_VERSION", "0.7.0-alpha")
    user_api_key = (
        _get_user_api_key(request.user) if request.user.is_authenticated else None
    )

    # Test password for dev mode only (for API docs examples)
    test_password = ""
    if settings.DEBUG and request.user.is_authenticated:
        test_password = getattr(settings, "TEST_USER_PASSWORD", "")

    context = {
        "section_title": section_info["title"],
        "section_template": section_info["template"],
        "current_section": section,
        "sections": get_all_sections(),
        "campaign_token": get_active_campaign_token(),
        "user_api_key": user_api_key,
        "version": version,
        "test_password": test_password,
        "debug": settings.DEBUG,
    }

    if section == "mcp-api":
        from apps.infra.public_app.config.mcp_tools import MCP_TOOLS

        context["mcp_tools"] = MCP_TOOLS
        context["mcp_tool_count"] = sum(c["count"] for c in MCP_TOOLS)

    return render(request, "public_app/pages/api_docs_section.html", context)


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

    from apps.infra.public_app.config import get_active_campaign_token
    from apps.infra.public_app.services import generate_api_docs_markdown

    version = getattr(settings, "SCITEX_CLOUD_VERSION", "0.7.0-alpha")
    base_url = request.build_absolute_uri("/").rstrip("/")
    campaign_token = get_active_campaign_token() or "your-api-key"

    # Generate markdown content from API registry (single source of truth)
    md_content = generate_api_docs_markdown(version, base_url, campaign_token)

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
