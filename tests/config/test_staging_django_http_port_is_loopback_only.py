"""Staging Django's HTTP port is published on loopback only.

Measured 2026-11-27: ``docker-compose.staging.yml`` published Django's port
8000 as ``0.0.0.0:31294``, so staging (with every route prod has, including
unauthenticated ones being fixed in #1244) was reachable from anything that
reaches the host. Host-side callers, including the host-network cloudflared,
still reach ``127.0.0.1:31294``.
"""

from pathlib import Path

import yaml
from tests.config._compose_helpers import published_on_public_interface

ROOT = Path(__file__).resolve().parents[2]
STAGING = ROOT / "deployment/docker/docker-compose.staging.yml"


def _django_http_ports():
    ports = yaml.safe_load(STAGING.read_text())["services"]["django"]["ports"]
    return [p for p in ports if str(p).rstrip('"').endswith(":8000")]


def test_staging_django_publishes_its_http_port():
    # Arrange
    ports = _django_http_ports()
    # Act
    count = len(ports)
    # Assert
    assert count == 1


def test_staging_django_http_port_is_not_on_a_public_interface():
    # Arrange
    ports = _django_http_ports()
    # Act
    public = [p for p in ports if published_on_public_interface(p)]
    # Assert
    assert public == []
