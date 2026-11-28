"""nginx / gitea deploy config: plain-HTTP visitors are redirected to https,
no server version is disclosed, and gitea marks its cookies Secure.

Behaviour (301 for an http edge scheme, no redirect for internal callers,
404 for the anonymous /api/v1/version) was exercised against these exact
files in throwaway nginx containers; these tests pin the rules so an edit
cannot silently drop them.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "deployment/docker/common"
HUB = COMMON / "nginx/nginx_prod.conf"
FRONT = COMMON / "gitea/front/nginx.conf"
DEV = COMMON / "nginx/nginx.conf"
COMPOSE = ROOT / "deployment/docker/docker_prod/docker-compose.yml"
REDIRECT = "if ($edge_plain_http) { return 301 https://$host$request_uri; }"


def _server_blocks(text):
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


@pytest.mark.parametrize("conf", [HUB, FRONT, DEV], ids=["hub", "gitea-front", "dev"])
def test_server_tokens_are_off(conf):
    # Arrange
    text = conf.read_text()
    # Act
    found = re.search(r"^\s*server_tokens off;", text, re.M)
    # Assert
    assert found


@pytest.mark.parametrize("conf", [HUB, FRONT], ids=["hub", "gitea-front"])
def test_edge_scheme_map_is_defined(conf):
    # Arrange
    text = conf.read_text()
    # Act
    found = 'map "$http_cf_visitor|$http_x_forwarded_proto" $edge_plain_http' in text
    # Assert
    assert found


@pytest.mark.parametrize(
    "server_name",
    ["scitex.ai", "git.scitex.ai", "a2a.scitex.ai", "analytics.scitex.ai"],
)
def test_every_public_hub_server_redirects_plain_http(server_name):
    # Arrange
    blocks = _server_blocks(HUB.read_text())
    # Act
    block = next(
        b
        for b in blocks
        if re.search(rf"server_name[^;]*\s{re.escape(server_name)}[\s;]", b)
    )
    # Assert
    assert REDIRECT in block


def test_gitea_front_redirects_plain_http():
    # Arrange
    text = FRONT.read_text()
    # Act
    found = REDIRECT in text
    # Assert
    assert found


def test_gitea_front_hides_the_version_from_anonymous_tunnel_visitors():
    # Arrange
    text = FRONT.read_text()
    # Act
    rule = re.search(r"location = /api/v1/version \{(.*?)\n        \}", text, re.S)
    # Assert
    assert (
        rule
        and "return 404" in rule.group(1)
        and "http_cf_connecting_ip" in rule.group(1)
    )


@pytest.mark.parametrize(
    "line",
    [
        "GITEA__session__COOKIE_SECURE=true",
        "GITEA__other__SHOW_FOOTER_VERSION=false",
        "GITEA__other__SHOW_FOOTER_POWERED_BY=false",
        "GITEA__other__SHOW_FOOTER_TEMPLATE_LOAD_TIME=false",
    ],
)
def test_prod_gitea_env_hardening(line):
    # Arrange
    text = COMPOSE.read_text()
    # Act
    found = f"- {line}" in text
    # Assert
    assert found
