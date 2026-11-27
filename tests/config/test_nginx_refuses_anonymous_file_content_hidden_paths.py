"""Prod nginx refuses anonymous file-content reads of hidden paths (edge tourniquet).

``/api/workspace/file-content/<path>`` serves every file of a public project to
anonymous readers, hidden files included. Until the view decides which hidden
files a public reader may see, nginx refuses any path with a component starting
with "." unless the request carries Django's session cookie (``sessionid``);
signed-in users reach Django, which applies its own permission check. This pins
the rule in every server that proxies to django and exercises its regex.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NGINX = ROOT / "deployment/docker/common/nginx/nginx_prod.conf"
LOCATION = r"location ~ ^/api/workspace/file-content/(.*/)?\. {"
COOKIE_GATE = 'if ($cookie_sessionid = "") { return 403; }'


def _pattern():
    return re.compile(LOCATION.split("location ~ ", 1)[1].rsplit(" {", 1)[0])


def _blocks_after_location():
    text = NGINX.read_text()
    return [part.split("\n        }", 1)[0] for part in text.split(LOCATION)[1:]]


def test_both_django_servers_carry_the_rule():
    # Arrange
    text = NGINX.read_text()
    # Act
    count = text.count(LOCATION)
    # Assert
    assert count == 2


def test_every_copy_is_gated_on_the_session_cookie():
    # Arrange
    blocks = _blocks_after_location()
    # Act
    gated = [COOKIE_GATE in block for block in blocks]
    # Assert
    assert gated == [True, True]


@pytest.mark.parametrize(
    "path",
    [
        "/api/workspace/file-content/.scitex/writer/config.yaml",
        "/api/workspace/file-content/.envrc",
        "/api/workspace/file-content/docs/a/.claude/settings.json",
        "/api/workspace/file-content/a/b/.ssh/id_rsa",
    ],
)
def test_hidden_paths_match(path):
    # Arrange
    pattern = _pattern()
    # Act
    matched = pattern.search(path)
    # Assert
    assert matched


@pytest.mark.parametrize(
    "path",
    [
        "/api/workspace/file-content/README.md",
        "/api/workspace/file-content/paper/main.tex",
        "/api/workspace/file-content/scripts/run.v2.py",
        "/api/workspace/files/.scitex/config.yaml",
    ],
)
def test_ordinary_paths_do_not_match(path):
    # Arrange
    pattern = _pattern()
    # Act
    matched = pattern.search(path)
    # Assert
    assert not matched
