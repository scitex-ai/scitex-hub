#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for scitex_hub.sdk — Platform SDK client library."""

from unittest.mock import MagicMock, patch

import pytest

# ── PlatformClient ─────────────────────────────────────────────────────


class TestPlatformClient:
    """Test PlatformClient initialization and request routing."""

    def test_defaults(self):
        from scitex_hub.sdk._client import PlatformClient

        client = PlatformClient()
        assert client.base_url == "http://127.0.0.1:8000"
        assert client.token == ""

    def test_env_vars(self):
        from scitex_hub.sdk._client import PlatformClient

        with patch.dict(
            "os.environ",
            {
                "SCITEX_API_TOKEN": "test-jwt",
                "SCITEX_API_URL": "https://scitex.ai",
            },
        ):
            client = PlatformClient()
            assert client.token == "test-jwt"
            assert client.base_url == "https://scitex.ai"

    def test_explicit_args_override_env(self):
        from scitex_hub.sdk._client import PlatformClient

        with patch.dict(
            "os.environ",
            {
                "SCITEX_API_TOKEN": "env-token",
                "SCITEX_API_URL": "https://env.example.com",
            },
        ):
            client = PlatformClient(
                token="arg-token", base_url="https://arg.example.com"
            )
            assert client.token == "arg-token"
            assert client.base_url == "https://arg.example.com"

    def test_trailing_slash_stripped(self):
        from scitex_hub.sdk._client import PlatformClient

        client = PlatformClient(base_url="http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"

    def test_unsupported_method_raises(self):
        from scitex_hub.sdk._client import PlatformClient

        client = PlatformClient()
        with pytest.raises(ValueError, match="Unsupported HTTP method"):
            with patch("requests.get"):
                client.request("PATCH", "/api/test/")

    def test_get_client_singleton(self):
        from scitex_hub.sdk._client import get_client, reset_client

        reset_client()
        c1 = get_client()
        c2 = get_client()
        assert c1 is c2
        reset_client()

    def test_reset_client(self):
        from scitex_hub.sdk._client import get_client, reset_client

        reset_client()
        c1 = get_client()
        reset_client()
        c2 = get_client()
        assert c1 is not c2
        reset_client()

    @patch("requests.get")
    def test_auth_header_sent(self, mock_get):
        from scitex_hub.sdk._client import PlatformClient

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client = PlatformClient(token="my-jwt")
        client.request("GET", "/test/")

        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["headers"]["Authorization"] == "Bearer my-jwt"


# ── DataStore ──────────────────────────────────────────────────────────


class TestDataModule:
    """Test scitex_hub.sdk.data functions."""

    @patch("scitex_hub.sdk._data.get_client")
    def test_create(self, mock_gc):
        from scitex_hub.sdk import data

        mock_client = MagicMock()
        mock_client.request.return_value = {"id": "abc", "data": {"title": "Test"}}
        mock_gc.return_value = mock_client

        result = data.create("my-app", "Experiment", {"title": "Test"})
        mock_client.request.assert_called_once_with(
            "POST", "/platform/api/data/my-app/Experiment/", data={"title": "Test"}
        )
        assert result["id"] == "abc"

    @patch("scitex_hub.sdk._data.get_client")
    def test_list_records(self, mock_gc):
        from scitex_hub.sdk import data

        mock_client = MagicMock()
        mock_client.request.return_value = {"results": [], "count": 0}
        mock_gc.return_value = mock_client

        result = data.list_records("app", "Schema", filters={"status": "running"})
        mock_client.request.assert_called_once_with(
            "GET", "/platform/api/data/app/Schema/", params={"status": "running"}
        )
        assert result["count"] == 0

    @patch("scitex_hub.sdk._data.get_client")
    def test_get(self, mock_gc):
        from scitex_hub.sdk import data

        mock_client = MagicMock()
        mock_client.request.return_value = {"id": "123"}
        mock_gc.return_value = mock_client

        data.get("app", "Schema", "123")
        mock_client.request.assert_called_once_with(
            "GET", "/platform/api/data/app/Schema/123/"
        )

    @patch("scitex_hub.sdk._data.get_client")
    def test_update(self, mock_gc):
        from scitex_hub.sdk import data

        mock_client = MagicMock()
        mock_client.request.return_value = {"id": "123", "data": {"x": 1}}
        mock_gc.return_value = mock_client

        data.update("app", "Schema", "123", {"x": 1})
        mock_client.request.assert_called_once_with(
            "PUT", "/platform/api/data/app/Schema/123/", data={"x": 1}
        )

    @patch("scitex_hub.sdk._data.get_client")
    def test_delete(self, mock_gc):
        from scitex_hub.sdk import data

        mock_client = MagicMock()
        mock_client.request.return_value = {"deleted": True}
        mock_gc.return_value = mock_client

        data.delete("app", "Schema", "123")
        mock_client.request.assert_called_once_with(
            "DELETE", "/platform/api/data/app/Schema/123/"
        )

    @patch("scitex_hub.sdk._data.get_client")
    def test_search(self, mock_gc):
        from scitex_hub.sdk import data

        mock_client = MagicMock()
        mock_client.request.return_value = {"results": []}
        mock_gc.return_value = mock_client

        data.search("app", "Schema", "neural")
        mock_client.request.assert_called_once_with(
            "POST", "/platform/api/data/app/Schema/search/", data={"query": "neural"}
        )


# ── FileVault ──────────────────────────────────────────────────────────


class TestFilesModule:
    """Test scitex_hub.sdk.files functions."""

    @patch("scitex_hub.sdk._files.get_client")
    def test_list_files(self, mock_gc):
        from scitex_hub.sdk import files

        mock_client = MagicMock()
        mock_client.request.return_value = {"files": []}
        mock_gc.return_value = mock_client

        files.list_files("app", path="exports/")
        mock_client.request.assert_called_once_with(
            "GET", "/platform/api/files/app/exports/", params={}
        )

    @patch("scitex_hub.sdk._files.get_client")
    def test_upload_text(self, mock_gc):
        from scitex_hub.sdk import files

        mock_client = MagicMock()
        mock_client.request.return_value = {"uploaded": True}
        mock_gc.return_value = mock_client

        files.upload("app", "out.csv", "a,b\n1,2")
        mock_client.request.assert_called_once_with(
            "POST", "/platform/api/files/app/out.csv", data={"content": "a,b\n1,2"}
        )

    @patch("scitex_hub.sdk._files.get_client")
    def test_upload_bytes(self, mock_gc):
        from scitex_hub.sdk import files

        mock_client = MagicMock()
        mock_client.request.return_value = {"uploaded": True}
        mock_gc.return_value = mock_client

        files.upload("app", "img/photo.png", b"\x89PNG")
        call_args = mock_client.request.call_args
        assert call_args.args[0] == "POST"
        assert "files" in call_args.kwargs

    @patch("scitex_hub.sdk._files.get_client")
    def test_download(self, mock_gc):
        from scitex_hub.sdk import files

        mock_client = MagicMock()
        mock_client.request.return_value = {"content": "data"}
        mock_gc.return_value = mock_client

        files.download("app", "exports/data.csv")
        mock_client.request.assert_called_once_with(
            "GET", "/platform/api/files/app/exports/data.csv", params={}
        )


# ── JobQueue ───────────────────────────────────────────────────────────


class TestJobsModule:
    """Test scitex_hub.sdk.jobs functions."""

    @patch("scitex_hub.sdk._jobs.get_client")
    def test_submit(self, mock_gc):
        from scitex_hub.sdk import jobs

        mock_client = MagicMock()
        mock_client.request.return_value = {"job_id": "j1"}
        mock_gc.return_value = mock_client

        jobs.submit("app", "export_csv", params={"fmt": "xlsx"})
        call_data = mock_client.request.call_args.kwargs["data"]
        assert call_data["job_name"] == "export_csv"
        assert call_data["params"] == {"fmt": "xlsx"}

    @patch("scitex_hub.sdk._jobs.get_client")
    def test_status(self, mock_gc):
        from scitex_hub.sdk import jobs

        mock_client = MagicMock()
        mock_client.request.return_value = {"status": "completed"}
        mock_gc.return_value = mock_client

        jobs.status("app", "j1")
        mock_client.request.assert_called_once_with("GET", "/platform/api/jobs/app/j1/")

    @patch("scitex_hub.sdk._jobs.get_client")
    def test_cancel(self, mock_gc):
        from scitex_hub.sdk import jobs

        mock_client = MagicMock()
        mock_client.request.return_value = {"cancelled": True}
        mock_gc.return_value = mock_client

        jobs.cancel("app", "j1")
        mock_client.request.assert_called_once_with(
            "POST", "/platform/api/jobs/app/j1/cancel/"
        )

    @patch("scitex_hub.sdk._jobs.get_client")
    def test_list_jobs(self, mock_gc):
        from scitex_hub.sdk import jobs

        mock_client = MagicMock()
        mock_client.request.return_value = {"jobs": []}
        mock_gc.return_value = mock_client

        jobs.list_jobs("app")
        mock_client.request.assert_called_once_with("GET", "/platform/api/jobs/app/")


# ── CLI ────────────────────────────────────────────────────────────────


class TestSDKCLI:
    """Test SDK CLI commands invoke the right SDK functions."""

    def test_sdk_group_exists(self):
        from click.testing import CliRunner

        from scitex_hub._cli.sdk import sdk

        runner = CliRunner()
        result = runner.invoke(sdk, ["--help"])
        assert result.exit_code == 0
        assert "data" in result.output
        assert "files" in result.output
        assert "jobs" in result.output

    def test_data_subcommands(self):
        from click.testing import CliRunner

        from scitex_hub._cli.sdk import data

        runner = CliRunner()
        result = runner.invoke(data, ["--help"])
        assert result.exit_code == 0
        for cmd in ["list", "get", "create", "update", "delete", "search"]:
            assert cmd in result.output

    def test_files_subcommands(self):
        from click.testing import CliRunner

        from scitex_hub._cli.sdk import files

        runner = CliRunner()
        result = runner.invoke(files, ["--help"])
        assert result.exit_code == 0
        for cmd in ["list", "upload", "download", "delete"]:
            assert cmd in result.output

    def test_jobs_subcommands(self):
        from click.testing import CliRunner

        from scitex_hub._cli.sdk import jobs

        runner = CliRunner()
        result = runner.invoke(jobs, ["--help"])
        assert result.exit_code == 0
        for cmd in ["submit", "status", "cancel", "list"]:
            assert cmd in result.output


# EOF
