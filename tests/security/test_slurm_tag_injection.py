"""Regression: SLURM attribution tags cannot inject directives or options.

The project and session tags land in ``#SBATCH --comment/--wckey`` lines and
in ``sbatch``/``srun`` argv. SLURM parses those values, so shell quoting
cannot neutralise them (CWE-78): anything but a positive int project id or a
canonical UUID session is rejected, and ``create_batch_script`` only accepts
a validated ``SlurmTags``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.workspace.console_app.services.slurm.script_generator import (
    create_batch_script,
)
from apps.workspace.console_app.services.slurm.tags import NO_PROJECT, SlurmTags

pytestmark = pytest.mark.security

SESSION = "0f8fad5b-d9cb-469f-a165-70867728950e"


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
        tags=SlurmTags.for_project(42, session_id=SESSION),
    )
    kwargs.update(overrides)
    return create_batch_script(**kwargs)


@pytest.mark.parametrize(
    "payload",
    [
        "42",  # a string, even of digits: ints only
        "42\n#SBATCH --uid=0",
        "42 --uid=0",
        "$(id)",
        "none",  # the token is not the sentinel
        0,
        -1,
        True,  # bool is an int subclass
        4.0,
        10**19,  # beyond bigint
    ],
)
def test_project_id_other_than_positive_int_is_rejected(payload):
    # Arrange
    # Act
    # Assert
    with pytest.raises(ValueError):
        SlurmTags.for_project(payload)


@pytest.mark.parametrize(
    "payload",
    [
        f"{SESSION}\n#SBATCH --uid=0",
        f"{SESSION},project:1",
        "{" + SESSION + "}",
        "urn:uuid:" + SESSION,
        SESSION.upper(),
        "$(id)",
    ],
)
def test_session_other_than_canonical_uuid_is_rejected(payload):
    # Arrange
    # Act
    # Assert
    with pytest.raises(ValueError):
        SlurmTags.for_project(1, session_id=payload)


def test_batch_script_carries_comment_and_wckey(tmp_path):
    # Arrange
    expected = [
        f"#SBATCH --comment=project:42,session:{SESSION}",
        "#SBATCH --wckey=p42",
        "#SBATCH --account=user_100",
    ]
    # Act
    lines = _script(tmp_path).splitlines()
    # Assert
    assert set(expected) <= set(lines)


def test_batch_script_without_project_is_tagged_none(tmp_path):
    # Arrange
    tags = SlurmTags.for_project(NO_PROJECT, session_id=SESSION)
    # Act
    lines = _script(tmp_path, tags=tags).splitlines()
    # Assert
    assert "#SBATCH --wckey=pnone" in lines


def test_batch_script_rejects_unvalidated_tags(tmp_path):
    # Arrange
    forged = type("Forged", (), {"directives": lambda self: "#SBATCH --uid=0"})()
    # Act
    # Assert
    with pytest.raises(ValueError):
        _script(tmp_path, tags=forged)


def test_batch_script_rejects_non_numeric_user_id(tmp_path):
    # Arrange
    payload = "100\n#SBATCH --uid=0"
    # Act
    # Assert
    with pytest.raises(ValueError):
        _script(tmp_path, user_id=payload)


def test_every_directive_line_is_well_formed(tmp_path):
    # Arrange
    script = _script(tmp_path)
    # Act
    directives = [ln for ln in script.splitlines() if ln.startswith("#SBATCH")]
    # Assert
    assert all(len(ln.split()) == 2 for ln in directives)
