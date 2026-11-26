#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The prod ``cloudflared`` service reads its tunnel token from a file secret.

WHY. The token has leaked twice through where it was stored, not through who
held it: from argv via ``ps aux`` (2026-08-03, see
``test_compose_keeps_credentials_out_of_argv.py``) and from the environment via
``cloudflared tunnel run --help``, which prints every flag's default -- and the
default of ``--token`` is ``$TUNNEL_TOKEN`` (2026-11-26). A file secret avoids
both: compose bind-mounts it at ``/run/secrets/<name>`` and cloudflared reads it
through ``TUNNEL_TOKEN_FILE``.

``--token`` (``TUNNEL_TOKEN``) takes precedence over ``--token-file``, so a
``TUNNEL_TOKEN`` anywhere in the service -- directly or through ``env_file`` --
silently brings the environment path back. Hence no ``env_file`` either.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from tests.config._compose_helpers import environment

REPO_ROOT = Path(__file__).resolve().parents[2]
PROD_COMPOSE = REPO_ROOT / "deployment/docker/docker_prod/docker-compose.yml"
SECRET_NAME = "cloudflared_tunnel_token"


def _compose():
    return yaml.safe_load(PROD_COMPOSE.read_text())


def test_cloudflared_mounts_the_token_secret():
    # Arrange
    service = _compose()["services"]["cloudflared"]
    # Act
    secrets = service.get("secrets")
    # Assert
    assert secrets == [SECRET_NAME]


def test_cloudflared_environment_only_points_at_the_token_file():
    # Arrange
    service = _compose()["services"]["cloudflared"]
    # Act
    env = environment(service)
    # Assert
    assert env == {"TUNNEL_TOKEN_FILE": f"/run/secrets/{SECRET_NAME}"}


def test_cloudflared_takes_no_env_file():
    # Arrange: env_file injects every hub secret and would re-introduce
    # TUNNEL_TOKEN (which beats --token-file) the day .env.prod gains it.
    service = _compose()["services"]["cloudflared"]
    # Act
    has_env_file = "env_file" in service
    # Assert
    assert has_env_file is False


def test_cloudflared_command_carries_no_token_flag():
    # Arrange
    service = _compose()["services"]["cloudflared"]
    # Act
    command = str(service.get("command", ""))
    # Assert
    assert "--token" not in command


def test_token_secret_defaults_to_the_gitignored_envs_secrets_dir():
    # Arrange
    compose = _compose()
    # Act
    source = compose["secrets"][SECRET_NAME]["file"]
    # Assert
    assert source.endswith(":-../envs/secrets/cloudflared-tunnel-token}")


def test_cloudflared_image_is_pinned():
    # Arrange
    service = _compose()["services"]["cloudflared"]
    # Act
    tag = service["image"].rpartition(":")[2]
    # Assert
    assert tag not in ("", "latest")


def test_cloudflared_log_is_capped():
    # Arrange
    service = _compose()["services"]["cloudflared"]
    # Act
    logging = service.get("logging")
    # Assert
    assert logging == {
        "driver": "json-file",
        "options": {"max-size": "100m", "max-file": "5"},
    }
