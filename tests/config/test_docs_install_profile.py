"""Execute the docs install step using inert local installer processes."""

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / ".github/workflows/rtd-sphinx-build-on-ubuntu-latest.yml"
)


@pytest.mark.parametrize("status", [0, 17])
def test_docs_install_failure_cannot_qualify_a_reduced_profile(tmp_path, status):
    # Arrange
    steps = yaml.safe_load(WORKFLOW.read_text())["jobs"]["sphinx"]["steps"]
    script = next(
        s["run"] for s in steps if s.get("name") == "Install package + docs deps"
    )
    directory = tmp_path / "bin"
    directory.mkdir()
    installer = directory / "uv"
    installer.write_text(
        "#!/usr/bin/env python3\n"
        "import json,os,sys\n"
        "with open(os.environ['CALLS'],'a') as stream:\n"
        " stream.write(json.dumps(sys.argv[1:])+'\\n')\n"
        "raise SystemExit(int(os.environ['INSTALL_EXIT']) if '.[all]' in sys.argv else 0)\n"
    )
    installer.chmod(0o700)
    calls = tmp_path / "calls.jsonl"
    next_path = tmp_path / "github-path"
    environment = {
        "PATH": str(directory) + os.pathsep + os.defpath,
        "CALLS": str(calls),
        "INSTALL_EXIT": str(status),
        "GITHUB_PATH": str(next_path),
    }
    # Act
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", script],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    installs = [
        args
        for args in map(json.loads, calls.read_text().splitlines())
        if args[:2] == ["pip", "install"]
    ]
    # Assert
    assert (result.returncode, installs, next_path.exists()) == (
        status,
        [["pip", "install", "--python", ".venv/bin/python", "-e", ".[all]"]],
        status == 0,
    )
