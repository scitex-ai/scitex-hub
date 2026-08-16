#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_repeated_error_throttle.py
"""The repeat throttle behind the admin-mail rail, on its own.

``RepeatThrottle`` decides whether an error is the first of its kind in the
current window. It is pure Python with no Django in it, so it is exercised
here rather than in ``tests/config/test_admin_error_mail.py``, which is about
the rail: the configuration, the recipients, and a real ERROR arriving in a
real outbox.

Two of these tests are regressions for defects measured on 2026-08-15 in the
first version of the module: a prune that never reclaimed a key that had ever
suppressed a repeat (its own docstring promised the opposite), and a window
renderer that printed "0 seconds" for any sub-second window.
"""

from __future__ import annotations

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
    graph into a test that only exercises a dictionary and a lock.
    """
    path = SETTINGS_DIR / module_filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_throttle_module = _load("_suppress_repeated_errors.py")
RepeatThrottle = _throttle_module.RepeatThrottle
format_window = _throttle_module._format_window


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


class TestRepeatThrottle:
    def test_the_first_occurrence_is_delivered(self):
        # Arrange
        throttle = RepeatThrottle()
        # Act
        suppressed = throttle.consider(_error_record("boom"))
        # Assert
        assert suppressed == 0

    def test_repeats_of_the_same_error_are_dropped(self):
        # Arrange
        throttle = RepeatThrottle()
        # Act
        verdicts = [throttle.consider(_error_record("boom")) for _ in range(5)]
        # Assert
        assert verdicts == [0, None, None, None, None]

    def test_a_different_error_is_never_suppressed(self):
        # Arrange
        throttle = RepeatThrottle()
        throttle.consider(_error_record("boom"))
        # Act
        suppressed = throttle.consider(_error_record("a different failure"))
        # Assert
        assert suppressed == 0

    def test_the_same_message_from_another_logger_is_delivered(self):
        # Arrange
        throttle = RepeatThrottle()
        throttle.consider(_error_record("boom", name="django.request"))
        # Act
        suppressed = throttle.consider(_error_record("boom", name="scitex.errors"))
        # Assert
        assert suppressed == 0

    def test_the_suppressed_count_is_carried_to_the_next_window(self):
        # Arrange
        throttle = RepeatThrottle(window_seconds=0.05)
        throttle.consider(_error_record("boom"))
        for _ in range(3):
            throttle.consider(_error_record("boom"))
        time.sleep(0.06)
        # Act
        suppressed = throttle.consider(_error_record("boom"))
        # Assert
        assert suppressed == 3

    def test_the_window_reopens_once_it_has_elapsed(self):
        # Arrange
        throttle = RepeatThrottle(window_seconds=0.05)
        throttle.consider(_error_record("boom"))
        time.sleep(0.06)
        # Act
        suppressed = throttle.consider(_error_record("boom"))
        # Assert
        assert suppressed is not None

    def test_a_window_that_could_suppress_nothing_is_refused(self):
        # Arrange
        window_that_suppresses_nothing = 0
        # Act
        construct = lambda: RepeatThrottle(  # noqa: E731
            window_seconds=window_that_suppresses_nothing
        )
        # Assert
        with pytest.raises(ValueError, match="window must be positive"):
            construct()

    def test_expired_keys_that_suppressed_repeats_are_reclaimed(self):
        """The leak the first version's own docstring promised not to have.

        django.request messages embed the URL ("Internal Server Error: /path"),
        so a crawler walking distinct erroring URLs mints a distinct key per
        URL. The first ``_prune`` only reclaimed keys whose suppressed count
        was zero, so every key that had ever suppressed a repeat was kept for
        the life of the process: measured at 500 distinct messages seen twice
        each, 500 keys retained, 499 expired and never reclaimed.
        """
        # Arrange
        window = 0.5  # the 500 records below take ~0.1s to feed in
        throttle = RepeatThrottle(window_seconds=window)
        for index in range(500):
            record = _error_record(f"Internal Server Error: /path/{index}")
            throttle.consider(record)
            throttle.consider(record)
        assert throttle.tracked_error_count() == 500
        time.sleep(2 * window + 0.1)  # past the window AND its one-window grace
        # Act
        throttle.consider(_error_record("a brand new failure"))
        # Assert
        assert throttle.tracked_error_count() == 1, (
            "expired keys were not reclaimed; a long-lived gunicorn worker "
            "grows one permanent dict entry per distinct erroring URL"
        )

    def test_a_recent_error_still_reports_its_count_after_expiry(self):
        """Reclaiming must not cost the count within the grace window."""
        # Arrange
        throttle = RepeatThrottle(window_seconds=0.05)
        throttle.consider(_error_record("boom"))
        throttle.consider(_error_record("boom"))
        time.sleep(0.06)  # expired, but inside the one-window grace
        # Act
        suppressed = throttle.consider(_error_record("boom"))
        # Assert
        assert suppressed == 1

    def test_the_tracked_set_is_capped_while_new_errors_keep_arriving(self):
        """Bounded even when distinct messages arrive faster than they expire."""
        # Arrange
        throttle = RepeatThrottle(window_seconds=300, max_tracked_errors=50)
        # Act
        for index in range(500):
            throttle.consider(_error_record(f"Internal Server Error: /path/{index}"))
        # Assert
        assert throttle.tracked_error_count() == 50


class TestWindowRendering:
    """'%d seconds' % int(0.05) renders '0 seconds', which reads as a bug."""

    def test_a_sub_second_window_reads_as_itself(self):
        assert format_window(0.05) == "0.05 seconds"

    def test_one_second_is_singular(self):
        assert format_window(1) == "1 second"

    def test_the_default_window_reads_as_a_whole_number(self):
        assert format_window(300) == "300 seconds"


# EOF
