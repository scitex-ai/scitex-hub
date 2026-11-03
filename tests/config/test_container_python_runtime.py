"""Container Python gates must not discover incomplete runner-host interpreters."""

from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/tests.yml"


@pytest.mark.parametrize("job_name", ["terminal-tests", "security-regression"])
def test_container_gate_owns_managed_runtime_before_full_install(job_name):
    job = yaml.safe_load(WORKFLOW.read_text())["jobs"][job_name]
    assert job["container"]["options"] == "--user 1000:1000 --cpus 4 --memory 8g"
    step = next(s for s in job["steps"] if s.get("name") == "Install dependencies")
    assert step["env"]["UV_PYTHON_INSTALL_DIR"] == (
        "${{ runner.temp }}/hub-managed-python-${{ github.job }}"
    )
    commands = step["run"]
    assert "uv venv --managed-python --python 3.11 .venv" in commands
    assert commands.index("sysconfig.get_config_vars()") < commands.index(
        "uv pip install"
    )
    assert 'uv pip install --python .venv/bin/python -e ".[all,dev]"' in commands
    assert "||" not in commands
    assert "exit 1" in commands


def test_required_matrix_owns_a_fresh_seeded_managed_runtime_per_attempt():
    # Arrange: validate the actual required three-version workflow, not only
    # the separate security/terminal jobs that already isolate their runtimes.
    matrix = WORKFLOW.with_name("pytest-matrix-on-ubuntu-py3-11-3-12-3-13.yml")
    job = yaml.safe_load(matrix.read_text())["jobs"]["test"]
    step = next(
        s
        for s in job["steps"]
        if s.get("name", "").startswith("Install dependencies (")
    )
    commands = step["run"]
    # Act
    venv = next(
        line.strip()
        for line in commands.splitlines()
        if line.strip().startswith("uv venv ")
    )
    observed = (
        job["strategy"]["matrix"]["python-version"],
        step["env"]["UV_PYTHON_INSTALL_DIR"],
        venv,
        commands.index("sysconfig.get_config_vars()")
        < commands.index("uv pip install"),
        'uv pip install --python .venv/bin/python -e ".[all,dev]"' in commands,
        "||" in commands,
    )
    # Assert: runtime isolation cannot drop pip seeding or the declared cohort.
    assert observed == (
        ["3.11", "3.12", "3.13"],
        "${{ runner.temp }}/hub-managed-python-${{ github.run_id }}-${{ github.run_attempt }}-${{ github.job }}-${{ matrix.python-version }}",
        "uv venv --seed --managed-python --python ${{ matrix.python-version }} .venv",
        True,
        True,
        False,
    )


@pytest.mark.parametrize(
    "job_name,step_name,version,install_command",
    [
        (
            "test",
            "Install full declared environment",
            "${{ matrix.python-version }}",
            'uv pip install --python $P -e ".[all,dev]"',
        ),
        (
            "build",
            "Install build tools",
            "3.12",
            "uv pip install --python .venv/bin/python build",
        ),
    ],
)
def test_release_gate_owns_its_runtime_and_never_reduces_declared_install(
    job_name, step_name, version, install_command
):
    # Arrange
    release = WORKFLOW.with_name("pypi-publish-and-github-release-on-tag.yml")
    job = yaml.safe_load(release.read_text())["jobs"][job_name]
    step = next(s for s in job["steps"] if s.get("name") == step_name)
    commands = step["run"]
    # Act
    observed = (
        step["env"]["UV_PYTHON_INSTALL_DIR"],
        f"uv venv --seed --managed-python --python {version} .venv" in commands,
        commands.index("sysconfig.get_config_vars()")
        < commands.index("uv pip install"),
        "||" in commands,
        install_command in commands,
    )
    # Assert
    assert observed == (
        "${{ runner.temp }}/hub-managed-python-${{ github.run_id }}-${{ github.run_attempt }}-${{ github.job }}-"
        + version,
        True,
        True,
        False,
        True,
    )


@pytest.mark.parametrize(
    "workflow_name,step_name",
    [
        ("pytest-matrix-on-ubuntu-py3-11-3-12-3-13.yml", "Run tests"),
        ("pypi-publish-and-github-release-on-tag.yml", "Run pytest"),
    ],
)
def test_full_suite_status_store_uses_the_same_disposable_database_as_django(
    workflow_name, step_name
):
    # Arrange
    job = yaml.safe_load(WORKFLOW.with_name(workflow_name).read_text())["jobs"]["test"]
    step = next(s for s in job["steps"] if s.get("name") == step_name)
    env = step["env"]
    database = job["services"]["postgres"]["env"]
    # Act: keep expression-valued service/host routing intact. GitHub resolves
    # these same expressions for Django and the status-ledger client.
    expected = (
        f"postgresql://{database['POSTGRES_USER']}:{database['POSTGRES_PASSWORD']}"
        f"@{env['SCITEX_HUB_DB_HOST_DEV']}:{env['SCITEX_HUB_DB_PORT_DEV']}"
        f"/{database['POSTGRES_DB']}?connect_timeout=5"
    )
    # Assert
    assert env["SCITEX_STORE_DSN"] == expected
