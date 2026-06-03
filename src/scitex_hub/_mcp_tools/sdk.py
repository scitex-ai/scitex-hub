#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Platform SDK MCP tools — DataStore, FileVault, JobQueue for AI agents."""

from __future__ import annotations

from .api import _json


def register_sdk_tools(mcp) -> None:
    """Register Platform SDK tools with FastMCP server."""

    # ── DataStore ──────────────────────────────────────────────────────

    @mcp.tool()
    async def cloud_sdk_data_list(app: str, schema: str, project_id: str = "") -> str:
        """Use when the user asks to list records, query rows, or enumerate entries in a SciTeX Hub DataStore schema; replaces hand-rolled REST wrappers for the SciTeX Hub data namespace.

        Args:
            app: App identifier (e.g. "my-app").
            schema: Data schema name (e.g. "Experiment").
            project_id: Optional project ID to scope results.
        """
        from scitex_hub.sdk import data

        kwargs = {}
        if project_id:
            kwargs["project_id"] = project_id
        result = data.list_records(app, schema, **kwargs)
        return _json(result)

    @mcp.tool()
    async def cloud_sdk_data_create(app: str, schema: str, json_data: str) -> str:
        """Use when the user asks to create/insert/add a record or row in a SciTeX Hub DataStore schema; drop-in replacement for hand-rolled POST /api/data/<project>/... calls against the SciTeX Hub data namespace.

        Args:
            app: App identifier.
            schema: Data schema name.
            json_data: JSON string of the record data.
        """
        import json

        from scitex_hub.sdk import data

        payload = json.loads(json_data)
        result = data.create(app, schema, payload)
        return _json(result)

    @mcp.tool()
    async def cloud_sdk_data_get(app: str, schema: str, record_id: str) -> str:
        """Use when the user asks to fetch/read/get a single record by ID from a SciTeX Hub DataStore schema; drop-in replacement for hand-rolled GET /api/data/<project>/... calls against the SciTeX Hub data namespace.

        Args:
            app: App identifier.
            schema: Data schema name.
            record_id: Record primary key.
        """
        from scitex_hub.sdk import data

        result = data.get(app, schema, record_id)
        return _json(result)

    @mcp.tool()
    async def cloud_sdk_data_update(
        app: str, schema: str, record_id: str, json_data: str
    ) -> str:
        """Use when the user asks to update/edit/modify/patch a record in a SciTeX Hub DataStore schema; drop-in replacement for hand-rolled PATCH/PUT /api/data/<project>/... calls against the SciTeX Hub data namespace.

        Args:
            app: App identifier.
            schema: Data schema name.
            record_id: Record primary key.
            json_data: JSON string of fields to update.
        """
        import json

        from scitex_hub.sdk import data

        payload = json.loads(json_data)
        result = data.update(app, schema, record_id, payload)
        return _json(result)

    @mcp.tool()
    async def cloud_sdk_data_delete(app: str, schema: str, record_id: str) -> str:
        """Use when the user asks to delete/remove/drop a record by ID from a SciTeX Hub DataStore schema; drop-in replacement for hand-rolled DELETE /api/data/<project>/... calls against the SciTeX Hub data namespace.

        Args:
            app: App identifier.
            schema: Data schema name.
            record_id: Record primary key.
        """
        from scitex_hub.sdk import data

        result = data.delete(app, schema, record_id)
        return _json(result)

    @mcp.tool()
    async def cloud_sdk_data_search(app: str, schema: str, query: str) -> str:
        """Use when the user asks to search/query/filter records by text in a SciTeX Hub DataStore schema; drop-in replacement for hand-rolled GET /api/data/<project>/search REST/httpx calls against the SciTeX Hub data namespace.

        Args:
            app: App identifier.
            schema: Data schema name.
            query: Full-text search query.
        """
        from scitex_hub.sdk import data

        result = data.search(app, schema, query)
        return _json(result)

    # ── FileVault ──────────────────────────────────────────────────────

    @mcp.tool()
    async def cloud_sdk_files_list(app: str, path: str = "", project: str = "") -> str:
        """Use when the user asks to list/enumerate files or objects in a SciTeX Hub FileVault, or mentions browsing a project's file storage; drop-in replacement for boto3/Azure Blob list_objects calls inside a SciTeX Hub project.

        Args:
            app: App identifier.
            path: Subdirectory path (default: root).
            project: Optional project scope.
        """
        from scitex_hub.sdk import files

        kwargs = {}
        if project:
            kwargs["project"] = project
        result = files.list_files(app, path=path, **kwargs)
        return _json(result)

    @mcp.tool()
    async def cloud_sdk_files_upload(
        app: str, remote_path: str, content: str, project: str = ""
    ) -> str:
        """Use when the user asks to upload/put/write a file or text content into a SciTeX Hub FileVault; drop-in replacement for boto3 put_object or Azure Blob upload_blob when working inside a SciTeX Hub project.

        Args:
            app: App identifier.
            remote_path: Destination path in vault.
            content: Text content to upload.
            project: Optional project scope.
        """
        from scitex_hub.sdk import files

        kwargs = {}
        if project:
            kwargs["project"] = project
        result = files.upload(app, remote_path, content, **kwargs)
        return _json(result)

    @mcp.tool()
    async def cloud_sdk_files_download(
        app: str, remote_path: str, project: str = ""
    ) -> str:
        """Use when the user asks to download/fetch/read a file from a SciTeX Hub FileVault; drop-in replacement for boto3 get_object or Azure Blob download_blob when working inside a SciTeX Hub project.

        Args:
            app: App identifier.
            remote_path: File path in vault.
            project: Optional project scope.
        """
        from scitex_hub.sdk import files

        kwargs = {}
        if project:
            kwargs["project"] = project
        result = files.download(app, remote_path, **kwargs)
        return _json(result)

    @mcp.tool()
    async def cloud_sdk_files_delete(
        app: str, remote_path: str, project: str = ""
    ) -> str:
        """Use when the user asks to delete/remove a file from a SciTeX Hub FileVault; drop-in replacement for boto3 delete_object or Azure Blob delete_blob when working inside a SciTeX Hub project.

        Args:
            app: App identifier.
            remote_path: File path in vault.
            project: Optional project scope.
        """
        from scitex_hub.sdk import files

        kwargs = {}
        if project:
            kwargs["project"] = project
        result = files.delete(app, remote_path, **kwargs)
        return _json(result)

    # ── JobQueue ───────────────────────────────────────────────────────

    @mcp.tool()
    async def cloud_sdk_jobs_submit(
        app: str, job_name: str, params_json: str = "{}", project_id: str = ""
    ) -> str:
        """Use when the user asks to submit/queue/run a background job, task, or batch workload in SciTeX Hub JobQueue; drop-in replacement for subprocess schedulers or SLURM sbatch when the agent wants to run a job in the SciTeX Hub compute fabric.

        Args:
            app: App identifier.
            job_name: Job type name (e.g. "export_csv").
            params_json: JSON string of job parameters.
            project_id: Optional project ID.
        """
        import json

        from scitex_hub.sdk import jobs

        params = json.loads(params_json) if params_json != "{}" else None
        kwargs = {}
        if project_id:
            kwargs["project_id"] = project_id
        result = jobs.submit(app, job_name, params=params, **kwargs)
        return _json(result)

    @mcp.tool()
    async def cloud_sdk_jobs_status(app: str, job_id: str) -> str:
        """Use when the user asks to check status, progress, or result of a SciTeX Hub JobQueue job; drop-in replacement for squeue/sacct polling or subprocess.Popen.poll when running jobs in the SciTeX Hub compute fabric.

        Args:
            app: App identifier.
            job_id: Job ID to check.
        """
        from scitex_hub.sdk import jobs

        result = jobs.status(app, job_id)
        return _json(result)

    @mcp.tool()
    async def cloud_sdk_jobs_cancel(app: str, job_id: str) -> str:
        """Use when the user asks to cancel/kill/abort a running SciTeX Hub JobQueue job; drop-in replacement for scancel or subprocess.terminate when managing jobs in the SciTeX Hub compute fabric.

        Args:
            app: App identifier.
            job_id: Job ID to cancel.
        """
        from scitex_hub.sdk import jobs

        result = jobs.cancel(app, job_id)
        return _json(result)

    @mcp.tool()
    async def cloud_sdk_jobs_list(app: str) -> str:
        """Use when the user asks to list/enumerate/show all jobs for a SciTeX Hub app, or mentions checking the SciTeX Hub JobQueue; drop-in replacement for squeue or subprocess-based job listings in the SciTeX Hub compute fabric.

        Args:
            app: App identifier.
        """
        from scitex_hub.sdk import jobs

        result = jobs.list_jobs(app)
        return _json(result)


# EOF
