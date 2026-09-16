#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The dev site check after a rebuild polls the port compose PUBLISHED, not a literal.

WHAT WENT WRONG (2026-09-05, measured on scitex-compute-03; card
hub-rebuild-dev-verify-url-hardcodes-31295-20260905)
``scripts/deploy/rebuild.sh`` step 7c chose the dev verify URL with a literal::

    dev)     VERIFY_URL="http://127.0.0.1:31295/" ;;

31295 is the port of the NAS *preview* compose recipe. The dev compose on the
host publishes django on ``127.0.0.1:${SCITEX_HUB_HTTP_PORT_DEV:-8000}`` and
that host's ``.env`` says 8000. So a rebuild whose image passed the sibling
preflight, whose containers all reported healthy and whose tunnel answered 200
the whole time ended with "❌ Site NOT answering after 8 min (last code:
000000)" — eight minutes of connection-refused against a port nothing listened
on, then a failed exit code for a deploy that had succeeded.

THE FIX asks compose what it actually published (``$COMPOSE_CMD port django
8000``). That answer cannot drift from the compose file or the host's env, and
an EMPTY answer is reported as a failed check ("site check impossible"), never
downgraded to "no URL, skipped" — constitution §2, a gate must be able to fail
for the right reason and must not fail for the wrong one.

WHAT EACH TEST IS FOR
  the_dev_branch_is_not_a_literal_loopback_port
      the shape that shipped the incident is gone from the script.
  the_dev_branch_asks_compose_for_the_published_port
      the replacement is a question to compose, not a different literal.
  the_checker_rejects_the_pre_fix_line
      the detector used above goes red on the real pre-fix line, so the
      first test cannot pass vacuously.
  the_case_block_resolves_the_url_compose_published
      the ACTUAL shell block, run by bash against a stand-in compose that
      answers "127.0.0.1:8000", yields http://127.0.0.1:8000/.
  the_case_block_reports_nothing_published_as_an_error
      the same block against a compose that answers nothing leaves the URL
      empty and names the error.
  an_underivable_url_fails_the_check
      the ACTUAL verify block, given an empty URL plus that error, sets
      VERIFY_FAILED=1 rather than printing "SKIPPED".
  the_script_still_parses
      ``bash -n`` on the edited script.

No Docker required: the shell blocks are extracted from the script and run
with a stand-in ``compose`` executable, so this runs in the headless matrix.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REBUILD_SH = REPO_ROOT / "scripts" / "deploy" / "rebuild.sh"

# The exact line that shipped the incident, kept verbatim so the detector is
# proven against a real defect rather than a strawman.
PRE_FIX_LINE = '    dev)     VERIFY_URL="http://127.0.0.1:31295/" ;;'

_LITERAL_DEV_PORT = re.compile(r'^\s*dev\)\s*VERIFY_URL="http://127\.0\.0\.1:\d+/"', re.MULTILINE)


def _has_literal_dev_port(script: str) -> bool:
    """True when the dev branch assigns a literal loopback URL."""
    return _LITERAL_DEV_PORT.search(script) is not None


def _case_block(script: str) -> str:
    """The `case "$ENV" in … esac` block that chooses VERIFY_URL, verbatim."""
    start = script.index('VERIFY_URL_ERROR=""')
    end = script.index("\nesac\n", start) + len("\nesac\n")
    return script[start:end]


def _verify_block(script: str) -> str:
    """The `if [ -n "$VERIFY_URL" ]; then … fi` block (column-0 `fi` closes it)."""
    start = script.index('if [ -n "$VERIFY_URL" ]; then')
    end = script.index("\nfi\n", start) + len("\nfi\n")
    return script[start:end]


def _fake_compose(tmp_path: Path, answer: str) -> Path:
    """A stand-in `compose` executable that answers `port django 8000` with `answer`."""
    exe = tmp_path / "compose"
    exe.write_text(
        "#!/bin/bash\n"
        'if [ "$1 $2 $3" = "port django 8000" ]; then\n'
        f'    printf "%s" "{answer}"\n'
        "fi\n"
    )
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    return exe


def _run_block(block: str, env: dict[str, str], *, then_print: str) -> str:
    """Run a shell block under bash with `env` pre-set and print `then_print`."""
    preamble = "".join(f'{key}="{value}"\n' for key, value in env.items())
    script = preamble + block + f'\nprintf "%s" "{then_print}"\n'
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
        env={"PATH": os.environ["PATH"]},
    )
    return result.stdout


def test_the_dev_branch_is_not_a_literal_loopback_port() -> None:
    # Arrange
    script = REBUILD_SH.read_text()
    # Act
    literal = _has_literal_dev_port(script)
    # Assert
    assert literal is False


def test_the_dev_branch_asks_compose_for_the_published_port() -> None:
    # Arrange
    block = _case_block(REBUILD_SH.read_text())
    # Act
    asks_compose = "$COMPOSE_CMD port django 8000" in block
    # Assert
    assert asks_compose is True, block


def test_the_checker_rejects_the_pre_fix_line() -> None:
    # Arrange — the real pre-fix arrangement, not a strawman.
    pre_fix = 'case "$ENV" in\n' + PRE_FIX_LINE + "\nesac\n"
    # Act
    literal = _has_literal_dev_port(pre_fix)
    # Assert
    assert literal is True


def test_the_case_block_resolves_the_url_compose_published(tmp_path: Path) -> None:
    # Arrange — a compose that published django on 127.0.0.1:8000.
    compose = _fake_compose(tmp_path, "127.0.0.1:8000")
    block = _case_block(REBUILD_SH.read_text())
    # Act
    url = _run_block(block, {"ENV": "dev", "COMPOSE_CMD": str(compose)}, then_print="$VERIFY_URL")
    # Assert
    assert url == "http://127.0.0.1:8000/"


def test_the_case_block_reports_nothing_published_as_an_error(tmp_path: Path) -> None:
    # Arrange — a compose that published no host port for django:8000.
    compose = _fake_compose(tmp_path, "")
    block = _case_block(REBUILD_SH.read_text())
    # Act
    outcome = _run_block(
        block,
        {"ENV": "dev", "COMPOSE_CMD": str(compose)},
        then_print='url=[$VERIFY_URL] error_set=${VERIFY_URL_ERROR:+yes}',
    )
    # Assert
    assert outcome == "url=[] error_set=yes"


def test_an_underivable_url_fails_the_check() -> None:
    # Arrange — the verify block, entered with no URL but a stated reason.
    block = _verify_block(REBUILD_SH.read_text())
    # Act
    failed = _run_block(
        block,
        {"ENV": "dev", "VERIFY_URL": "", "VERIFY_URL_ERROR": "nothing published", "VERIFY_FAILED": "0"},
        then_print="$VERIFY_FAILED",
    )
    # Assert
    assert failed == "1"


def test_the_script_still_parses() -> None:
    # Arrange
    argv = ["bash", "-n", str(REBUILD_SH)]
    # Act
    result = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    # Assert
    assert result.returncode == 0, result.stderr
