"""Connection and authentication throttling for the public SSH gateway.

The gateway is a public login service (like an HPC login node), so it has to
withstand scanning and key-guessing without help from the network. Three
limits apply, all in memory in the gateway process:

* concurrent connections per source address;
* new connections per source address per minute;
* temporary bans: a source address, or a username, that accumulates
  ``max_failures`` failed connections within ``window`` seconds is refused
  for ``ban`` seconds.

A *failed connection* is a connection that tried to authenticate and never
succeeded. Counting connections instead of individual attempts matters:
an ``ssh`` client with an agent offers each of its keys in turn, so a
legitimate user with several keys makes several failed attempts before the
right key succeeds.

Sources listed in ``trusted_proxies`` (the WebSocket bridge, which connects
on behalf of many users) are exempt from the per-address limits; usernames
are still banned, and the bridge itself requires a signed-in Hub session.

All limits come from environment variables so operators can tune them
without a release (see docs/ops/ssh-gateway.md).
"""

from __future__ import annotations

import ipaddress
import os
import socket
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    value = int(raw)
    if value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _parse_proxies(raw: str) -> tuple:
    """IPs/CIDRs stay networks; anything else is a hostname resolved later.

    A hostname (e.g. the ``ws_ssh_proxy`` compose service) is the robust way
    to name a container whose address changes on recreate. Never trust a
    whole Docker subnet: the subnet gateway is also where published-port
    traffic can appear to come from.
    """
    entries = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            entries.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            entries.append(item)
    return tuple(entries)


def _resolve(hostname: str) -> set:
    try:
        return {info[4][0] for info in socket.getaddrinfo(hostname, None)}
    except OSError:
        return set()


@dataclass(frozen=True)
class ThrottleConfig:
    max_concurrent_per_source: int = 10
    max_new_per_minute_per_source: int = 30
    max_failures: int = 5
    window_seconds: int = 600
    ban_seconds: int = 900
    max_auth_attempts_per_connection: int = 12
    trusted_proxies: tuple = field(default_factory=tuple)

    @classmethod
    def from_env(cls) -> "ThrottleConfig":
        prefix = "SCITEX_HUB_SSH_GATEWAY_"
        return cls(
            max_concurrent_per_source=_env_int(
                f"{prefix}MAX_CONCURRENT_PER_SOURCE", 10
            ),
            max_new_per_minute_per_source=_env_int(f"{prefix}MAX_NEW_PER_MINUTE", 30),
            max_failures=_env_int(f"{prefix}MAX_FAILURES", 5),
            window_seconds=_env_int(f"{prefix}FAILURE_WINDOW_SECONDS", 600),
            ban_seconds=_env_int(f"{prefix}BAN_SECONDS", 900),
            max_auth_attempts_per_connection=_env_int(f"{prefix}MAX_AUTH_ATTEMPTS", 12),
            trusted_proxies=_parse_proxies(
                os.environ.get(f"{prefix}TRUSTED_PROXIES", "")
            ),
        )


class GatewayThrottle:
    """Thread-safe admission and ban bookkeeping."""

    def __init__(
        self,
        config: ThrottleConfig | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.config = config or ThrottleConfig()
        self._clock = clock
        self._lock = threading.Lock()
        self._active: dict[str, int] = defaultdict(int)
        self._recent: dict[str, deque] = defaultdict(deque)
        self._failures: dict[str, deque] = defaultdict(deque)
        self._banned_until: dict[str, float] = {}
        self._resolved: tuple[float, set] = (float("-inf"), set())

    # -- keys ---------------------------------------------------------------
    def _trusted_host_addresses(self) -> set:
        names = [e for e in self.config.trusted_proxies if isinstance(e, str)]
        if not names:
            return set()
        resolved_at, addresses = self._resolved
        now = self._clock()
        if now - resolved_at > 60:
            addresses = set().union(*(_resolve(name) for name in names))
            self._resolved = (now, addresses)
        return addresses

    def is_trusted_proxy(self, source: str) -> bool:
        try:
            address = ipaddress.ip_address(source)
        except ValueError:
            return False
        networks = [e for e in self.config.trusted_proxies if not isinstance(e, str)]
        if any(address in network for network in networks):
            return True
        return source in self._trusted_host_addresses()

    @staticmethod
    def _source_key(source: str) -> str:
        return f"ip:{source}"

    @staticmethod
    def _user_key(username: str) -> str:
        return f"user:{username.lower()}"

    # -- helpers (caller holds the lock) ------------------------------------
    def _prune(self, queue: deque, horizon: float) -> None:
        while queue and queue[0] <= horizon:
            queue.popleft()

    def _ban_active(self, key: str, now: float) -> bool:
        until = self._banned_until.get(key)
        if until is None:
            return False
        if until <= now:
            del self._banned_until[key]
            return False
        return True

    # -- public API ---------------------------------------------------------
    def admit(self, source: str) -> tuple[bool, str]:
        """Decide whether to accept a new TCP connection from ``source``.

        On ``True`` the caller must call :meth:`release` when it ends.
        """
        now = self._clock()
        with self._lock:
            if self.is_trusted_proxy(source):
                self._active[source] += 1
                return True, "trusted-proxy"
            key = self._source_key(source)
            if self._ban_active(key, now):
                return False, "banned"
            if self._active[source] >= self.config.max_concurrent_per_source:
                return False, "too-many-concurrent"
            recent = self._recent[source]
            self._prune(recent, now - 60)
            if len(recent) >= self.config.max_new_per_minute_per_source:
                return False, "too-many-new"
            recent.append(now)
            self._active[source] += 1
            return True, "ok"

    def release(self, source: str) -> None:
        with self._lock:
            if self._active.get(source, 0) > 0:
                self._active[source] -= 1
            if self._active.get(source) == 0:
                del self._active[source]

    def username_banned(self, username: str) -> bool:
        with self._lock:
            return self._ban_active(self._user_key(username), self._clock())

    def record_failed_connection(self, source: str, username: str | None) -> list[str]:
        """Count one failed connection; return the keys that became banned."""
        now = self._clock()
        keys = []
        if not self.is_trusted_proxy(source):
            keys.append(self._source_key(source))
        if username:
            keys.append(self._user_key(username))
        newly_banned = []
        with self._lock:
            for key in keys:
                failures = self._failures[key]
                self._prune(failures, now - self.config.window_seconds)
                failures.append(now)
                if len(failures) >= self.config.max_failures and not self._ban_active(
                    key, now
                ):
                    self._banned_until[key] = now + self.config.ban_seconds
                    failures.clear()
                    newly_banned.append(key)
        return newly_banned

    def record_success(self, source: str, username: str) -> None:
        """A successful login clears that username's failure history."""
        with self._lock:
            self._failures.pop(self._user_key(username), None)


# EOF
