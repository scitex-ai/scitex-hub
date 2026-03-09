#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/console_app/services/terminal_broker/broker.py

Tests message routing, input/resize/close dispatch.
"""

import base64
import json
import os
import struct
from unittest.mock import MagicMock, patch

import pytest

from apps.workspace.console_app.services.terminal_broker.broker import TerminalBroker

# ---------------------------------------------------------------------------
# Message routing
# ---------------------------------------------------------------------------


class TestHandleMessageRouting:
    """_handle_message dispatches to correct handler based on action."""

    def _make_broker(self):
        broker = TerminalBroker.__new__(TerminalBroker)
        broker.sessions = {}
        broker.session_index = {}
        broker.allocations = {}
        broker.alloc_index = {}
        broker.shells = {}
        broker.shell_index = {}
        broker.lock = __import__("threading").Lock()
        return broker

    def test_unknown_action_returns_error(self):
        broker = self._make_broker()
        client = MagicMock()
        result = broker._handle_message({"action": "nonexistent"}, client)
        assert result["status"] == "error"
        assert "Unknown action" in result["error"]

    @patch(
        "apps.workspace.console_app.services.terminal_broker.broker.SHARED_ALLOCATION",
        False,
    )
    def test_spawn_routes_to_legacy(self):
        broker = self._make_broker()
        client = MagicMock()
        with patch(
            "apps.workspace.console_app.services.terminal_broker.broker.TerminalBroker._handle_spawn"
        ) as mock:
            mock.return_value = {"status": "ok"}
            result = broker._handle_message({"action": "spawn"}, client)
            mock.assert_called_once()

    def test_input_routes_to_handle_input(self):
        broker = self._make_broker()
        client = MagicMock()
        with patch.object(broker, "_handle_input", return_value=None) as mock:
            broker._handle_message({"action": "input"}, client)
            mock.assert_called_once()

    def test_resize_routes_to_handle_resize(self):
        broker = self._make_broker()
        client = MagicMock()
        with patch.object(broker, "_handle_resize", return_value=None) as mock:
            broker._handle_message({"action": "resize"}, client)
            mock.assert_called_once()

    def test_close_routes_to_handle_close(self):
        broker = self._make_broker()
        client = MagicMock()
        with patch.object(
            broker, "_handle_close", return_value={"status": "ok"}
        ) as mock:
            broker._handle_message({"action": "close"}, client)
            mock.assert_called_once()


# ---------------------------------------------------------------------------
# Input dispatch
# ---------------------------------------------------------------------------


class TestHandleInput:
    """_handle_input writes data to the correct session or shell."""

    def _make_broker(self):
        broker = TerminalBroker.__new__(TerminalBroker)
        broker.sessions = {}
        broker.shells = {}
        broker.lock = __import__("threading").Lock()
        return broker

    def test_input_writes_to_session(self):
        broker = self._make_broker()
        mock_session = MagicMock()
        broker.sessions["sess-1"] = mock_session
        data = base64.b64encode(b"ls\n").decode()
        broker._handle_input({"session_id": "sess-1", "data": data})
        mock_session.write.assert_called_once_with(b"ls\n")

    def test_input_writes_to_shell(self):
        broker = self._make_broker()
        mock_shell = MagicMock()
        broker.shells["shell-1"] = mock_shell
        data = base64.b64encode(b"pwd\n").decode()
        broker._handle_input({"session_id": "shell-1", "data": data})
        mock_shell.write.assert_called_once_with(b"pwd\n")

    def test_input_noop_for_unknown_id(self):
        broker = self._make_broker()
        result = broker._handle_input(
            {"session_id": "unknown", "data": base64.b64encode(b"x").decode()}
        )
        assert result is None


# ---------------------------------------------------------------------------
# Resize dispatch
# ---------------------------------------------------------------------------


class TestHandleResize:
    """_handle_resize sets window size on the correct session or shell."""

    def _make_broker(self):
        broker = TerminalBroker.__new__(TerminalBroker)
        broker.sessions = {}
        broker.shells = {}
        broker.lock = __import__("threading").Lock()
        return broker

    def test_resize_session(self):
        broker = self._make_broker()
        mock_session = MagicMock()
        broker.sessions["sess-1"] = mock_session
        broker._handle_resize({"session_id": "sess-1", "rows": 40, "cols": 120})
        mock_session.resize.assert_called_once_with(40, 120)

    def test_resize_shell(self):
        broker = self._make_broker()
        mock_shell = MagicMock()
        broker.shells["shell-1"] = mock_shell
        broker._handle_resize({"session_id": "shell-1", "rows": 30, "cols": 100})
        mock_shell.resize.assert_called_once_with(30, 100)

    def test_resize_defaults(self):
        broker = self._make_broker()
        mock_session = MagicMock()
        broker.sessions["sess-1"] = mock_session
        broker._handle_resize({"session_id": "sess-1"})
        mock_session.resize.assert_called_once_with(24, 80)


# ---------------------------------------------------------------------------
# Close dispatch
# ---------------------------------------------------------------------------


class TestHandleClose:
    """_handle_close removes and closes sessions/shells."""

    def _make_broker(self):
        broker = TerminalBroker.__new__(TerminalBroker)
        broker.sessions = {}
        broker.session_index = {}
        broker.allocations = {}
        broker.shells = {}
        broker.shell_index = {}
        broker.lock = __import__("threading").Lock()
        return broker

    def test_close_legacy_session(self):
        broker = self._make_broker()
        mock_session = MagicMock()
        broker.sessions["sess-1"] = mock_session
        broker.session_index[("alice", "scitex-0")] = "sess-1"
        result = broker._handle_close({"session_id": "sess-1"})
        assert result["status"] == "ok"
        mock_session.close.assert_called_once()
        assert "sess-1" not in broker.sessions

    def test_close_shared_shell(self):
        broker = self._make_broker()
        mock_shell = MagicMock()
        mock_shell.allocation_id = "alloc-1"
        mock_alloc = MagicMock()
        broker.shells["shell-1"] = mock_shell
        broker.shell_index[("alice", "scitex-0")] = "shell-1"
        broker.allocations["alloc-1"] = mock_alloc
        result = broker._handle_close({"session_id": "shell-1"})
        assert result["status"] == "ok"
        mock_shell.close.assert_called_once()
        mock_alloc.decrement_shells.assert_called_once()
        assert "shell-1" not in broker.shells

    def test_close_unknown_returns_ok(self):
        broker = self._make_broker()
        result = broker._handle_close({"session_id": "unknown"})
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# send_message format
# ---------------------------------------------------------------------------


class TestSendMessage:
    """_send_message sends length-prefixed JSON."""

    def test_send_message_format(self):
        broker = TerminalBroker.__new__(TerminalBroker)
        mock_sock = MagicMock()
        broker._send_message(mock_sock, {"status": "ok"})
        mock_sock.sendall.assert_called_once()
        raw = mock_sock.sendall.call_args[0][0]
        length = struct.unpack(">I", raw[:4])[0]
        payload = json.loads(raw[4:].decode())
        assert payload == {"status": "ok"}
        assert length == len(raw) - 4


# ---------------------------------------------------------------------------
# Output callback
# ---------------------------------------------------------------------------


class TestMakeOutputCallback:
    """_make_output_callback creates a callback that sends base64 output."""

    def test_output_callback_sends_data(self):
        broker = TerminalBroker.__new__(TerminalBroker)
        mock_sock = MagicMock()
        cb = broker._make_output_callback(mock_sock)
        cb("sess-1", b"hello world")
        mock_sock.sendall.assert_called_once()
        raw = mock_sock.sendall.call_args[0][0]
        payload = json.loads(raw[4:].decode())
        assert payload["action"] == "output"
        assert payload["session_id"] == "sess-1"
        assert base64.b64decode(payload["data"]) == b"hello world"


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__), "-v"])
