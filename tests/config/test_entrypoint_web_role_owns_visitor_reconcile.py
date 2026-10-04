"""Boot roles remain explicit and never reactivate retired visitor allocation.

Visitor allocation was retired on 2026-09-10. Neither web nor worker startup
may create or reconcile its slots; explicit historical cleanup is separate.
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


def _visitor_commands(script: str) -> list[str]:
    """Inspect shell tokens, ignoring comments and separating shell operators."""
    lexer = shlex.shlex(script, posix=True, punctuation_chars="();&|")
    lexer.whitespace_split = True
    tokens = list(lexer)
    retired = {"create_visitor_pool", "reconcile_visitor_slots"}
    return [
        command
        for executable, command in zip(tokens, tokens[1:], strict=False)
        if Path(executable).name == "manage.py" and command in retired
    ]


@pytest.mark.parametrize("entrypoint", ENTRYPOINTS, ids=lambda path: path.parent.name)
def test_every_dev_and_prod_entrypoint_keeps_visitor_allocation_retired(entrypoint):
    script = entrypoint.read_text(encoding="utf-8")
    assert "service_role.src" in script
    assert _visitor_commands(script) == []


def test_source_checker_rejects_the_old_unconditional_dev_block():
    assert _visitor_commands(OLD_UNSAFE_DEV_BLOCK) == [
        "create_visitor_pool", "reconcile_visitor_slots"
    ]


def test_web_role_guard_cannot_reactivate_retired_visitor_allocation():
    script = 'if [ "$IS_WEB_ROLE" = true ]; then\n' + OLD_UNSAFE_DEV_BLOCK + "fi\n"
    assert _visitor_commands(script) == ["create_visitor_pool", "reconcile_visitor_slots"]


def test_comment_about_historical_cleanup_is_not_a_boot_command():
    assert _visitor_commands("# python manage.py reconcile_visitor_slots\n") == []


@pytest.mark.parametrize("compose_path", sorted({case[0] for case in COMPOSE_CASES}))
def test_compose_does_not_restore_the_retired_visitor_worker(compose_path):
    compose = yaml.safe_load((REPO_ROOT / compose_path).read_text(encoding="utf-8"))
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
