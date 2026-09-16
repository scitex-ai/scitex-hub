"""Keep the declared Cards sibling live-editable in the development stack."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = REPO_ROOT / "deployment/docker/docker_dev/docker-compose.yml"
INSTALLER_PATH = REPO_ROOT / "deployment/docker/docker_dev/install_ecosystem.sh"
MANIFEST_PATH = REPO_ROOT / ".scitex-apps.json"
PYTHON_SERVICES = ("django", "celery_worker", "celery_beat")
CARDS_MOUNT = "../../../../scitex-cards:/scitex-cards:cached"


def test_cards_is_declared_as_a_sibling_app():
    manifest = json.loads(MANIFEST_PATH.read_text())

    cards = next(app for app in manifest["apps"] if app["name"] == "scitex-cards")

    assert cards["source"] == "sibling"
    assert cards["pip_package"] == "scitex-cards"


def test_every_dev_python_service_mounts_the_cards_sibling():
    compose = yaml.safe_load(COMPOSE_PATH.read_text())

    missing = [
        service
        for service in PYTHON_SERVICES
        if CARDS_MOUNT not in compose["services"][service]["volumes"]
    ]

    assert missing == [], f"Cards is not mounted in development services: {missing}"


def test_ecosystem_installer_installs_cards_from_its_mount():
    installer = INSTALLER_PATH.read_text()

    assert 'try_editable_install "/scitex-cards" "scitex-cards"' in installer
