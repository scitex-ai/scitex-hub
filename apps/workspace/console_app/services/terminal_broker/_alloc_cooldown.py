"""Hard-failure cooldown state for shared allocations.

Extracted from ``_handlers_shared.py`` (512-line cap). One shared,
process-local dict tracks recent hard allocation failures (node DOWN,
SLURM not installed) so spawn/recovery paths back off with escalating
cooldowns instead of hammering a dead scheduler.
"""

# Cooldown: don't retry allocation after hard failures (node DOWN, not installed)
# Escalates: 30s -> 60s -> 120s -> 240s (capped at 4 min)
_HARD_FAIL_COOLDOWN_BASE = 30  # seconds
_HARD_FAIL_COOLDOWN_MAX = 240  # seconds

# alloc_key -> (timestamp, reason, fail_count)
_hard_fail_info: dict[tuple, tuple[float, str, int]] = {}


def _get_cooldown(fail_count: int) -> int:
    """Return escalating cooldown in seconds based on consecutive failure count."""
    return min(_HARD_FAIL_COOLDOWN_BASE * (2**fail_count), _HARD_FAIL_COOLDOWN_MAX)


# EOF
