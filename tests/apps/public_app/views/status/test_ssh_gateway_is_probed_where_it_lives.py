#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Workspace SSH Gateway must be probed at an address valid from the probing process.

The gateway binds 0.0.0.0:2200 inside the ``django`` container. The check
assumed it always ran there and probed 127.0.0.1. But the public /status/ page
is served from a cache that ``warm_public_status_cache`` refreshes every 60 s
from the CELERY WORKER container, where 127.0.0.1:2200 is nothing — so for a
day (2026-09-05) scitex.ai/status/ announced "Workspace SSH Gateway: Down" and
"Partial System Outage" while the gateway answered its banner inside the
container it lives in. The page reported the worker's blind spot as an outage.

WHAT EACH TEST IS FOR
  configured_host_wins_*        an explicit SCITEX_HUB_SSH_GATEWAY_PROBE_HOST is
                                the answer in and out of Docker (the operator's
                                escape hatch when the service is renamed).
  in_docker_uses_service_name   inside Docker the compose service name, which
                                Docker's DNS resolves from every container on
                                the network — the worker included.
  outside_docker_uses_loopback  the developer's laptop case is unchanged.
  blank_override_is_ignored     an empty variable must not become host "".
  a_down_verdict_names_where_it_probed
                                a "down" that names its vantage point can be
                                checked; the one that did not was believed for
                                a day. Runs the real check against a closed
                                loopback port, no doubles.
"""

from __future__ import annotations

import os
import socket
from collections.abc import Iterator

import pytest

from apps.infra.public_app.views.status.health_checks import (
    SSH_GATEWAY_PROBE_HOST_ENV,
    SSH_GATEWAY_SERVICE_NAME,
    check_ssh_services,
    ssh_gateway_probe_host,
)


def test_configured_host_wins_inside_docker() -> None:
    # Arrange
    env = {SSH_GATEWAY_PROBE_HOST_ENV: "gateway.internal"}
    # Act
    host = ssh_gateway_probe_host(env=env, in_docker=True)
    # Assert
    assert host == "gateway.internal"


def test_configured_host_wins_outside_docker() -> None:
    # Arrange
    env = {SSH_GATEWAY_PROBE_HOST_ENV: "gateway.internal"}
    # Act
    host = ssh_gateway_probe_host(env=env, in_docker=False)
    # Assert
    assert host == "gateway.internal"


def test_in_docker_uses_the_compose_service_name() -> None:
    # Arrange — no override, running in a container (any container).
    env: dict[str, str] = {}
    # Act
    host = ssh_gateway_probe_host(env=env, in_docker=True)
    # Assert
    assert host == SSH_GATEWAY_SERVICE_NAME == "django"


def test_outside_docker_uses_loopback() -> None:
    # Arrange
    env: dict[str, str] = {}
    # Act
    host = ssh_gateway_probe_host(env=env, in_docker=False)
    # Assert
    assert host == "127.0.0.1"


def test_blank_override_is_ignored() -> None:
    # Arrange — an exported-but-empty variable is the common misconfiguration.
    env = {SSH_GATEWAY_PROBE_HOST_ENV: "   "}
    # Act
    host = ssh_gateway_probe_host(env=env, in_docker=True)
    # Assert
    assert host == SSH_GATEWAY_SERVICE_NAME


@pytest.fixture(name="closed_port_verdict")
def _closed_port_verdict() -> Iterator[dict]:
    """Run the REAL check with the probe host pointed at loopback.

    Whether 2200 is open on this machine is not this test's business: it asserts
    the verdict NAMES the host that was probed, which holds for up and down
    alike. The variable is set in the real environment and removed on teardown;
    nothing is doubled.
    """
    previous = os.environ.get(SSH_GATEWAY_PROBE_HOST_ENV)
    os.environ[SSH_GATEWAY_PROBE_HOST_ENV] = "127.0.0.1"
    try:
        status_data: dict = {"ssh_services": []}
        check_ssh_services(status_data)
        yield next(
            s
            for s in status_data["ssh_services"]
            if s["name"] == "Workspace SSH Gateway"
        )
    finally:
        if previous is None:
            os.environ.pop(SSH_GATEWAY_PROBE_HOST_ENV, None)
        else:
            os.environ[SSH_GATEWAY_PROBE_HOST_ENV] = previous


def test_the_verdict_records_the_probed_host(closed_port_verdict: dict) -> None:
    # Arrange
    entry = closed_port_verdict
    # Act
    probed = entry.get("probed_host")
    # Assert
    assert probed == "127.0.0.1", entry


def test_a_down_verdict_names_where_it_probed(closed_port_verdict: dict) -> None:
    # Arrange — whichever arm this machine lands in: a running gateway carries
    # no error, and a down one must name the vantage point in its error.
    entry = closed_port_verdict
    # Act
    error = entry["error"]
    # Assert
    assert error is None or error.endswith("(probed 127.0.0.1:2200)"), entry


def test_the_control_a_closed_port_is_reported_down() -> None:
    # Arrange — bind then close an ephemeral port so it is provably closed,
    # and prove the underlying banner probe returns the "down" arm for it.
    from apps.infra.public_app.views.status.health_checks import _check_ssh_banner

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    # Act
    is_functional, _error = _check_ssh_banner("127.0.0.1", port, timeout=1.0)
    # Assert
    assert is_functional is False
