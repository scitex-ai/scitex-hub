"""compose.sh supplies the release dependency-resolution input to Compose.

The release compose files declare the Django build arg as
``${SCITEX_HUB_DEPENDENCY_RESOLUTION:?set by protected rebuild}``. Compose
interpolates build args for every command, so a manual
``scripts/deploy/compose.sh prod ps`` used to abort with "required variable
SCITEX_HUB_DEPENDENCY_RESOLUTION is missing a value". compose.sh now derives
the value from the committed nonce file, exactly as rebuild.sh does.

These tests run the real compose.sh with a stand-in ``docker`` executable on
PATH that records the value it received and its arguments.
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_SH = ROOT / "scripts/deploy/compose.sh"
NONCE_FILE = ROOT / "deployment/docker/dependency-resolution.nonce"
ARG = "SCITEX_HUB_DEPENDENCY_RESOLUTION"
UNSET = "<unset>"


@dataclass
class Outcome:
    returncode: int
    stderr: str
    record: Path

    @property
    def value(self) -> str:
        return self.record.read_text().splitlines()[0]

    @property
    def argv(self) -> str:
        return self.record.read_text().splitlines()[1]


def _run(tmp_path: Path, env_name: str, *args: str, extra_env=None) -> Outcome:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    record = tmp_path / "record.txt"
    docker = bin_dir / "docker"
    docker.write_text(
        f'#!/bin/bash\nprintf "%s\\n" "${{{ARG}-{UNSET}}}" "$*" > "{record}"\n'
    )
    docker.chmod(0o755)
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {ARG, "SCITEX_HUB_DEPENDENCY_RESOLUTION_FILE", "SCITEX_HUB_APP_IMAGE"}
    }
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env.update(extra_env or {})
    result = subprocess.run(
        [str(COMPOSE_SH), env_name, *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return Outcome(result.returncode, result.stderr, record)


@pytest.fixture
def committed_input() -> str:
    return NONCE_FILE.read_text().strip()


@pytest.mark.parametrize("env_name", ["prod", "staging"])
def test_read_only_command_succeeds_without_a_hand_set_value(tmp_path, env_name):
    # Arrange
    args = ("ps",)
    # Act
    outcome = _run(tmp_path, env_name, *args)
    # Assert
    assert outcome.returncode == 0, outcome.stderr


@pytest.mark.parametrize("env_name", ["prod", "staging"])
def test_read_only_command_receives_the_committed_release_input(
    tmp_path, env_name, committed_input
):
    # Arrange
    args = ("ps",)
    # Act
    outcome = _run(tmp_path, env_name, *args)
    # Assert
    assert outcome.value == committed_input


def test_compose_arguments_are_passed_through(tmp_path):
    # Arrange
    args = ("ps",)
    # Act
    outcome = _run(tmp_path, "prod", *args)
    # Assert
    assert outcome.argv.endswith(" ps")


def test_caller_value_is_ignored_in_favour_of_the_committed_input(
    tmp_path, committed_input
):
    # Arrange
    extra = {ARG: "hand-typed-value"}
    # Act
    outcome = _run(tmp_path, "prod", "ps", extra_env=extra)
    # Assert
    assert outcome.value == committed_input


@pytest.fixture
def missing_input_outcome(tmp_path) -> Outcome:
    extra = {"SCITEX_HUB_DEPENDENCY_RESOLUTION_FILE": str(tmp_path / "missing.nonce")}
    return _run(tmp_path, "prod", "ps", extra_env=extra)


def test_missing_release_input_exits_non_zero(missing_input_outcome):
    # Arrange
    outcome = missing_input_outcome
    # Act
    observed = outcome.returncode != 0
    # Assert
    assert observed


def test_missing_release_input_names_the_variable(missing_input_outcome):
    # Arrange
    outcome = missing_input_outcome
    # Act
    observed = ARG in outcome.stderr
    # Assert
    assert observed


def test_missing_release_input_names_the_nonce_file(missing_input_outcome):
    # Arrange
    outcome = missing_input_outcome
    # Act
    observed = "dependency-resolution.nonce" in outcome.stderr
    # Assert
    assert observed


def test_missing_release_input_never_invokes_compose(missing_input_outcome):
    # Arrange
    outcome = missing_input_outcome
    # Act
    observed = not outcome.record.exists()
    # Assert
    assert observed
