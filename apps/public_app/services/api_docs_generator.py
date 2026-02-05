#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API Documentation Generator.

Generates markdown documentation from the API registry.
Single source of truth ensures consistency across HTML docs and PDF/MD exports.
"""

from __future__ import annotations

from datetime import datetime


def generate_api_docs_markdown(version: str, base_url: str, campaign_token: str) -> str:
    """Generate comprehensive markdown API documentation from registry."""
    from apps.public_app.config.api_registry import (
        API_REGISTRY,
        ERROR_CODES,
        RATE_LIMITS,
    )

    lines = [
        "# SciTeX API Documentation",
        "",
        f"**Version:** {version}",
        f"**Base URL:** `{base_url}` (or `https://scitex.ai` for cloud)",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d')}",
        "**License:** AGPL-3.0",
        "",
        "> **Note:** Replace `{BASE_URL}` in examples with your deployment URL.",
        "",
        "---",
        "",
    ]

    # Table of Contents
    lines.extend(_generate_toc(API_REGISTRY))

    # Getting Started
    lines.extend(_generate_getting_started(base_url, campaign_token))

    # API Categories
    for category, info in API_REGISTRY.items():
        lines.extend(_generate_category_docs(category, info, base_url, campaign_token))

    # Rate Limits
    lines.extend(_generate_rate_limits(RATE_LIMITS))

    # Error Codes
    lines.extend(_generate_error_codes(ERROR_CODES))

    # Footer
    lines.extend(
        [
            "---",
            "",
            f"*SciTeX API Documentation v{version}*",
            f"*{base_url}*",
            "*AGPL-3.0 License*",
        ]
    )

    return "\n".join(lines)


def _generate_toc(registry: dict) -> list[str]:
    """Generate table of contents."""
    lines = [
        "## Table of Contents",
        "",
        "1. [Getting Started](#getting-started)",
        "   - [Authentication](#authentication)",
        "   - [Quick Start](#quick-start)",
    ]

    idx = 2
    for category, info in registry.items():
        anchor = category.replace("_", "-")
        lines.append(f"{idx}. [{info['name']}](#{anchor})")
        for ep in info["endpoints"]:
            ep_anchor = ep["name"].lower().replace(" ", "-")
            lines.append(f"   - [{ep['name']}](#{ep_anchor})")
        idx += 1

    lines.extend(
        [
            f"{idx}. [Rate Limits](#rate-limits)",
            f"{idx + 1}. [Error Codes](#error-codes)",
            "",
            "---",
            "",
        ]
    )
    return lines


def _generate_getting_started(base_url: str, campaign_token: str) -> list[str]:
    """Generate getting started section."""
    return [
        "## Getting Started",
        "",
        "### Introduction",
        "",
        "The SciTeX API provides programmatic access to:",
        "- **Scholar**: Search academic papers across PubMed, arXiv, CrossRef, and more",
        "- **Writer**: Compile LaTeX manuscripts with version control",
        "- **Project**: Manage research project files and Git operations",
        "",
        "### Authentication",
        "",
        "#### API Key (Recommended)",
        "",
        "Include in `X-SCITEX-API-KEY` header:",
        "",
        "```bash",
        f'curl -H "X-SCITEX-API-KEY: {campaign_token}" \\',
        f'     "{base_url}/api/v1/scholar/search/?q=neural+networks"',
        "```",
        "",
        "#### JWT Token",
        "",
        "**Get token:**",
        "```bash",
        f"curl -X POST {base_url}/api/token/ \\",
        '  -H "Content-Type: application/json" \\',
        '  -d \'{"username": "user", "password": "pass"}\'',
        "```",
        "",
        "**Use token:**",
        "```bash",
        f'curl -H "Authorization: Bearer YOUR_TOKEN" {base_url}/scholar/api/search/',
        "```",
        "",
        "### Quick Start",
        "",
        "**Search papers (no auth):**",
        "```bash",
        f'curl "{base_url}/api/v1/scholar/search/?q=machine+learning&limit=10"',
        "```",
        "",
        "**Export as BibTeX:**",
        "```bash",
        f'curl "{base_url}/api/v1/scholar/search/?q=neural&format=bibtex" -o refs.bib',
        "```",
        "",
        "---",
        "",
    ]


def _generate_category_docs(
    category: str, info: dict, base_url: str, campaign_token: str
) -> list[str]:
    """Generate documentation for an API category."""
    anchor = category.replace("_", "-")
    lines = [
        f"## {info['name']}",
        "",
        f"{info['description']}",
        "",
        f"**Base Path:** `{info['base_path']}`",
        f"**Auth Required:** {'Yes' if info['auth_required'] else 'No'}",
        "",
    ]

    for ep in info["endpoints"]:
        lines.extend(_generate_endpoint_docs(ep, info, base_url, campaign_token))

    lines.append("---")
    lines.append("")
    return lines


def _generate_endpoint_docs(
    ep: dict, category_info: dict, base_url: str, campaign_token: str
) -> list[str]:
    """Generate documentation for a single endpoint."""
    full_path = f"{category_info['base_path']}{ep['path']}"
    ep_anchor = ep["name"].lower().replace(" ", "-")

    lines = [
        f"### {ep['name']}",
        "",
        f"{ep['description']}",
        "",
        f"**Endpoint:** `{ep['method']} {full_path}`",
        "",
    ]

    # Parameters
    params = ep.get("params", [])
    if params:
        lines.extend(
            [
                "**Parameters:**",
                "",
                "| Name | Type | Required | Description |",
                "|------|------|----------|-------------|",
            ]
        )
        for p in params:
            req = "Yes" if p.get("required") else "No"
            lines.append(f"| `{p['name']}` | {p['type']} | {req} | {p['desc']} |")
        lines.append("")

    # Example
    lines.append("**Example:**")
    lines.append("")
    lines.append("```bash")

    if category_info["auth_required"]:
        if ep["method"] == "GET":
            query = "&".join(
                f"{p['name']}=example" for p in params if p.get("required")
            )
            url = f"{base_url}{full_path}"
            if query:
                url += f"?{query}"
            lines.append(f'curl -H "X-SCITEX-API-KEY: {campaign_token}" "{url}"')
        else:
            body = ", ".join(
                f'"{p["name"]}": "value"' for p in params if p.get("required")
            )
            lines.append(f'curl -X {ep["method"]} "{base_url}{full_path}" \\')
            lines.append(f'  -H "X-SCITEX-API-KEY: {campaign_token}" \\')
            lines.append('  -H "Content-Type: application/json" \\')
            lines.append(f"  -d '{{{body}}}'")
    else:
        query = "&".join(f"{p['name']}=example" for p in params if p.get("required"))
        url = f"{base_url}{full_path}"
        if query:
            url += f"?{query}"
        lines.append(f'curl "{url}"')

    lines.append("```")
    lines.append("")

    # Response fields
    resp_fields = ep.get("response_fields", [])
    if resp_fields:
        lines.extend(
            [
                "**Response Fields:**",
                "",
                "| Field | Type | Description |",
                "|-------|------|-------------|",
            ]
        )
        for f in resp_fields:
            lines.append(f"| `{f['name']}` | {f['type']} | {f['desc']} |")
        lines.append("")

    # Response example
    resp_example = ep.get("response_example")
    if resp_example:
        import json

        lines.extend(
            [
                "**Response Example:**",
                "",
                "```json",
                json.dumps(resp_example, indent=2),
                "```",
                "",
            ]
        )

    return lines


def _generate_rate_limits(rate_limits: dict) -> list[str]:
    """Generate rate limits section."""
    lines = [
        "## Rate Limits",
        "",
        "| Access Type | Limit | Notes |",
        "|-------------|-------|-------|",
    ]
    for name, info in rate_limits.items():
        lines.append(
            f"| {name.replace('_', ' ').title()} | {info['limit']}/{info['window']} | {info['note']} |"
        )
    lines.extend(
        [
            "",
            "Rate limit headers in responses:",
            "- `X-RateLimit-Limit`: Max requests per window",
            "- `X-RateLimit-Remaining`: Requests remaining",
            "- `X-RateLimit-Reset`: Unix timestamp when limit resets",
            "",
        ]
    )
    return lines


def _generate_error_codes(error_codes: dict) -> list[str]:
    """Generate error codes section."""
    lines = [
        "## Error Codes",
        "",
        "| Code | Meaning |",
        "|------|---------|",
    ]
    for code, meaning in error_codes.items():
        lines.append(f"| {code} | {meaning} |")
    lines.extend(
        [
            "",
            "Error response format:",
            "```json",
            "{",
            '  "status": "error",',
            '  "error": "error_type",',
            '  "message": "Human readable message"',
            "}",
            "```",
            "",
        ]
    )
    return lines
