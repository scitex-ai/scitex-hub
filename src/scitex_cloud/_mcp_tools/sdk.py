#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Platform SDK MCP tools — DataStore, FileVault, JobQueue for AI agents."""

from __future__ import annotations

from .api import _json


def register_sdk_tools(mcp) -> None:
    """Register Platform SDK tools with FastMCP server."""

    # ── DataStore ──────────────────────────────────────────────────────

    @mcp.tool()
    async def platform_data_list(app: str, schema: str, project_id: str = "") -> str:
        """List DataStore records for an app/schema.

        Args:
            app: App identifier (e.g. "my-app").
            schema: Data schema name (e.g. "Experiment").
            project_id: Optional project ID to scope results.
        """
        from scitex_cloud.sdk import data

        kwargs = {}
        if project_id:
            kwargs["project_id"] = project_id
        result = data.list_records(app, schema, **kwargs)
        return _json(result)

    @mcp.tool()
    async def platform_data_create(app: str, schema: str, json_data: str) -> str:
        """Create a DataStore record.

        Args:
            app: App identifier.
            schema: Data schema name.
            json_data: JSON string of the record data.
        """
        import json

        from scitex_cloud.sdk import data

        payload = json.loads(json_data)
        result = data.create(app, schema, payload)
        return _json(result)

    @mcp.tool()
    async def platform_data_get(app: str, schema: str, record_id: str) -> str:
        """Get a single DataStore record by ID.

        Args:
            app: App identifier.
            schema: Data schema name.
            record_id: Record primary key.
        """
        from scitex_cloud.sdk import data

        result = data.get(app, schema, record_id)
        return _json(result)

    @mcp.tool()
    async def platform_data_update(
        app: str, schema: str, record_id: str, json_data: str
    ) -> str:
        """Update a DataStore record.

        Args:
            app: App identifier.
            schema: Data schema name.
            record_id: Record primary key.
            json_data: JSON string of fields to update.
        """
        import json

        from scitex_cloud.sdk import data

        payload = json.loads(json_data)
        result = data.update(app, schema, record_id, payload)
        return _json(result)

    @mcp.tool()
    async def platform_data_delete(app: str, schema: str, record_id: str) -> str:
        """Delete a DataStore record.

        Args:
            app: App identifier.
            schema: Data schema name.
            record_id: Record primary key.
        """
        from scitex_cloud.sdk import data

        result = data.delete(app, schema, record_id)
        return _json(result)

    @mcp.tool()
    async def platform_data_search(app: str, schema: str, query: str) -> str:
        """Search DataStore records.

        Args:
            app: App identifier.
            schema: Data schema name.
            query: Full-text search query.
        """
        from scitex_cloud.sdk import data

        result = data.search(app, schema, query)
        return _json(result)

    # ── FileVault ──────────────────────────────────────────────────────

    @mcp.tool()
    async def platform_files_list(app: str, path: str = "", project: str = "") -> str:
        """List files in an app's FileVault.

        Args:
            app: App identifier.
            path: Subdirectory path (default: root).
            project: Optional project scope.
        """
        from scitex_cloud.sdk import files

        kwargs = {}
        if project:
            kwargs["project"] = project
        result = files.list_files(app, path=path, **kwargs)
        return _json(result)

    @mcp.tool()
    async def platform_files_upload(
        app: str, remote_path: str, content: str, project: str = ""
    ) -> str:
        """Upload text content to FileVault.

        Args:
            app: App identifier.
            remote_path: Destination path in vault.
            content: Text content to upload.
            project: Optional project scope.
        """
        from scitex_cloud.sdk import files

        kwargs = {}
        if project:
            kwargs["project"] = project
        result = files.upload(app, remote_path, content, **kwargs)
        return _json(result)

    @mcp.tool()
    async def platform_files_download(
        app: str, remote_path: str, project: str = ""
    ) -> str:
        """Download a file from FileVault.

        Args:
            app: App identifier.
            remote_path: File path in vault.
            project: Optional project scope.
        """
        from scitex_cloud.sdk import files

        kwargs = {}
        if project:
            kwargs["project"] = project
        result = files.download(app, remote_path, **kwargs)
        return _json(result)

    @mcp.tool()
    async def platform_files_delete(
        app: str, remote_path: str, project: str = ""
    ) -> str:
        """Delete a file from FileVault.

        Args:
            app: App identifier.
            remote_path: File path in vault.
            project: Optional project scope.
        """
        from scitex_cloud.sdk import files

        kwargs = {}
        if project:
            kwargs["project"] = project
        result = files.delete(app, remote_path, **kwargs)
        return _json(result)

    # ── JobQueue ───────────────────────────────────────────────────────

    @mcp.tool()
    async def platform_jobs_submit(
        app: str, job_name: str, params_json: str = "{}", project_id: str = ""
    ) -> str:
        """Submit a background job to JobQueue.

        Args:
            app: App identifier.
            job_name: Job type name (e.g. "export_csv").
            params_json: JSON string of job parameters.
            project_id: Optional project ID.
        """
        import json

        from scitex_cloud.sdk import jobs

        params = json.loads(params_json) if params_json != "{}" else None
        kwargs = {}
        if project_id:
            kwargs["project_id"] = project_id
        result = jobs.submit(app, job_name, params=params, **kwargs)
        return _json(result)

    @mcp.tool()
    async def platform_jobs_status(app: str, job_id: str) -> str:
        """Get job status and result.

        Args:
            app: App identifier.
            job_id: Job ID to check.
        """
        from scitex_cloud.sdk import jobs

        result = jobs.status(app, job_id)
        return _json(result)

    @mcp.tool()
    async def platform_jobs_cancel(app: str, job_id: str) -> str:
        """Cancel a running job.

        Args:
            app: App identifier.
            job_id: Job ID to cancel.
        """
        from scitex_cloud.sdk import jobs

        result = jobs.cancel(app, job_id)
        return _json(result)

    @mcp.tool()
    async def platform_jobs_list(app: str) -> str:
        """List all jobs for an app.

        Args:
            app: App identifier.
        """
        from scitex_cloud.sdk import jobs

        result = jobs.list_jobs(app)
        return _json(result)


# EOF
