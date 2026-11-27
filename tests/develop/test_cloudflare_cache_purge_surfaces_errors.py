"""The Cloudflare cache purge must report its failures, never hide them.

Regression guard (2026-11-27). ``cloudflare_cache_purge.sh`` looked for
``deployment/docker/docker_prod/.env``, which does not exist on prod (the env
file is ``deployment/docker/envs/.env.prod``), and ``rebuild.sh`` ran it as
``... all 2>/dev/null || echo skipped``. Every prod release therefore printed
"Cache purge skipped" and nothing was ever purged.

These tests run the real script against a local HTTP endpoint that speaks the
Cloudflare response shape, so the exit-status contract (0 ok / 1 failed /
2 not configured) and the stderr reporting are exercised end to end.
"""

import http.server
import json
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PURGE_SH = (
    REPO_ROOT
    / "deployment"
    / "docker"
    / "common"
    / "scripts"
    / "cloudflare_cache_purge.sh"
)
REBUILD_SH = REPO_ROOT / "scripts" / "deploy" / "rebuild.sh"

GOOD_ZONE = "0123456789abcdef0123456789abcdef"
BAD_ZONE = "not-a-zone-id"
TOKEN = "test-token-not-a-secret-0000000000"
OK_REPLY = (200, {"success": True, "errors": [], "result": {"id": "x"}})
ROUTE_ERROR_REPLY = (
    400,
    {"success": False, "errors": [{"code": 7003, "message": "Could not route"}]},
)

pytestmark = pytest.mark.skipif(
    shutil.which("curl") is None or shutil.which("jq") is None,
    reason="curl and jq are required by the purge script",
)


class _Recorder(http.server.BaseHTTPRequestHandler):
    """Answers purge_cache with the reply configured on the server."""

    def do_POST(self):  # noqa: N802 (http.server API)
        length = int(self.headers.get("Content-Length", 0))
        self.server.requests.append(
            {
                "path": self.path,
                "auth": self.headers.get("Authorization"),
                "body": json.loads(self.rfile.read(length) or b"{}"),
            }
        )
        status, payload = self.server.reply
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def _serve(reply):
    server = http.server.HTTPServer(("127.0.0.1", 0), _Recorder)
    server.requests = []
    server.reply = reply
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _write_env(tmp_path, zone=GOOD_ZONE, token=TOKEN, quote="", newline="\n"):
    lines = ["SCITEX_HUB_SOMETHING=1"]
    if zone is not None:
        lines.append(f"CLOUDFLARE_ZONE_ID={quote}{zone}{quote}")
    if token is not None:
        lines.append(f"CLOUDFLARE_API_TOKEN={quote}{token}{quote}")
    env_file = tmp_path / ".env.prod"
    env_file.write_bytes((newline.join(lines) + newline).encode())
    return env_file


def _run(env_file, server, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLOUDFLARE_")}
    env["CLOUDFLARE_ENV_FILE"] = str(env_file)
    env["CLOUDFLARE_API_BASE"] = f"http://127.0.0.1:{server.server_port}"
    proc = subprocess.run(
        ["bash", str(PURGE_SH), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    server.shutdown()
    return proc, server.requests


@pytest.fixture
def quoted_crlf_url_purge(tmp_path):
    """One URL purge from a hand-edited env file (quoted values, CRLF)."""
    env_file = _write_env(tmp_path, quote='"', newline="\r\n")
    return _run(env_file, _serve(OK_REPLY), "urls", "https://scitex.ai/")


@pytest.fixture
def route_error_purge(tmp_path):
    """A purge that Cloudflare rejects with 7003."""
    return _run(_write_env(tmp_path), _serve(ROUTE_ERROR_REPLY), "all")


@pytest.fixture
def unconfigured_purge(tmp_path):
    return _run(_write_env(tmp_path, zone=None, token=None), _serve(OK_REPLY), "all")


@pytest.fixture
def malformed_zone_purge(tmp_path):
    return _run(_write_env(tmp_path, zone=BAD_ZONE), _serve(OK_REPLY), "all")


def test_url_purge_from_env_file_exits_0(quoted_crlf_url_purge):
    # Arrange: the fixture/file under test
    # Act
    proc, _ = quoted_crlf_url_purge
    # Assert
    assert proc.returncode == 0, proc.stderr


def test_url_purge_sends_the_expected_request(quoted_crlf_url_purge):
    # Arrange
    expected = {
        "path": f"/zones/{GOOD_ZONE}/purge_cache",
        "auth": f"Bearer {TOKEN}",
        "body": {"files": ["https://scitex.ai/"]},
    }
    # Act
    _, requests = quoted_crlf_url_purge
    # Assert
    assert requests == [expected]


def test_cloudflare_error_exits_1(route_error_purge):
    # Arrange: the fixture/file under test
    # Act
    proc, _ = route_error_purge
    # Assert
    assert proc.returncode == 1


def test_cloudflare_error_code_is_printed_on_stderr(route_error_purge):
    # Arrange: the fixture/file under test
    # Act
    proc, _ = route_error_purge
    # Assert
    assert "7003" in proc.stderr


def test_cloudflare_error_output_does_not_contain_the_token(route_error_purge):
    # Arrange: the fixture/file under test
    # Act
    proc, _ = route_error_purge
    # Assert
    assert TOKEN not in proc.stdout + proc.stderr


def test_missing_credentials_exit_2(unconfigured_purge):
    # Arrange: the fixture/file under test
    # Act
    proc, _ = unconfigured_purge
    # Assert
    assert proc.returncode == 2


def test_missing_credentials_make_no_api_call(unconfigured_purge):
    # Arrange: the fixture/file under test
    # Act
    _, requests = unconfigured_purge
    # Assert
    assert requests == []


def test_malformed_zone_id_exits_1(malformed_zone_purge):
    # Arrange: the fixture/file under test
    # Act
    proc, _ = malformed_zone_purge
    # Assert
    assert proc.returncode == 1


def test_malformed_zone_id_is_named_but_not_printed(malformed_zone_purge):
    # Arrange
    proc, _ = malformed_zone_purge
    assert (
        # Act
        "CLOUDFLARE_ZONE_ID is malformed" in proc.stderr and BAD_ZONE not in proc.stderr
        # Assert
    )


def test_malformed_zone_id_makes_no_api_call(malformed_zone_purge):
    # Arrange: the fixture/file under test
    # Act
    _, requests = malformed_zone_purge
    # Assert
    assert requests == []


def test_token_never_appears_in_curl_argv():
    # Arrange: the fixture/file under test
    # Act
    argv_headers = re.findall(r'-H\s+"Authorization:[^"]*"', PURGE_SH.read_text())
    # Assert
    assert argv_headers == [], "pass the token via `curl -K -`, not -H in argv"


def test_rebuild_does_not_discard_purge_stderr():
    # Arrange
    purge_calls = [
        ln
        for ln in REBUILD_SH.read_text().splitlines()
        if '"$CACHE_PURGE_SCRIPT" all' in ln
        # Act
    ]
    # Assert
    assert purge_calls and all("2>/dev/null" not in ln for ln in purge_calls)


def test_rebuild_points_the_purge_at_the_compose_env_file():
    # Arrange: the fixture/file under test
    # Act
    expected = 'CLOUDFLARE_ENV_FILE="$PROJECT_ROOT/deployment/docker/envs/.env.${ENV}"'
    # Assert
    assert expected in REBUILD_SH.read_text()
