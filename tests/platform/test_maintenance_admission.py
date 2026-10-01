"""Exercise live flag changes and protocol admission without a production database."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from click.testing import CliRunner
from django.http import HttpResponse
from django.test import Client, RequestFactory, override_settings
from django.urls import path

from apps.infra.public_app.middleware_maintenance import (
    MaintenanceASGI,
    MaintenanceMiddleware,
)
from scitex_hub._cli.maintenance import maintenance
from scitex_hub.maintenance import read_state, write_state

urlpatterns = [path("apps/example/", lambda request: HttpResponse("workspace"))]


@pytest.fixture(autouse=True)
def isolated_request_routing():
    with override_settings(
        ROOT_URLCONF=__name__,
        MIDDLEWARE=[
            "apps.infra.public_app.middleware_maintenance.MaintenanceMiddleware"
        ],
        ALLOWED_HOSTS=["testserver"],
    ):
        yield


def test_running_client_observes_enable_and_disable_without_restart(tmp_path):
    flag = tmp_path / "operator" / "maintenance.json"
    with override_settings(SCITEX_HUB_MAINTENANCE_FILE=flag):
        client = Client()
        assert client.get("/apps/example/").content == b"workspace"
        write_state(flag, enabled=True, retry_after=60)
        response = client.get("/apps/example/")
        assert response.status_code == 503
        assert response["Retry-After"] == "60"
        assert response["Cache-Control"] == "no-store"
        write_state(flag, enabled=False)
        assert client.get("/apps/example/").content == b"workspace"


@pytest.mark.parametrize(
    "raw",
    [
        b'{"enabled":"false"}',
        b'{"enabled":true,"retry_after":true}',
        b"not-json",
        b"x" * 4097,
        b'{"enabled":true,"message":"\\ud800"}',
    ],
)
def test_bad_operator_state_blocks_instead_of_opening(tmp_path, raw):
    flag = tmp_path / "maintenance.json"
    flag.write_bytes(raw)
    with override_settings(SCITEX_HUB_MAINTENANCE_FILE=flag):
        response = Client().get("/apps/example/")
    assert response.status_code == 503
    assert not read_state(flag).valid


def test_liveness_and_maintenance_readiness_do_not_access_storage(tmp_path):
    flag = tmp_path / "maintenance.json"
    write_state(flag, enabled=True)
    with override_settings(SCITEX_HUB_MAINTENANCE_FILE=flag):
        client = Client()
        assert client.get("/livez/").json() == {"status": "alive"}
        ready = client.get("/maintenance-ready/")
        assert ready.status_code == 503
        assert ready.json()["scope"] == "maintenance"
        assert client.get("/livez/unsafe/").status_code == 503
    assert read_state(flag).enabled


def test_staff_and_query_headers_cannot_bypass_domain_admission(tmp_path):
    flag = tmp_path / "maintenance.json"
    write_state(flag, enabled=True)
    request = RequestFactory().post(
        "/apps/example/?maintenance=false", HTTP_X_MAINTENANCE_BYPASS="1"
    )
    request.user = Mock(is_authenticated=True, is_staff=True, is_superuser=True)
    downstream = Mock(side_effect=AssertionError("domain handler must not execute"))
    with override_settings(SCITEX_HUB_MAINTENANCE_FILE=flag):
        assert MaintenanceMiddleware(downstream)(request).status_code == 503
    downstream.assert_not_called()


def test_mounted_api_and_json_posts_receive_machine_readable_errors(tmp_path):
    flag = tmp_path / "maintenance.json"
    write_state(flag, enabled=True, message="Storage maintenance")
    with override_settings(SCITEX_HUB_MAINTENANCE_FILE=flag):
        client = Client()
        api = client.get("/apps/example/api/save/")
        post = client.post("/apps/example/", data="{}", content_type="application/json")
    assert api.status_code == post.status_code == 503
    assert api.json()["error"] == post.json()["error"] == "maintenance"


def test_page_escapes_message_and_needs_no_remote_assets(tmp_path):
    flag = tmp_path / "maintenance.json"
    write_state(flag, enabled=True, message='<script>alert("x")</script>')
    with override_settings(SCITEX_HUB_MAINTENANCE_FILE=flag):
        content = Client().get("/apps/example/").content.decode()
    assert "&lt;script&gt;" in content
    assert "<script" not in content
    assert 'src="' not in content and 'href="' not in content


def test_atomic_control_state_is_private_and_cli_has_structured_status(tmp_path):
    flag = tmp_path / "operator" / "maintenance.json"
    runner = CliRunner()
    enabled = runner.invoke(
        maintenance, ["--state-file", str(flag), "enable", "--json"]
    )
    assert enabled.exit_code == 0, enabled.output
    assert json.loads(enabled.stdout)["enabled"] is True
    assert os.stat(flag).st_mode & 0o777 == 0o600
    assert not list(flag.parent.glob(".maintenance-*"))
    assert (
        runner.invoke(
            maintenance, ["--state-file", str(flag), "disable", "--json"]
        ).exit_code
        == 0
    )
    status = runner.invoke(maintenance, ["--state-file", str(flag), "status", "--json"])
    assert json.loads(status.stdout)["enabled"] is False
    flag.write_text("broken")
    bad = runner.invoke(maintenance, ["--state-file", str(flag), "status", "--json"])
    assert bad.exit_code != 0
    assert json.loads(bad.stdout)["valid"] is False


def test_human_status_honors_threshold_while_json_remains_parseable(tmp_path, monkeypatch):
    import logging

    import scitex_logging

    monkeypatch.setattr(scitex_logging, "get_level", lambda: logging.ERROR)
    runner = CliRunner()
    args = ["--state-file", str(tmp_path / "missing.json"), "status"]
    human = runner.invoke(maintenance, args)
    assert human.exit_code == 0 and human.stdout == ""
    machine = runner.invoke(maintenance, [*args, "--json"])
    assert machine.exit_code == 0
    assert json.loads(machine.stdout)["enabled"] is False


def test_maximum_multilingual_message_round_trips_within_state_limit(tmp_path):
    flag = tmp_path / "maintenance.json"
    message = "🔧" * 512
    write_state(flag, enabled=True, message=message)
    assert flag.stat().st_size <= 4096
    assert read_state(flag).message == message
    assert read_state(flag).valid


def test_health_check_delegates_while_other_requests_are_closed(tmp_path):
    flag = tmp_path / "maintenance.json"
    write_state(flag, enabled=True)
    downstream = Mock(return_value=HttpResponse("existing-health-check"))
    with override_settings(SCITEX_HUB_MAINTENANCE_FILE=flag):
        response = MaintenanceMiddleware(downstream)(RequestFactory().get("/healthz/"))
    assert response.content == b"existing-health-check"
    downstream.assert_called_once()


def test_fifo_and_symlink_flags_fail_closed_without_blocking(tmp_path):
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from scitex_hub.maintenance import read_state; s=read_state(sys.argv[1]); assert s.enabled and not s.valid",
            str(fifo),
        ],
        timeout=3,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    target = tmp_path / "state.json"
    write_state(target, enabled=False)
    link = tmp_path / "link.json"
    link.symlink_to(target)
    assert read_state(link).enabled and not read_state(link).valid


def test_liveness_does_not_even_open_the_operator_state(tmp_path, monkeypatch):
    from apps.infra.public_app import middleware_maintenance as gate

    def fail_read():
        raise AssertionError("liveness must not read operator storage")

    monkeypatch.setattr(gate, "current_state", fail_read)
    assert Client().get("/livez/").status_code == 200
    sent = []

    async def send(message):
        sent.append(message)

    asyncio.run(MaintenanceASGI(None)({"type": "http", "path": "/livez/"}, None, send))
    assert sent[0]["status"] == 200


def test_ssl_redirect_keeps_probe_and_gate_consistent_with_asgi(tmp_path):
    import importlib.util

    source = (
        Path(__file__).resolve().parents[2] / "config/settings/settings_middleware.py"
    )
    spec = importlib.util.spec_from_file_location("isolated_middleware_order", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    selected = module.MIDDLEWARE[:2]
    assert set(selected) == {
        "apps.infra.public_app.middleware_maintenance.MaintenanceMiddleware",
        "django.middleware.security.SecurityMiddleware",
    }
    flag = tmp_path / "maintenance.json"
    with override_settings(
        MIDDLEWARE=selected, SECURE_SSL_REDIRECT=True, SCITEX_HUB_MAINTENANCE_FILE=flag
    ):
        assert Client().get("/livez/").status_code == 200
        assert Client().get("/apps/example/").status_code == 301
        write_state(flag, enabled=True)
        assert Client().get("/apps/example/").status_code == 503
        assert Client().get("/maintenance-ready/").status_code == 503


def test_failed_state_replacement_preserves_old_flag_and_cleans_temporary(
    tmp_path, monkeypatch
):
    flag = tmp_path / "maintenance.json"
    write_state(flag, enabled=True)
    old = flag.read_bytes()

    def fail_replace(*args):
        raise OSError("replacement failed")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError):
        write_state(flag, enabled=False)
    assert flag.read_bytes() == old
    assert not list(flag.parent.glob(".maintenance-*"))


@pytest.mark.parametrize(
    "protocol,path,headers",
    [
        ("http", "/mcp", []),
        ("http", "/api/save/", []),
        ("http", "/apps/example/", []),
        ("websocket", "/ws/example/", []),
    ],
)
def test_asgi_blocks_before_mcp_auth_and_websocket_handlers(
    tmp_path, protocol, path, headers
):
    flag = tmp_path / "maintenance.json"
    write_state(flag, enabled=True)
    messages = []

    async def downstream(*args):
        raise AssertionError("protocol handler must not execute")

    async def receive():
        return {
            "type": "websocket.connect" if protocol == "websocket" else "http.request"
        }

    async def send(message):
        messages.append(message)

    with override_settings(SCITEX_HUB_MAINTENANCE_FILE=flag):
        asyncio.run(
            MaintenanceASGI(downstream)(
                {"type": protocol, "path": path, "headers": headers, "method": "GET"},
                receive,
                send,
            )
        )
    if protocol == "websocket":
        assert messages == [
            {
                "type": "websocket.close",
                "code": 1013,
                "reason": "Service temporarily unavailable",
            }
        ]
    else:
        assert messages[0]["status"] == 503
        assert dict(messages[0]["headers"])[b"retry-after"] == b"300"


def test_disabled_asgi_preserves_protocol_and_lifespan(tmp_path):
    received = []

    async def downstream(scope, receive, send):
        received.append(scope["type"])

    with override_settings(SCITEX_HUB_MAINTENANCE_FILE=tmp_path / "absent"):
        for protocol in ["http", "websocket", "lifespan"]:
            asyncio.run(
                MaintenanceASGI(downstream)(
                    {"type": protocol, "path": "/example/"}, None, None
                )
            )
    assert received == ["http", "websocket", "lifespan"]
