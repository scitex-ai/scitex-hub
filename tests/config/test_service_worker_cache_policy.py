"""Execute the actual worker and check private-data and stream boundaries."""

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def worker_policy():
    run = subprocess.run(
        ["node", str(Path(__file__).with_name("fixtures") / "worker_cache_policy.cjs"),
         str(ROOT / "static/shared/sw.js")],
        capture_output=True, text=True, timeout=20,
    )
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def test_private_apis_streams_and_unsafe_requests_bypass_worker(worker_policy):
    assert worker_policy["bypassed"] == [
        "api", "event-stream", "media", "post", "external", "authorization",
    ]
    assert worker_policy["bypass_cache_writes"] == 0


def test_navigation_and_private_static_replies_are_never_cached(worker_policy):
    assert worker_policy["private_cache_writes"] == 0
    assert worker_policy["offline_navigation_status"] == 503
    assert worker_policy["offline_navigation_uses_cached_private_reply"] is False


def test_public_static_assets_keep_network_and_offline_behavior(worker_policy):
    assert worker_policy["static_online_body"] == "public-code"
    assert worker_policy["static_offline_body"] == "public-code"
    assert worker_policy["gateway_navigation_status"] == 503


def test_activation_removes_only_the_legacy_private_cache(worker_policy):
    assert worker_policy["deleted_caches"] == ["scitex-v1"]
    assert worker_policy["unrelated_cache_preserved"] is True
    assert worker_policy["clients_claimed"] is True
