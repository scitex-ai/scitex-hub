#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/workspace/console_app/views/terminal/consumer.py

Covers:
- TerminalConsumer.tts_speak(event): the Django Channels group-message
  handler must base64-encode text and send an OSC escape sequence
  \\x1b]9999;speak:<b64>\\x07 over the WebSocket; empty text sends nothing.
- The post-accept setup pipeline: a forced exception must decline LOUDLY
  (visible ❌ frame naming the failed stage, specific 4xxx close code) —
  never the bare 1011 with zero frames it used to leak.
- send_decline(): the shared decline shape, including spawn_direct's
  formerly-mute SLURM-unavailable close(4003) and the visitor upsell.

Source: apps/workspace/console_app/views/terminal/consumer.py,
        apps/workspace/console_app/views/terminal/decline.py
"""

import asyncio
import base64
from types import SimpleNamespace

import pytest


def _run(coro):
    """Run a coroutine synchronously on a fresh event loop.

    `asyncio.get_event_loop()` raises on Python 3.10+ when called from a
    thread with no running loop — we create a dedicated loop per call and
    close it after the coroutine completes so repeated invocations don't
    share state.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class RecordingTransport:
    """Hand-rolled fake for the consumer's WebSocket transport side.

    Records every send/close in order so tests can assert on the real
    frames the production code produced (no mock library involved).
    """

    def __init__(self):
        self.calls = []

    async def send(self, text_data=None, bytes_data=None):
        self.calls.append(("send", text_data))

    async def close(self, code=None):
        self.calls.append(("close", code))

    @property
    def sent_texts(self):
        return [payload for name, payload in self.calls if name == "send"]

    @property
    def close_codes(self):
        return [payload for name, payload in self.calls if name == "close"]

    @property
    def call_names(self):
        return [name for name, _payload in self.calls]


def _build_consumer(authenticated=True):
    """Return (TerminalConsumer, RecordingTransport) wired together.

    We deliberately avoid importing the module at the top level so that
    Django channel layer and SLURM imports are deferred until this factory
    is called inside individual tests. The consumer is built via __new__
    WITHOUT a channel_layer attribute, so the first post-accept stage
    (channel-layer group_add) raises naturally for authenticated users —
    the same class of unhandled setup exception observed on prod. For
    anonymous (visitor) users the pipeline fails naturally at session
    dispatch instead (no project attribute on this bare consumer).
    """
    from apps.workspace.console_app.views.terminal.consumer import TerminalConsumer

    consumer = TerminalConsumer.__new__(TerminalConsumer)
    transport = RecordingTransport()
    consumer.send = transport.send
    consumer.close = transport.close
    consumer.user = SimpleNamespace(is_authenticated=authenticated, username="tester")
    consumer.channel_name = "test-channel"
    return consumer, transport


def _osc_b64_payload(text_data):
    """Extract and decode the base64 segment of an OSC speak escape."""
    prefix = "\x1b]9999;speak:"
    b64_part = text_data[len(prefix) : text_data.index("\x07")]
    return base64.b64decode(b64_part.encode()).decode()


# ---------------------------------------------------------------------------
# tts_speak: nominal case
# ---------------------------------------------------------------------------


class TestTtsSpeakSendsOscEscape:
    """tts_speak must forward speech as OSC 9999 escape over the WebSocket."""

    def test_tts_speak_sends_exactly_one_frame(self):
        """Calling tts_speak({'text': 'hello'}) must send exactly one frame."""
        # Arrange
        consumer, transport = _build_consumer()
        # Act
        _run(consumer.tts_speak({"text": "hello"}))
        # Assert
        assert len(transport.sent_texts) == 1

    def test_tts_speak_osc_prefix_present(self):
        """The sent frame must start with the OSC speak prefix."""
        # Arrange
        consumer, transport = _build_consumer()
        # Act
        _run(consumer.tts_speak({"text": "hello"}))
        # Assert
        assert transport.sent_texts[0].startswith("\x1b]9999;speak:")

    def test_tts_speak_osc_suffix_present(self):
        """The sent frame must end with BEL (\\x07)."""
        # Arrange
        consumer, transport = _build_consumer()
        # Act
        _run(consumer.tts_speak({"text": "hello"}))
        # Assert
        assert transport.sent_texts[0].endswith("\x07")

    def test_tts_speak_base64_encodes_text(self):
        """The base64 segment inside the OSC escape must decode to the text."""
        # Arrange
        input_text = "speak this carefully"
        consumer, transport = _build_consumer()
        # Act
        _run(consumer.tts_speak({"text": input_text}))
        # Assert
        assert _osc_b64_payload(transport.sent_texts[0]) == input_text

    def test_tts_speak_exact_format(self):
        """Full OSC message must match the pattern exactly."""
        # Arrange
        input_text = "exact format check"
        expected_b64 = base64.b64encode(input_text.encode()).decode()
        expected = f"\x1b]9999;speak:{expected_b64}\x07"
        consumer, transport = _build_consumer()
        # Act
        _run(consumer.tts_speak({"text": input_text}))
        # Assert
        assert transport.sent_texts[0] == expected

    def test_tts_speak_unicode_text(self):
        """Unicode text must be correctly base64-encoded and sent."""
        # Arrange
        input_text = "Bonjour le monde"
        consumer, transport = _build_consumer()
        # Act
        _run(consumer.tts_speak({"text": input_text}))
        # Assert
        assert _osc_b64_payload(transport.sent_texts[0]) == input_text


