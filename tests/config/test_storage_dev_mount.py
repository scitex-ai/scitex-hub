"""Keep the declared Storage sibling live-editable in the development stack."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = REPO_ROOT / "deployment/docker/docker_dev/docker-compose.yml"
INSTALLER_PATH = REPO_ROOT / "deployment/docker/docker_dev/install_ecosystem.sh"
MANIFEST_PATH = REPO_ROOT / ".scitex-apps.json"
PYTHON_SERVICES = ("django", "celery_worker", "celery_beat")
STORAGE_MOUNT = "../../../../scitex-storage:/scitex-storage:cached"


def test_storage_is_declared_as_a_sibling_app():
    manifest = json.loads(MANIFEST_PATH.read_text())

    storage = next(app for app in manifest["apps"] if app["name"] == "scitex-storage")

    assert storage["source"] == "sibling"
    assert storage["pip_package"] == "scitex-storage"


def test_every_dev_python_service_mounts_the_storage_sibling():
    compose = yaml.safe_load(COMPOSE_PATH.read_text())

    missing = [
        service
        for service in PYTHON_SERVICES
        if STORAGE_MOUNT not in compose["services"][service]["volumes"]
    ]

    assert missing == [], f"Storage is not mounted in development services: {missing}"


def test_ecosystem_installer_installs_storage_from_its_mount():
    installer = INSTALLER_PATH.read_text()

    assert 'try_editable_install "/scitex-storage" "scitex-storage"' in installer
