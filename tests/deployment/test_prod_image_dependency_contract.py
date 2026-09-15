#!/usr/bin/env python3
"""Production services must preserve the dependency graph baked into the image."""

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
COMPOSE = REPO / "deployment/docker/docker_prod/docker-compose.yml"
INSTALLER = REPO / "scripts/apps/install_apps.sh"
DOCKERFILE = REPO / "deployment/docker/docker_prod/Dockerfile.prod"
VERIFIER = REPO / "scripts/deploy/verify_image_dependency_contract.py"
IMAGE_SERVICES = ("django", "celery_worker", "celery_worker_vis", "celery_beat")


def _compose():
    return yaml.safe_load(COMPOSE.read_text())


def _environment(service):
    values = _compose()["services"][service].get("environment", [])
    return dict(item.split("=", 1) for item in values)


def test_every_hub_python_service_forbids_runtime_editable_overrides():
    assert {
        service: _environment(service).get("SCITEX_APPS_PYTHON_MODE")
        for service in IMAGE_SERVICES
    } == {service: "image-only" for service in IMAGE_SERVICES}


def test_image_only_mode_skips_editable_installs():
    text = INSTALLER.read_text()
    assert 'SCITEX_APPS_PYTHON_MODE' in text
    assert '"$PYTHON_MODE" == "image-only"' in text


def test_actual_runtime_image_runs_relationship_verifier_after_all_installs():
    text = DOCKERFILE.read_text()
    verifier_run = "RUN python scripts/deploy/verify_image_dependency_contract.py"
    assert verifier_run in text
    assert text.index(verifier_run) > text.index('"crossref-local" &&')


def test_verifier_exists_and_cards_floor_is_release_target():
    assert VERIFIER.is_file()
    assert '"scitex-cards>=0.53.1"' in (REPO / "pyproject.toml").read_text()
