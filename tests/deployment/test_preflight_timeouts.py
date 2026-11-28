"""The dependency check's deadlines are configurable for every docker call.

compose.sh runs ``preflight_sibling_floors.sh <env>`` before each ``up`` and
passes nothing else, so on a busy host (IO pressure from CI jobs) its fixed
30/60 s docker deadlines refused every deploy as "could not be interrogated".
The deadlines now come from ``SCITEX_HUB_PREFLIGHT_TIMEOUT`` and
``SCITEX_HUB_PREFLIGHT_DOCKER_TIMEOUT`` (or ``--timeout``/``--docker-timeout``),
and no docker call in the direct-bind target keeps a literal deadline.
"""

import ast
import importlib
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(
    os.environ.get("SCITEX_PREFLIGHT_TEST_ROOT", Path(__file__).resolve().parents[2])
)
sys.path.insert(0, str(ROOT / "scripts/deploy"))
floors = importlib.import_module("preflight_sibling_floors")
TARGET = ROOT / "scripts/deploy/_direct_bind/target.py"
NAMES = ("SCITEX_HUB_PREFLIGHT_TIMEOUT", "SCITEX_HUB_PREFLIGHT_DOCKER_TIMEOUT")


@pytest.fixture
def deadline_env():
    """Real os.environ, restored afterwards; tests set what they need."""
    saved = {name: os.environ.pop(name, None) for name in NAMES}
    yield os.environ
    for name, value in saved.items():
        os.environ.pop(name, None)
        if value is not None:
            os.environ[name] = value


def test_docker_deadline_defaults_to_sixty_seconds(deadline_env):
    # Arrange
    deadline_env.pop("SCITEX_HUB_PREFLIGHT_DOCKER_TIMEOUT", None)
    # Act
    seconds = floors._env_seconds("SCITEX_HUB_PREFLIGHT_DOCKER_TIMEOUT", 60)
    # Assert
    assert seconds == 60


def test_environment_lengthens_the_docker_deadline(deadline_env):
    # Arrange
    deadline_env["SCITEX_HUB_PREFLIGHT_DOCKER_TIMEOUT"] = "600"
    # Act
    seconds = floors._env_seconds("SCITEX_HUB_PREFLIGHT_DOCKER_TIMEOUT", 60)
    # Assert
    assert seconds == 600


@pytest.mark.parametrize("raw", ["0", "-5", "soon"])
def test_an_invalid_deadline_refuses_instead_of_falling_back(deadline_env, raw):
    # Arrange
    deadline_env["SCITEX_HUB_PREFLIGHT_TIMEOUT"] = raw
    # Act
    attempt = lambda: floors._env_seconds("SCITEX_HUB_PREFLIGHT_TIMEOUT", 300)  # noqa: E731
    # Assert
    with pytest.raises(SystemExit):
        attempt()


def _literal_timeouts(path):
    found = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "timeout" and isinstance(keyword.value, ast.Constant):
                    found.append(node.lineno)
    return found


def test_no_docker_call_in_the_direct_bind_target_keeps_a_literal_deadline():
    # Arrange
    target = TARGET
    # Act
    literals = _literal_timeouts(target)
    # Assert
    assert literals == []


target_module = importlib.import_module("_direct_bind.target")


def test_no_cache_directory_means_no_cache_mount():
    # Arrange
    environ = {}
    # Act
    args = target_module.uv_cache_args(environ)
    # Assert
    assert args == []


def test_a_cache_directory_is_bind_mounted_for_the_install(tmp_path):
    # Arrange
    environ = {"SCITEX_HUB_PREFLIGHT_UV_CACHE": str(tmp_path)}
    # Act
    args = target_module.uv_cache_args(environ)
    # Assert
    assert args == [
        "--mount",
        "type=bind,src={0},dst=/preflight-uv-cache".format(tmp_path),
        "--env",
        "SCITEX_PREFLIGHT_UV_CACHE_DIR=/preflight-uv-cache",
    ]


def test_a_missing_cache_directory_refuses(tmp_path):
    # Arrange
    environ = {"SCITEX_HUB_PREFLIGHT_UV_CACHE": str(tmp_path / "absent")}
    # Act
    attempt = lambda: target_module.uv_cache_args(environ)  # noqa: E731
    # Assert
    with pytest.raises(target_module.TargetUnreachable):
        attempt()
