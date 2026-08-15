#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: config/settings/_suppress_repeated_errors.py
"""Suppress repeats of the SAME error so the admin mailbox stays readable.

``django.utils.log.AdminEmailHandler`` has no throttle of its own. Attached to
``django.request`` it sends one email per 500, so a single crash-looping view
delivers hundreds of identical messages -- and an inbox that receives hundreds
of identical messages is a channel the operator learns to ignore. That is the
same failure as sending nothing, one layer along.

This filter passes the FIRST occurrence of each distinct error and drops its
repeats for ``window_seconds``. Distinctness is (logger name, level, formatted
message, exception type) -- deliberately NOT the traceback text, because two
occurrences of one bug differ in line-level detail while being the same thing
to whoever reads the mail.

WHAT IT DOES NOT DO, on purpose:

* It never suppresses a DIFFERENT error. A new failure always gets through,
  however many copies of an older one are being dropped.
* It never suppresses silently. The first message of each window carries how
  many repeats the previous window swallowed, so the count is visible in the
  mail itself rather than only in a metric nobody reads.
* It does not touch any other handler. Files keep every record; only the
  notification rail is de-duplicated.
"""

from __future__ import annotations

import logging
import threading
import time

DEFAULT_WINDOW_SECONDS = 300


class SuppressRepeatedErrors(logging.Filter):
    """Pass the first of each distinct error per window; drop its repeats."""

    def __init__(self, window_seconds: float = DEFAULT_WINDOW_SECONDS) -> None:
        super().__init__()
        if window_seconds <= 0:
            raise ValueError(
                "SuppressRepeatedErrors(window_seconds=%r): the window must be "
                "positive. A zero or negative window would suppress nothing "
                "while reading as if it throttles -- set a real duration (the "
                "default is %d seconds) or remove the filter."
                % (window_seconds, DEFAULT_WINDOW_SECONDS)
            )
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        # key -> [window_started_at, suppressed_since_window_started]
        self._seen: dict[tuple, list] = {}

    def _key(self, record: logging.LogRecord) -> tuple:
        exc_type = record.exc_info[0].__name__ if record.exc_info else ""
        try:
            message = record.getMessage()
        except Exception:  # a bad format string must not break logging
            message = str(record.msg)
        return (record.name, record.levelno, message, exc_type)

    def filter(self, record: logging.LogRecord) -> bool:
        key = self._key(record)
        now = time.monotonic()
        with self._lock:
            state = self._seen.get(key)
            if state is not None and now - state[0] < self.window_seconds:
                state[1] += 1
                return False
            suppressed = state[1] if state is not None else 0
            self._seen[key] = [now, 0]
            self._prune(now)
        if suppressed:
            record.msg = (
                "%s\n\n[%d identical message(s) were suppressed in the previous "
                "%d seconds by SuppressRepeatedErrors]"
                % (record.getMessage(), suppressed, int(self.window_seconds))
            )
            record.args = ()
        return True

    def _prune(self, now: float) -> None:
        """Drop expired keys so a long-lived process cannot grow unbounded."""
        expired = [
            key
            for key, state in self._seen.items()
            if now - state[0] >= self.window_seconds and state[1] == 0
        ]
        for key in expired:
            del self._seen[key]


# EOF
