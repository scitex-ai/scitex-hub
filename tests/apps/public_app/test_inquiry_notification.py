#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scitex-hub#1235: every new inquiry reaches the operator; open ones are listed.

Prod held 8 inquiries, all unhandled, and nobody had been told about any of
them. These tests drive the real views and the real scitex-notification sender
against a real SMTP server on 127.0.0.1 (tests/apps/public_app/_smtp_server.py),
including one that refuses the login exactly as prod's did (535).

Disposable data only (example.com addresses, made-up names).
"""

from __future__ import annotations

import os

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from apps.infra.public_app.models import ServiceInquiry

from ._smtp_server import TestSMTPServer

OPERATOR = "operator@example.com"
INBOX = "inbox@example.com"

SERVICES_POST = {
    "name": "Test Inquirer",
    "affiliation": "Example University",
    "request": "We would like a quote for on-prem installation.",
    "budget": "support",
}
CONTACT_POST = {
    "name": "Contact Tester",
    "email": "reply-here@example.com",
    "type": "sales",
    "request": "Please tell me about team plans.",
}


@pytest.fixture
def no_notification_env():
    """The notification account is the Hub's own unless these are set; unset them."""
    names = ["SCITEX_NOTIFICATION_EMAIL_FROM", "SCITEX_NOTIFICATION_EMAIL_PASSWORD"]
    saved = {n: os.environ.pop(n) for n in names if n in os.environ}
    yield
    os.environ.update(saved)


def _point_at(settings, smtp):
    settings.EMAIL_HOST = "127.0.0.1"
    settings.EMAIL_PORT = smtp.port
    settings.DEFAULT_FROM_EMAIL = "no-reply@example.com"
    settings.EMAIL_HOST_PASSWORD = "test-only"  # pragma: allowlist secret
    settings.INQUIRY_NOTIFY_TO = OPERATOR
    settings.SERVICES_INQUIRY_EMAIL = INBOX
    settings.SITE_URL = "https://hub.example.com"


def _post(client, url, data, capture):
    with capture(execute=True):
        return client.post(url, data)


@pytest.fixture
def delivered(
    db, client, settings, no_notification_env, django_capture_on_commit_callbacks
):
    with TestSMTPServer() as smtp:
        _point_at(settings, smtp)
        resp = _post(
            client,
            reverse("public_app:services"),
            SERVICES_POST,
            django_capture_on_commit_callbacks,
        )
        return resp, smtp.state, ServiceInquiry.objects.get()


@pytest.fixture
def refused(
    db, client, settings, no_notification_env, django_capture_on_commit_callbacks
):
    with TestSMTPServer(refuse_login=True) as smtp:
        _point_at(settings, smtp)
        resp = _post(
            client,
            reverse("public_app:services"),
            SERVICES_POST,
            django_capture_on_commit_callbacks,
        )
        return resp, smtp.state, ServiceInquiry.objects.get()


@pytest.fixture
def contact_delivered(
    db, client, settings, no_notification_env, django_capture_on_commit_callbacks
):
    with TestSMTPServer() as smtp:
        _point_at(settings, smtp)
        _post(
            client,
            reverse("public_app:contact"),
            CONTACT_POST,
            django_capture_on_commit_callbacks,
        )
        return smtp.state, ServiceInquiry.objects.get()


# ---------------------------------------------------------------------------
# Notification on a new inquiry
# ---------------------------------------------------------------------------


def test_a_services_inquiry_sends_exactly_one_notification(delivered):
    # Arrange
    _resp, state, _row = delivered
    # Act
    count = len(state.messages)
    # Assert
    assert count == 1


def test_the_operator_is_the_first_recipient(delivered):
    # Arrange
    _resp, state, _row = delivered
    # Act
    recipients = state.messages[0].rcpt_to
    # Assert
    assert recipients == [OPERATOR, INBOX]


def test_the_notification_never_goes_to_the_hiring_inbox(delivered):
    # Arrange
    _resp, state, _row = delivered
    # Act
    recipients = state.messages[0].rcpt_to
    # Assert
    assert not any("recruit@" in r for r in recipients)


def test_the_notification_authenticates_before_sending(delivered):
    # Arrange
    _resp, state, _row = delivered
    # Act
    logins = state.logins
    # Assert
    assert logins != []


def test_the_notification_subject_names_the_inquirer(delivered):
    # Arrange
    _resp, state, _row = delivered
    # Act
    subject = state.messages[0].message["Subject"]
    # Assert
    assert subject == "[SciTeX inquiry] services: Test Inquirer"


def test_the_notification_carries_the_request_and_the_admin_link(delivered):
    # Arrange
    _resp, state, row = delivered
    link = "https://hub.example.com" + reverse(
        "admin:public_app_serviceinquiry_change", args=[row.pk]
    )
    # Act
    body = state.messages[0].message.get_payload(decode=True).decode()
    # Assert
    assert SERVICES_POST["request"] in body and link in body


