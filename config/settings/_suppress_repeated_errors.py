#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: config/settings/_suppress_repeated_errors.py
"""Suppress repeats of the SAME error so the admin mailbox stays readable.

``django.utils.log.AdminEmailHandler`` has no throttle of its own. Attached to
``django.request`` it sends one email per 500, so a single crash-looping view
delivers hundreds of identical messages -- and an inbox that receives hundreds
of identical messages is a channel the operator learns to ignore. That is the
same failure as sending nothing, one layer along.

``ThrottledAdminEmailHandler`` delivers the FIRST occurrence of each distinct
error and drops its repeats for ``window_seconds``. Distinctness is (logger
name, level, formatted message, exception type) -- deliberately NOT the
traceback text, because two occurrences of one bug differ in line-level detail
while being the same thing to whoever reads the mail.

WHY A HANDLER AND NOT A ``logging.Filter``
------------------------------------------
The throttle has to say, in the delivered mail, how many repeats it swallowed.
A filter can only do that by rewriting ``record.msg`` -- and the LogRecord is
SHARED by every handler on the logger, so a filter that rewrites it corrupts
what the rotating file handlers write. The first version of this module did
exactly that and was correct only because ``mail_admins`` happened to be listed
last in every handler list; reordering one list would have silently started
writing throttle annotations into errors.log. A handler owns its own emit path,
so it can tag a COPY of the record and leave the shared one untouched, and
correctness no longer depends on the order of a list in a settings file.

The count is appended in ``format`` -- which builds the mail BODY -- rather
than written into the message, because ``AdminEmailHandler`` derives the
SUBJECT from ``record.getMessage()``. Rewriting the message would put the
throttle's own bookkeeping, newlines escaped to a literal ``\\n``, into the
subject line of every mail that follows a storm, exactly where the operator
needs to read the failure.

WHAT IT DOES NOT DO, on purpose:

* It never suppresses a DIFFERENT error. A new failure always gets through,
  however many copies of an older one are being dropped.
* It never suppresses silently. The first message of each window carries how
  many repeats the previous window swallowed, so the count is visible in the
  mail itself rather than only in a metric nobody reads.
* It does not touch any other handler. Files keep every record, byte for byte;
  only the notification rail is de-duplicated.
"""

from __future__ import annotations

import copy
import logging
import threading
import time

from django.utils.log import AdminEmailHandler

DEFAULT_WINDOW_SECONDS = 300

# Upper bound on how many distinct errors are tracked at once. It exists
# because ``django.request`` messages embed the URL ("Internal Server Error:
# /path"), so a crawler walking distinct erroring URLs mints a distinct key per
# URL. Without a cap, a long-lived gunicorn worker accumulates one dict entry
# per URL for as long as the traffic lasts.
DEFAULT_MAX_TRACKED_ERRORS = 4096


def _format_window(seconds: float) -> str:
    """Render a window the way a person reads it.

    ``"%d seconds" % int(0.05)`` renders "0 seconds", which reads as a bug in
    the throttle rather than as a short window. Sub-second windows only occur
    in tests today, but a message that lies in a test is a message that will
    lie in production the first time someone tunes the default down.
    """
    value = float(seconds)
    rendered = (
        "%d" % int(value)
        if value.is_integer()
        else ("%.6f" % value).rstrip("0").rstrip(".")
    )
    return "%s second%s" % (rendered, "" if value == 1 else "s")


