"""Bind shipped docs to their source version and actual read-only help routes."""

import json
import os
import re
import runpy
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_sphinx_import_root_does_not_depend_on_invocation_directory(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", list(sys.path))
    runpy.run_path(str(ROOT / "docs/sphinx/conf.py"))
    assert sys.path[0] == str(ROOT / "src")


def test_shipped_documentation_identifies_its_declared_package_version():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    options = (
        ROOT / "src/scitex_hub/_sphinx_html/_static/documentation_options.js"
    ).read_text()
    observed = re.search(r"\bVERSION:\s*(['\"])([^'\"]+)\1", options)
    assert observed is not None
    assert observed.group(2) == version
    index = (ROOT / "src/scitex_hub/_sphinx_html/index.html").read_text()
    assert f"SciTeX Hub v{version}" in index
    assert "https://github.com/scitex-ai/scitex-hub/" in index
    assert not (ROOT / "src/scitex_hub/_sphinx_html/.doctrees").exists()


@pytest.mark.parametrize(
    "route",
    [[], ["project"], ["workspace"], ["dev"], ["app"], ["mcp"], ["skills"]],
)
def test_documented_help_routes_parse_without_remote_operations(tmp_path, route):
    code = r"""
import json, sys
def refuse(event, arguments):
    if event in ("socket.connect", "socket.connect_ex", "subprocess.Popen"):
        raise RuntimeError("Documentation help must remain offline")
sys.addaudithook(refuse)
for event in ("socket.connect", "subprocess.Popen"):
    try:
        sys.audit(event, None, None)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Documentation guard inactive")
from click.testing import CliRunner
from scitex_hub._cli.main import main
result = CliRunner().invoke(main, json.loads(sys.argv[1]) + ["--help"])
assert result.exit_code == 0, result.output
assert "Usage:" in result.output and "Options:" in result.output
print(json.dumps({"exit": result.exit_code, "help": result.output}))
"""
    environment = {
        "PATH": os.defpath,
        "LANG": "C.UTF-8",
        "HOME": str(tmp_path),
        "SCITEX_DIR": str(tmp_path / "state"),
        "PYTHONPATH": str(ROOT / "src"),
    }
    result = subprocess.run(
        [sys.executable, "-c", code, json.dumps(route)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["exit"] == 0
