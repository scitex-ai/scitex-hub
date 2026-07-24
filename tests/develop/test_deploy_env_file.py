"""Deploy-path env-file conformance gate.

Regression guard for card ``hub-make-rebuild-drops-env-file``: the
sanctioned prod/staging deploy path MUST invoke ``docker compose`` with
an ``--env-file`` flag pointing at an ABSOLUTE path. If it does not,
compose resolves every ``${VAR:?...}`` in ``docker_prod/docker-compose.yml``
to an empty string and either aborts on the secret guard (post PR #372) or
— before that guard existed — silently builds blank-secret containers
(the gitea blank-DB-password outage, 2026-07-13).

Two independent surfaces must stay correct and in sync, so both are
asserted here:

* ``scripts/deploy/compose_env.sh`` — the single-source resolver that
  ``rebuild.sh`` / ``compose.sh`` source (``make ENV=<env> rebuild``
  delegates here).
* the top-level ``Makefile``'s inline ``COMPOSE_CMD`` — used by
  ``rebuild-no-cache`` / ``start`` / ``migrate`` / ``restart``.

These are shell/make assertions (no Docker, no real ``.env.*`` secret
file required — ``resolve_compose_env`` only checks the compose DIR
exists), so the gate runs in the headless pytest matrix.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_ENV_SH = REPO_ROOT / "scripts" / "deploy" / "compose_env.sh"
ENVS_DIR = REPO_ROOT / "deployment" / "docker" / "envs"

_MAKE_MISSING = shutil.which("make") is None
_needs_make = pytest.mark.skipif(_MAKE_MISSING, reason="make not installed")


def _resolve_compose_cmd(env: str) -> str:
    """Return the COMPOSE_CMD that compose_env.sh resolves for ``env``."""
    script = (
        f'source "{COMPOSE_ENV_SH}" && '
        f'resolve_compose_env "{env}" "{REPO_ROOT}" && '
        f'printf "%s" "$COMPOSE_CMD"'
    )
    proc = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"resolve_compose_env {env} failed: {proc.stderr}")
    return proc.stdout.strip()


def _make_output(*args: str) -> str:
    """Run ``make`` with the given args from the repo root, return stdout."""
    proc = subprocess.run(
        ["make", *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"make {' '.join(args)} failed: {proc.stderr}")
    return proc.stdout


def _env_file_flag(env: str) -> str:
    """The exact ``--env-file <abs>`` token the deploy path must carry."""
    return f"--env-file {ENVS_DIR / f'.env.{env}'}"


@pytest.mark.parametrize("env", ["prod", "staging"])
def test_compose_env_carries_absolute_env_file(env):
    # Arrange
    expected = _env_file_flag(env)
    # Act
    compose_cmd = _resolve_compose_cmd(env)
    # Assert
    assert expected in compose_cmd, (
        f"{env} COMPOSE_CMD must carry `{expected}`; got: {compose_cmd!r}"
    )


def test_compose_env_dev_has_no_env_file():
    # Arrange
    env = "dev"
    # Act
    compose_cmd = _resolve_compose_cmd(env)
    # Assert
    assert "--env-file" not in compose_cmd, (
        f"dev COMPOSE_CMD should reference no --env-file; got: {compose_cmd!r}"
    )


@_needs_make
def test_make_rebuild_delegates_to_script():
    # Arrange
    args = ("-n", "ENV=prod", "rebuild")
    # Act
    recipe = _make_output(*args)
    # Assert
    assert "scripts/deploy/rebuild.sh" in recipe, (
        "`make ENV=prod rebuild` must delegate to scripts/deploy/rebuild.sh; "
        f"recipe was:\n{recipe}"
    )


@_needs_make
def test_make_rebuild_has_no_inline_docker_compose():
    # Arrange
    args = ("-n", "ENV=prod", "rebuild")
    # Act
    recipe = _make_output(*args)
    # Assert
    assert "docker compose" not in recipe, (
        "`make ENV=prod rebuild` must NOT invoke `docker compose` inline "
        f"(the env-file-drop regression); recipe was:\n{recipe}"
    )


@_needs_make
@pytest.mark.parametrize("env", ["prod", "staging"])
def test_makefile_compose_cmd_carries_absolute_env_file(env):
    # Arrange
    expected = _env_file_flag(env)
    # Act
    db = _make_output("-pn", f"ENV={env}", "help")
    compose_lines = [
        ln for ln in db.splitlines() if ln.startswith("COMPOSE_CMD")
    ]
    # Assert
    assert compose_lines and all(expected in ln for ln in compose_lines), (
        f"Makefile {env} COMPOSE_CMD must carry `{expected}`; "
        f"got: {compose_lines!r}"
    )