class RepeatThrottle:
    """Decide whether a record is the first of its kind in the current window.

    Kept separate from the handler so it can be exercised without Django, and
    so the handler's ``emit`` stays a three-line reading of a decision.
    """

    def __init__(
        self,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        max_tracked_errors: int = DEFAULT_MAX_TRACKED_ERRORS,
    ) -> None:
        if window_seconds <= 0:
            raise ValueError(
                "RepeatThrottle(window_seconds=%r): the window must be "
                "positive. A zero or negative window would suppress nothing "
                "while reading as if it throttles -- set a real duration (the "
                "default is %d seconds) or remove the throttle."
                % (window_seconds, DEFAULT_WINDOW_SECONDS)
            )
        if max_tracked_errors <= 0:
            raise ValueError(
                "RepeatThrottle(max_tracked_errors=%r): the cap must be "
                "positive, otherwise nothing is ever remembered and every "
                "repeat is delivered." % (max_tracked_errors,)
            )
        self.window_seconds = window_seconds
        self.max_tracked_errors = max_tracked_errors
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

    def consider(self, record: logging.LogRecord) -> int | None:
        """``None`` to drop this record; otherwise the repeats swallowed since
        the last delivery of the same error (0 when there were none)."""
        key = self._key(record)
        now = time.monotonic()
        with self._lock:
            state = self._seen.get(key)
            if state is not None and now - state[0] < self.window_seconds:
                state[1] += 1
                return None
            suppressed = state[1] if state is not None else 0
            self._seen[key] = [now, 0]
            self._prune(now)
        return suppressed

    def _prune(self, now: float) -> None:
        """Drop expired keys so a long-lived process cannot grow unbounded.

        Two rules, both of which only ever cost a suppression COUNT and never
        cause a suppression -- i.e. forgetting can make the throttle deliver
        more mail, never less:

        1. A key is kept for one window AFTER its window expired, so an error
           that recurs promptly can still report how many repeats were dropped.
           Past that grace it is forgotten, whatever its count. The first
           version kept any key whose count was non-zero forever, which is the
           opposite of what its own docstring promised: measured at 500
           distinct django.request messages seen twice each, all 500 keys
           survived expiry and 499 were never reclaimed.
        2. Above ``max_tracked_errors`` the oldest windows are forgotten first,
           which bounds the map even while a crawler is minting new distinct
           messages faster than the grace period retires them.
        """
        cutoff = now - 2 * self.window_seconds
        for key in [key for key, state in self._seen.items() if state[0] <= cutoff]:
            del self._seen[key]

        overflow = len(self._seen) - self.max_tracked_errors
        if overflow > 0:
            oldest_first = sorted(self._seen.items(), key=lambda item: item[1][0])
            for key, _state in oldest_first[:overflow]:
                del self._seen[key]

    def tracked_error_count(self) -> int:
        """How many distinct errors are currently remembered."""
        with self._lock:
            return len(self._seen)


class ThrottledAdminEmailHandler(AdminEmailHandler):
    """``AdminEmailHandler`` that mails the first of each error per window."""

    def __init__(
        self,
        *args,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        max_tracked_errors: int = DEFAULT_MAX_TRACKED_ERRORS,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.throttle = RepeatThrottle(window_seconds, max_tracked_errors)

    def emit(self, record: logging.LogRecord) -> None:
        suppressed = self.throttle.consider(record)
        if suppressed is None:
            return
        if suppressed:
            record = self._tagged(record, suppressed)
        super().emit(record)

    def _tagged(self, record: logging.LogRecord, suppressed: int):
        """A COPY carrying the suppressed count -- never the shared record.

        Every other handler on the same logger is handed the very same
        LogRecord object, so tagging in place would leak this handler's
        bookkeeping into what they write.
        """
        tagged = copy.copy(record)
        tagged.suppressed_repeats = suppressed
        return tagged

    def format(self, record: logging.LogRecord) -> str:
        """The mail BODY, with the suppressed count appended when there is one.

        The count is added here rather than by rewriting ``record.msg``
        because AdminEmailHandler builds the SUBJECT from
        ``record.getMessage()``: a rewritten message would put the throttle's
        bookkeeping -- newlines escaped to a literal ``\\n`` -- into the
        subject line of every mail after a storm, where the operator needs to
        read the failure. The body is where the count belongs.
        """
        formatted = super().format(record)
        suppressed = getattr(record, "suppressed_repeats", 0)
        if not suppressed:
            return formatted
        return (
            "%s\n\n[%d identical message(s) were suppressed in the previous %s "
            "by hub's repeated-error throttle]"
            % (
                formatted,
                suppressed,
                _format_window(self.throttle.window_seconds),
            )
        )


# EOF