def test_a_delivered_notification_is_recorded_on_the_row(delivered):
    # Arrange
    _resp, _state, row = delivered
    # Act
    notified = row.notified_at
    # Assert
    assert notified is not None


def test_the_contact_form_notification_carries_the_reply_address(contact_delivered):
    # Arrange
    state, _row = contact_delivered
    # Act
    body = state.messages[0].message.get_payload(decode=True).decode()
    # Assert
    assert "Reply to: reply-here@example.com" in body


# ---------------------------------------------------------------------------
# A refused login (the prod failure) loses nothing and is visible
# ---------------------------------------------------------------------------


def test_a_refused_login_still_shows_the_visitor_success(refused):
    # Arrange
    resp, _state, _row = refused
    # Act
    page = resp.content.decode()
    # Assert
    assert "We've received your inquiry" in page


def test_a_refused_login_still_stores_the_inquiry(refused):
    # Arrange
    _resp, _state, row = refused
    # Act
    stored = row.request
    # Assert
    assert stored == SERVICES_POST["request"]


def test_a_refused_login_is_recorded_on_the_row_as_not_notified(refused):
    # Arrange
    _resp, _state, row = refused
    # Act
    outcome = (row.notified_at, row.notify_error)
    # Assert
    assert outcome == (None, "SMTPAuthenticationError")


def test_a_refused_login_delivers_nothing(refused):
    # Arrange
    _resp, state, _row = refused
    # Act
    count = len(state.messages)
    # Assert
    assert count == 0


# ---------------------------------------------------------------------------
# Handled state and the admin list of open inquiries
# ---------------------------------------------------------------------------


@pytest.fixture
def staff(db):
    return User.objects.create_superuser("inq_admin", "inq_admin@example.com", "pw-x")


@pytest.fixture
def two_inquiries(db):
    open_one = ServiceInquiry.objects.create(name="Open One", request="a")
    done = ServiceInquiry.objects.create(name="Done One", request="b")
    done.mark_handled()
    return open_one, done


def test_mark_handled_records_when(two_inquiries):
    # Arrange
    _open_one, done = two_inquiries
    # Act
    done.refresh_from_db()
    # Assert
    assert done.handled_at is not None


def test_mark_handled_records_who(two_inquiries, staff):
    # Arrange
    open_one, _done = two_inquiries
    # Act
    open_one.mark_handled(staff)
    open_one.refresh_from_db()
    # Assert
    assert open_one.handled_by == staff


def test_first_response_time_is_handled_minus_created(two_inquiries):
    # Arrange
    _open_one, done = two_inquiries
    done.refresh_from_db()
    # Act
    delta = done.first_response_time
    # Assert
    assert delta == done.handled_at - done.created_at


def test_an_open_inquiry_has_no_first_response_time(two_inquiries):
    # Arrange
    open_one, _done = two_inquiries
    # Act
    delta = open_one.first_response_time
    # Assert
    assert delta is None


def test_ticking_handled_directly_also_stamps_the_time(db):
    # Arrange: the list_editable checkbox path, which bypasses mark_handled().
    row = ServiceInquiry.objects.create(name="Checkbox", request="c")
    row.handled = True
    # Act
    row.save()
    row.refresh_from_db()
    # Assert
    assert row.handled_at is not None


def test_reopening_clears_the_handled_stamp(two_inquiries):
    # Arrange
    _open_one, done = two_inquiries
    # Act
    done.reopen()
    done.refresh_from_db()
    # Assert
    assert (done.handled_at, done.handled_by) == (None, None)


def test_the_admin_list_opens_on_open_inquiries_only(client, staff, two_inquiries):
    # Arrange
    client.force_login(staff)
    # Act
    page = client.get(reverse("admin:public_app_serviceinquiry_changelist"))
    names = [obj.name for obj in page.context["cl"].result_list]
    # Assert
    assert names == ["Open One"]


def test_the_admin_list_can_show_handled_inquiries(client, staff, two_inquiries):
    # Arrange
    client.force_login(staff)
    url = reverse("admin:public_app_serviceinquiry_changelist") + "?status=handled"
    # Act
    page = client.get(url)
    names = [obj.name for obj in page.context["cl"].result_list]
    # Assert
    assert names == ["Done One"]


def test_the_admin_action_marks_handled_by_the_acting_staff(
    client, staff, two_inquiries
):
    # Arrange
    open_one, _done = two_inquiries
    client.force_login(staff)
    # Act
    client.post(
        reverse("admin:public_app_serviceinquiry_changelist"),
        {"action": "mark_handled", "_selected_action": [open_one.pk]},
    )
    open_one.refresh_from_db()
    # Assert
    assert (open_one.handled, open_one.handled_by) == (True, staff)
