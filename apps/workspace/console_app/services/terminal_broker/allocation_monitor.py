"""Allocation health monitor — warns before expiry + node health daemon."""

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .broker import TerminalBroker

from ._handler_utils import send_state
from .slurm_health import NodeHealthDaemon, set_daemon

logger = logging.getLogger(__name__)

WARNING_THRESHOLDS = [900, 300, 60]  # 15min, 5min, 1min in seconds
CHECK_INTERVAL = 30  # seconds between health checks


class AllocationMonitor:
    """Background thread that warns clients before their allocation expires.

    Also starts and manages the NodeHealthDaemon for proactive node recovery.
    """

    def __init__(self, broker: "TerminalBroker"):
        self.broker = broker
        self._stop = threading.Event()
        self._thread = None
        self._warned: dict[str, set] = {}  # alloc_id -> set of thresholds warned
        self._node_daemon = NodeHealthDaemon()

    def start(self):
        """Start the monitor thread and node health daemon."""
        # Start node health daemon first (spawn path depends on it)
        self._node_daemon.start()
        set_daemon(self._node_daemon)

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("AllocationMonitor started")

    def stop(self):
        """Stop the monitor thread and node health daemon."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

        self._node_daemon.stop()
        set_daemon(None)

        logger.info("AllocationMonitor stopped")

    def _run(self):
        while not self._stop.is_set():
            try:
                self._check_all()
            except Exception as e:
                logger.error(f"AllocationMonitor error: {e}")
            self._stop.wait(CHECK_INTERVAL)

    def _check_all(self):
        with self.broker.lock:
            allocs = list(self.broker.allocations.items())
            shells = list(self.broker.shells.values())

        for alloc_id, alloc in allocs:
            if alloc.state.value != "ready":
                continue
            remaining = alloc.get_remaining_seconds()
            if remaining is None:
                continue

            warned = self._warned.setdefault(alloc_id, set())
            for threshold in WARNING_THRESHOLDS:
                if remaining <= threshold and threshold not in warned:
                    warned.add(threshold)
                    self._notify_shells(alloc_id, shells, remaining)
                    break

    def _notify_shells(self, alloc_id: str, shells: list, remaining: int):
        """Send expiry warning to all shells attached to this allocation."""
        for shell in shells:
            if shell.allocation_id != alloc_id:
                continue
            if not shell.client_socket:
                continue
            send_state(
                self.broker,
                shell.client_socket,
                shell.pty_id,
                "allocation_expiring",
                extra={"remaining": remaining},
            )
            logger.info(
                f"Allocation {alloc_id[:8]}: warned shell {shell.pty_id[:8]}, "
                f"{remaining}s remaining"
            )


# EOF
