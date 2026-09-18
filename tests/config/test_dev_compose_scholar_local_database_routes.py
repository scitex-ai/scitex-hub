"""Development Scholar must read the NAS-03 local corpora, not itself."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
COMPOSE = REPO / "deployment/docker/docker_dev/docker-compose.yml"
PYTHON_SERVICES = ("django", "celery_worker", "celery_beat")
EXPECTED = {
    "SCITEX_SCHOLAR_CROSSREF_MODE": "http",
    "CROSSREF_LOCAL_MODE": "http",
    "CROSSREF_LOCAL_API_URL": (
        "${SCITEX_HUB_CROSSREF_API_URL_DEV:-http://scitex-primary:31291}"
    ),
    "OPENALEX_LOCAL_MODE": "http",
    "OPENALEX_LOCAL_API_URL": (
        "${SCITEX_HUB_OPENALEX_API_URL_DEV:-http://scitex-primary:31292}"
    ),
}


def _environment(service: dict) -> dict[str, str]:
    values = {}
    for entry in service.get("environment", []):
        key, value = entry.split("=", 1)
        values[key] = value
    return values


def test_dev_python_services_route_scholar_corpora_to_nas03():
    compose = yaml.safe_load(COMPOSE.read_text())

    for service_name in PYTHON_SERVICES:
        environment = _environment(compose["services"][service_name])
        assert {key: environment.get(key) for key in EXPECTED} == EXPECTED


def test_dev_compose_does_not_point_scholar_at_compute03_itself():
    compose_text = COMPOSE.read_text()

    assert "host.docker.internal:31291" not in compose_text
    assert "host.docker.internal:31292" not in compose_text


def test_source_mounted_python_services_do_not_write_bytecode():
    compose = yaml.safe_load(COMPOSE.read_text())

    for service_name in PYTHON_SERVICES:
        environment = _environment(compose["services"][service_name])
        assert environment.get("PYTHONDONTWRITEBYTECODE") == "1"
