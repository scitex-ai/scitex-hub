#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the api_tts_relay endpoint in apps/llm_app/views/chat.py

The relay endpoint accepts POST {"text": "..."} from authenticated users,
pushes a tts_speak message to the user's speech_<username> channel group,
and returns {"success": True, "relayed_to": "speech_<username>"}.

These tests run against a real in-memory channel layer (no mocks): the view
calls ``get_channel_layer()`` which, under ``override_settings`` below,
returns ``channels.layers.InMemoryChannelLayer``. The delivered message is
read back from the group to assert on real behaviour.
"""

import asyncio
import json

import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

_TEST_PW = "Testpass123!"  # pragma: allowlist secret
# llm_app is mounted at /apps/llm/ in config/urls.py (post app-reorg);
# resolve by name so the test does not hard-code the mount prefix.
_RELAY_URL = reverse("llm_app:api_tts_relay")

_IN_MEMORY_LAYER = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


def _post_json(client, body):
    """POST a JSON body string to the relay endpoint."""
    return client.post(_RELAY_URL, data=body, content_type="application/json")


def _subscribe(group_name):
    """Subscribe a fresh channel to the group and return it.

    Must be called BEFORE the relay POST: a channel layer only delivers a
    group_send to channels already in the group at send time, so the
    subscriber has to be registered before the message is sent.
    """
    layer = get_channel_layer()

    async def _add():
        channel = await layer.new_channel()
        await layer.group_add(group_name, channel)
        return channel

    return async_to_sync(_add)()


def _receive(channel):
    """Receive one message on a previously subscribed channel.

    Returns the delivered dict, or None if nothing arrived within the timeout.
    """
    layer = get_channel_layer()

    async def _pull():
        try:
            return await asyncio.wait_for(layer.receive(channel), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    return async_to_sync(_pull)()


class TestTtsRelayAuthentication(TestCase):
    """api_tts_relay requires a logged-in user."""

    def test_relay_unauthenticated_request_is_rejected(self):
        """Unauthenticated request must be redirected or rejected."""
        # Arrange
        body = json.dumps({"text": "hello"})
        # Act
        response = _post_json(self.client, body)
        # Assert
        # login_required redirects to the login page (302) or returns 401/403
        assert response.status_code in (302, 401, 403)

    def test_relay_get_method_returns_405(self):
        """GET request to the relay endpoint must return 405 Method Not Allowed."""
        # Arrange
        User.objects.create_user("tts_relay_get_user", password=_TEST_PW)
        self.client.login(username="tts_relay_get_user", password=_TEST_PW)
        # Act
        response = self.client.get(_RELAY_URL)
        # Assert
        assert response.status_code == 405


@override_settings(CHANNEL_LAYERS=_IN_MEMORY_LAYER)
class TestTtsRelayInputValidation(TestCase):
    """api_tts_relay validates the request body before sending to channel layer."""

    def setUp(self):
        self.user = User.objects.create_user("tts_relay_val_user", password=_TEST_PW)
        self.client.login(username="tts_relay_val_user", password=_TEST_PW)

    def test_relay_empty_text_returns_400(self):
        """POST with empty text must return 400."""
        # Arrange
        body = json.dumps({"text": ""})
        # Act
        response = _post_json(self.client, body)
        # Assert
        assert response.status_code == 400

    def test_relay_empty_text_response_has_error_field(self):
        """The 400 response for empty text must carry an error field."""
        # Arrange
        body = json.dumps({"text": ""})
        # Act
        response = _post_json(self.client, body)
        # Assert
        assert "error" in json.loads(response.content)

    def test_relay_missing_text_field_returns_400(self):
        """POST without any text key must return 400."""
        # Arrange
        body = json.dumps({})
        # Act
        response = _post_json(self.client, body)
        # Assert
        assert response.status_code == 400

    def test_relay_missing_text_field_response_has_error_field(self):
        """The 400 response for a missing text key must carry an error field."""
        # Arrange
        body = json.dumps({})
        # Act
        response = _post_json(self.client, body)
        # Assert
        assert "error" in json.loads(response.content)

    def test_relay_whitespace_only_text_returns_400(self):
        """POST with whitespace-only text (strips to empty) must return 400."""
        # Arrange
        body = json.dumps({"text": "   "})
        # Act
        response = _post_json(self.client, body)
        # Assert
        assert response.status_code == 400

    def test_relay_invalid_json_returns_400(self):
        """Malformed JSON body must return 400."""
        # Arrange
        body = "not-valid-json"
        # Act
        response = _post_json(self.client, body)
        # Assert
        assert response.status_code == 400

    def test_relay_invalid_json_response_has_error_field(self):
        """The 400 response for malformed JSON must carry an error field."""
        # Arrange
        body = "not-valid-json"
        # Act
        response = _post_json(self.client, body)
        # Assert
        assert "error" in json.loads(response.content)


@override_settings(CHANNEL_LAYERS=_IN_MEMORY_LAYER)
class TestTtsRelayChannelSend(TestCase):
    """api_tts_relay pushes the correct message to the channel layer."""

    def setUp(self):
        self.user = User.objects.create_user("tts_relay_chan_user", password=_TEST_PW)
        self.client.login(username="tts_relay_chan_user", password=_TEST_PW)
        self.group_name = f"speech_{self.user.username}"

    def test_relay_delivers_message_to_user_speech_group(self):
        """A subscriber on speech_<username> must receive the relayed message."""
        # Arrange
        channel = _subscribe(self.group_name)
        # Act
        _post_json(self.client, json.dumps({"text": "hello from container"}))
        message = _receive(channel)
        # Assert
        assert message is not None

    def test_relay_message_has_tts_speak_type(self):
        """The message delivered to the group must have type tts_speak."""
        # Arrange
        channel = _subscribe(self.group_name)
        # Act
        _post_json(self.client, json.dumps({"text": "speak this"}))
        message = _receive(channel)
        # Assert
        assert message["type"] == "tts_speak"

    def test_relay_message_carries_exact_text(self):
        """The delivered message must carry the exact text from the request body."""
        # Arrange
        expected_text = "precise text payload"
        channel = _subscribe(self.group_name)
        # Act
        _post_json(self.client, json.dumps({"text": expected_text}))
        message = _receive(channel)
        # Assert
        assert message["text"] == expected_text


@override_settings(CHANNEL_LAYERS=_IN_MEMORY_LAYER)
class TestTtsRelaySuccessResponse(TestCase):
    """api_tts_relay returns the correct JSON on success."""

    def setUp(self):
        self.user = User.objects.create_user("tts_relay_resp_user", password=_TEST_PW)
        self.client.login(username="tts_relay_resp_user", password=_TEST_PW)

    def test_relay_response_status_is_200(self):
        """A valid relay request must return HTTP 200."""
        # Arrange
        body = json.dumps({"text": "test status"})
        # Act
        response = _post_json(self.client, body)
        # Assert
        assert response.status_code == 200

    def test_relay_response_reports_success_true(self):
        """Successful relay must include success: True in the response."""
        # Arrange
        body = json.dumps({"text": "test success flag"})
        # Act
        response = _post_json(self.client, body)
        # Assert
        assert json.loads(response.content)["success"] is True

    def test_relay_response_reports_relayed_to_group_name(self):
        """Response must include relayed_to with the correct group name."""
        # Arrange
        body = json.dumps({"text": "test group name"})
        # Act
        response = _post_json(self.client, body)
        # Assert
        assert json.loads(response.content)["relayed_to"] == (
            f"speech_{self.user.username}"
        )

    def test_relay_long_text_is_truncated_to_4096_chars(self):
        """Text longer than 4096 chars must be truncated to 4096 on the wire."""
        # Arrange
        group_name = f"speech_{self.user.username}"
        channel = _subscribe(group_name)
        # Act
        _post_json(self.client, json.dumps({"text": "a" * 5000}))
        message = _receive(channel)
        # Assert
        assert len(message["text"]) <= 4096


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])
