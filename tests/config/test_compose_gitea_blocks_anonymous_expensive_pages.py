#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prod gitea refuses anonymous requests for its expensive pages.

WHY. On 2026-11-26 a distributed crawler (82,117 IPs in one hour, robots.txt
ignored) sent ~57 req/s to git.scitex.ai, 74 % of them ``/compare/`` at a
median 19 s each; gitea answered 126,626 of them with 500 and logged 49,619
"too many clients" errors from the postgres it shares with the hub. The tunnel
sends git.scitex.ai straight to gitea:3000, so nginx's bot rules never apply.
Gitea's own ``REQUIRE_SIGNIN_VIEW=expensive`` redirects anonymous requests for
those pages to the login page before any git work is done.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from tests.config._compose_helpers import environment

REPO_ROOT = Path(__file__).resolve().parents[2]
PROD_COMPOSE = REPO_ROOT / "deployment/docker/docker_prod/docker-compose.yml"
ROBOTS = REPO_ROOT / "deployment/docker/common/gitea/public/robots.txt"


def _gitea():
    return yaml.safe_load(PROD_COMPOSE.read_text())["services"]["gitea"]


def test_gitea_defaults_to_blocking_anonymous_expensive_pages():
    # Arrange
    env = environment(_gitea())
    # Act
    value = env.get("GITEA__service__REQUIRE_SIGNIN_VIEW", "")
    # Assert
    assert value.endswith(":-expensive}")


def test_gitea_does_not_log_every_request():
    # Arrange
    env = environment(_gitea())
    # Act
    value = env.get("GITEA__log__LEVEL", "")
    # Assert
    assert value.endswith(":-Warn}")


def test_gitea_log_is_capped():
    # Arrange
    service = _gitea()
    # Act
    logging = service.get("logging")
    # Assert
    assert logging == {
        "driver": "json-file",
        "options": {"max-size": "100m", "max-file": "5"},
    }


def test_gitea_serves_the_tracked_robots_txt():
    # Arrange
    volumes = _gitea()["volumes"]
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
