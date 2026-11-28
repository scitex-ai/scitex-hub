#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_admin_mail_rate_limit.py
"""The same error subject reaches the admin inbox at most once per hour.

Operator, 2026-11-27: his inbox was flooded with Django error mail. The repeat
filter existed, but kept its window per PROCESS, so every gunicorn/celery
worker sent its own copy and a restart reset it. These tests drive the real
filter through Django's real AdminEmailHandler against a real (in-memory)
Django cache shared by several filter instances -- the stand-in for several
worker processes on one host -- and assert on the delivered outbox.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import time
from pathlib import Path

import pytest

SETTINGS_DIR = Path(__file__).resolve().parents[2] / "config" / "settings"


def _load(module_filename: str):
    path = SETTINGS_DIR / module_filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_suppress = _load("_suppress_repeated_errors.py")
SuppressRepeatedErrors = _suppress.SuppressRepeatedErrors
LOGGING = _load("settings_logging.py").LOGGING

SHARED = "admin-mail-throttle-test"
DUMMY = "admin-mail-throttle-dummy"


@pytest.fixture
def shared_cache_mail():
    """Prod-like mail settings plus a dedicated, empty in-memory cache."""
    from django.conf import settings as django_settings

    prod_like = dict(
        DEBUG=False,
        ADMINS=[("Ops", "ops@example.com")],
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="hub@example.com",
        SERVER_EMAIL="hub@example.com",
        SECRET_KEY="test-only-never-a-real-secret",
        CACHES={
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
            SHARED: {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": f"{SHARED}-{time.monotonic_ns()}",
            },
            DUMMY: {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
        },
    )
    if not django_settings.configured:
        import django

        django_settings.configure(INSTALLED_APPS=[], **prod_like)
        django.setup()

    from django.core import mail
    from django.core.cache import caches
    from django.test import override_settings

    with override_settings(**prod_like):
        caches[SHARED].clear()
        mail.outbox = []
        yield mail


def _record(message: str, name: str = "django.request") -> logging.LogRecord:
    return logging.LogRecord(
        name=name,
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )


def _worker_handler(window_seconds: float = 3600, alias: str = SHARED):
    """One worker process's mail_admins handler, as LOGGING builds it."""
    from django.utils.log import AdminEmailHandler

    handler = AdminEmailHandler()
    handler.addFilter(
        SuppressRepeatedErrors(window_seconds=window_seconds, cache_alias=alias)
    )
    return handler


class TestOneSubjectPerWindowAcrossWorkers:
    def test_a_storm_across_four_workers_delivers_one_mail(self, shared_cache_mail):
        # Arrange
        workers = [_worker_handler() for _ in range(4)]
        # Act
        for _ in range(25):
            for worker in workers:
                worker.handle(_record("Internal Server Error: /writer/"))
        # Assert
        assert len(shared_cache_mail.outbox) == 1, (
            "four workers each sent their own copy: the repeat window is per "
            "process again, which is how the operator's inbox was flooded"
        )

    def test_a_different_subject_still_gets_through(self, shared_cache_mail):
        # Arrange
        first, second = _worker_handler(), _worker_handler()
        first.handle(_record("Internal Server Error: /writer/"))
        # Act
        second.handle(_record("Internal Server Error: /scholar/"))
        # Assert
        assert len(shared_cache_mail.outbox) == 2

    def test_a_changing_id_in_the_message_is_still_one_subject(self, shared_cache_mail):
        # Arrange
        handler = _worker_handler()
        # Act
        for project_id in range(30):
            handler.handle(
                _record(f"Internal Server Error: /project/{project_id + 1000}/")
            )
        # Assert
        assert len(shared_cache_mail.outbox) == 1

    def test_a_changing_uuid_in_the_message_is_still_one_subject(
        self, shared_cache_mail
    ):
        # Arrange
        handler = _worker_handler()
        ids = [
            "3f2b8c1e-9a4d-4e6f-8b2a-1c3d5e7f9a0b",
            "a1b2c3d4-0000-4111-8222-333344445555",
        ]
        # Act
        for job in ids:
            handler.handle(_record(f"Task {job} failed"))
        # Assert
        assert len(shared_cache_mail.outbox) == 1

    @staticmethod
    def _storm_then_next_window():
        first, second = _worker_handler(window_seconds=1), _worker_handler(1)
        first.handle(_record("boom"))
        for _ in range(3):
            second.handle(_record("boom"))
        time.sleep(1.1)
        first.handle(_record("boom"))

    def test_the_window_reopens_for_every_worker(self, shared_cache_mail):
        # Arrange
        # Act
        self._storm_then_next_window()
        # Assert
        assert len(shared_cache_mail.outbox) == 2

    def test_the_next_window_reports_what_other_workers_suppressed(
        self, shared_cache_mail
    ):
        # Arrange
        # Act
        self._storm_then_next_window()
        # Assert
        assert "3 identical message(s) were suppressed" in (
            shared_cache_mail.outbox[-1].body
        )

    def test_a_dummy_cache_falls_back_to_the_in_process_window(self, shared_cache_mail):
        # Arrange
        handler = _worker_handler(alias=DUMMY)
        # Act
        for _ in range(10):
            handler.handle(_record("boom"))
        # Assert
        assert len(shared_cache_mail.outbox) == 1, (
            "a DummyCache 'accepts' every add(), which would pass every repeat"
        )

    def test_an_unknown_cache_alias_falls_back_instead_of_flooding(
        self, shared_cache_mail
    ):
        # Arrange
        handler = _worker_handler(alias="no-such-cache")
        # Act
        for _ in range(10):
            handler.handle(_record("boom"))
        # Assert
        assert len(shared_cache_mail.outbox) == 1


class TestTheConfiguredWindow:
    def test_the_default_window_is_one_hour(self):
        # Arrange
        one_hour = 3600
        # Act
        default = _suppress.DEFAULT_WINDOW_SECONDS
        # Assert
        assert default == one_hour

    def test_logging_shares_the_window_through_the_default_cache(self):
        # Arrange
        config = LOGGING["filters"]["suppress_repeated_errors"]
        # Act
        alias = config.get("cache_alias")
        # Assert
        assert alias == "default", (
            "without a cache alias the window is per process: N workers send "
            "N copies of every error"
        )

    def test_logging_window_is_an_hour_unless_overridden(self, window_env_unset):
        # Arrange
        logging_module = _load("settings_logging.py")
        # Act
        window = logging_module.LOGGING["filters"]["suppress_repeated_errors"][
            "window_seconds"
        ]
        # Assert
        assert window == 3600


@pytest.fixture
def window_env_unset():
    """Really remove the override so the committed default is what is read."""
    key = "SCITEX_HUB_ADMIN_MAIL_REPEAT_WINDOW_SECONDS"
    previous = os.environ.pop(key, None)
    try:
        yield key
    finally:
        if previous is not None:
            os.environ[key] = previous


# EOF
