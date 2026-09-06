#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`networkidle` must not come back to tests/e2e/playwright/.

WHY THIS GUARD EXISTS, AND WHY A COMMENT WAS NOT ENOUGH.

The defect this protects against has now been diagnosed twice, correctly
both times, and came back anyway:

    2026-08-16  CI run 31955719803. `wait_for_load_state("networkidle")` on
                /apps/home/ timed out at 30s and took the screenshot capture
                down with 33 errors. Diagnosed exactly. The fix shipped as
                tests/e2e/playwright/page_ready.py, whose docstring explains
                in full why this product can never reach networkidle.

    2026-09-06  job 101449817274. Same exception, same cause, in
                conftest.py's visitor_storage_state. 14/14 mobile tests
                ERRORED in fixture setup -- not one assertion in the mobile
                suite had ever been evaluated.

Between those two dates the correct fix existed IN THIS REPOSITORY and was
adopted by exactly one caller (pooled_visitor_page, in the same conftest.py
as the fixture that kept the bug). A written explanation does not propagate
itself. This test does.

WHY `networkidle` CANNOT WORK HERE, in one line: it means "500 ms with no
requests in flight", and a pooled visitor session polls a heartbeat for as
long as the page is open, so the condition never arrives.

WHY THIS PARSES THE AST INSTEAD OF GREPPING FOR THE WORD. The prose that
explains the ban necessarily quotes the banned call -- page_ready.py's
docstring does, and so do the comments this guard's own fix added. A text
scan would flag the documentation and force it to be written obscurely to
appease the checker. Walking real Call nodes matches code and only code.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

E2E_DIR = (
    pathlib.Path(__file__).resolve().parents[2]
    / "tests"
    / "e2e"
    / "playwright"
)

#: Below this, assume the scan itself broke rather than that the tree is clean.
#: A guard whose population silently goes to zero returns the pass answer.
MIN_FILES_SCANNED = 5


def _networkidle_calls(tree: ast.AST) -> list[int]:
    """Line numbers of real calls that wait for networkidle."""
    hits: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # page.wait_for_load_state("networkidle")
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "wait_for_load_state":
            for arg in node.args:
                if isinstance(arg, ast.Constant) and arg.value == "networkidle":
                    hits.append(node.lineno)
        # page.goto(url, wait_until="networkidle") / page.reload(wait_until=...)
        for kw in node.keywords:
            if (
                kw.arg == "wait_until"
                and isinstance(kw.value, ast.Constant)
                and kw.value.value == "networkidle"
            ):
                hits.append(node.lineno)
    return hits


def _python_files() -> list[pathlib.Path]:
    return sorted(p for p in E2E_DIR.rglob("*.py"))


class TestNetworkidleStaysOut:
    def test_the_scan_can_actually_see_the_pattern(self):
        # Arrange -- a POSITIVE CONTROL. Without it, a detector that silently
        # stopped matching (a renamed method, an ast API change) would return
        # "clean" for a dirty tree, which is the exact shape of the CI failure
        # this whole card is about: a check that reports success while
        # measuring nothing.
        sample = (
            "def f(page):\n"
            "    page.wait_for_load_state('networkidle')\n"
            "    page.goto('/', wait_until='networkidle')\n"
        )
        # Act
        hits = _networkidle_calls(ast.parse(sample))
        # Assert
        assert hits == [2, 3], (
            "the detector failed to find networkidle calls in a sample that "
            f"provably contains two; got {hits}. Every clean result below is "
            "meaningless until this passes."
        )

    def test_the_scan_does_not_flag_prose_that_explains_the_ban(self):
        # Arrange -- the NEGATIVE control. page_ready.py's docstring quotes
        # the banned call while explaining why it is banned; so do the
        # comments in conftest.py. A guard that flagged those would push the
        # explanation out of the codebase, which is how the knowledge got
        # lost the first time.
        sample = (
            '"""wait_for_load_state("networkidle") threw here once."""\n'
            "# page.wait_for_load_state('networkidle')  <- do not do this\n"
            "def f(page):\n"
            "    page.wait_for_load_state('load')\n"
        )
        # Act
        hits = _networkidle_calls(ast.parse(sample))
        # Assert
        assert hits == [], f"prose and comments must not count as calls; got {hits}"

    def test_the_directory_being_scanned_is_populated(self):
        # Arrange -- tie the verdict to the population. A wrong path, a
        # renamed directory, or a glob typo yields an empty file list, and an
        # empty list passes the real assertion below for free.
        # Act
        files = _python_files()
        # Assert
        assert E2E_DIR.is_dir(), f"{E2E_DIR} is not a directory"
        assert len(files) >= MIN_FILES_SCANNED, (
            f"only {len(files)} python file(s) found under {E2E_DIR}; expected "
            f"at least {MIN_FILES_SCANNED}. The scan below cannot be trusted "
            "-- fix the path before reading its result as 'clean'."
        )

    @pytest.mark.parametrize("path", _python_files(), ids=lambda p: p.name)
    def test_file_does_not_wait_for_networkidle(self, path: pathlib.Path):
        # Arrange -- parametrized per file so a failure names the file in the
        # test id, rather than one aggregate failure listing everything.
        source = path.read_text(encoding="utf-8")
        # Act
        hits = _networkidle_calls(ast.parse(source, filename=str(path)))
        # Assert
        assert not hits, (
            f"{path.name} waits for `networkidle` at line(s) "
            f"{', '.join(str(h) for h in hits)}. A pooled-visitor page polls a "
            "heartbeat forever, so that state never arrives and the wait can "
            "only time out (30s, then the whole file errors at setup). Use "
            "tests/e2e/playwright/page_ready.wait_for_page_ready() instead; "
            "read its docstring first if this looks like a rule without a "
            "reason."
        )


# EOF
