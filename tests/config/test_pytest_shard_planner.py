#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Safety contract for the opt-in pytest shard planner."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PLANNER_PATH = ROOT / "scripts" / "ci" / "pytest_shards.py"
SHARED_WRITER_STATE = Path("tests/integration/writer_shared_state")
SHARED_READER_STATE = Path("tests/integration/reader_shared_state")
REQUIRED_WORKFLOW = (
    ROOT / ".github/workflows/pytest-matrix-on-ubuntu-py3-11-3-12-3-13.yml"
)


def _load_planner():
    spec = importlib.util.spec_from_file_location("pytest_shards", PLANNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _test_file(root: Path, relative: str, test_count: int) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(f"def test_{index}(): pass" for index in range(test_count)) + "\n",
        encoding="utf-8",
    )
    return Path(relative)


def _run_cli(
    repository_root: Path,
    shards: int = 2,
    serial_groups: tuple[tuple[str, Path], ...] = (),
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(PLANNER_PATH),
        "--repo-root",
        str(repository_root),
        "--test-root",
        "tests",
        "--shards",
        str(shards),
    ]
    for name, directory in serial_groups:
        command.extend(("--serial-group", f"{name}={directory.as_posix()}"))
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_declared_cross_file_group_is_one_indivisible_bundle(tmp_path):
    planner = _load_planner()
    grouped_files = {
        _test_file(tmp_path, str(SHARED_WRITER_STATE / "test_writer.py"), 6),
        _test_file(tmp_path, str(SHARED_READER_STATE / "test_reader.py"), 5),
    }
    files = [
        *grouped_files,
        _test_file(tmp_path, "tests/test_heavy.py", 10),
        _test_file(tmp_path, "tests/test_light.py", 1),
    ]
    serial_group = planner.SerialGroup(
        "shared-state",
        (SHARED_WRITER_STATE, SHARED_READER_STATE),
    )

    shards = planner.plan_shards(
        tmp_path,
        files,
        shard_count=2,
        serial_groups=(serial_group,),
    )

    containing = [shard for shard in shards if grouped_files.intersection(shard.files)]
    assert len(containing) == 1
    assert grouped_files.issubset(set(containing[0].files))


def test_cli_manifest_has_total_coverage_without_duplicates(tmp_path):
    expected = {
        str(_test_file(tmp_path, str(SHARED_WRITER_STATE / "test_writer.py"), 3)),
        str(_test_file(tmp_path, str(SHARED_READER_STATE / "test_reader.py"), 2)),
        str(_test_file(tmp_path, "tests/unit/test_alpha.py", 4)),
        str(_test_file(tmp_path, "tests/unit/test_beta.py", 1)),
    }

    result = _run_cli(
        tmp_path,
        serial_groups=(
            ("shared-state", SHARED_WRITER_STATE),
            ("shared-state", SHARED_READER_STATE),
        ),
    )

    assert result.returncode == 0, result.stderr
    manifest = json.loads(result.stdout)
    selected = [path for shard in manifest["shards"] for path in shard["files"]]
    assert set(selected) == expected
    assert len(selected) == len(expected)
    assert all(shard["files"] for shard in manifest["shards"])
    assert manifest["serial_groups"] == [
        {
            "name": "shared-state",
            "directories": [
                SHARED_READER_STATE.as_posix(),
                SHARED_WRITER_STATE.as_posix(),
            ],
        }
    ]


def test_output_is_deterministic_and_balanced(tmp_path):
    _test_file(tmp_path, str(SHARED_WRITER_STATE / "test_writer.py"), 3)
    _test_file(tmp_path, str(SHARED_READER_STATE / "test_reader.py"), 3)
    _test_file(tmp_path, "tests/unit/test_five.py", 5)
    _test_file(tmp_path, "tests/unit/test_four.py", 4)
    _test_file(tmp_path, "tests/unit/test_three.py", 3)

    serial_groups = (
        ("shared-state", SHARED_WRITER_STATE),
        ("shared-state", SHARED_READER_STATE),
    )
    first = _run_cli(tmp_path, serial_groups=serial_groups)
    second = _run_cli(tmp_path, serial_groups=serial_groups)

    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout
    weights = [shard["weight"] for shard in json.loads(first.stdout)["shards"]]
    assert weights == [9, 9]


def test_helper_error_fails_without_partial_manifest(tmp_path):
    broken = tmp_path / SHARED_WRITER_STATE / "test_broken.py"
    broken.parent.mkdir(parents=True)
    broken.write_bytes(b"\xff\xfe")

    result = _run_cli(
        tmp_path,
        shards=1,
        serial_groups=(("shared-state", SHARED_WRITER_STATE),),
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert "pytest shard planning failed" in result.stderr


def test_empty_selection_fails_without_manifest(tmp_path):
    (tmp_path / "tests").mkdir()

    result = _run_cli(tmp_path, shards=1)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "no test files found" in result.stderr


def test_shard_that_would_be_empty_fails_without_manifest(tmp_path):
    _test_file(tmp_path, "tests/unit/test_only.py", 1)

    result = _run_cli(tmp_path, shards=2)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "would leave an empty selection" in result.stderr


def test_stale_serial_directory_fails_without_manifest(tmp_path):
    _test_file(tmp_path, str(SHARED_WRITER_STATE / "test_writer.py"), 1)

    result = _run_cli(
        tmp_path,
        shards=1,
        serial_groups=(
            ("shared-state", SHARED_WRITER_STATE),
            ("shared-state", SHARED_READER_STATE),
        ),
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert "selected no files" in result.stderr


def test_required_matrix_is_not_switched_to_shards_or_unbounded_cpus():
    workflow = yaml.safe_load(REQUIRED_WORKFLOW.read_text(encoding="utf-8"))
    job = workflow["jobs"]["test"]
    run_commands = "\n".join(
        str(step.get("run", "")) for step in job["steps"] if "run" in step
    )
    test_step = next(step for step in job["steps"] if step.get("name") == "Run tests")

    assert job["name"] == "pytest-matrix-on-ubuntu-py${{ matrix.python-version }}"
    assert job["strategy"]["matrix"]["python-version"] == ["3.11", "3.12", "3.13"]
    assert "--cpus 8" in job["container"]["options"]
    assert test_step["env"]["PYTEST_XDIST_WORKERS"] == (
        "${{ job.container.id && '8' || 'auto' }}"
    )
    assert "pytest tests/" in run_commands
    assert "pytest_shards.py" not in run_commands
