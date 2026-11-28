"""Prod nginx admits the SSH-over-WebSocket bridge only for Hub credentials.

``/ws/ssh/`` forwards raw SSH to the public gateway. The gateway requires a
registered key, and the bridge additionally requires a signed-in Hub session
or API key, checked by Django through ``auth_request``. This pins that every
``/ws/ssh/`` location carries the gate and that the auth location is internal.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NGINX = ROOT / "deployment/docker/common/nginx/nginx_prod.conf"


def _location_body(text: str, header: str) -> list[str]:
    bodies = []
    for match in re.finditer(re.escape(header) + r"\s*\{", text):
        depth, i = 1, match.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        bodies.append(text[match.end() : i - 1])
    return bodies


def test_ws_ssh_location_exists():
    # Arrange
    text = NGINX.read_text()
    # Act
    bodies = _location_body(text, "location /ws/ssh/")
    # Assert
    assert bodies


def test_every_ws_ssh_location_requires_hub_auth():
    # Arrange
    text = NGINX.read_text()
    # Act
    ungated = [
        b
        for b in _location_body(text, "location /ws/ssh/")
        if "auth_request /_auth/ws-ssh;" not in b
    ]
    # Assert
    assert ungated == []


def test_auth_location_is_internal_and_targets_the_bridge_view():
    # Arrange
    text = NGINX.read_text()
    # Act
    bodies = _location_body(text, "location = /_auth/ws-ssh")
    # Assert
    assert bodies and all(
        "internal;" in b and "/apps/workspace/api/ssh-bridge/authorize/" in b
        for b in bodies
    )
