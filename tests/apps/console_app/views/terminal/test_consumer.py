#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the tts_speak handler in apps/console_app/views/terminal/consumer.py

TerminalConsumer.tts_speak(event) is a Django Channels group-message handler.
When called with {"text": "..."}, it must:
- base64-encode the text
- send an OSC escape sequence  \\x1b]9999;speak:<b64>\\x07  over the WebSocket

When called with empty text it must not send anything.

Source: apps/console_app/views/terminal/consumer.py
"""

import asyncio
import base64
from unittest.mock import AsyncMock

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


def _build_consumer():
    """Return a TerminalConsumer instance with send replaced by an AsyncMock.

    We deliberately avoid importing the module at the top level so that
    Django channel layer and SLURM imports are deferred until this factory
    is called inside individual tests. This keeps the test class itself
    importable even when channels/SLURM are not configured.
    """
    from apps.workspace.console_app.views.terminal.consumer import TerminalConsumer

    consumer = TerminalConsumer.__new__(TerminalConsumer)
    consumer.send = AsyncMock()
    return consumer


# ---------------------------------------------------------------------------
# tts_speak: nominal case
# ---------------------------------------------------------------------------


class TestTtsSpeakSendsOscEscape:
    """tts_speak must forward speech as OSC 9999 escape over the WebSocket."""

    def test_tts_speak_sends_osc_escape_with_text(self):
        """Calling tts_speak({'text': 'hello'}) must call send with the OSC sequence."""
        consumer = _build_consumer()
        _run(consumer.tts_speak({"text": "hello"}))
        consumer.send.assert_called_once()

    def test_tts_speak_osc_prefix_present(self):
        """The text_data argument passed to send must start with the OSC prefix."""
        consumer = _build_consumer()
        _run(consumer.tts_speak({"text": "hello"}))

        call_kwargs = consumer.send.call_args
        text_data = call_kwargs[1].get("text_data") or call_kwargs[0][0]
        assert text_data.startswith("\x1b]9999;speak:")

    def test_tts_speak_osc_suffix_present(self):
        """The text_data argument passed to send must end with BEL (\\x07)."""
        consumer = _build_consumer()
        _run(consumer.tts_speak({"text": "hello"}))

        call_kwargs = consumer.send.call_args
        text_data = call_kwargs[1].get("text_data") or call_kwargs[0][0]
        assert text_data.endswith("\x07")

    def test_tts_speak_base64_encodes_text(self):
        """The base64 segment inside the OSC escape must decode to the original text."""
        input_text = "speak this carefully"
        consumer = _build_consumer()
        _run(consumer.tts_speak({"text": input_text}))

        call_kwargs = consumer.send.call_args
        text_data = call_kwargs[1].get("text_data") or call_kwargs[0][0]

        # Extract b64 portion: between "speak:" and "\x07"
        prefix = "\x1b]9999;speak:"
        b64_part = text_data[len(prefix) : text_data.index("\x07")]
        decoded = base64.b64decode(b64_part.encode()).decode()
        assert decoded == input_text

    def test_tts_speak_exact_format(self):
        """Full OSC message must match the pattern exactly."""
        input_text = "exact format check"
        expected_b64 = base64.b64encode(input_text.encode()).decode()
        expected = f"\x1b]9999;speak:{expected_b64}\x07"

        consumer = _build_consumer()
        _run(consumer.tts_speak({"text": input_text}))

        call_kwargs = consumer.send.call_args
        text_data = call_kwargs[1].get("text_data") or call_kwargs[0][0]
        assert text_data == expected

    def test_tts_speak_unicode_text(self):
        """Unicode text must be correctly base64-encoded and sent."""
        input_text = "Bonjour le monde"
        consumer = _build_consumer()
        _run(consumer.tts_speak({"text": input_text}))

        call_kwargs = consumer.send.call_args
        text_data = call_kwargs[1].get("text_data") or call_kwargs[0][0]

        prefix = "\x1b]9999;speak:"
        b64_part = text_data[len(prefix) : text_data.index("\x07")]
        decoded = base64.b64decode(b64_part.encode()).decode()
        assert decoded == input_text


# ---------------------------------------------------------------------------
# tts_speak: empty / missing text guard
# ---------------------------------------------------------------------------


class TestTtsSpeakEmptyTextNoSend:
    """tts_speak must not send anything when text is empty or absent."""

    def test_empty_string_does_not_call_send(self):
        """tts_speak({'text': ''}) must not call self.send at all."""
        consumer = _build_consumer()
        _run(consumer.tts_speak({"text": ""}))
        consumer.send.assert_not_called()

    def test_missing_text_key_does_not_call_send(self):
        """tts_speak({}) (no 'text' key) must not call self.send."""
        consumer = _build_consumer()
        _run(consumer.tts_speak({}))
        consumer.send.assert_not_called()


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])
