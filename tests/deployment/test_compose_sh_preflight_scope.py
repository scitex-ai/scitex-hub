"""compose.sh runs the application-image preflight for every ``up`` that can start it.

The sibling floor + import preflight interrogates the hub APPLICATION image
(Django, Celery). On 2026-11-27 it refused ``up --no-deps gitea gitea_front``
(gitea and an nginx sidecar, neither built from that image) for 11 stale floors
of the Django image. The scope decision lives in
``scripts/deploy/up_needs_app_preflight.py``; these tests run it, as compose.sh
does, against the real prod compose file. It may answer ``skip`` only with
proof; everything else must stay ``run``.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/deploy/up_needs_app_preflight.py"
COMPOSE_SH = ROOT / "scripts/deploy/compose.sh"
PROD_DIR = ROOT / "deployment/docker/docker_prod"
PROD_CMD = "docker compose --env-file /nonexistent/.env.prod"


def _verdict(*up_args, docker_dir=PROD_DIR, compose_cmd=PROD_CMD):
    completed = subprocess.run(
        [sys.executable, str(HELPER), str(docker_dir), compose_cmd, *up_args],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def test_up_gitea_and_its_sidecar_skips_the_preflight():
    # Arrange
    args = (
        "up",
        "-d",
        "--no-deps",
        "--no-build",
        "--force-recreate",
        "gitea",
        "gitea_front",
    )
    # Act
    verdict = _verdict(*args)
    # Assert
    assert verdict == "skip"


def test_up_django_still_runs_the_preflight():
    # Arrange
    args = ("up", "-d", "--no-deps", "--force-recreate", "django")
    # Act
    verdict = _verdict(*args)
    # Assert
    assert verdict == "run"


def test_bare_up_with_no_service_list_still_runs_the_preflight():
    # Arrange
    args = ("up", "-d")
    # Act
    verdict = _verdict(*args)
    # Assert
    assert verdict == "run"


@pytest.mark.parametrize("service", ["celery_worker", "celery_beat"])
def test_up_a_celery_worker_still_runs_the_preflight(service):
    # Arrange
    args = ("up", "-d", "--no-deps", service)
    # Act
    verdict = _verdict(*args)
    # Assert
    assert verdict == "run"


def test_a_dependency_on_the_app_image_runs_the_preflight():
    # Arrange -- nginx is a third-party image, but it depends_on django, and
    # without --no-deps compose starts (and may recreate) django too.
    args = ("up", "-d", "nginx")
    # Act
    verdict = _verdict(*args)
    # Assert
    assert verdict == "run"


def test_no_deps_limits_the_check_to_the_named_service():
    # Arrange
    args = ("up", "-d", "--no-deps", "nginx")
    # Act
    verdict = _verdict(*args)
    # Assert
    assert verdict == "skip"


@pytest.mark.parametrize(
    "args",
    [
        ("up", "-d", "-t", "5", "gitea"),  # an option this script does not model
        ("up", "-d", "--scale", "django=2", "gitea"),
        ("up", "-d", "no_such_service"),
        ("restart", "gitea"),
    ],
)
def test_anything_unproven_runs_the_preflight(args):
    # Arrange
    up_args = args
    # Act
    verdict = _verdict(*up_args)
    # Assert
    assert verdict == "run"


def test_an_unreadable_compose_directory_runs_the_preflight(tmp_path):
    # Arrange
    empty = tmp_path / "no_compose_here"
    empty.mkdir()
    # Act
    verdict = _verdict(
        "up", "-d", "gitea", docker_dir=empty, compose_cmd="docker compose"
    )
    # Assert
    assert verdict == "run"


def _skip_branch():
    text = COMPOSE_SH.read_text()
    before, after = text.split('if [ "$verdict" = "skip" ]; then', 1)
    return before, after.split("\n        fi\n", 1)[0]


def test_compose_sh_verdict_defaults_to_running_the_preflight():
    # Arrange
    before, _ = _skip_branch()
    # Act
    default_is_empty = 'verdict=""' in before
    # Assert
    assert default_is_empty


def test_compose_sh_calls_the_preflight_whenever_the_verdict_is_not_skip():
    # Arrange
    _, branch = _skip_branch()
    # Act
    else_part = branch.split("else", 1)[1]
    # Assert
    assert '"$SCRIPT_DIR/preflight_sibling_floors.sh" "$ENV"' in else_part
