"""Usage statistics helper extracted from UserLLMService for file size compliance."""

from typing import Any, Dict, List

from django.db import models
from django.db.models import Count, Sum
from django.db.models.functions import TruncDay
from django.utils import timezone


def get_usage_stats(connection, llm_connection, days: int = 30) -> Dict[str, Any]:
    """Get usage statistics for an LLM connection.

    Args:
        connection: Active IntegrationConnection instance
        llm_connection: Related LLMConnection instance
        days: Number of days to look back
    """
    if not connection:
        return {"error": "No active connection"}

    since = timezone.now() - timezone.timedelta(days=days)
    logs = connection.llm_usage_logs.filter(created_at__gte=since)

    total_requests = logs.count()
    successful_requests = logs.filter(success=True).count()
    failed_requests = logs.filter(success=False).count()

    token_stats = logs.aggregate(
        total_tokens=models.Sum("total_tokens"),
        total_prompt_tokens=models.Sum("prompt_tokens"),
        total_completion_tokens=models.Sum("completion_tokens"),
    )

    total_cost = (
        logs.aggregate(total_cost=models.Sum("estimated_cost_usd"))["total_cost"] or 0
    )

    app_breakdown = {}
    for log in logs.values("app_name").annotate(
        count=models.Count("id"),
        tokens=models.Sum("total_tokens"),
        cost=models.Sum("estimated_cost_usd"),
    ):
        app_breakdown[log["app_name"]] = {
            "requests": log["count"],
            "tokens": log["tokens"],
            "cost": float(log["cost"] or 0),
        }

    return {
        "provider": connection.get_service_display(),
        "period_days": days,
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "token_usage": {
            "total": token_stats["total_tokens"] or 0,
            "prompt": token_stats["total_prompt_tokens"] or 0,
            "completion": token_stats["total_completion_tokens"] or 0,
        },
        "total_cost_usd": float(total_cost),
        "by_app": app_breakdown,
        "today": llm_connection.get_daily_usage(),
        "rate_limits": {
            "daily_request_limit": llm_connection.daily_request_limit,
            "daily_token_limit": llm_connection.daily_token_limit,
        },
    }


def get_usage_time_series(
    connection, days: int = 30, granularity: str = "day"
) -> List[Dict]:
    """Get time series of usage data for charts.

    Args:
        connection: Active IntegrationConnection instance
        days: Number of days to look back
        granularity: Aggregation granularity (currently only "day" supported)

    Returns:
        List of dicts: [{"date": date, "requests": N, "tokens": N, "cost": float}]
    """
    if not connection:
        return []

    since = timezone.now() - timezone.timedelta(days=days)
    logs = connection.llm_usage_logs.filter(created_at__gte=since)

    rows = (
        logs.annotate(date=TruncDay("created_at"))
        .values("date")
        .annotate(
            requests=Count("id"),
            tokens=Sum("total_tokens"),
            cost=Sum("estimated_cost_usd"),
        )
        .order_by("date")
    )

    return [
        {
            "date": row["date"].date() if row["date"] else None,
            "requests": row["requests"] or 0,
            "tokens": row["tokens"] or 0,
            "cost": float(row["cost"] or 0),
        }
        for row in rows
    ]


def get_usage_by_model(connection, days: int = 30) -> List[Dict]:
    """Get usage breakdown by model.

    Args:
        connection: Active IntegrationConnection instance
        days: Number of days to look back

    Returns:
        List of dicts: [{"model": str, "requests": N, "tokens": N, "cost": float}]
    """
    if not connection:
        return []

    since = timezone.now() - timezone.timedelta(days=days)
    logs = connection.llm_usage_logs.filter(created_at__gte=since)

    rows = (
        logs.values("model_used")
        .annotate(
            requests=Count("id"),
            tokens=Sum("total_tokens"),
            cost=Sum("estimated_cost_usd"),
        )
        .order_by("-requests")
    )

    return [
        {
            "model": row["model_used"] or "unknown",
            "requests": row["requests"] or 0,
            "tokens": row["tokens"] or 0,
            "cost": float(row["cost"] or 0),
        }
        for row in rows
    ]
