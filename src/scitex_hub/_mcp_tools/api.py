#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_mcp_tools/api.py
"""Django API tools for FastMCP server."""

import json
import os
from typing import Optional


def _json(data: dict) -> str:
    return json.dumps(data, indent=2, default=str)


def get_on_site_env(username: str = "", site_url: str = "") -> dict[str, str]:
    """Build env vars for on-site MCP auth (injected into .mcp.json).

    Args:
        username: The container user's Django username.
        site_url: Django server URL. Falls back to SCITEX_CLOUD_SITE_URL env
                  var, then to http://web:8000 (Docker internal).
    """
    url = site_url or os.environ.get("SCITEX_CLOUD_SITE_URL", "http://web:8000")
    env = {"SCITEX_CLOUD_IS_ON_SITE": "1", "SCITEX_CLOUD_URL": url}
    if username:
        env["SCITEX_CLOUD_USERNAME"] = username
    return env


def _get_config() -> dict:
    """Get API configuration from environment."""
    is_on_site = os.environ.get("SCITEX_CLOUD_IS_ON_SITE") == "1"
    return {
        "api_key": os.environ.get("SCITEX_CLOUD_API_KEY"),
        "base_url": os.environ.get(
            "SCITEX_CLOUD_URL",
            "http://web:8000" if is_on_site else "https://scitex.ai",
        ),
        "is_on_site": is_on_site,
        "username": os.environ.get("SCITEX_CLOUD_USERNAME", ""),
    }


