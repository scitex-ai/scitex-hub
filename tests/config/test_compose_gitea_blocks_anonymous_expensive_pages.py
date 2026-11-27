#!/usr/bin/env python3
"""Prod gitea asks anonymous visitors to sign in for its heavy pages only.

WHY. On 2026-11-26 a distributed crawler (82,117 IPs in one hour, robots.txt
ignored) sent ~57 req/s to git.scitex.ai, 74 % of them ``/compare/`` at a
median 19 s each; gitea answered 126,626 of them with 500 and logged 49,619
"too many clients" errors from the postgres it shares with the hub.

The author's decision ("sign-in for heavy pages only"): anonymous visitors keep
repository pages; compare, blame, commit history and archives need sign-in.
Gitea 1.25.2's ``REQUIRE_SIGNIN_VIEW=expensive`` does not fit: its route list
has no ``/compare/`` and it also closes src, raw, issues, pulls and wiki. So the
rule lives in ``gitea_front``, an nginx in gitea's network namespace. These
tests pin that wiring; the policy regex is exercised against real gitea paths.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from tests.config._compose_helpers import environment

REPO_ROOT = Path(__file__).resolve().parents[2]
PROD_COMPOSE = REPO_ROOT / "deployment/docker/docker_prod/docker-compose.yml"
FRONT_CONF = REPO_ROOT / "deployment/docker/common/gitea/front/nginx.conf"
ROBOTS = REPO_ROOT / "deployment/docker/common/gitea/public/robots.txt"


def _services():
    return yaml.safe_load(PROD_COMPOSE.read_text())["services"]


def _heavy_page_pattern():
    """The regex of the one nginx location that demands sign-in."""
    for line in FRONT_CONF.read_text().splitlines():
        match = re.match(r"\s*location ~ (\S+) \{", line)
        if match and "compare" in match.group(1):
            return re.compile(match.group(1))
    raise AssertionError("no sign-in location for compare in gitea_front's nginx.conf")


def test_gitea_does_not_use_signin_view_expensive():
    # Arrange
    env = environment(_services()["gitea"])
    # Act
    value = env.get("GITEA__service__REQUIRE_SIGNIN_VIEW")
    # Assert
    assert value == "false"


def test_gitea_listens_only_inside_its_namespace():
    # Arrange
    env = environment(_services()["gitea"])
    # Act
    listen = (env.get("GITEA__server__HTTP_ADDR"), env.get("GITEA__server__HTTP_PORT"))
    # Assert
    assert listen == ("127.0.0.1", "3001")


def test_front_answers_on_giteas_published_port():
    # Arrange
    front = _services()["gitea_front"]
    # Act
    wiring = (front["network_mode"], front["volumes"])
    # Assert
    assert wiring == (
        "service:gitea",
        ["../common/gitea/front/nginx.conf:/etc/nginx/nginx.conf:ro"],
    )


def test_front_listens_on_3000_and_proxies_to_3001():
    # Arrange
    text = FRONT_CONF.read_text()
    # Act
    upstreams = set(re.findall(r"proxy_pass (http://[^;/]+)", text))
    # Assert
    assert "listen 3000" in text and upstreams == {"http://127.0.0.1:3001"}


def test_front_is_restarted_when_unhealthy():
    # Arrange
    front = _services()["gitea_front"]
    # Act
    labels = front.get("labels", [])
    # Assert
    assert "autoheal=true" in labels and "healthcheck" in front


@pytest.mark.parametrize(
    "path",
    [
        "/u/r/compare/main...develop",
        "/u/r/compare",
        "/u/r/blame/branch/main/README.md",
        "/u/r/commits/branch/main",
        "/u/r/commit/0123abcd",
        "/u/r/graph",
        "/u/r/archive/main.zip",
        "/u/r/archive/v1.0.tar.gz",
    ],
)
def test_heavy_pages_need_sign_in(path):
    # Arrange
    pattern = _heavy_page_pattern()
    # Act
    matched = pattern.search(path)
    # Assert
    assert matched, path


@pytest.mark.parametrize(
    "path",
    [
        "/u/r",
        "/u/r/src/branch/main/README.md",
        "/u/r/src/commit/0123abcd/README.md",
        "/u/r/raw/branch/main/README.md",
        "/u/r/issues",
        "/u/r/pulls/1",
        "/u/r/releases",
        "/u/r/wiki",
        "/u/r.git/info/refs",
        "/api/v1/repos/u/r/compare/main...develop",
        "/user/login",
        "/explore/repos",
    ],
)
def test_repository_pages_stay_public(path):
    # Arrange
    pattern = _heavy_page_pattern()
    # Act
    matched = pattern.search(path)
    # Assert
    assert not matched, path


def test_gitea_overload_protection_and_db_pool_cap():
    # Arrange
    env = environment(_services()["gitea"])
    # Act
    settings = (
        env.get("GITEA__qos__ENABLED"),
        int(env.get("GITEA__database__MAX_OPEN_CONNS", "0")),
    )
    # Assert
    assert settings[0] == "true" and 0 < settings[1] <= 50


def test_gitea_does_not_log_every_request():
    # Arrange
    env = environment(_services()["gitea"])
    # Act
    value = env.get("GITEA__log__LEVEL", "")
    # Assert
    assert value.endswith(":-Warn}")


@pytest.mark.parametrize("name", ["gitea", "gitea_front"])
def test_gitea_logs_are_capped(name):
    # Arrange
    service = _services()[name]
    # Act
    logging = service.get("logging", {})
    # Assert
    assert logging.get("driver") == "json-file" and set(logging.get("options", {})) == {
        "max-size",
        "max-file",
    }


def test_gitea_serves_the_tracked_robots_txt():
    # Arrange
    volumes = _services()["gitea"]["volumes"]
    # Act
    mounted = "../common/gitea/public/robots.txt:/data/gitea/public/robots.txt:ro"
    # Assert
    assert mounted in volumes


def test_tracked_robots_txt_disallows_compare():
    # Arrange
    text = ROBOTS.read_text()
    # Act
    lines = text.splitlines()
    # Assert
    assert "Disallow: /*/*/compare/" in lines


def test_front_logs_only_5xx_and_a_one_percent_sample():
    # Arrange
    text = FRONT_CONF.read_text()
    # Act
    wiring = (
        "1%  1;" in text,
        '"00"    0;' in text,
        "access_log /dev/stdout front if=$front_log;" in text,
    )
    # Assert
    assert wiring == (True, True, True)
