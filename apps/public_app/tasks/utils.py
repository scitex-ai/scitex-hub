#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utility functions for public_app tasks."""

from __future__ import annotations

import socket


def check_port(port: int, host: str = "127.0.0.1", timeout: int = 1) -> bool:
    """Check if a port is open/accessible."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


# EOF
