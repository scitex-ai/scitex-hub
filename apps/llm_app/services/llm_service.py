import time
from typing import Any, Dict, Optional

from django.db import models
from django.utils import timezone

from apps.integrations_app.models import IntegrationConnection
from apps.llm_app.models import LLMUsageLog


class LLMProviderError(Exception):
    """Base exception for LLM provider errors"""

    pass


class RateLimitError(LLMProviderError):
    """Rate limit exceeded"""

    pass


class UserLLMService:
    """Service for managing user LLM connections and requests"""

    def __init__(self, user, preferred_provider: Optional[str] = None):
        """
        Initialize LLM service for a user.

        Args:
            user: Django User instance
            preferred_provider: Optional provider name (anthropic, openai, local_llm)
        """
        self.user = user
        self.preferred_provider = preferred_provider
        self.connection = None
        self.llm_connection = None

        # Try to load the scitex.llm module
        try:
            import scitex.llm

            self.scitex_llm = scitex.llm
        except (ImportError, AttributeError):
            self.scitex_llm = None

        self._find_active_connection()

    def _find_active_connection(self):
        """Find the active LLM connection for the user"""
        query = IntegrationConnection.objects.filter(
            user=self.user,
            service__in=["anthropic", "openai", "local_llm"],
            status="active",
        ).select_related("llm_connection")

        if self.preferred_provider:
            query = query.filter(service=self.preferred_provider)

        try:
            self.connection = query.first()
            if self.connection and hasattr(self.connection, "llm_connection"):
                self.llm_connection = self.connection.llm_connection
        except IntegrationConnection.DoesNotExist:
            pass

    def check_rate_limits(self) -> tuple[bool, Optional[str]]:
        """
        Check if the user has exceeded rate limits.

        Returns:
            (allowed, error_message): Tuple of boolean and optional error message
        """
        if not self.llm_connection:
            return False, "No active LLM connection found"

        return self.llm_connection.check_rate_limits()

    def complete(
        self,
        prompt: str,
        app_name: str,
        feature: str,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate a completion using the connected LLM provider.

        Args:
            prompt: The prompt text
            app_name: Which SciTeX app is using this (writer, scholar, console)
            feature: Feature name (improve_clarity, summarize, etc.)
            model: Optional model override
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters

        Returns:
            Dict containing response text, tokens used, and cost estimate
        """
        if not self.connection:
            raise LLMProviderError("No active LLM connection found for this user")

        # Check rate limits
        allowed, error_msg = self.check_rate_limits()
        if not allowed:
            raise RateLimitError(error_msg)

        # Use default model if not specified
        model_to_use = model or self.llm_connection.default_model
        if not model_to_use:
            raise LLMProviderError("No model specified and no default model configured")

        # Start timing
        start_time = time.time()

        try:
            # Get API key
            api_key = self.connection.get_api_key()
            if not api_key:
                raise LLMProviderError("No API key configured for this connection")

            # Call the appropriate provider
            if self.scitex_llm is None:
                # Stub response when scitex.llm is not available
                raise LLMProviderError(
                    "scitex.llm module not available. "
                    "This is a placeholder service. "
                    "Actual LLM calls will be implemented when scitex.llm is ready."
                )

            # TODO: Replace with actual scitex.llm calls when available
            # Example structure:
            # if self.connection.service == "anthropic":
            #     response = self.scitex_llm.anthropic.complete(
            #         api_key=api_key,
            #         model=model_to_use,
            #         prompt=prompt,
            #         max_tokens=max_tokens,
            #         temperature=temperature,
            #         **kwargs
            #     )
            # elif self.connection.service == "openai":
            #     response = self.scitex_llm.openai.complete(...)
            # elif self.connection.service == "local_llm":
            #     response = self.scitex_llm.local.complete(...)

            raise NotImplementedError(
                f"Provider {self.connection.service} not yet implemented"
            )

        except Exception as e:
            # Log failed request
            response_time_ms = int((time.time() - start_time) * 1000)
            self._log_usage(
                app_name=app_name,
                feature=feature,
                model_used=model_to_use,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                response_time_ms=response_time_ms,
                estimated_cost_usd=0,
                success=False,
                error_message=str(e),
            )
            raise

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        # Extract token counts from response
        prompt_tokens = response.get("usage", {}).get("prompt_tokens", 0)
        completion_tokens = response.get("usage", {}).get("completion_tokens", 0)
        total_tokens = prompt_tokens + completion_tokens

        # Estimate cost (placeholder - should be provider-specific)
        estimated_cost = self._estimate_cost(
            self.connection.service, model_to_use, prompt_tokens, completion_tokens
        )

        # Log successful request
        self._log_usage(
            app_name=app_name,
            feature=feature,
            model_used=model_to_use,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            response_time_ms=response_time_ms,
            estimated_cost_usd=estimated_cost,
            success=True,
        )

        # Update connection stats
        self.llm_connection.total_tokens_used += total_tokens
        self.llm_connection.total_requests += 1
        self.llm_connection.estimated_cost_usd += estimated_cost
        self.llm_connection.last_request_at = timezone.now()
        self.llm_connection.save()

        return {
            "text": response.get("text", ""),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": float(estimated_cost),
            "response_time_ms": response_time_ms,
        }

    def _estimate_cost(
        self, provider: str, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        """
        Estimate cost based on provider pricing.

        This is a placeholder implementation with rough estimates.
        Should be updated with actual pricing from each provider.
        """
        # Rough pricing estimates (per 1K tokens)
        pricing = {
            "anthropic": {
                "claude-sonnet-4-5": {"prompt": 0.003, "completion": 0.015},
                "claude-opus-4": {"prompt": 0.015, "completion": 0.075},
                "default": {"prompt": 0.003, "completion": 0.015},
            },
            "openai": {
                "gpt-4": {"prompt": 0.03, "completion": 0.06},
                "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
                "default": {"prompt": 0.001, "completion": 0.002},
            },
            "local_llm": {
                "default": {"prompt": 0.0, "completion": 0.0},  # Local is free
            },
        }

        provider_pricing = pricing.get(provider, {})
        model_pricing = provider_pricing.get(model, provider_pricing.get("default", {}))

        prompt_cost = (prompt_tokens / 1000) * model_pricing.get("prompt", 0)
        completion_cost = (completion_tokens / 1000) * model_pricing.get(
            "completion", 0
        )

        return prompt_cost + completion_cost

    def _log_usage(
        self,
        app_name: str,
        feature: str,
        model_used: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        response_time_ms: int,
        estimated_cost_usd: float,
        success: bool,
        error_message: str = "",
    ):
        """Log API usage to the database"""
        LLMUsageLog.objects.create(
            connection=self.connection,
            app_name=app_name,
            feature=feature,
            model_used=model_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            response_time_ms=response_time_ms,
            estimated_cost_usd=estimated_cost_usd,
            success=success,
            error_message=error_message,
        )

    def get_usage_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get usage statistics for the connection.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with usage statistics
        """
        if not self.connection:
            return {"error": "No active connection"}

        since = timezone.now() - timezone.timedelta(days=days)
        logs = self.connection.llm_usage_logs.filter(created_at__gte=since)

        # Overall stats
        total_requests = logs.count()
        successful_requests = logs.filter(success=True).count()
        failed_requests = logs.filter(success=False).count()

        # Token usage
        token_stats = logs.aggregate(
            total_tokens=models.Sum("total_tokens"),
            total_prompt_tokens=models.Sum("prompt_tokens"),
            total_completion_tokens=models.Sum("completion_tokens"),
        )

        # Cost
        total_cost = (
            logs.aggregate(total_cost=models.Sum("estimated_cost_usd"))["total_cost"]
            or 0
        )

        # Per-app breakdown
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

        # Daily usage
        daily_usage = self.llm_connection.get_daily_usage()

        return {
            "provider": self.connection.get_service_display(),
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
            "today": daily_usage,
            "rate_limits": {
                "daily_request_limit": self.llm_connection.daily_request_limit,
                "daily_token_limit": self.llm_connection.daily_token_limit,
            },
        }
