#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_admin_error_mail.py
"""The operator must be told when hub fails -- and told readably.

Operator request, Telegram 2026-08-10:
「サイテクスハブの ... 失敗っていうのは必ず私にメールが届くようにしてほしいんですよ」

This file covers the base configuration, the recipients, and the BEHAVIOUR of
the rail: a real ERROR through the real handler, into a real outbox.

Two neighbours carry the rest:

* ``tests/config/test_logging_wiring_per_environment.py`` is the GATE for
  whether deployed environments keep the wiring -- it composes the actual
  ``settings_{prod,staging,dev}`` modules. Everything in this file passed on
  2026-08-15 while composed production had thrown the wiring away and sent
  nothing, which is exactly why the composed gate exists.
* ``tests/config/test_repeated_error_throttle.py`` covers the throttle
  mechanism on its own, without Django.
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
    graph into a test that only reads a dictionary.
    """
    path = SETTINGS_DIR / module_filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE_LOGGING = _load("settings_logging.py").LOGGING
ThrottledAdminEmailHandler = _load(
    "_suppress_repeated_errors.py"
).ThrottledAdminEmailHandler

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

# Rendering an admin mail runs Django's ExceptionReporter over the whole
# settings dump, measured at ~0.2s. A throttle window shorter than that would
# expire while the first mail is still being built, so these tests would
# measure the reporter rather than the throttle.
HANDLER_TEST_WINDOW_SECONDS = 1


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


@pytest.fixture
def admin_mail_settings():
    """A prod-like mail configuration with an in-memory outbox.

    Works whether or not the project's Django settings are already loaded:
    standalone it configures a minimal set, and under the full suite it
    overrides only what these tests depend on. DEBUG is pinned False because
    the real handler carries require_debug_false, and a test that quietly ran
    with DEBUG=True would prove nothing about production.
    """
    from django.conf import settings as django_settings

    prod_like = dict(
        DEBUG=False,
        ADMINS=[("Operator", "operator@example.com")],
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="hub@example.com",
        SERVER_EMAIL="hub@example.com",
        # AdminEmailHandler renders a traceback report, which reads
        # SECRET_KEY to cleanse the settings dump it embeds.
        SECRET_KEY="test-only-never-a-real-secret",
    )
    if not django_settings.configured:
        import django

        # AdminEmailHandler renders through Django's traceback reporter, which
        # walks the app registry -- so a bare settings.configure() is not
        # enough, the registry has to be populated too. Empty is fine: these
        # tests exercise the mail rail, not any application.
        django_settings.configure(INSTALLED_APPS=[], **prod_like)
        django.setup()

    from django.core import mail
    from django.test import override_settings

    with override_settings(**prod_like):
        mail.outbox = []
        yield


