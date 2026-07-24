"""Regression: SLURM batch-script generation must neutralize shell injection.

apps/workspace/console_app/services/slurm/script_generator.create_batch_script
interpolates tenant-controlled fields (job_name, env_vars, cpus, memory_gb,
partition, time_limit) into a bash script that SLURM executes — historically
unescaped (CWE-78). An authenticated tenant could POST
env_vars={"X": "$(cmd)"} and get command execution in the batch job's shell,
which runs OUTSIDE the Apptainer sandbox (the sandbox wraps only the python
payload). See sec-slurm-jobscript-cmd-injection.

Fields that land in #SBATCH directives / arithmetic (job_name, partition,
time_limit, cpus, memory_gb) cannot be shell-quoted (SLURM parses them), so they
are validated and REJECTED; env-var values that land in bash are shlex-quoted.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from apps.workspace.console_app.services.slurm.script_generator import (
    create_batch_script,
)

pytestmark = pytest.mark.security

CMD_SUB = "$(touch /tmp/pwned)"


def _script(tmp_path, **overrides):
    kwargs = dict(
        user_id="100",
        script_path=Path("/workspace/x.py"),
        container_path=Path("/opt/scitex/container.sif"),
        workspace=tmp_path,
        job_name="scitex_job",
        partition="normal",
        cpus=2,
        memory_gb=4,
        time_limit="01:00:00",
        env_vars={},
    )
    kwargs.update(overrides)
    return create_batch_script(**kwargs)


def test_valid_inputs_produce_a_bash_script(tmp_path):
    # Arrange
    env = {"DEBUG": "1"}
    # Act
    script = _script(tmp_path, env_vars=env)
    # Assert
    assert script.startswith("#!/bin/bash")


def test_job_name_with_command_substitution_is_rejected(tmp_path):
    # Arrange
    payload = CMD_SUB
    # Act
    # Assert
    with pytest.raises(ValueError):
        _script(tmp_path, job_name=payload)


def test_env_value_injection_is_shell_quoted_not_executable(tmp_path):
    # Arrange
    payload = CMD_SUB
    # Act
    script = _script(tmp_path, env_vars={"X": payload})
    # Assert
    assert "export X='$(touch /tmp/pwned)'" in script


def test_env_name_that_is_not_a_shell_identifier_is_rejected(tmp_path):
    # Arrange
    bad_env = {"X; rm -rf /": "1"}
    # Act
    # Assert
    with pytest.raises(ValueError):
        _script(tmp_path, env_vars=bad_env)


def test_non_integer_cpus_is_rejected(tmp_path):
    # Arrange
    payload = "$(id)"
    # Act
    # Assert
    with pytest.raises(ValueError):
        _script(tmp_path, cpus=payload)


def test_partition_with_newline_injection_is_rejected(tmp_path):
    # Arrange
    payload = "normal\n#SBATCH --uid=0"
    # Act
    # Assert
    with pytest.raises(ValueError):
        _script(tmp_path, partition=payload)
