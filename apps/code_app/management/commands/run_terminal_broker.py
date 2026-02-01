#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Django management command to run the Terminal Broker.

The Terminal Broker handles PTY operations in a separate process from Daphne,
preventing asyncio/signal conflicts that can cause deadlocks.

Usage:
    python manage.py run_terminal_broker

The broker listens on /tmp/scitex-terminal-broker.sock and handles:
- PTY fork/exec for terminal sessions
- SIGCHLD handling for zombie reaping
- Clean process termination
"""

import logging
import os
import signal
import sys

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Run the terminal broker process."""

    help = "Run the terminal broker for PTY session management"

    def add_arguments(self, parser):
        parser.add_argument(
            "--socket-path",
            type=str,
            default="/tmp/scitex-terminal-broker.sock",
            help="Path to Unix socket (default: /tmp/scitex-terminal-broker.sock)",
        )

    def handle(self, *args, **options):
        """Run the terminal broker."""
        socket_path = options["socket_path"]

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] terminal-broker: %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )

        self.stdout.write(
            self.style.SUCCESS(f"Starting Terminal Broker on {socket_path}")
        )

        try:
            from apps.code_app.services.terminal_broker import TerminalBroker

            broker = TerminalBroker(socket_path=socket_path)

            def signal_handler(signum, frame):
                self.stdout.write("\nShutdown signal received")
                broker.stop()
                sys.exit(0)

            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)

            broker.start()

        except KeyboardInterrupt:
            self.stdout.write("\nShutdown requested")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Broker error: {e}"))
            raise
