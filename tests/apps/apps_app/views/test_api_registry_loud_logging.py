#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Source-text guards for the ``api_submit_jwt`` loud-failure wrap.

The endpoint ``apps.workspace.apps_app.views.api_registry.api_submit_jwt``
must wrap its body in a ``try / except Exception`` that calls
``logger.exception(...)`` before re-raising. This pattern surfaces the
real traceback in production logs BEFORE DRF's generic-500 handler
converts the response to a no-frame HTML page (or no-traceback DRF
response, depending on ``DEBUG``). It was added in response to the
operator-12834 demo where an indirect paramiko-SSH banner error
produced a 500 with zero usable log frames in ``DEBUG=False`` prod
logs — the silent-failure mode that motivated this PR.

These tests pin the wrap shape with two source-text guards so a future
"cleanup" PR that drops the wrap fails loudly. Same no-mock pattern
as the source-text guards in PR #269 (stale-import) and PR #270
(clone-URL).
"""

from __future__ import annotations

import inspect
from pathlib import Path


def _read_function_source(func) -> str:
    """Read the on-disk source of a module-level function (no mocks)."""
    src_path = Path(inspect.getsourcefile(func))
    return src_path.read_text()


def test_api_submit_jwt_body_is_wrapped_in_try_except_logger_exception():
    # Arrange
    from apps.workspace.apps_app.views.api_registry import api_submit_jwt

    src = inspect.getsource(api_submit_jwt)

    # Act
    has_try_block = "    try:" in src
    has_except_handler = "    except Exception:" in src
    has_logger_exception = "logger.exception(" in src
    has_reraise = "        raise" in src

    # Assert — all four pieces are the wrap. Dropping any of them
    # reverts the loud-failure semantics: a missing ``except`` lets the
    # exception bubble pre-DRF (re-introducing the silent-500); a
    # missing ``logger.exception`` swallows the traceback; a missing
    # ``raise`` changes the HTTP surface.
    assert has_try_block and has_except_handler and has_logger_exception and has_reraise


def test_api_submit_jwt_logs_at_least_username_and_project_name():
    # Arrange
    from apps.workspace.apps_app.views.api_registry import api_submit_jwt

    src = inspect.getsource(api_submit_jwt)

    # Act
    # The log call must include enough context to correlate a 500 with
    # the offending request: which user and which project_name. Without
    # those the log line is just "an exception happened somewhere".
    log_includes_username = (
        "username" in src.split("logger.exception(")[1].split(")")[0]
    )
    log_includes_project_name = (
        "project_name" in src.split("logger.exception(")[1].split(")")[0]
    )

    # Assert
    assert log_includes_username and log_includes_project_name


# EOF
