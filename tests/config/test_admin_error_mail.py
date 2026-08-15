#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_admin_error_mail.py
"""The operator must be told when hub fails.

Operator request, Telegram 2026-08-10:
「サイテクスハブの ... 失敗っていうのは必ず私にメールが届くようにしてほしいんですよ」

Until 2026-08-15 the ``mail_admins`` handler was DEFINED in
``settings_logging`` and referenced by no logger at all, so hub had never sent
a single admin error email while the config read as though it did. That is the
constitution's own example of a gate that cannot fail: "the config still lists
it and everyone believes it is working."

``test_every_defined_handler_is_attached_to_a_logger`` is the gate that would
have caught it, and it is written to catch the CLASS rather than this one
instance -- any future handler added and never wired fails it too.
"""

from __future__ import annotations

import ast
import importlib.util
import logging
import time
from pathlib import Path

import pytest

SETTINGS_DIR = Path(__file__).resolve().parents[2] / "config" / "settings"


def _load(module_filename: str):
    """Load one settings module WITHOUT importing the ``config`` package.

    ``config/__init__.py`` pulls in celery_app, so a plain
    ``from config.settings... import ...`` drags the whole application import
    graph into a test that only reads a dictionary. Loading by path keeps this
    gate runnable in any environment -- including one where the app's runtime
    dependencies are absent -- which matters because a gate you cannot run is
    a gate that quietly stops running.
    """
    path = SETTINGS_DIR / module_filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LOGGING = _load("settings_logging.py").LOGGING
SuppressRepeatedErrors = _load("_suppress_repeated_errors.py").SuppressRepeatedErrors

# A handler may legitimately have no logger ONLY when its purpose is to be
# referenced by name at runtime. Each entry needs a written reason; this list
# is deliberately not a wildcard, because a blanket exemption would hide every
# future instance of the defect this file exists to prevent.
HANDLERS_ALLOWED_TO_HAVE_NO_LOGGER = {
    # A no-op sink attached on demand to silence a third-party logger.
    "null",
}

# Loggers that carry operational failure. Each must reach the operator.
LOGGERS_THAT_MUST_MAIL_ADMINS = (
    "django.request",
    "django.security",
    "scitex.errors",
    "apps.infra.project_app",
    "apps.workspace.writer_app",
    "apps.workspace.scholar_app",
    "apps.workspace.console_app",
)

def _admins_from_source(source: str) -> list[tuple[str, str]]:
    """Read the ADMINS literal without importing settings_shared.

    settings_shared reads the environment at import time, so evaluating it in
    a test would measure this machine's env rather than the committed value.
    ``ast.literal_eval`` reads exactly what is in the file.
    """
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "ADMINS"
            for target in node.targets
        ):
            return [tuple(entry) for entry in ast.literal_eval(node.value)]
    raise AssertionError(
        "settings_shared defines no ADMINS. The mail_admins handler would be "
        "constructed with the empty default and deliver to nobody."
    )


def _handlers_referenced_by_loggers() -> set[str]:
    referenced: set[str] = set()
    for logger in LOGGING["loggers"].values():
        referenced.update(logger.get("handlers", []))
    root = LOGGING.get("root")
    if root:
        referenced.update(root.get("handlers", []))
    return referenced


def _error_record(message: str, name: str = "django.request") -> logging.LogRecord:
    return logging.LogRecord(
        name=name,
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )


class TestHandlersAreActuallyWired:
    def test_every_defined_handler_is_attached_to_a_logger(self):
        # Arrange
        defined = set(LOGGING["handlers"])
        # Act
        orphaned = defined - _handlers_referenced_by_loggers()
        orphaned -= HANDLERS_ALLOWED_TO_HAVE_NO_LOGGER
        # Assert
        assert not orphaned, (
            "These handlers are defined in settings_logging and referenced by "
            f"no logger, so they never run: {sorted(orphaned)}. A handler that "
            "is configured but unattached reads as a working safety mechanism "
            "to anyone who greps for it while doing nothing at all. Either "
            "attach it to the loggers it is meant to serve, or delete it. If "
            "it genuinely has no logger by design, add it to "
            "HANDLERS_ALLOWED_TO_HAVE_NO_LOGGER with the reason."
        )

    @pytest.mark.parametrize("logger_name", LOGGERS_THAT_MUST_MAIL_ADMINS)
    def test_failure_carrying_loggers_reach_the_operator(self, logger_name):
        # Arrange
        logger = LOGGING["loggers"][logger_name]
        # Act
        handlers = logger.get("handlers", [])
        # Assert
        assert "mail_admins" in handlers, (
            f"logger {logger_name!r} carries operational failures but does not "
            "attach 'mail_admins', so its errors reach a rotating log file and "
            "nobody else. This is how the visitor pool sat 14/16 quarantined "
            "for four days in August 2026."
        )

    def test_mail_admins_suppresses_repeated_errors(self):
        # Arrange
        handler = LOGGING["handlers"]["mail_admins"]
        # Act
        filters = handler["filters"]
        # Assert
        assert "suppress_repeated_errors" in filters, (
            "mail_admins has no repeat suppression. AdminEmailHandler has no "
            "throttle of its own, so one crash-looping view delivers hundreds "
            "of identical emails and the operator mutes the channel -- the "
            "same outcome as sending nothing."
        )

    def test_mail_admins_stays_off_developer_machines(self):
        # Arrange
        handler = LOGGING["handlers"]["mail_admins"]
        # Act
        filters = handler["filters"]
        # Assert
        assert "require_debug_false" in filters

    def test_the_suppressor_dotted_path_resolves_to_a_real_class(self):
        """Django resolves this filter by STRING at startup, not by import."""
        # Arrange
        dotted = LOGGING["filters"]["suppress_repeated_errors"]["()"]
        module_path, class_name = dotted.rsplit(".", 1)
        source = SETTINGS_DIR / f"{module_path.rsplit('.', 1)[1]}.py"
        # Act
        defines_it = source.is_file() and f"class {class_name}" in source.read_text()
        # Assert
        assert defines_it, (
            f"settings_logging names {dotted!r} as a filter, but no such class "
            f"was found at {source}. Django resolves this string at startup, so "
            "a rename that misses it does not fail here -- it fails when the "
            "first error tries to reach the operator, which is the worst "
            "possible moment to discover it."
        )