# ---------------------------------------------------------------------------
# tts_speak: empty / missing text guard
# ---------------------------------------------------------------------------


class TestTtsSpeakEmptyTextNoSend:
    """tts_speak must not send anything when text is empty or absent."""

    def test_empty_string_does_not_send(self):
        """tts_speak({'text': ''}) must not send any frame."""
        # Arrange
        consumer, transport = _build_consumer()
        # Act
        _run(consumer.tts_speak({"text": ""}))
        # Assert
        assert transport.sent_texts == []

    def test_missing_text_key_does_not_send(self):
        """tts_speak({}) (no 'text' key) must not send any frame."""
        # Arrange
        consumer, transport = _build_consumer()
        # Act
        _run(consumer.tts_speak({}))
        # Assert
        assert transport.sent_texts == []


# ---------------------------------------------------------------------------
# Post-accept setup failures must decline LOUDLY (never a bare 1011)
# ---------------------------------------------------------------------------


class TestSetupFailureDeclinesLoudly:
    """A forced exception in the setup pipeline must yield a ❌ frame and a
    specific close code — never the bare 1011 (zero frames) it used to be."""

    def test_setup_failure_sends_frame_naming_stage_and_error_class(self):
        """The client must receive a ❌ frame naming stage + error class."""
        # Arrange
        consumer, transport = _build_consumer()
        # Act
        _run(consumer._run_post_accept_setup())
        # Assert
        text = transport.sent_texts[0]
        assert (
            "❌ Terminal unavailable" in text
            and "channel groups" in text
            and "AttributeError" in text
        )

    def test_setup_failure_closes_with_4010_not_1011(self):
        """The socket must close with the transient 4xxx code, not 1011."""
        # Arrange
        consumer, transport = _build_consumer()
        # Act
        _run(consumer._run_post_accept_setup())
        # Assert
        assert transport.close_codes == [4010]

    def test_setup_failure_sends_frame_before_close(self):
        """The ❌ frame must reach the client before the socket closes."""
        # Arrange
        consumer, transport = _build_consumer()
        # Act
        _run(consumer._run_post_accept_setup())
        # Assert
        assert transport.call_names == ["send", "close"]

    def test_visitor_setup_failure_frame_includes_sign_in_upsell(self):
        """Anonymous (visitor) declines must carry the sign-in upsell."""
        # Arrange
        consumer, transport = _build_consumer(authenticated=False)
        # Act
        _run(consumer._run_post_accept_setup())
        # Assert
        assert "Sign up or log in to get a full terminal." in transport.sent_texts[0]

    def test_authenticated_setup_failure_frame_has_no_upsell(self):
        """Signed-in users must not be told to sign in."""
        # Arrange
        consumer, transport = _build_consumer(authenticated=True)
        # Act
        _run(consumer._run_post_accept_setup())
        # Assert
        assert "Sign up or log in" not in transport.sent_texts[0]


# ---------------------------------------------------------------------------
# send_decline: the shared shape for every loud terminal decline
# ---------------------------------------------------------------------------


class TestSendDeclineHelper:
    """send_decline() — shared decline shape, including spawn_direct's
    formerly-mute SLURM-unavailable close(4003)."""

    def test_permanent_decline_sends_detail_frame_then_closes_4003(self):
        """detail + code=4003 (spawn_direct SLURM path): ❌ frame, then close."""
        # Arrange
        from apps.workspace.console_app.views.terminal.decline import send_decline

        consumer, transport = _build_consumer()
        expected_frame = (
            "\x1b[1;31m❌ Terminal unavailable — slurm: "
            "computing resources unavailable (down)\x1b[0m\r\n"
        )
        # Act
        _run(
            send_decline(
                consumer,
                "slurm",
                code=4003,
                detail="computing resources unavailable (down)",
            )
        )
        # Assert
        assert transport.calls == [("send", expected_frame), ("close", 4003)]

    def test_exception_decline_shows_error_class_not_message(self):
        """Client sees the exception class, not its message (logs get both)."""
        # Arrange
        from apps.workspace.console_app.views.terminal.decline import send_decline

        consumer, transport = _build_consumer()
        # Act
        _run(
            send_decline(
                consumer,
                "workspace setup",
                exc=PermissionError("/secret/host/path denied"),
            )
        )
        # Assert
        text = transport.sent_texts[0]
        assert (
            "workspace setup" in text
            and "PermissionError" in text
            and "/secret/host/path" not in text
        )

    def test_exception_decline_defaults_to_transient_4010(self):
        """An exception decline without an explicit code must close 4010."""
        # Arrange
        from apps.workspace.console_app.views.terminal.decline import send_decline

        consumer, transport = _build_consumer()
        # Act
        _run(send_decline(consumer, "workspace setup", exc=RuntimeError("boom")))
        # Assert
        assert transport.close_codes == [4010]

    def test_visitor_permanent_decline_carries_upsell(self):
        """Visitor + permanent decline (no SLURM) must include the upsell."""
        # Arrange
        from apps.workspace.console_app.views.terminal.decline import send_decline

        consumer, transport = _build_consumer(authenticated=False)
        # Act
        _run(
            send_decline(
                consumer,
                "slurm",
                code=4003,
                detail="computing resources unavailable (not_installed)",
            )
        )
        # Assert
        assert "Sign up or log in to get a full terminal." in transport.sent_texts[0]


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])
