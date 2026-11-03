"""A final normal resolution must repair incompatible cached installations."""

import base64
import csv
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/deploy/installed_runtime_roots.py"
SPEC = importlib.util.spec_from_file_location("owned_runtime_roots", SCRIPT)
COLLECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLECTOR)


@pytest.mark.parametrize(
    "name", ["", "bad\npackage", "project @ https://example.org", None]
)
def test_metadata_cannot_inject_requirement_lines_or_urls(name):
    with pytest.raises(ValueError):
        COLLECTOR.installed_names([SimpleNamespace(metadata={"Name": name})])


def wheel(directory, name, version, requires=()):
    module = name.replace("-", "_")
    info = f"{module}-{version}.dist-info"
    members = {
        f"{module}/__init__.py": b"",
        f"{info}/METADATA": (
            f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
            + "".join(f"Requires-Dist: {requirement}\n" for requirement in requires)
        ).encode(),
        f"{info}/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    }
    record = io.StringIO()
    rows = csv.writer(record)
    for path, content in members.items():
        digest = (
            base64.urlsafe_b64encode(hashlib.sha256(content).digest())
            .decode()
            .rstrip("=")
        )
        rows.writerow((path, f"sha256={digest}", len(content)))
    rows.writerow((f"{info}/RECORD", "", ""))
    members[f"{info}/RECORD"] = record.getvalue().encode()
    with zipfile.ZipFile(
        directory / f"{module}-{version}-py3-none-any.whl", "w"
    ) as archive:
        for path, content in members.items():
            archive.writestr(path, content)


def test_one_normal_resolution_repairs_a_real_incompatible_cached_graph(tmp_path):
    uv = shutil.which("uv")
    assert uv, "The deployment integration runner requires its normal uv tool"
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir()
    wheel(wheelhouse, "runtime-graph-dependency", "1.0")
    wheel(wheelhouse, "runtime-graph-dependency", "2.0")
    wheel(wheelhouse, "runtime-graph-holder", "1.0", ["runtime-graph-dependency<2"])
    environment = tmp_path / "env"

    def run(*args, check=True):
        return subprocess.run(
            args, cwd=tmp_path, capture_output=True, text=True, check=check
        )

    run(uv, "venv", "--python", sys.executable, str(environment))
    python = str(environment / "bin/python")
    install = [
        uv,
        "pip",
        "install",
        "--python",
        python,
        "--no-index",
        "--find-links",
        str(wheelhouse),
    ]
    run(*install, "runtime-graph-holder==1.0")
    # Both are normal dependency-resolving installs, reproducing Docker's
    # separate cache-layer transactions without any --no-deps shortcut.
    run(*install, "runtime-graph-dependency==2.0")
    assert run(uv, "pip", "check", "--python", python, check=False).returncode != 0
    roots = tmp_path / "runtime-roots.in"
    run(python, str(SCRIPT), str(roots))
    assert roots.read_text().splitlines() == [
        "runtime-graph-dependency",
        "runtime-graph-holder",
    ]
    run(*install, "-r", str(roots))
    assert run(uv, "pip", "check", "--python", python).returncode == 0
    result = run(
        python,
        "-c",
        "import importlib.metadata as m,json;print(json.dumps(m.version('runtime-graph-dependency')))",
    )
    assert json.loads(result.stdout) == "1.0"
