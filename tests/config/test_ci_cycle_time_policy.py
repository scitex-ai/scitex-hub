"""Policy tests for the required, fail-closed CI fan-out."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/pytest-matrix-on-ubuntu-py3-11-3-12-3-13.yml"
SCRIPT = ROOT / "scripts/ci/pytest_shards.py"
MATRIX_SCRIPT = ROOT / "scripts/ci/python_matrix.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("pytest_shards", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def _workflow():
    return yaml.safe_load(WORKFLOW.read_text())


def _load_matrix_script():
    spec = importlib.util.spec_from_file_location("python_matrix", MATRIX_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_complete_gate(workflow: dict) -> None:
    jobs = workflow["jobs"]
    shard = jobs["test"]
    matrix = shard["strategy"]["matrix"]
    assert "select-python-versions.outputs.versions" in str(matrix["python-version"])
    assert matrix["shard"] == [0, 1, 2]
    assert shard["strategy"]["fail-fast"] is False
    assert "pytest_shards.py" in str(shard["steps"])
    assert "PYTEST_XDIST_WORKERS" not in str(shard)
    assert "--cpus" not in str(shard["container"]["options"])
    assert "nice -n 10 ionice -c 2 -n 7" in str(shard["steps"])
    gate = jobs["ci-gate"]
    assert gate["if"] == "always()"
    assert gate["needs"] == ["select-python-versions", "test"]
    command = str(gate["steps"])
    assert '!= "success"' in command


def test_workflow_has_nine_shards_and_a_fail_closed_gate():
    assert_complete_gate(_workflow())


def test_policy_negative_control_rejects_a_missing_python_version():
    broken = _workflow()
    broken["jobs"]["test"]["strategy"]["matrix"]["python-version"] = ["3.12"]
    with pytest.raises(AssertionError):
        assert_complete_gate(broken)


def test_policy_negative_control_rejects_a_skipped_shard_result():
    broken = _workflow()
    broken["jobs"]["ci-gate"]["steps"][0]["run"] = 'test "$RESULT" != "failure"'
    with pytest.raises(AssertionError):
        assert_complete_gate(broken)


@pytest.mark.parametrize(
    ("event", "base", "expected"),
    [
        ("pull_request", "develop", ["3.11"]),
        ("pull_request", "main", ["3.11", "3.12", "3.13"]),
        ("pull_request", "release/v0.20.0-alpha", ["3.11", "3.12", "3.13"]),
        ("schedule", "", ["3.11", "3.12", "3.13"]),
        ("workflow_dispatch", "", ["3.11", "3.12", "3.13"]),
        ("push", "develop", ["3.11", "3.12", "3.13"]),
    ],
)
def test_python_matrix_event_and_base_policy(event, base, expected):
    assert _load_matrix_script().versions_for(event, base) == expected


def test_file_groups_are_complete_disjoint_and_balanced(tmp_path):
    module = _load_script()
    files = []
    for index, count in enumerate((9, 8, 7, 6, 5, 4, 3)):
        path = tmp_path / f"test_{index}.py"
        path.write_text("\n".join(f"def test_{n}(): pass" for n in range(count)))
        files.append(path)
    groups = module.group_files(files, 3)
    flattened = [path for group in groups for path in group]
    assert sorted(flattened) == sorted(files)
    assert len(flattened) == len(set(flattened))
    weights = [sum(module.test_weight(path) for path in group) for group in groups]
    assert max(weights) - min(weights) <= max(module.test_weight(path) for path in files)


def test_effective_cpu_count_uses_the_tightest_real_limit(monkeypatch):
    module = _load_script()
    monkeypatch.setattr(module.os, "cpu_count", lambda: 64)
    monkeypatch.setattr(module.os, "sched_getaffinity", lambda _pid: set(range(12)))
    monkeypatch.setattr(module, "cgroup_cpu_limit", lambda: 6)
    assert module.effective_cpu_count() == 6
