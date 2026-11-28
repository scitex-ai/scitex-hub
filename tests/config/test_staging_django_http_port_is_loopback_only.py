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


# stag.scitex.ai: the prod tunnel reaches staging django over an internal
# network that holds only prod cloudflared and staging django. Both compose
# files declare it, so a recreate of either container keeps the route.
PROD = ROOT / "deployment/docker/docker_prod/docker-compose.yml"
STAGING_SETTINGS = ROOT / "config/settings/settings_staging.py"
INGRESS = "scitex-hub-stag-ingress"


def test_staging_django_joins_the_stag_ingress_network():
    # Arrange
    doc = yaml.safe_load(STAGING.read_text())
    # Act
    joined = (
        INGRESS in doc["services"]["django"]["networks"],
        doc["networks"][INGRESS],
    )
    # Assert
    assert joined == (True, {"external": True})


def test_prod_cloudflared_joins_the_stag_ingress_network():
    # Arrange
    doc = yaml.safe_load(PROD.read_text())
    # Act
    joined = (
        INGRESS in doc["services"]["cloudflared"]["networks"],
        doc["networks"][INGRESS],
    )
    # Assert
    assert joined == (True, {"external": True})


def test_staging_settings_always_allow_the_public_staging_host():
    # Arrange
    text = STAGING_SETTINGS.read_text()
    # Act
    wired = (
        'STAGING_PUBLIC_HOST = "stag.scitex.ai"' in text,
        "ALLOWED_HOSTS.append(STAGING_PUBLIC_HOST)" in text,
        'CSRF_TRUSTED_ORIGINS.append(f"https://{STAGING_PUBLIC_HOST}")' in text,
    )
    # Assert
    assert wired == (True, True, True)
