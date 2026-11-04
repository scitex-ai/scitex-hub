"""Password-reset credentials reach the mail transport, never application logs."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from django.http import HttpResponse

from apps.infra.auth_app.views import password_reset


@pytest.mark.parametrize("mail_fails", [False, True])
def test_reset_token_is_not_logged_on_delivery_attempt(monkeypatch, rf, mail_fails):
    # Arrange: no database query, real mailbox or valid reset credential.
    token = "fixture-reset-token-never-for-logging"
    user = SimpleNamespace(pk=123, username="reset_logging_fixture")
    query = Mock()
    query.order_by.return_value.first.return_value = user
    monkeypatch.setattr(password_reset.User.objects, "filter", Mock(return_value=query))
    monkeypatch.setattr(
        password_reset.default_token_generator, "make_token", lambda _user: token
    )
    sender = Mock(
        side_effect=(
            RuntimeError("fixture mail transport failure") if mail_fails else None
        )
    )
    monkeypatch.setattr("django.core.mail.send_mail", sender)
    monkeypatch.setattr(password_reset, "_reset_feedback", Mock())
    monkeypatch.setattr(
        password_reset, "render", lambda *_args: HttpResponse("fixture")
    )
    logger = Mock()
    request = rf.post("/auth/forgot-password/", {"email": "reset@example.invalid"})

    # Act: exercise the actual view, including its trailing-slash reset URL.
    with patch("logging.getLogger", return_value=logger):
        response = password_reset.forgot_password(request)

    # Assert: delivery still receives the credential; logs do not expose it.
    assert response.status_code == 200
    sender.assert_called_once()
    assert token in sender.call_args.args[1]
    assert token in sender.call_args.kwargs["html_message"]
    assert token not in repr(logger.mock_calls)
