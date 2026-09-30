"""Web-role ownership of boot mutations in the container entrypoints.

HISTORY. Visitor-slot allocation used to run at boot, and this file pinned
that ONLY the web container ran it (``create_visitor_pool`` /
``reconcile_visitor_slots`` guarded by ``IS_WEB_ROLE``): running the
reconcile from the worker that must consume those tasks is a circular
dependency that leaves the pool down.

RETIREMENT. Anonymous visitor allocation was then retired from the product
(b3ca29027 "fix(deploy): retire visitor-pool boot lifecycle", completed by
dab365317 "[verified] refactor: complete visitor runtime removal", which
also deleted the ``celery_worker_vis`` service). The ABSENCE of every
visitor command in every shipped entrypoint is now pinned by
``tests/develop/test_visitor_retirement_contract.py`` — asserting their
presence here would directly contradict it.

What this file still owns: the surviving contract underneath.

- Every dev/prod entrypoint sources the shared role library and takes its
  role from ``is_web_role`` (no per-entrypoint role heuristics).
- Every remaining compose service routes to the expected role
  (``celery_worker_vis`` is gone with the visitor runtime).
- ``is_web_role`` itself: unknown commands fail closed (the old
  not-celery heuristic classified ``python manage.py shell`` as web).
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
    ("deployment/docker/docker_prod/docker-compose.yml", "celery_beat", False),
)


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


@pytest.mark.parametrize("entrypoint", ENTRYPOINTS, ids=lambda path: path.parent.name)
def test_every_dev_and_prod_entrypoint_takes_its_role_from_the_shared_library(
    entrypoint,
):
    script = entrypoint.read_text(encoding="utf-8")
    assert "service_role.src" in script
    assert "is_web_role" in script


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
