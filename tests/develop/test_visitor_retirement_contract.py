"""Deployment must not revive the retired visitor/guest product concept."""

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
ENTRYPOINT = REPO / "deployment/docker/common/scripts/entrypoint-prod.sh"
REBUILD = REPO / "scripts/deploy/rebuild.sh"
PROD_COMPOSE = REPO / "deployment/docker/docker_prod/docker-compose.yml"

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
