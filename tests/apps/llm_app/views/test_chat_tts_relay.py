#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the api_tts_relay endpoint in apps/llm_app/views/chat.py

The relay endpoint accepts POST {"text": "..."} from authenticated users,
pushes a tts_speak message to the user's speech_<username> channel group,
and returns {"success": True, "relayed_to": "speech_<username>"}.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.test import TestCase

_TEST_PW = "Testpass123!"  # pragma: allowlist secret
_RELAY_URL = "/llm/api/tts/relay/"


class TestTtsRelayAuthentication(TestCase):
    """api_tts_relay requires a logged-in user."""

    def test_relay_requires_authentication(self):
        """Unauthenticated request must be redirected or rejected."""
        response = self.client.post(
            _RELAY_URL,
            data=json.dumps({"text": "hello"}),
            content_type="application/json",
        )
        # login_required redirects to the login page (302) or returns 401/403
        self.assertIn(response.status_code, (302, 401, 403))

    def test_relay_requires_post(self):
        """GET request to the relay endpoint must return 405 Method Not Allowed."""
        User.objects.create_user("tts_relay_get_user", password=_TEST_PW)
        self.client.login(username="tts_relay_get_user", password=_TEST_PW)
        response = self.client.get(_RELAY_URL)
        self.assertEqual(response.status_code, 405)


class TestTtsRelayInputValidation(TestCase):
    """api_tts_relay validates the request body before sending to channel layer."""

    def setUp(self):
        self.user = User.objects.create_user("tts_relay_val_user", password=_TEST_PW)
        self.client.login(username="tts_relay_val_user", password=_TEST_PW)

    def test_relay_requires_text_field(self):
        """POST with empty text must return 400."""
        response = self.client.post(
            _RELAY_URL,
            data=json.dumps({"text": ""}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        body = json.loads(response.content)
        self.assertIn("error", body)

    def test_relay_requires_text_field_missing(self):
        """POST without any text key must return 400."""
        response = self.client.post(
            _RELAY_URL,
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        body = json.loads(response.content)
        self.assertIn("error", body)

    def test_relay_whitespace_only_text_returns_400(self):
        """POST with whitespace-only text (strips to empty) must return 400."""
        response = self.client.post(
            _RELAY_URL,
            data=json.dumps({"text": "   "}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_relay_invalid_json_returns_400(self):
        """Malformed JSON body must return 400."""
        response = self.client.post(
            _RELAY_URL,
            data="not-valid-json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        body = json.loads(response.content)
        self.assertIn("error", body)


class TestTtsRelayChannelSend(TestCase):
    """api_tts_relay pushes the correct message to the channel layer."""

    def setUp(self):
        self.user = User.objects.create_user("tts_relay_chan_user", password=_TEST_PW)
        self.client.login(username="tts_relay_chan_user", password=_TEST_PW)

    def _post_text(self, text):
        return self.client.post(
            _RELAY_URL,
            data=json.dumps({"text": text}),
            content_type="application/json",
        )

    def test_relay_sends_to_correct_channel_group(self):
        """group_send must be called with group_name = speech_<username>."""
        mock_layer = MagicMock()
        # group_send is called inside a new event loop via run_until_complete,
        # so it must be an awaitable.
        mock_layer.group_send = AsyncMock(return_value=None)

        with patch(
            "apps.infra.llm_app.views.chat.get_channel_layer", return_value=mock_layer
        ):
            response = self._post_text("hello from container")

        self.assertEqual(response.status_code, 200)
        mock_layer.group_send.assert_called_once()
        call_args = mock_layer.group_send.call_args
        group_name = call_args[0][0]
        self.assertEqual(group_name, f"speech_{self.user.username}")

    def test_relay_sends_correct_message_type(self):
        """The message dict passed to group_send must have type tts_speak."""
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock(return_value=None)

        with patch(
            "apps.infra.llm_app.views.chat.get_channel_layer", return_value=mock_layer
        ):
            response = self._post_text("speak this")

        self.assertEqual(response.status_code, 200)
        call_args = mock_layer.group_send.call_args
        message = call_args[0][1]
        self.assertEqual(message["type"], "tts_speak")

    def test_relay_sends_correct_text_in_message(self):
        """The message dict must carry the exact text from the request body."""
        expected_text = "precise text payload"
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock(return_value=None)

        with patch(
            "apps.infra.llm_app.views.chat.get_channel_layer", return_value=mock_layer
        ):
            response = self._post_text(expected_text)

        self.assertEqual(response.status_code, 200)
        call_args = mock_layer.group_send.call_args
        message = call_args[0][1]
        self.assertEqual(message["text"], expected_text)


class TestTtsRelaySuccessResponse(TestCase):
    """api_tts_relay returns the correct JSON on success."""

    def setUp(self):
        self.user = User.objects.create_user("tts_relay_resp_user", password=_TEST_PW)
        self.client.login(username="tts_relay_resp_user", password=_TEST_PW)

    def test_relay_returns_success_true(self):
        """Successful relay must include success: True in the response."""
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock(return_value=None)

        with patch(
            "apps.infra.llm_app.views.chat.get_channel_layer", return_value=mock_layer
        ):
            response = self.client.post(
                _RELAY_URL,
                data=json.dumps({"text": "test success flag"}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertTrue(body["success"])

    def test_relay_returns_relayed_to_group_name(self):
        """Response must include relayed_to with the correct group name."""
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock(return_value=None)

        with patch(
            "apps.infra.llm_app.views.chat.get_channel_layer", return_value=mock_layer
        ):
            response = self.client.post(
                _RELAY_URL,
                data=json.dumps({"text": "test group name"}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        expected_group = f"speech_{self.user.username}"
        self.assertEqual(body["relayed_to"], expected_group)

    def test_relay_text_is_truncated_at_4096_chars(self):
        """Text longer than 4096 chars must be accepted without error (truncated silently)."""
        long_text = "a" * 5000
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock(return_value=None)

        with patch(
            "apps.infra.llm_app.views.chat.get_channel_layer", return_value=mock_layer
        ):
            response = self.client.post(
                _RELAY_URL,
                data=json.dumps({"text": long_text}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertTrue(body["success"])
        # Verify the actual sent text is capped at 4096
        call_args = mock_layer.group_send.call_args
        sent_text = call_args[0][1]["text"]
        self.assertLessEqual(len(sent_text), 4096)


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])
