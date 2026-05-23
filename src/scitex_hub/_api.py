#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/api.py
"""
SciTeX Hub Python API - Programmatic access to cloud operations.

Usage:
    >>> import scitex_hub
    >>> client = scitex_hub.CloudClient()
    >>> client.scholar_search("neural networks")
    >>> client.enrich_bibtex("@article{...}")
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional


class CloudClient:
    """Python client for SciTeX Hub API.

    Parameters
    ----------
    api_key : str, optional
        API key for authenticated endpoints. Falls back to SCITEX_CLOUD_API_KEY env var.
    base_url : str, optional
        Cloud server URL. Falls back to SCITEX_CLOUD_URL env var or https://scitex.cloud.

    Examples
    --------
    >>> client = CloudClient()
    >>> result = client.scholar_search("machine learning")
    >>> print(result["papers"])
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("SCITEX_CLOUD_API_KEY")
        self.base_url = (
            base_url or os.environ.get("SCITEX_CLOUD_URL") or "https://scitex.cloud"
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        files: Optional[dict] = None,
        auth_required: bool = True,
    ) -> dict:
        """Make HTTP request to SciTeX Hub API."""
        import requests

        url = f"{self.base_url}{endpoint}"
        headers = {"X-Requested-With": "XMLHttpRequest"}

        if auth_required:
            if not self.api_key:
                raise ValueError(
                    "API key required. Set SCITEX_CLOUD_API_KEY or pass api_key."
                )
            headers["Authorization"] = f"Bearer {self.api_key}"

        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=data, timeout=60)
        elif method.upper() == "POST":
            if files:
                response = requests.post(
                    url, headers=headers, data=data, files=files, timeout=120
                )
            else:
                response = requests.post(url, headers=headers, json=data, timeout=60)
        else:
            raise ValueError(f"Unknown method: {method}")

        response.raise_for_status()

        try:
            return response.json()
        except json.JSONDecodeError:
            return {"content": response.text}

    def scholar_search(self, query: str, limit: int = 10) -> dict:
        """Search papers via SciTeX Hub (public, no auth required).

        Parameters
        ----------
        query : str
            Search query string.
        limit : int, optional
            Maximum number of results.

        Returns
        -------
        dict
            Search results with papers list.
        """
        return self._request(
            "GET",
            "/api/v1/scholar/search/",
            data={"q": query, "limit": limit},
            auth_required=False,
        )

    def crossref_search(self, query: str, rows: int = 10, offset: int = 0) -> dict:
        """Search CrossRef database via cloud proxy.

        Parameters
        ----------
        query : str
            Search query string.
        rows : int, optional
            Number of results per page.
        offset : int, optional
            Offset for pagination.

        Returns
        -------
        dict
            CrossRef search results.
        """
        return self._request(
            "GET",
            "/scholar/api/crossref/search/",
            data={"query": query, "rows": rows, "offset": offset},
        )

    def crossref_by_doi(self, doi: str) -> dict:
        """Get CrossRef metadata by DOI.

        Parameters
        ----------
        doi : str
            Digital Object Identifier.

        Returns
        -------
        dict
            CrossRef metadata for the DOI.
        """
        return self._request(
            "GET",
            "/scholar/api/crossref/doi/",
            data={"doi": doi},
        )

    def enrich_bibtex(
        self,
        bibtex_content: str,
        use_cache: bool = True,
        timeout: int = 120,
    ) -> str:
        """Enrich BibTeX content with metadata.

        Parameters
        ----------
        bibtex_content : str
            BibTeX content to enrich.
        use_cache : bool, optional
            Whether to use cached results.
        timeout : int, optional
            Maximum time to wait for enrichment (seconds).

        Returns
        -------
        str
            Enriched BibTeX content.
        """
        import io

        import requests

        # Upload file
        files = {"bibtex_file": ("input.bib", io.StringIO(bibtex_content))}
        data = {"use_cache": "true" if use_cache else "false"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Requested-With": "XMLHttpRequest",
        }

        response = requests.post(
            f"{self.base_url}/scholar/bibtex/upload/",
            headers=headers,
            files=files,
            data=data,
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()

        if not result.get("success"):
            raise RuntimeError(result.get("error", "Upload failed"))

        job_id = result["job_id"]

        # Poll for completion
        max_attempts = timeout // 2
        for _ in range(max_attempts):
            status_response = requests.get(
                f"{self.base_url}/scholar/api/bibtex/job/{job_id}/status/",
                headers=headers,
                timeout=30,
            )
            status_data = status_response.json()
            status = status_data.get("status")

            if status == "completed":
                download_response = requests.get(
                    f"{self.base_url}/scholar/api/bibtex/job/{job_id}/download/",
                    headers=headers,
                    timeout=60,
                )
                if download_response.status_code == 200:
                    return download_response.text
                raise RuntimeError("Download failed")

            elif status in ("failed", "cancelled"):
                raise RuntimeError(f"Job {status}")

            time.sleep(2)

        raise TimeoutError(f"Enrichment timed out after {timeout}s")

    def writer_compile(
        self,
        project_id: str,
        document_type: str = "manuscript",
    ) -> dict:
        """Compile LaTeX manuscript via cloud.

        Parameters
        ----------
        project_id : str
            Project identifier.
        document_type : str, optional
            Type of document: manuscript, supplementary, revision.

        Returns
        -------
        dict
            Compilation result with PDF URL.
        """
        return self._request(
            "POST",
            "/writer/api/compile/",
            data={"project_id": project_id, "document_type": document_type},
        )

    def project_list_files(self, project_id: str, path: str = "") -> dict:
        """List files in a cloud project.

        Parameters
        ----------
        project_id : str
            Project identifier.
        path : str, optional
            Subdirectory path.

        Returns
        -------
        dict
            File listing.
        """
        return self._request(
            "GET",
            "/project/api/files/",
            data={"project_id": project_id, "path": path},
        )

    def get_context(self, page: str = "") -> dict:
        """Get web app context for AI agents.

        Parameters
        ----------
        page : str, optional
            Current page URL (e.g. /writer/).

        Returns
        -------
        dict
            Context including username, active skill, all skills,
            available actions, and aggregated context.
        """
        return self._request("GET", "/llm/api/context/", data={"page": page})

    def eval_js(self, code: str, timeout: int = 10) -> dict:
        """Evaluate JavaScript in the user's browser.

        Parameters
        ----------
        code : str
            JavaScript code to evaluate.
        timeout : int, optional
            Max seconds to wait for result.

        Returns
        -------
        dict
            Evaluation result from the browser.
        """
        return self._request(
            "POST",
            "/llm/api/eval-js/",
            data={"code": code, "timeout": timeout},
        )

    def ui_action(self, steps: list, delay_ms: int = 900) -> dict:
        """Drive browser UI actions via WebSocket relay.

        Parameters
        ----------
        steps : list
            Action steps (navigate, highlight, click, fill, scroll, clear).
        delay_ms : int, optional
            Delay between steps in milliseconds.

        Returns
        -------
        dict
            Result with number of steps sent.
        """
        return self._request(
            "POST",
            "/llm/api/ui-action/",
            data={"steps": steps, "delay_ms": delay_ms},
        )

    def status(self) -> dict:
        """Check cloud service status.

        Returns
        -------
        dict
            Status information including cloud availability.
        """
        import requests

        result = {
            "base_url": self.base_url,
            "api_key_configured": bool(self.api_key),
        }

        try:
            response = requests.get(
                f"{self.base_url}/api/v1/status/",
                timeout=10,
            )
            result["cloud_status"] = (
                "online" if response.status_code == 200 else "error"
            )
        except Exception as e:
            result["cloud_status"] = "unreachable"
            result["error"] = str(e)

        return result


# EOF
