"""Entrypoint role gate for visitor-pool boot reconciliation.

The visitor reconcile quarantines every slot before dispatching the safe re-clean.
It therefore belongs to web boot only: running it while restarting the worker that
must consume those tasks creates a circular dependency and leaves the pool down.
"""

from pathlib import Path
import shlex
import subprocess

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
    ("deployment/docker/docker_prod/docker-compose.yml", "celery_worker_vis", False),
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


def _visitor_block(script: str) -> str:
    marker = "# Initialize Visitor Pool"
    separator = "# ============================================"
    if marker not in script:
        return ""
    block = script.split(marker, 1)[1]
    # Skip the separator that closes this heading, then stop at the next one.
    block = block.split(separator, 1)[1]
    return block.split(separator, 1)[0]


def _visitor_role_violations(script: str) -> list[str]:
    """Reject pool mutations not enclosed by the explicit web-role branch."""
    block = _visitor_block(script)
    live = [line.strip() for line in block.splitlines() if not line.lstrip().startswith("#")]
    mutations = [
        index
        for index, line in enumerate(live)
        if "manage.py create_visitor_pool" in line
        or "manage.py reconcile_visitor_slots" in line
    ]
    guards = [
        index
        for index, line in enumerate(live)
        if line == 'if [ "$IS_WEB_ROLE" = true ]; then'
    ]
    if not mutations:
        return ["visitor-pool create/reconcile commands are missing"]
    if not guards or guards[0] > min(mutations):
        return ["visitor-pool mutation is not guarded by IS_WEB_ROLE"]
    if not any(index > max(mutations) and live[index] == "else" for index in range(len(live))):
        return ["non-web roles have no explicit visitor-pool skip branch"]
    return []


@pytest.mark.parametrize("entrypoint", ENTRYPOINTS, ids=lambda path: path.parent.name)
def test_every_dev_and_prod_entrypoint_guards_pool_mutation_by_web_role(entrypoint):
    script = entrypoint.read_text(encoding="utf-8")
    assert "service_role.src" in script
    assert _visitor_role_violations(script) == []


def test_source_checker_rejects_the_old_unconditional_dev_block():
    assert _visitor_role_violations(OLD_UNSAFE_DEV_BLOCK) == [
        "visitor-pool mutation is not guarded by IS_WEB_ROLE"
    ]


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
