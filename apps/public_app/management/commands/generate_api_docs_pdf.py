#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate API Documentation as Markdown.

Usage:
    python manage.py generate_api_docs_pdf

Generates a Markdown file at:
    static/public_app/docs/scitex-api-docs-v{version}.md

The markdown can be converted to PDF using:
    pandoc scitex-api-docs.md -o scitex-api-docs.pdf
"""

from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate API Documentation as Markdown"

    def handle(self, *args, **options):
        from apps.public_app.config import (
            API_DOC_SECTION_ORDER,
            get_active_campaign_token,
            get_section,
        )

        version = getattr(settings, "SCITEX_VERSION", "0.6.11-alpha")
        base_url = getattr(settings, "SITE_URL", "https://scitex.ai")
        campaign_token = get_active_campaign_token() or "your-api-key"
        generated_date = datetime.now().strftime("%Y-%m-%d")

        # Build markdown content
        md_lines = [
            "# SciTeX API Documentation",
            "",
            f"**Version:** {version}  ",
            f"**Base URL:** {base_url}  ",
            f"**Generated:** {generated_date}  ",
            "**License:** AGPL-3.0",
            "",
            "---",
            "",
            "## Table of Contents",
            "",
        ]

        # Add TOC
        for section_key in API_DOC_SECTION_ORDER:
            section_info = get_section(section_key)
            if section_info:
                title = section_info["title"]
                md_lines.append(f"- [{title}](#{section_key})")
                for sub in section_info.get("subsections", []):
                    md_lines.append(
                        f"  - [{sub['emoji']} {sub['title']}](#{sub['id']})"
                    )

        md_lines.extend(["", "---", ""])

        # Add sections
        for section_key in API_DOC_SECTION_ORDER:
            section_info = get_section(section_key)
            if not section_info:
                continue

            md_lines.extend(
                [
                    f"## {section_info['title']} {{#{section_key}}}",
                    "",
                ]
            )

            for sub in section_info.get("subsections", []):
                md_lines.extend(
                    [
                        f"### {sub['emoji']} {sub['title']} {{#{sub['id']}}}",
                        "",
                    ]
                )

        # Add API Reference section with actual endpoints
        md_lines.extend(
            [
                "---",
                "",
                "## API Endpoints Quick Reference",
                "",
                "### Public API (No Authentication Required)",
                "",
                "| Method | Endpoint | Description |",
                "|--------|----------|-------------|",
                "| GET | `/api/v1/scholar/search/` | Search academic databases |",
                "| GET | `/api/v1/scholar/info/` | API documentation & rate limits |",
                "",
                "#### Example: Public Search",
                "",
                "```bash",
                f'curl "{base_url}/api/v1/scholar/search/?q=neural+networks&limit=10"',
                "```",
                "",
                "#### Example: With API Key (Higher Rate Limit)",
                "",
                "```bash",
                f'curl -H "X-SCITEX-API-KEY: {campaign_token}" \\',
                f'     "{base_url}/api/v1/scholar/search/?q=machine+learning"',
                "```",
                "",
                "### Scholar API (Authentication Required)",
                "",
                "| Method | Endpoint | Description |",
                "|--------|----------|-------------|",
                "| GET | `/scholar/api/crossref/search/` | CrossRef proxy search |",
                "| GET | `/scholar/api/crossref/health/` | CrossRef health check |",
                "| GET | `/scholar/api/crossref/stats/` | CrossRef usage stats |",
                "| POST | `/scholar/api/pdf/download/` | Download paper PDF |",
                "| GET | `/scholar/api/pdf/status/` | PDF download status |",
                "",
                "### Writer API",
                "",
                "| Method | Endpoint | Description |",
                "|--------|----------|-------------|",
                "| POST | `/writer/api/compile/` | Compile LaTeX manuscript |",
                "| GET | `/writer/api/sections/` | List manuscript sections |",
                "",
                "### Project API",
                "",
                "| Method | Endpoint | Description |",
                "|--------|----------|-------------|",
                "| GET | `/project/api/files/` | List project files |",
                "| POST | `/project/api/git/commit/` | Git commit |",
                "",
                "---",
                "",
                "## Authentication",
                "",
                "### API Key Header",
                "",
                "```",
                "X-SCITEX-API-KEY: your-api-key",
                "```",
                "",
                "### Campaign Token (Alpha)",
                "",
                "```",
                f"{campaign_token}",
                "```",
                "",
                "---",
                "",
                "## Rate Limits",
                "",
                "| Access Type | Limit | Notes |",
                "|-------------|-------|-------|",
                "| Anonymous | 10 req/min | Public API only |",
                "| API Key | 100 req/min | All endpoints |",
                "| Campaign Token | 100 req/min | Alpha testing |",
                "",
                "---",
                "",
                "## Response Format",
                "",
                "All endpoints return JSON by default:",
                "",
                "```json",
                "{",
                '  "status": "success",',
                '  "data": { ... },',
                '  "meta": {',
                '    "count": 10,',
                '    "page": 1',
                "  }",
                "}",
                "```",
                "",
                "---",
                "",
                f"*SciTeX API Documentation v{version} - {base_url}*",
            ]
        )

        # Output
        output_dir = Path(settings.BASE_DIR) / "static" / "public_app" / "docs"
        output_dir.mkdir(parents=True, exist_ok=True)

        md_file = output_dir / f"scitex-api-docs-v{version}.md"
        latest_md = output_dir / "scitex-api-docs-latest.md"

        content = "\n".join(md_lines)
        md_file.write_text(content)

        # Create latest symlink
        if latest_md.exists() or latest_md.is_symlink():
            latest_md.unlink()
        latest_md.symlink_to(md_file.name)

        self.stdout.write(self.style.SUCCESS(f"Markdown generated: {md_file}"))
        self.stdout.write(self.style.SUCCESS(f"Latest link: {latest_md}"))
        self.stdout.write("")
        self.stdout.write("To convert to PDF:")
        self.stdout.write(f"  pandoc {md_file} -o {md_file.with_suffix('.pdf')}")
