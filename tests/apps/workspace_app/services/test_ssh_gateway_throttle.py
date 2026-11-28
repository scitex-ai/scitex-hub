"""GatewayThrottle: admission limits and temporary bans for the SSH gateway.

Pure logic with an injected clock, so no sleeping and no mocks.
"""

from __future__ import annotations

import pytest

from apps.infra.workspace_app.services.ssh_gateway.throttle import (
    GatewayThrottle,
    ThrottleConfig,
    _parse_proxies,
)


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock()


def _throttle(clock, **overrides):
    config = ThrottleConfig(**overrides)
    return GatewayThrottle(config, clock=clock)


def test_first_connection_is_admitted(clock):
    # Arrange
    throttle = _throttle(clock)
    # Act
    admitted, _reason = throttle.admit("203.0.113.7")
    # Assert
    assert admitted


def test_concurrent_connections_beyond_the_limit_are_refused(clock):
    # Arrange
    throttle = _throttle(clock, max_concurrent_per_source=2)
    throttle.admit("203.0.113.7")
    throttle.admit("203.0.113.7")
    # Act
    _admitted, reason = throttle.admit("203.0.113.7")
    # Assert
    assert reason == "too-many-concurrent"


def test_released_slot_can_be_reused(clock):
    # Arrange
    throttle = _throttle(clock, max_concurrent_per_source=1)
    throttle.admit("203.0.113.7")
    throttle.release("203.0.113.7")
    # Act
    admitted, _reason = throttle.admit("203.0.113.7")
    # Assert
    assert admitted


def test_new_connection_rate_is_limited_per_minute(clock):
    # Arrange
    throttle = _throttle(clock, max_new_per_minute_per_source=3)
    for _ in range(3):
        throttle.admit("203.0.113.7")
        throttle.release("203.0.113.7")
    # Act
    _admitted, reason = throttle.admit("203.0.113.7")
    # Assert
    assert reason == "too-many-new"


def test_new_connection_rate_recovers_after_a_minute(clock):
    # Arrange
    throttle = _throttle(clock, max_new_per_minute_per_source=1)
    throttle.admit("203.0.113.7")
    throttle.release("203.0.113.7")
    clock.now += 61
    # Act
    admitted, _reason = throttle.admit("203.0.113.7")
    # Assert
    assert admitted


def test_repeated_failed_connections_ban_the_source(clock):
    # Arrange
    throttle = _throttle(clock, max_failures=3)
    for _ in range(3):
        throttle.record_failed_connection("203.0.113.7", "alice")
    # Act
    _admitted, reason = throttle.admit("203.0.113.7")
    # Assert
    assert reason == "banned"


def test_repeated_failed_connections_ban_the_username(clock):
    # Arrange
    throttle = _throttle(clock, max_failures=3)
    for octet in range(3):
        throttle.record_failed_connection(f"203.0.113.{octet}", "Alice")
    # Act
    banned = throttle.username_banned("alice")
    # Assert
    assert banned


def test_source_ban_expires_after_ban_seconds(clock):
    # Arrange
    throttle = _throttle(clock, max_failures=1, ban_seconds=900)
    throttle.record_failed_connection("203.0.113.7", "alice")
    clock.now += 901
    # Act
    admitted, _reason = throttle.admit("203.0.113.7")
    # Assert
    assert admitted


def test_failures_outside_the_window_do_not_accumulate(clock):
    # Arrange
    throttle = _throttle(clock, max_failures=2, window_seconds=600)
    throttle.record_failed_connection("203.0.113.7", "alice")
    clock.now += 601
    throttle.record_failed_connection("203.0.113.7", "alice")
    # Act
    banned = throttle.username_banned("alice")
    # Assert
    assert not banned


def test_success_clears_the_username_failure_history(clock):
    # Arrange
    throttle = _throttle(clock, max_failures=2)
    throttle.record_failed_connection("203.0.113.7", "alice")
    throttle.record_success("203.0.113.7", "alice")
    throttle.record_failed_connection("203.0.113.8", "alice")
    # Act
    banned = throttle.username_banned("alice")
    # Assert
    assert not banned


def test_trusted_proxy_is_never_banned_by_address(clock):
    # Arrange
    throttle = _throttle(
        clock, max_failures=1, trusted_proxies=_parse_proxies("10.9.0.5")
    )
    throttle.record_failed_connection("10.9.0.5", "alice")
    # Act
    admitted, _reason = throttle.admit("10.9.0.5")
    # Assert
    assert admitted


def test_trusted_proxy_still_bans_the_username(clock):
    # Arrange
    throttle = _throttle(
        clock, max_failures=1, trusted_proxies=_parse_proxies("10.9.0.0/24")
    )
    throttle.record_failed_connection("10.9.0.5", "alice")
    # Act
    banned = throttle.username_banned("alice")
    # Assert
    assert banned


def test_trusted_proxy_hostname_is_resolved(clock):
    # Arrange
    throttle = _throttle(clock, trusted_proxies=_parse_proxies("localhost"))
    # Act
    trusted = throttle.is_trusted_proxy("127.0.0.1")
    # Assert
    assert trusted


def test_untrusted_address_is_not_a_proxy(clock):
    # Arrange
    throttle = _throttle(clock, trusted_proxies=_parse_proxies("localhost"))
    # Act
    trusted = throttle.is_trusted_proxy("203.0.113.7")
    # Assert
    assert not trusted


@pytest.fixture
def zero_max_failures_env():
    import os

    name = "SCITEX_HUB_SSH_GATEWAY_MAX_FAILURES"
    previous = os.environ.get(name)
    os.environ[name] = "0"
    yield
    if previous is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous


def test_from_env_rejects_non_positive_limits(zero_max_failures_env):
    # Arrange
    env_name = "SCITEX_HUB_SSH_GATEWAY_MAX_FAILURES"
    # Act
    # Assert
    with pytest.raises(ValueError, match=env_name):
        ThrottleConfig.from_env()
