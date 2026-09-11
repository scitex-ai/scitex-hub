"""Development terminals bind one exact host artifact at a neutral alias."""

from pathlib import Path

import yaml

REPO = Path(__file__).parents[2]
COMPOSE = REPO / "deployment/docker/docker_dev/docker-compose.yml"


def test_django_terminal_container_bind_is_exact_and_fail_closed():
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    django = compose["services"]["django"]
    mount = next(
        volume
        for volume in django["volumes"]
        if isinstance(volume, dict)
        and volume.get("target") == "/app/singularity/current"
    )

    assert mount == {
        "type": "bind",
        "source": "${SCITEX_HUB_SLURM_CONTAINER_PATH:-/nonexistent/scitex-hub-terminal-sandbox}",
        "target": "/app/singularity/current",
        "read_only": True,
        "bind": {"create_host_path": False},
    }


def test_django_terminal_config_uses_the_neutral_mount_alias():
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    environment = compose["services"]["django"]["environment"]

    assert "SCITEX_HUB_CONTAINER_PATH_IN_DJANGO=/app/singularity/current" in environment


def test_django_and_mount_share_the_same_host_source_variable():
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    environment = compose["services"]["django"]["environment"]

    assert (
        "SCITEX_HUB_SLURM_CONTAINER_PATH=${SCITEX_HUB_SLURM_CONTAINER_PATH:-"
        "/nonexistent/scitex-hub-terminal-sandbox}" in environment
    )
