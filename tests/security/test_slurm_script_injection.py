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
from apps.workspace.console_app.services.slurm.tags import SlurmTags

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
        tags=SlurmTags.for_project(7),
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
    assert "export APPTAINERENV_X='$(touch /tmp/pwned)'" in script


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


@pytest.mark.parametrize("name", ["PATH", "LD_PRELOAD", "BASH_ENV", "IFS"])
def test_requested_env_never_reaches_the_host_side_script_shell(tmp_path, name):
    # Arrange
    env = {name: str(tmp_path / "tenant-controlled")}
    # Act
    script = _script(tmp_path, env_vars=env)
    # Assert
    assert f"export {name}=" not in script


@pytest.mark.parametrize("name", ["PATH", "LD_PRELOAD", "DEBUG"])
def test_requested_env_is_handed_to_the_container(tmp_path, name):
    # Arrange
    env = {name: "value"}
    # Act
    script = _script(tmp_path, env_vars=env)
    # Assert
    assert f"export APPTAINERENV_{name}=value" in script


@pytest.fixture
def run_script(tmp_path):
    """Run a generated script with real bash. tenant/ holds binaries a tenant
    could have uploaded; host-bin/ holds a stand-in apptainer that records
    what it was handed."""
    import subprocess

    tenant = tmp_path / "tenant"
    tenant.mkdir()
    marker = tmp_path / "TENANT_BINARY_RAN"
    for tool in ("date", "hostname", "apptainer"):
        fake = tenant / tool
        # Shell builtins only: under the tenant PATH no other tool resolves.
        fake.write_text(f"#!/bin/sh\n: > {marker}\n")
        fake.chmod(0o755)
    host_bin = tmp_path / "host-bin"
    host_bin.mkdir()
    handoff = tmp_path / "handoff.txt"
    stand_in = host_bin / "apptainer"
    stand_in.write_text(f'#!/bin/sh\nprintf "%s" "$APPTAINERENV_PATH" > {handoff}\n')
    stand_in.chmod(0o755)

    def _run(script: str):
        path = tmp_path / "job.sh"
        path.write_text(script)
        env = {"PATH": f"{host_bin}:/usr/bin:/bin", "HOME": str(tmp_path)}
        subprocess.run(
            ["bash", str(path)], env=env, capture_output=True, text=True, check=False
        )
        return marker, handoff

    return _run


def test_tenant_path_does_not_choose_host_binaries(tmp_path, run_script):
    # Arrange
    script = _script(tmp_path, env_vars={"PATH": str(tmp_path / "tenant")})
    # Act
    marker, _handoff = run_script(script)
    # Assert
    assert not marker.exists()


def test_tenant_path_is_delivered_to_apptainer(tmp_path, run_script):
    # Arrange
    tenant = str(tmp_path / "tenant")
    script = _script(tmp_path, env_vars={"PATH": tenant})
    # Act
    _marker, handoff = run_script(script)
    # Assert
    assert handoff.read_text() == tenant
