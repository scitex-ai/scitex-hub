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
repeats for ``window_seconds`` (default one hour). Distinctness is the mail's
SUBJECT as AdminEmailHandler builds it -- logger name, level and the formatted
message -- plus the exception type; deliberately NOT the traceback text,
because two occurrences of one bug differ in line-level detail while being the
same thing to whoever reads the mail. Runs of digits and hex ids (row ids,
UUIDs, PIDs, ports) are folded to ``#`` first, so one log line that embeds a
changing id is still ONE subject and cannot flood the inbox.

WHY A SHARED STORE (2026-11-27). The first version kept its state in a dict,
i.e. per PROCESS. Hub runs several gunicorn workers and celery workers, each
with its own dict, so "at most once per window" was really "once per window per
process", and a restart loop reset it entirely. The operator's inbox was
flooded anyway. With ``cache_alias`` set (the LOGGING config sets ``default``,
Redis in every deployment) the window is held in the Django cache with an
atomic ``add``, so it holds across every process on the host. If the cache is
unreachable the filter degrades to the in-process window -- never to "send
everything" and never to "send nothing".

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

import hashlib
import logging
import re
import threading
import time

DEFAULT_WINDOW_SECONDS = 3600

#: Cache key namespace. Versioned so a change to the key shape cannot collide
#: with windows written by an older deployment still draining.
_CACHE_PREFIX = "admin-mail-repeat:v2:"

# Hex ids first (UUIDs, hashes), then any remaining digit run.
_HEX_ID = re.compile(r"\b[0-9a-fA-F]{8,}(?:-[0-9a-fA-F]{4,})*\b")
_DIGITS = re.compile(r"\d+")


def subject_key(record: logging.LogRecord) -> tuple:
    """What makes two records "the same mail" for the throttle."""
    exc_type = record.exc_info[0].__name__ if record.exc_info else ""
    try:
        message = record.getMessage()
    except Exception:  # a bad format string must not break logging
        message = str(record.msg)
    first_line = message.split("\n", 1)[0]
    normalised = _DIGITS.sub("#", _HEX_ID.sub("#", first_line))
    return (record.name, record.levelno, normalised, exc_type)


class SuppressRepeatedErrors(logging.Filter):
    """Pass the first of each distinct error per window; drop its repeats."""

    def __init__(
        self,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        cache_alias: str | None = None,
    ) -> None:
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
        self.cache_alias = cache_alias
        self._lock = threading.Lock()
        # key -> [window_started_at, suppressed_since_window_started]
        self._seen: dict[tuple, list] = {}

    # Kept under its old name: tests and callers use it.
    def _key(self, record: logging.LogRecord) -> tuple:
        return subject_key(record)

    def filter(self, record: logging.LogRecord) -> bool:
        key = self._key(record)
        verdict = self._shared_verdict(key)
        if verdict is None:
            verdict = self._local_verdict(key)
        passes, suppressed = verdict
        if passes and suppressed:
            record.msg = (
                "%s\n\n[%d identical message(s) were suppressed in the previous "
                "%d seconds by SuppressRepeatedErrors]"
                % (record.getMessage(), suppressed, int(self.window_seconds))
            )
            record.args = ()
        return passes

    # -- shared (cross-process) window -------------------------------------

    def _shared_verdict(self, key: tuple) -> tuple[bool, int] | None:
        """(passes, suppressed_before) via the Django cache; None if unusable."""
        if self.cache_alias is None:
            return None
        try:
            from django.core.cache import caches
            from django.core.cache.backends.dummy import DummyCache

            cache = caches[self.cache_alias]
            if isinstance(cache, DummyCache):
                # add() always "succeeds" on a dummy cache, which would pass
                # every repeat. It remembers nothing, so it cannot hold a window.
                return None
            digest = hashlib.sha256(repr(key).encode("utf-8")).hexdigest()[:32]
            window_key = _CACHE_PREFIX + digest
            count_key = window_key + ":suppressed"
            timeout = int(max(1, round(self.window_seconds)))
            if cache.add(window_key, 1, timeout=timeout):
                suppressed = int(cache.get(count_key) or 0)
                if suppressed:
                    cache.delete(count_key)
                return True, suppressed
            # The counter outlives the window so the NEXT window's first mail
            # can still report it.
            cache.add(count_key, 0, timeout=timeout * 24)
            try:
                cache.incr(count_key)
            except ValueError:  # counter expired between add and incr
                pass  # an uncounted repeat is still a repeat: stay suppressed
            return False, 0
        except Exception:  # cache down / Django not configured: degrade locally
            return None

    # -- in-process window ---------------------------------------------------

    def _local_verdict(self, key: tuple) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            state = self._seen.get(key)
            if state is not None and now - state[0] < self.window_seconds:
                state[1] += 1
                return False, 0
            suppressed = state[1] if state is not None else 0
            self._seen[key] = [now, 0]
            self._prune(now)
        return True, suppressed

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
