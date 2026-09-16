"""Deployment must not revive the retired visitor/guest product concept."""

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
ENTRYPOINT = REPO / "deployment/docker/common/scripts/entrypoint-prod.sh"
REBUILD = REPO / "scripts/deploy/rebuild.sh"
PROD_COMPOSE = REPO / "deployment/docker/docker_prod/docker-compose.yml"
ENTRYPOINTS = (
    REPO / "deployment/docker/common/scripts/entrypoint-dev.sh",
    REPO / "deployment/docker/common/scripts/entrypoint-prod.sh",
    REPO / "deployment/docker/docker_dev/entrypoint.sh",
    REPO / "deployment/docker/docker_prod/entrypoint.sh",
)
COMPOSE_FILES = (
    REPO / "deployment/docker/docker-compose.override.yml",
    REPO / "deployment/docker/docker-compose.prod.yml",
    REPO / "deployment/docker/docker-compose.staging.yml",
    REPO / "deployment/docker/docker_dev/docker-compose.yml",
    PROD_COMPOSE,
)

RETIRED_RUNTIME_COMMANDS = (
    "create_visitor_pool",
    "reconcile_visitor_slots",
    "visitor_pool_ready",
    "assert_visitor_pool_ready",
)


def test_production_boot_does_not_create_or_reconcile_visitor_slots():
    # Arrange
    entrypoint = ENTRYPOINT.read_text()
    # Act
    found = [command for command in RETIRED_RUNTIME_COMMANDS if command in entrypoint]
    # Assert
    assert found == []


def test_no_shipped_entrypoint_creates_or_reconciles_visitor_slots():
    offenders = []
    for path in ENTRYPOINTS:
        live = "\n".join(
            line
            for line in path.read_text().splitlines()
            if not line.lstrip().startswith("#")
        )
        for command in RETIRED_RUNTIME_COMMANDS:
            if command in live:
                offenders.append(f"{path.relative_to(REPO)}:{command}")

    assert offenders == []


def test_protected_deploy_has_no_visitor_pool_postcondition_or_repair():
    # Arrange
    rebuild = REBUILD.read_text()
    # Act
    found = [command for command in RETIRED_RUNTIME_COMMANDS if command in rebuild]
    # Assert
    assert found == []


def test_production_compose_has_no_visitor_only_worker():
    # Arrange
    services = yaml.safe_load(PROD_COMPOSE.read_text())["services"]
    # Act
    visitor_services = [
        name
        for name, service in services.items()
        if ("visitor" in name or name.endswith("_vis"))
        and "retired-visitor" not in service.get("profiles", [])
    ]
    # Assert
    assert visitor_services == []


def test_no_compose_service_consumes_the_retired_visitor_queue():
    offenders = []
    for path in COMPOSE_FILES:
        services = yaml.safe_load(path.read_text())["services"]
        for name, service in services.items():
            if "vis_queue" in str(service) or name.endswith("_vis"):
                offenders.append(f"{path.relative_to(REPO)}:{name}")

    assert offenders == []
