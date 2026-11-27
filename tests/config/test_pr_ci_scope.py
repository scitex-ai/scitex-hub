#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_pr_ci_scope.py
"""Pull requests into develop run ONE full suite; everything else runs all three.

WHY THIS EXISTS. On 2026-11-27 pull requests waited one to three hours for the
seven scitex-docker runners: every PR held five of them -- the full suite on
3.11, 3.12 and 3.13, plus terminal-tests and security-regression, which are
subsets of that same suite. The ruling: PRs into develop run the full suite on
3.12 only; 3.11/3.13 run on every push to develop/main, nightly, on dispatch,
in the release gate, and on PRs into main.

What this pins, so the reduction can never silently become a hole:

* the matrix resolves to exactly ["3.12"] for a PR into develop and to all three
  versions for every other event;
* terminal-tests and security-regression skip ONLY for a PR into develop, and the
  summary tolerates that skip ONLY under the same predicate;
* the 3.12 job that replaces them really runs the whole ``tests/`` tree, so both
  directories stay covered (nothing narrows collection: no -m, -k, --ignore or
  --deselect, and neither directory is in ``norecursedirs``).
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
MATRIX_WORKFLOW = WORKFLOWS / "pytest-matrix-on-ubuntu-py3-11-3-12-3-13.yml"
TESTS_WORKFLOW = WORKFLOWS / "tests.yml"

PR_INTO_DEVELOP = "github.event_name == 'pull_request' && github.base_ref == 'develop'"
SKIP_ON_PR_INTO_DEVELOP = "${{ !(" + PR_INTO_DEVELOP + ") }}"
SUBSET_JOBS = {
    "terminal-tests": (
        "tests/apps/console_app/views/terminal/",
        "tests/apps/console_app/services/terminal_broker/",
    ),
    "security-regression": ("tests/security/",),
}
MATRIX_EXPRESSION = re.compile(
    r"\$\{\{ fromJSON\(\((?P<cond>[^)]*)\) && '(?P<yes>\[[^']*\])'"
    r" \|\| '(?P<no>\[[^']*\])'\) \}\}"
)


def _jobs(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["jobs"]


def _summary_script() -> str:
    return _jobs(TESTS_WORKFLOW)["test-summary"]["steps"][0]["run"]


def _full_suite_pytest_line() -> str:
    job = _jobs(MATRIX_WORKFLOW)["test"]
    command = next(s for s in job["steps"] if s.get("name") == "Run tests")["run"]
    return next(line for line in command.splitlines() if "-m pytest" in line)


def test_a_pr_into_develop_runs_only_312_and_every_other_event_runs_all_three():
    # Arrange
    expression = _jobs(MATRIX_WORKFLOW)["test"]["strategy"]["matrix"]["python-version"]
    # Act
    match = MATRIX_EXPRESSION.fullmatch(expression)
    resolved = match and (
        match["cond"],
        json.loads(match["yes"]),
        json.loads(match["no"]),
    )
    # Assert
    assert resolved == (PR_INTO_DEVELOP, ["3.12"], ["3.11", "3.12", "3.13"])


def test_subset_jobs_skip_only_on_a_pr_into_develop():
    # Arrange
    jobs = _jobs(TESTS_WORKFLOW)
    # Act
    observed = {name: jobs[name].get("if") for name in SUBSET_JOBS}
    # Assert
    assert observed == dict.fromkeys(SUBSET_JOBS, SKIP_ON_PR_INTO_DEVELOP)


def test_the_summary_evaluates_the_same_predicate_as_the_skipping_jobs():
    # Arrange
    script = _summary_script()
    # Act
    declared = f'PR_INTO_DEVELOP="${{{{ {PR_INTO_DEVELOP} }}}}"' in script
    # Assert
    assert declared


def test_the_summary_tolerates_a_skip_only_when_the_predicate_holds():
    # Arrange
    script = _summary_script()
    # Act
    guarded = {
        variable: (
            f'! {{ [ "$PR_INTO_DEVELOP" = "true" ] && [ "${variable}" = "skipped" ]; }}'
            in script
        )
        for variable in ("TERMINAL_RESULT", "SECURITY_RESULT")
    }
    # Assert
    assert guarded == {"TERMINAL_RESULT": True, "SECURITY_RESULT": True}


def test_typescript_and_vitest_still_accept_nothing_but_success():
    # Arrange
    script = _summary_script()
    # Act
    strict = [
        f'if [ "${variable}" != "success" ]; then' in script
        for variable in ("TS_RESULT", "TEST_RESULT")
    ]
    # Assert
    assert strict == [True, True]


def test_the_required_312_job_runs_the_whole_tree_without_narrowing():
    # Arrange
    # The interpreter's own "-m pytest" is not a marker filter.
    pytest_line = _full_suite_pytest_line().split("-m pytest", 1)[1]
    # Act
    observed = (
        " tests/ " in pytest_line,
        [f for f in (" -m ", " -k ", "--ignore", "--deselect") if f in pytest_line],
    )
    # Assert
    assert observed == (True, [])


def test_pytest_collection_reaches_every_subset_directory():
    # Arrange
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["pytest"][
        "ini_options"
    ]
    directories = [d for dirs in SUBSET_JOBS.values() for d in dirs]
    # Act
    unreachable = [
        d
        for d in directories
        if any(part in config["norecursedirs"] for part in Path(d).parts)
        or not any((ROOT / d).glob("test_*.py"))
    ]
    # Assert
    assert (config["testpaths"], unreachable) == (["tests"], [])


def test_terminal_tests_have_the_database_their_workload_tests_need():
    # Arrange
    job = _jobs(TESTS_WORKFLOW)["terminal-tests"]
    step = next(s for s in job["steps"] if s.get("name") == "Run terminal tests")
    # Act
    observed = (
        job["services"]["postgres"]["image"],
        step["env"]["SCITEX_HUB_DB_HOST_DEV"],
        step["env"]["SCITEX_HUB_DB_NAME_DEV"]
        == job["services"]["postgres"]["env"]["POSTGRES_DB"],
    )
    # Assert
    assert observed == (
        "postgres:16",
        "${{ job.container.id && 'postgres' || 'localhost' }}",
        True,
    )