def _make_request(
    method: str,
    endpoint: str,
    data: Optional[dict] = None,
    files: Optional[dict] = None,
    auth_required: bool = True,
) -> dict:
    """Make HTTP request to SciTeX Cloud API."""
    import requests

    config = _get_config()
    url = f"{config['base_url']}{endpoint}"

    headers = {"X-Requested-With": "XMLHttpRequest"}
    if auth_required:
        if config["is_on_site"] and config["username"]:
            # On-site: authenticate via trusted header (no API key needed)
            headers["X-SciTeX-OnSite"] = config["username"]
        elif config["api_key"]:
            headers["Authorization"] = f"Bearer {config['api_key']}"
        else:
            return {
                "success": False,
                "error": "API key required",
                "hint": "Set SCITEX_CLOUD_API_KEY or SCITEX_CLOUD_IS_ON_SITE=1",
            }

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=data, timeout=60)
        elif method.upper() == "POST":
            if files:
                response = requests.post(
                    url, headers=headers, data=data, files=files, timeout=120
                )
            else:
                response = requests.post(url, headers=headers, json=data, timeout=60)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            return {"success": False, "error": f"Unknown method: {method}"}

        if response.status_code >= 400:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text[:500],
            }

        try:
            result = response.json()
            result["success"] = True
            return result
        except json.JSONDecodeError:
            return {"success": True, "content": response.text}

    except requests.Timeout:
        return {"success": False, "error": "Request timed out"}
    except requests.ConnectionError:
        return {"success": False, "error": "Connection failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def register_api_tools(mcp) -> None:
    """Register Django API tools with FastMCP server."""

    @mcp.tool()
    async def api_scholar_search(
        query: str,
        limit: int = 10,
    ) -> str:
        """Use whenever the user asks to search papers, find publications, look up scholarly articles, or mentions the SciTeX Cloud scholar database; replaces raw HTTP calls to the SciTeX Cloud /api/v1/scholar/search/ REST endpoint (public, no auth)."""
        result = _make_request(
            "GET",
            "/api/v1/scholar/search/",
            data={"q": query, "limit": limit},
            auth_required=False,
        )
        return _json(result)

    @mcp.tool()
    async def api_crossref_search(
        query: str,
        rows: int = 10,
        offset: int = 0,
    ) -> str:
        """Use when the user asks to search CrossRef, lookup DOI metadata by query, or enrich a bibliography via the SciTeX Cloud CrossRef proxy; replaces raw HTTP calls to the SciTeX Cloud /scholar/api/crossref/search/ REST endpoint (auth required)."""
        result = _make_request(
            "GET",
            "/scholar/api/crossref/search/",
            data={"query": query, "rows": rows, "offset": offset},
        )
        return _json(result)

    @mcp.tool()
    async def api_crossref_by_doi(doi: str) -> str:
        """Use when the user asks to resolve a DOI, fetch CrossRef metadata for a specific DOI, or verify a citation via SciTeX Cloud; replaces raw HTTP calls to the SciTeX Cloud /scholar/api/crossref/doi/ REST endpoint."""
        result = _make_request(
            "GET",
            "/scholar/api/crossref/doi/",
            data={"doi": doi},
        )
        return _json(result)

    @mcp.tool()
    async def api_writer_compile(
        project_id: str,
        document_type: str = "manuscript",
    ) -> str:
        """Use when the user asks to compile a LaTeX manuscript, build a PDF, or render a writer project on SciTeX Cloud; replaces raw HTTP calls to the SciTeX Cloud /writer/api/compile/ REST endpoint. Document types: manuscript, supplementary, revision."""
        result = _make_request(
            "POST",
            "/writer/api/compile/",
            data={"project_id": project_id, "document_type": document_type},
        )
        return _json(result)

    @mcp.tool()
    async def api_writer_list_sections(project_id: str) -> str:
        """Use when the user asks to list manuscript sections, inspect writer project structure, or see chapter layout on SciTeX Cloud; replaces raw HTTP calls to the SciTeX Cloud /writer/api/sections/ REST endpoint."""
        result = _make_request(
            "GET",
            "/writer/api/sections/",
            data={"project_id": project_id},
        )
        return _json(result)

    @mcp.tool()
    async def api_project_list_files(
        project_id: str,
        path: str = "",
    ) -> str:
        """Use when the user asks to list files, browse a directory, or inspect the tree of a SciTeX Cloud project; replaces raw HTTP calls to the SciTeX Cloud /project/api/files/ REST endpoint."""
        result = _make_request(
            "GET",
            "/project/api/files/",
            data={"project_id": project_id, "path": path},
        )
        return _json(result)

    @mcp.tool()
    async def api_project_commit(
        project_id: str,
        message: str,
        files: Optional[list] = None,
    ) -> str:
        """Use when the user asks to commit changes, save edits, or snapshot a SciTeX Cloud project to Git; replaces raw HTTP calls to the SciTeX Cloud /project/api/commit/ REST endpoint. Pass files=[paths] to commit a subset, else all changes commit."""
        data = {"project_id": project_id, "message": message}
        if files:
            data["files"] = files
        result = _make_request("POST", "/project/api/commit/", data=data)
        return _json(result)

    @mcp.tool()
    async def api_enrich_bibtex(
        bibtex_content: str,
        use_cache: bool = True,
    ) -> str:
        """Use when the user asks to enrich a .bib file, fill in missing DOIs/abstracts/impact-factors, or run BibTeX enrichment via SciTeX Cloud; replaces raw HTTP calls to the SciTeX Cloud /scholar/bibtex/upload/ REST endpoint plus job polling."""
        import io
        import time

        # Upload file
        files = {"bibtex_file": ("input.bib", io.StringIO(bibtex_content))}
        data = {"use_cache": "true" if use_cache else "false"}

        upload_result = _make_request(
            "POST",
            "/scholar/bibtex/upload/",
            data=data,
            files=files,
        )

        if not upload_result.get("success"):
            return _json(upload_result)

        job_id = upload_result.get("job_id")
        if not job_id:
            return _json({"success": False, "error": "No job ID returned"})

        # Poll for completion
        config = _get_config()
        import requests

        headers = {"X-Requested-With": "XMLHttpRequest"}
        if config["is_on_site"] and config["username"]:
            headers["X-SciTeX-OnSite"] = config["username"]
        elif config["api_key"]:
            headers["Authorization"] = f"Bearer {config['api_key']}"

        max_attempts = 60
        for _ in range(max_attempts):
            try:
                response = requests.get(
                    f"{config['base_url']}/scholar/api/bibtex/job/{job_id}/status/",
                    headers=headers,
                    timeout=30,
                )
                status_data = response.json()
                status = status_data.get("status")

                if status == "completed":
                    # Download result
                    download_response = requests.get(
                        f"{config['base_url']}/scholar/api/bibtex/job/{job_id}/download/",
                        headers=headers,
                        timeout=60,
                    )
                    if download_response.status_code == 200:
                        return _json(
                            {
                                "success": True,
                                "bibtex": download_response.text,
                                "job_id": job_id,
                            }
                        )
                    else:
                        return _json({"success": False, "error": "Download failed"})

                elif status in ("failed", "cancelled"):
                    return _json(
                        {"success": False, "error": f"Job {status}", "job_id": job_id}
                    )

                time.sleep(2)

            except Exception as e:
                return _json({"success": False, "error": str(e)})

        return _json({"success": False, "error": "Job timed out", "job_id": job_id})

    @mcp.tool()
    async def api_status() -> str:
        """Use when the user asks whether SciTeX Cloud is up, to check API health, verify credentials, or debug a connection issue; replaces raw HTTP calls to the SciTeX Cloud /api/v1/status/ REST endpoint."""
        config = _get_config()
        result = {
            "base_url": config["base_url"],
            "api_key_configured": bool(config["api_key"]),
        }

        # Try a simple health check
        try:
            import requests

            response = requests.get(
                f"{config['base_url']}/api/v1/status/",
                timeout=10,
            )
            result["cloud_status"] = (
                "online" if response.status_code == 200 else "error"
            )
            result["success"] = True
        except Exception as e:
            result["cloud_status"] = "unreachable"
            result["error"] = str(e)
            result["success"] = False

        return _json(result)


# EOF