class TestAdminsAreRealRecipients:
    def test_admins_has_at_least_one_recipient(self):
        # Arrange
        shared_source = (SETTINGS_DIR / "settings_shared.py").read_text()
        # Act
        admins = _admins_from_source(shared_source)
        # Assert
        assert admins, (
            "ADMINS is empty, so AdminEmailHandler builds a message and sends "
            "it to nobody. An error-mail rail with no recipients fails exactly "
            "like one that is not configured, but looks configured."
        )

    def test_every_admin_entry_carries_an_address(self):
        # Arrange
        shared_source = (SETTINGS_DIR / "settings_shared.py").read_text()
        # Act
        addresses = [address for _name, address in _admins_from_source(shared_source)]
        # Assert
        assert all("@" in address for address in addresses)

    def test_admins_is_defined_in_exactly_one_settings_module(self):
        # Arrange
        modules = sorted(SETTINGS_DIR.glob("settings_*.py"))
        # Act
        definers = [
            path.name
            for path in modules
            if any(
                line.startswith("ADMINS") for line in path.read_text().splitlines()
            )
        ]
        # Assert
        assert definers == ["settings_shared.py"], (
            "ADMINS must be defined only in settings_shared. Found it in "
            f"{definers}. Defining it per environment is how staging ended up "
            "constructing the handler with the empty default."
        )


class TestSuppressRepeatedErrors:
    """The throttle itself -- pure Python, no Django needed."""

    def test_the_first_occurrence_is_delivered(self):
        # Arrange
        suppressor = SuppressRepeatedErrors()
        # Act
        delivered = suppressor.filter(_error_record("boom"))
        # Assert
        assert delivered is True

    def test_repeats_of_the_same_error_are_dropped(self):
        # Arrange
        suppressor = SuppressRepeatedErrors()
        # Act
        verdicts = [suppressor.filter(_error_record("boom")) for _ in range(5)]
        # Assert
        assert verdicts == [True, False, False, False, False]

    def test_a_different_error_is_never_suppressed(self):
        # Arrange
        suppressor = SuppressRepeatedErrors()
        suppressor.filter(_error_record("boom"))
        # Act
        delivered = suppressor.filter(_error_record("a different failure"))
        # Assert
        assert delivered is True

    def test_the_same_message_from_another_logger_is_delivered(self):
        # Arrange
        suppressor = SuppressRepeatedErrors()
        suppressor.filter(_error_record("boom", name="django.request"))
        # Act
        delivered = suppressor.filter(_error_record("boom", name="scitex.errors"))
        # Assert
        assert delivered is True

    def test_the_suppressed_count_is_reported_in_the_next_message(self):
        # Arrange
        suppressor = SuppressRepeatedErrors(window_seconds=0.05)
        suppressor.filter(_error_record("boom"))
        for _ in range(3):
            suppressor.filter(_error_record("boom"))
        time.sleep(0.06)
        # Act
        record = _error_record("boom")
        suppressor.filter(record)
        # Assert
        assert "3 identical message(s) were suppressed" in record.getMessage(), (
            "the next message must say how many repeats were dropped, or the "
            "throttle hides the scale of an incident"
        )

    def test_the_window_reopens_once_it_has_elapsed(self):
        # Arrange
        suppressor = SuppressRepeatedErrors(window_seconds=0.05)
        suppressor.filter(_error_record("boom"))
        time.sleep(0.06)
        # Act
        delivered = suppressor.filter(_error_record("boom"))
        # Assert
        assert delivered is True

    def test_a_window_that_could_suppress_nothing_is_refused(self):
        # Arrange
        window_that_suppresses_nothing = 0
        # Act
        construct = lambda: SuppressRepeatedErrors(  # noqa: E731
            window_seconds=window_that_suppresses_nothing
        )
        # Assert
        with pytest.raises(ValueError, match="window must be positive"):
            construct()


# EOF
