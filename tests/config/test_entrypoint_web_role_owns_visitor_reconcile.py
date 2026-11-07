"""Retired visitor pools must never be reintroduced by container startup.

Accepted dab365317 removed the visitor runtime and dedicated worker. Keep the
real service-role classifier controls, but do not require dead pool mutations
as the former reconciliation test did.
"""

import shlex
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLE_LIB = REPO_ROOT / "deployment/docker/common/lib/service_role.src"
ENTRYPOINTS = (
    REPO_ROOT / "deployment/docker/docker_dev/entrypoint.sh",
    REPO_ROOT / "deployment/docker/common/scripts/entrypoint-dev.sh",
    REPO_ROOT / "deployment/docker/common/scripts/entrypoint-prod.sh",
    REPO_ROOT / "deployment/docker/docker_prod/entrypoint.sh",
)
COMPOSE_CASES = (
    ("deployment/docker/docker_dev/docker-compose.yml", "django", True),
    ("deployment/docker/docker_dev/docker-compose.yml", "celery_worker", False),
    ("deployment/docker/docker_dev/docker-compose.yml", "celery_beat", False),
    ("deployment/docker/docker_prod/docker-compose.yml", "django", True),
    ("deployment/docker/docker_prod/docker-compose.yml", "celery_worker", False),
    ("deployment/docker/docker_prod/docker-compose.yml", "celery_beat", False),
)

OLD_UNSAFE_DEV_BLOCK = """
# Initialize Visitor Pool
# ============================================
python manage.py create_visitor_pool --verbosity 0
python manage.py reconcile_visitor_slots --async
# ============================================
# Initialize Test User
"""


def _command_argv(command):
    if isinstance(command, list):
        return [str(part) for part in command]
    return shlex.split(command)


def _is_web_role(*argv: str) -> bool:
    result = subprocess.run(
        ["bash", "-c", 'source "$1"; shift; is_web_role "$@"', "bash", str(ROLE_LIB), *argv],
        check=False,
    )
    return result.returncode == 0


def _visitor_role_violations(script: str) -> list[str]:
    """No live startup role may run a retired pool mutation."""
    live = [line.strip() for line in script.splitlines() if not line.lstrip().startswith("#")]
    if any(
        "manage.py create_visitor_pool" in line
        or "manage.py reconcile_visitor_slots" in line
        for line in live
    ):
        return ["retired visitor-pool bootstrap must not run in any role"]
    return []


def _live_lines(script: str) -> list[str]:
    """Non-comment lines: retirement notices may name the old commands."""
    return [
        line
        for line in script.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


@pytest.mark.parametrize("entrypoint", ENTRYPOINTS, ids=lambda path: path.parent.name)
def test_every_dev_and_prod_entrypoint_keeps_visitor_runtime_retired(entrypoint):
    script = entrypoint.read_text(encoding="utf-8")
    assert "service_role.src" in script
    assert _visitor_role_violations(script) == []
    live = "\n".join(_live_lines(script))
    assert "create_visitor_pool" not in live
    assert "reconcile_visitor_slots" not in live


def test_source_checker_rejects_the_old_unconditional_dev_block():
    assert _visitor_role_violations(OLD_UNSAFE_DEV_BLOCK) == [
        "retired visitor-pool bootstrap must not run in any role"
    ]


def test_web_role_guard_does_not_authorize_resurrecting_retired_pool():
    guarded = 'if [ "$IS_WEB_ROLE" = true ]; then\n' + OLD_UNSAFE_DEV_BLOCK + "\nfi"
    assert _visitor_role_violations(guarded) == [
        "retired visitor-pool bootstrap must not run in any role"
    ]


def test_production_has_no_retired_visitor_worker():
    compose = yaml.safe_load(
        (REPO_ROOT / "deployment/docker/docker_prod/docker-compose.yml").read_text()
    )
    assert "celery_worker_vis" not in compose["services"]


@pytest.mark.parametrize(
    ("compose_path", "service", "expected"),
    COMPOSE_CASES,
    ids=[f"{Path(path).parent.name}-{service}" for path, service, _ in COMPOSE_CASES],
)
def test_compose_command_has_expected_web_role(compose_path, service, expected):
    compose = yaml.safe_load((REPO_ROOT / compose_path).read_text(encoding="utf-8"))
    argv = _command_argv(compose["services"][service]["command"])
    assert _is_web_role(*argv) is expected


@pytest.mark.parametrize("argv", [(), ("bash",), ("python", "manage.py", "shell")])
def test_unknown_commands_fail_closed(argv):
    assert _is_web_role(*argv) is False


def test_old_not_celery_heuristic_classifies_unknown_command_as_web():
    result = subprocess.run(
        ["bash", "-c", '[[ ! "$*" =~ celery ]]', "bash", "python", "manage.py", "shell"],
        check=False,
    )
    assert result.returncode == 0
