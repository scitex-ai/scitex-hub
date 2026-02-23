"""LLM usage dashboard views — HTML summary page and PNG chart endpoints."""

import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from apps.llm_app.services import UserLLMService
from apps.llm_app.services._usage_charts import (
    generate_cost_chart,
    generate_model_breakdown_chart,
    generate_tokens_chart,
)
from apps.llm_app.services._usage_stats import (
    get_usage_by_model,
    get_usage_time_series,
)

logger = logging.getLogger("scitex")

_VALID_CHART_TYPES = {"cost", "tokens", "model_breakdown"}


@login_required
def usage_dashboard(request):
    """HTML page with summary cards and embedded chart images."""
    days = int(request.GET.get("days", 30))

    service = UserLLMService(user=request.user)

    context = {
        "days": days,
        "has_connection": bool(service.connection),
        "stats": None,
    }

    if service.connection and service.llm_connection:
        context["stats"] = service.get_usage_stats(days=days)

    return render(request, "llm_app/usage_dashboard.html", context)


@login_required
def api_usage_chart(request, chart_type: str):
    """Return a PNG chart image for the requested chart type.

    URL param:
        days (int): look-back window, default 30.

    Supported chart_type values: cost, tokens, model_breakdown.
    """
    if chart_type not in _VALID_CHART_TYPES:
        return JsonResponse(
            {"error": f"Invalid chart_type. Choose from: {sorted(_VALID_CHART_TYPES)}"},
            status=400,
        )

    days = int(request.GET.get("days", 30))

    service = UserLLMService(user=request.user)

    if not service.connection:
        # Return a minimal transparent placeholder rather than an error page
        png = _empty_chart_png()
        return HttpResponse(png, content_type="image/png")

    try:
        if chart_type == "cost":
            time_series = get_usage_time_series(service.connection, days=days)
            png = generate_cost_chart(time_series, days=days)
        elif chart_type == "tokens":
            time_series = get_usage_time_series(service.connection, days=days)
            png = generate_tokens_chart(time_series, days=days)
        elif chart_type == "model_breakdown":
            model_data = get_usage_by_model(service.connection, days=days)
            png = generate_model_breakdown_chart(model_data)
        else:
            # Unreachable due to guard above, but keeps linter happy
            return JsonResponse({"error": "Unknown chart type"}, status=400)

        return HttpResponse(png, content_type="image/png")

    except Exception as exc:
        logger.error("Failed to generate %s chart: %s", chart_type, exc)
        return HttpResponse(status=500)


def _empty_chart_png() -> bytes:
    """Return a minimal 1x1 transparent PNG for 'no connection' state."""
    import io

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5, 3))
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)
    ax.text(
        0.5,
        0.5,
        "No LLM connection",
        transform=ax.transAxes,
        ha="center",
        va="center",
        color="#d0dce3",
        fontsize=12,
    )
    ax.axis("off")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=72, transparent=True, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
