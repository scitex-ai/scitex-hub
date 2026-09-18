"""Disabled compatibility shims for the retired campaign chat path.

All server-funded traffic must enter ``FundedChatService.execute``. Keeping the
old shared-key adapter callable would reintroduce an unfenced billing path, so
these names remain only to fail closed for stale imports during rollout.
"""

from __future__ import annotations


class LegacyCampaignPathDisabled(RuntimeError):
    pass


def is_campaign_enabled() -> bool:
    return False


def get_campaign_config() -> dict:
    raise LegacyCampaignPathDisabled("legacy campaign chat is disabled")


def check_campaign_rate_limit(request) -> tuple[bool, int, str | None]:
    return False, 0, "Funded chat is unavailable"


def increment_campaign_usage(request) -> None:
    raise LegacyCampaignPathDisabled("legacy campaign chat is disabled")


async def campaign_complete_streaming(messages: list[dict]):
    raise LegacyCampaignPathDisabled("legacy campaign chat is disabled")
