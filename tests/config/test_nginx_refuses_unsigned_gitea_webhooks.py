"""Prod nginx refuses the two Gitea -> Hub webhooks from outside (until #1244).

Both webhooks accept unauthenticated POSTs: one adds or removes organisation
members, the other approves a pending app as public and verified. Gitea
delivers them to http://django:8000 directly, so nginx (the only public path to
django, via the tunnel) can refuse them for everyone. This pins that every
server block proxying to django carries the rule, and that the rule matches the
webhook paths and nothing else under /api/.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NGINX = ROOT / "deployment/docker/common/nginx/nginx_prod.conf"
RULE = "location ~ ^/api/(gitea/webhook/sync|apps/webhook)(/|$) { return 403; }"


def _server_blocks():
    """Top-level ``server { ... }`` bodies, split by brace depth."""
    text = NGINX.read_text()
    blocks, depth, start = [], 0, None
    for match in re.finditer(r"\bserver\s*\{|\{|\}", text):
        token = match.group(0)
        if token.startswith("server") and depth == 1:
            start = match.start()
        if token.endswith("{"):
            depth += 1
        else:
            depth -= 1
            if depth == 1 and start is not None:
                blocks.append(text[start : match.end()])
                start = None
    return blocks


def _django_servers():
    return [b for b in _server_blocks() if "http://django:8000" in b]


def _pattern():
    return re.compile(RULE.split("location ~ ", 1)[1].split(" {", 1)[0])


def test_found_the_servers_that_proxy_to_django():
    # Arrange
    servers = _django_servers()
    # Act
    count = len(servers)
    # Assert
    assert count >= 2


def test_every_server_that_proxies_to_django_refuses_the_webhooks():
    # Arrange
    servers = _django_servers()
    # Act
    missing = [b.split("\n", 3)[:3] for b in servers if RULE not in b]
    # Assert
    assert missing == []


@pytest.mark.parametrize(
    "path",
    [
        "/api/gitea/webhook/sync/",
        "/api/gitea/webhook/sync",
        "/api/apps/webhook/",
        "/api/apps/webhook",
    ],
)
def test_rule_matches_the_webhook_paths(path):
    # Arrange
    pattern = _pattern()
    # Act
    matched = pattern.search(path)
    # Assert
    assert matched


@pytest.mark.parametrize(
    "path",
    [
        "/api/apps/webhooks-docs/",
        "/api/apps/",
        "/api/gitea/repos/",
        "/apps/webhook/",
        "/api/gitea/webhook/",
    ],
)
def test_rule_leaves_other_paths_alone(path):
    # Arrange
    pattern = _pattern()
    # Act
    matched = pattern.search(path)
    # Assert
    assert not matched
