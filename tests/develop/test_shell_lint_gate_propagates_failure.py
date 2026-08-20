"""`make lint-shell` must go red when ShellCheck complains, and when it is missing.

WHAT WENT WRONG. The shell-lint half of ``format-shell`` was structurally
incapable of failing::

    -exec shellcheck --severity=error {} + \\
        2>&1 || echo "$(RED)❌ ShellCheck found errors$(NC)"; \\
    echo -e "$(GREEN)✅ Shell linting complete!$(NC)"; \\

Two independent silencers, either of which alone is fatal: the ``|| echo``
converts ShellCheck's non-zero exit into zero, and the ``echo`` after it is the
last command of the ``if`` branch, so IT supplies the recipe's exit status. Run
against the tree on 2026-08-15 it printed "❌ ShellCheck found errors" and
"✅ Shell linting complete!" back to back and exited 0, over 15 real
error-severity findings. The ``else`` branch was the same defect wearing a
different hat: no shellcheck installed printed "Skipping shell linting..." and
exited 0, so a machine without the linter reported the same green as a machine
that had run it.

WHY THIS TEST IS BEHAVIOURAL. Reading the recipe and asserting on its text is
what let the old shape survive: every individual piece looked reasonable. So this
runs the REAL target with a stub ``shellcheck`` on PATH and asserts on make's
exit status — the only thing a caller or a CI step ever observes. The stub is
what makes it fast and hermetic; the target under test is the shipped one.

ANTI-VACUITY. A stub that is never reached would make every assertion here pass
by testing nothing. So the stub RECORDS each invocation and the argument count,
and the green case asserts the target actually handed it the repo's shell scripts
(see ``MIN_FILES_LINTED``). A guard must measure the work the checked code did.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# The green case must prove real files reached the linter. The tree held 139
# matching scripts when this was written; a floor well below that survives normal
# churn but still catches a find/exclusion mistake that lints nothing.
MIN_FILES_LINTED = 50

SUCCESS_BANNER = "Shell linting complete"

# A stub is enough because the target's contract is "propagate the linter's exit
# status", not "reproduce ShellCheck's analysis".
STUB_TEMPLATE = """#!/bin/bash
printf '%s\\n' "$#" >> {marker}
exit {exit_code}
"""


def _make_path_dir(tmp_path, *, shellcheck_exit_code=None):
    """Build a PATH directory holding `find` and, optionally, a shellcheck stub.

    Returns ``(path_dir, marker_file)``. ``shellcheck_exit_code=None`` produces a
    directory with NO shellcheck at all, which is how the missing-linter case is
    exercised without depending on what the host happens to have installed.

    Only ``find`` is symlinked in: the recipe's other commands (``command -v``,
    ``echo``) are bash builtins, and make invokes ``/bin/bash`` by absolute path.
    """
    path_dir = tmp_path / "bin"
    path_dir.mkdir()

    real_find = shutil.which("find")
    assert real_find, "`find` is not on PATH; the recipe under test cannot run"
    (path_dir / "find").symlink_to(real_find)

    marker = tmp_path / "shellcheck-invocations.txt"
    if shellcheck_exit_code is not None:
        stub = path_dir / "shellcheck"
        stub.write_text(
            STUB_TEMPLATE.format(marker=marker, exit_code=shellcheck_exit_code),
            encoding="utf-8",
        )
        stub.chmod(0o755)
    return path_dir, marker


def _run_lint_shell(path_dir):
    """Run the shipped `make lint-shell` with PATH restricted to `path_dir`."""
    make = shutil.which("make")
    assert make, "`make` is not installed; this gate cannot be verified"

    env = dict(os.environ)
    env["PATH"] = str(path_dir)
    return subprocess.run(
        [make, "--no-print-directory", "lint-shell"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )


def _files_linted(marker):
    """Total argument count across every stub invocation (find batches by size)."""
    if not marker.exists():
        return 0
    return sum(int(line) for line in marker.read_text(encoding="utf-8").split())


@pytest.fixture(scope="module")
def makefile_text():
    makefile = REPO_ROOT / "Makefile"
    assert makefile.is_file(), f"missing Makefile: {makefile}"
    return makefile.read_text(encoding="utf-8")


def test_target_fails_when_shellcheck_reports_a_problem(tmp_path):
    """Red case: a non-zero linter must abort the target, banner unreached."""
    # Arrange
    path_dir, marker = _make_path_dir(tmp_path, shellcheck_exit_code=1)
    # Act
    result = _run_lint_shell(path_dir)
    # Assert
    assert result.returncode != 0, (
        "`make lint-shell` reported success while ShellCheck exited non-zero. "
        "A gate that cannot fail is not a gate.\n%s%s" % (result.stdout, result.stderr)
    )
    assert SUCCESS_BANNER not in result.stdout, (
        "the success banner printed on a failing run: %s" % result.stdout
    )


def test_target_passes_and_actually_lints_when_shellcheck_is_clean(tmp_path):
    """Green case, and the anti-vacuity guard for the red case above."""
    # Arrange
    path_dir, marker = _make_path_dir(tmp_path, shellcheck_exit_code=0)
    # Act
    result = _run_lint_shell(path_dir)
    # Assert
    assert result.returncode == 0, "%s%s" % (result.stdout, result.stderr)
    assert SUCCESS_BANNER in result.stdout
    assert _files_linted(marker) >= MIN_FILES_LINTED, (
        "the target handed only %d files to ShellCheck; the red case above would "
        "pass vacuously" % _files_linted(marker)
    )


def test_target_fails_when_shellcheck_is_not_installed(tmp_path):
    """A missing linter is a FAILED check, not a skipped one.

    Silently skipping is the same defect as ``|| true``: the target reports the
    same green whether or not anything was inspected.
    """
    # Arrange
    path_dir, _marker = _make_path_dir(tmp_path, shellcheck_exit_code=None)
    # Act
    result = _run_lint_shell(path_dir)
    # Assert
    assert result.returncode != 0, (
        "`make lint-shell` reported success with no shellcheck installed.\n%s%s"
        % (result.stdout, result.stderr)
    )
    assert "shellcheck not found" in result.stdout


def test_lint_aggregate_still_runs_the_shell_gate(makefile_text):
    """A correct gate nobody calls is a deleted gate. `make lint` must include it."""
    # Arrange
    prerequisites = [
        line.split(":", 1)[1].split()
        for line in makefile_text.splitlines()
        if line.startswith("lint:")
    ]
    # Act
    wired = any("lint-shell" in prereqs for prereqs in prerequisites)
    # Assert
    assert prerequisites, "no `lint:` target found in the Makefile"
    assert wired, "`lint` does not depend on lint-shell: %s" % prerequisites
