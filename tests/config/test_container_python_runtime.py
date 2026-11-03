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
    assert commands.index("sysconfig.get_config_vars()") < commands.index("uv pip install")
    assert 'uv pip install --python .venv/bin/python -e ".[all,dev]"' in commands
    assert "||" not in commands
    assert "exit 1" in commands
