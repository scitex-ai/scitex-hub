import time
from typing import Any, Dict, Optional

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

        self._find_active_connection()

    def _find_active_connection(self):
        """Find the active LLM connection for the user."""
        from apps.llm_app.utils import ALL_LLM_SERVICE_IDS

        query = IntegrationConnection.objects.filter(
            user=self.user,
            service__in=list(ALL_LLM_SERVICE_IDS),
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
            import litellm

            # Get API key
            from apps.llm_app.utils import LLM_PROVIDERS

            api_key = self.connection.get_api_key()
            needs_key = LLM_PROVIDERS.get(self.connection.service, {}).get(
                "needs_key", True
            )
            if not api_key and needs_key:
                raise LLMProviderError("No API key configured for this connection")

            from apps.llm_app.utils import litellm_model_string

            litellm_model = litellm_model_string(self.connection.service, model_to_use)

            result = litellm.completion(
                model=litellm_model,
                messages=[{"role": "user", "content": prompt}],
                api_key=api_key,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )

            # Cost from litellm (uses up-to-date provider pricing)
            try:
                estimated_cost = litellm.completion_cost(completion_response=result)
            except Exception:
                estimated_cost = 0.0

            response = {
                "text": result.choices[0].message.content,
                "usage": {
                    "prompt_tokens": result.usage.prompt_tokens,
                    "completion_tokens": result.usage.completion_tokens,
                },
                "estimated_cost": estimated_cost,
            }

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

        estimated_cost = response.get("estimated_cost", 0.0)

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

    async def complete_with_tools(
        self,
        messages: list,
        app_name: str,
        feature: str,
        model: Optional[str] = None,
        max_tokens: int = 8192,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Generate a completion with MCP tool access (async).

        Loads tools from the scitex MCP server, runs the LLM + tool loop,
        and logs usage.

        Returns:
            Dict with text, tools_used, usage, cost info.
        """
        from asgiref.sync import sync_to_async

        from apps.llm_app.services.mcp_client import load_openai_tools, run_tool_loop

        if not self.connection:
            raise LLMProviderError("No active LLM connection found for this user")

        allowed, error_msg = await sync_to_async(self.check_rate_limits)()
        if not allowed:
            raise RateLimitError(error_msg)

        model_to_use = model or self.llm_connection.default_model
        if not model_to_use:
            raise LLMProviderError("No model specified and no default model configured")

        api_key = await sync_to_async(self.connection.get_api_key)()
        from apps.llm_app.utils import LLM_PROVIDERS, litellm_model_string

        needs_key = LLM_PROVIDERS.get(self.connection.service, {}).get(
            "needs_key", True
        )
        if not api_key and needs_key:
            raise LLMProviderError("No API key configured for this connection")

        litellm_model = litellm_model_string(self.connection.service, model_to_use)
        log_usage = sync_to_async(self._log_usage)

        start_time = time.time()
        try:
            tools = await load_openai_tools()
            text, tools_used = await run_tool_loop(
                litellm_model=litellm_model,
                api_key=api_key,
                messages=messages,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            await log_usage(
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

        response_time_ms = int((time.time() - start_time) * 1000)
        await log_usage(
            app_name=app_name,
            feature=feature,
            model_used=model_to_use,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            response_time_ms=response_time_ms,
            estimated_cost_usd=0,
            success=True,
        )

        return {
            "text": text,
            "tools_used": tools_used,
            "response_time_ms": response_time_ms,
        }

    async def complete_with_tools_streaming(
        self,
        messages: list,
        app_name: str,
        feature: str,
        model: Optional[str] = None,
        max_tokens: int = 8192,
        temperature: float = 0.3,
    ):
        """
        Streaming version of complete_with_tools.

        Yields SSE-ready dicts:
          {"type": "model",      "name": "provider/model"}
          {"type": "chunk",      "text": "..."}
          {"type": "tool_start", "name": "tool_name"}
          {"type": "tool_end",   "name": "tool_name"}
          {"type": "done",       "tools_used": [...], "response_time_ms": N}
          {"type": "error",      "error": "..."}
        """
        from asgiref.sync import sync_to_async

        from apps.llm_app.services.mcp_client import (
            load_openai_tools,
            run_tool_loop_streaming,
        )
        from apps.llm_app.utils import LLM_PROVIDERS, litellm_model_string

        if not self.connection:
            yield {"type": "error", "error": "No active LLM connection found"}
            return

        allowed, error_msg = await sync_to_async(self.check_rate_limits)()
        if not allowed:
            yield {"type": "error", "error": error_msg}
            return

        model_to_use = model or self.llm_connection.default_model
        if not model_to_use:
            yield {
                "type": "error",
                "error": "No model specified and no default model configured",
            }
            return

        api_key = await sync_to_async(self.connection.get_api_key)()
        needs_key = LLM_PROVIDERS.get(self.connection.service, {}).get(
            "needs_key", True
        )
        if not api_key and needs_key:
            yield {
                "type": "error",
                "error": "No API key configured for this connection",
            }
            return

        litellm_model = litellm_model_string(self.connection.service, model_to_use)
        yield {"type": "model", "name": litellm_model or model_to_use}

        log_usage = sync_to_async(self._log_usage)
        start_time = time.time()
        tools_used: list[str] = []

        try:
            tools = await load_openai_tools()
            async for event in run_tool_loop_streaming(
                litellm_model=litellm_model,
                api_key=api_key,
                messages=messages,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
            ):
                if event["type"] == "tool_start":
                    tools_used.append(event["name"])
                if event["type"] == "done":
                    response_time_ms = int((time.time() - start_time) * 1000)
                    await log_usage(
                        app_name=app_name,
                        feature=feature,
                        model_used=model_to_use,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        response_time_ms=response_time_ms,
                        estimated_cost_usd=0,
                        success=True,
                    )
                    yield {**event, "response_time_ms": response_time_ms}
                else:
                    yield event
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            await log_usage(
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
            yield {"type": "error", "error": str(e)}

    def get_usage_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for the connection."""
        from apps.llm_app.services._usage_stats import get_usage_stats as _fn

        return _fn(self.connection, self.llm_connection, days)
