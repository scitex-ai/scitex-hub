"""Spend controls for SciTeX Cloud billing.

A per-account monthly usage cap with 50/80/100 % alerts, a hard stop for NEW
billable work at the cap, a grace window then a stop for RUNNING work,
failed-payment dunning, 30-day cancellation billed on actual usage, quota
enforcement, and idle auto-stop for interactive sessions.

Usage is read through :class:`apps.infra.spend_app.services.usage.UsageSource`.
The usage ledger (hub issue #1232) will implement that interface; until it
exists :class:`~apps.infra.spend_app.services.usage.ProvisionalUsageSource`
reads the best current source per resource and labels every line PROVISIONAL.
"""