class TestTheBaseConfiguration:
    """settings_logging on its own.

    These localise a base-level mistake. They are deliberately NOT trusted as
    the gate: every one of them passed while composed production sent nothing.
    """

    @pytest.mark.parametrize("logger_name", LOGGERS_THAT_MUST_MAIL_ADMINS)
    def test_failure_carrying_loggers_reach_the_operator(self, logger_name):
        # Arrange
        logger = BASE_LOGGING["loggers"][logger_name]
        # Act
        handlers = logger.get("handlers", [])
        # Assert
        assert "mail_admins" in handlers, (
            f"logger {logger_name!r} carries operational failures but does not "
            "attach 'mail_admins', so its errors reach a rotating log file and "
            "nobody else. This is how the visitor pool sat 14/16 quarantined "
            "for four days in August 2026."
        )

    def test_mail_admins_throttles_repeats(self):
        # Arrange
        handler = BASE_LOGGING["handlers"]["mail_admins"]
        # Act
        handler_class = handler["class"]
        # Assert
        assert handler_class.endswith("ThrottledAdminEmailHandler"), (
            f"mail_admins uses {handler_class!r}, which has no repeat "
            "suppression. AdminEmailHandler has no throttle of its own, so one "
            "crash-looping view delivers hundreds of identical emails and the "
            "operator mutes the channel -- the same outcome as sending nothing."
        )

    def test_mail_admins_stays_off_developer_machines(self):
        # Arrange
        handler = BASE_LOGGING["handlers"]["mail_admins"]
        # Act
        filters = handler["filters"]
        # Assert
        assert "require_debug_false" in filters

    def test_the_handler_dotted_path_resolves_to_a_real_class(self):
        """Django resolves this by STRING at dictConfig time, not by import."""
        # Arrange
        dotted = BASE_LOGGING["handlers"]["mail_admins"]["class"]
        module_path, class_name = dotted.rsplit(".", 1)
        source = SETTINGS_DIR / f"{module_path.rsplit('.', 1)[1]}.py"
        # Act
        defines_it = source.is_file() and f"class {class_name}" in source.read_text()
        # Assert
        assert defines_it, (
            f"settings_logging names {dotted!r} as the mail_admins handler, but "
            f"no such class was found at {source}. Django resolves this string "
            "at startup, so a rename that misses it does not fail here -- it "
            "fails when the first error tries to reach the operator, which is "
            "the worst possible moment to discover it."
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


class TestAnErrorActuallyReachesTheOperator:
    """Trigger a real ERROR and look in the outbox.

    The card that produced this file is explicit that reading the settings is
    not proof -- reading the settings is exactly what made everyone believe
    mail_admins worked for months.
    """

    def test_an_error_is_delivered_to_the_admins(self, admin_mail_settings):
        # Arrange
        from django.core import mail

        handler = ThrottledAdminEmailHandler()
        # Act
        handler.handle(_error_record("Template clone returned falsy"))
        # Assert
        assert len(mail.outbox) == 1

    def test_the_delivered_mail_names_the_failure(self, admin_mail_settings):
        # Arrange
        from django.core import mail

        handler = ThrottledAdminEmailHandler()
        # Act
        handler.handle(_error_record("Template clone returned falsy"))
        # Assert
        assert "Template clone returned falsy" in mail.outbox[0].subject

    def test_the_delivered_mail_goes_to_the_configured_admin(
        self, admin_mail_settings
    ):
        # Arrange
        from django.core import mail

        handler = ThrottledAdminEmailHandler()
        # Act
        handler.handle(_error_record("Template clone returned falsy"))
        # Assert
        assert mail.outbox[0].to == ["operator@example.com"]

    def test_a_storm_of_one_error_does_not_flood_the_mailbox(
        self, admin_mail_settings
    ):
        # Arrange
        from django.core import mail

        handler = ThrottledAdminEmailHandler()
        # Act
        for _ in range(50):
            handler.handle(_error_record("Template clone returned falsy"))
        # Assert
        assert len(mail.outbox) == 1

    def test_a_second_distinct_failure_still_gets_through_a_storm(
        self, admin_mail_settings
    ):
        # Arrange
        from django.core import mail

        handler = ThrottledAdminEmailHandler()
        for _ in range(50):
            handler.handle(_error_record("Template clone returned falsy"))
        # Act
        handler.handle(_error_record("Gitea project creation failed"))
        # Assert
        assert len(mail.outbox) == 2

    def test_the_next_mail_reports_how_many_repeats_were_dropped(
        self, admin_mail_settings
    ):
        # Arrange
        from django.core import mail

        handler = ThrottledAdminEmailHandler(
            window_seconds=HANDLER_TEST_WINDOW_SECONDS
        )
        handler.handle(_error_record("boom"))
        for _ in range(3):
            handler.handle(_error_record("boom"))
        time.sleep(HANDLER_TEST_WINDOW_SECONDS + 0.1)
        # Act
        handler.handle(_error_record("boom"))
        # Assert
        assert (
            "3 identical message(s) were suppressed in the previous 1 second"
            in mail.outbox[-1].body
        ), (
            "the next mail must say how many repeats were dropped, or the "
            "throttle hides the scale of an incident"
        )

    def test_the_record_other_handlers_share_is_never_touched(
        self, admin_mail_settings
    ):
        """Correctness must not depend on mail_admins being listed last.

        Every handler on one logger is handed the SAME LogRecord object. The
        first version of the throttle was a filter that rewrote record.msg in
        place, so it only happened to be harmless because mail_admins was last
        in every handler list; reordering one list would have started writing
        throttle annotations into errors.log.
        """
        # Arrange
        handler = ThrottledAdminEmailHandler(
            window_seconds=HANDLER_TEST_WINDOW_SECONDS
        )
        handler.handle(_error_record("boom"))
        handler.handle(_error_record("boom"))
        time.sleep(HANDLER_TEST_WINDOW_SECONDS + 0.1)
        record = _error_record("boom")
        # Act
        handler.handle(record)
        # Assert
        assert record.msg == "boom" and not hasattr(record, "suppressed_repeats"), (
            "the throttle wrote its own bookkeeping onto the shared LogRecord; "
            "every other handler on this logger sees the same object"
        )

    def test_the_subject_line_still_reads_as_the_failure(self, admin_mail_settings):
        """The count belongs in the body, not in the subject.

        AdminEmailHandler builds the subject from record.getMessage() and
        escapes newlines into a literal "\\n", so a throttle that annotated the
        message would push its own bookkeeping into the subject line of every
        mail after a storm -- where the operator needs to read the failure.
        """
        # Arrange
        handler = ThrottledAdminEmailHandler(
            window_seconds=HANDLER_TEST_WINDOW_SECONDS
        )
        from django.core import mail

        handler.handle(_error_record("Template clone returned falsy"))
        handler.handle(_error_record("Template clone returned falsy"))
        time.sleep(HANDLER_TEST_WINDOW_SECONDS + 0.1)
        # Act
        handler.handle(_error_record("Template clone returned falsy"))
        # Assert
        subject = mail.outbox[-1].subject
        assert subject.endswith("Template clone returned falsy"), (
            f"the subject reads {subject!r}; the throttle's suppressed-count "
            "note must stay in the body"
        )


# EOF
