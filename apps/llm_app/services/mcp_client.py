#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2026-02-20"
# File: apps/llm_app/services/mcp_client.py

"""
Thin MCP client that runs scitex tools in-process (no separate container).

FastMCP's Client(mcp_instance) uses in-memory transport — zero network overhead.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Maximum number of tool-call round-trips before forcing a text reply
MAX_TOOL_ROUNDS = 10

# Lazy-loaded scitex MCP instance (avoids import-time side effects at startup)
_scitex_mcp = None


def _get_mcp():
    global _scitex_mcp
    if _scitex_mcp is None:
        from scitex.mcp_server import mcp

        _scitex_mcp = mcp
    return _scitex_mcp


def _mcp_tool_to_openai(tool) -> dict[str, Any]:
    """Convert an mcp.types.Tool to OpenAI function-calling format."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema or {"type": "object", "properties": {}},
        },
    }


_UI_ACTION_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "ui_action",
        "description": (
            "Drive the browser UI to give the user a live demo or tutorial. "
            "Use this when the user asks how to use a feature or requests a walkthrough. "
            "Supported actions: navigate (go to URL), highlight (focus an element with optional message), "
            "scroll (scroll element into view), fill (type into an input), click (click an element), "
            "clear (remove all highlights). Steps execute sequentially with delay_ms between each."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": [
                                    "navigate",
                                    "highlight",
                                    "scroll",
                                    "fill",
                                    "click",
                                    "clear",
                                ],
                            },
                            "url": {
                                "type": "string",
                                "description": "For navigate: destination URL (e.g. /scholar/)",
                            },
                            "selector": {
                                "type": "string",
                                "description": "CSS selector for the target element",
                            },
                            "message": {
                                "type": "string",
                                "description": "For highlight: tooltip message to display",
                            },
                            "value": {
                                "type": "string",
                                "description": "For fill: text to type into the input",
                            },
                            "position": {
                                "type": "string",
                                "enum": ["top", "bottom", "left", "right"],
                                "description": "Tooltip position relative to element",
                            },
                        },
                        "required": ["action"],
                    },
                },
                "delay_ms": {
                    "type": "integer",
                    "description": "Milliseconds between steps (default: 900)",
                },
            },
            "required": ["steps"],
        },
    },
}


async def load_openai_tools() -> list[dict[str, Any]]:
    """Fetch tool definitions from the in-process scitex MCP server (OpenAI format)."""
    from fastmcp import Client

    async with Client(_get_mcp()) as client:
        mcp_tools = await client.list_tools()
    tools = [_mcp_tool_to_openai(t) for t in mcp_tools]
    tools.append(_UI_ACTION_TOOL)
    return tools


async def execute_tool_call(name: str, arguments: dict[str, Any]) -> str:
    """Execute a single tool call in-process, return text result."""
    from fastmcp import Client

    async with Client(_get_mcp()) as client:
        result = await client.call_tool(name, arguments)

    # Flatten CallToolResult content list into a single string
    parts = []
    for item in result.content:
        if hasattr(item, "text"):
            parts.append(item.text)
        else:
            parts.append(str(item))
    return "\n".join(parts)


def build_tool_result_message(tool_call, result_text: str) -> dict[str, Any]:
    """Build an OpenAI-format tool result message."""
    return {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": result_text,
    }


async def run_tool_loop(
    *,
    litellm_model: str,
    api_key: str | None,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    max_tokens: int = 8192,
    temperature: float = 0.3,
) -> tuple[str, list[str], dict[str, Any]]:
    """
    Run the LLM + tool-call loop until a text response is produced.

    Returns:
        (final_text, tools_used, usage): The assistant reply, list of tool names
        called, and accumulated token/cost usage dict with keys:
        prompt_tokens, completion_tokens, total_tokens, estimated_cost_usd.
    """
    import litellm

    tools_used: list[str] = []
    accumulated_prompt_tokens = 0
    accumulated_completion_tokens = 0
    accumulated_cost = 0.0

    def _accumulate_usage(resp) -> None:
        nonlocal accumulated_prompt_tokens, accumulated_completion_tokens, accumulated_cost
        if resp.usage:
            accumulated_prompt_tokens += getattr(resp.usage, "prompt_tokens", 0) or 0
            accumulated_completion_tokens += (
                getattr(resp.usage, "completion_tokens", 0) or 0
            )
        try:
            accumulated_cost += litellm.completion_cost(completion_response=resp)
        except Exception:
            pass

    for _round in range(MAX_TOOL_ROUNDS):
        response = await litellm.acompletion(
            model=litellm_model,
            messages=messages,
            tools=tools,
            api_key=api_key,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        _accumulate_usage(response)
        choice = response.choices[0]
        assistant_msg = choice.message

        # If no tool calls, we have the final text reply
        if not getattr(assistant_msg, "tool_calls", None):
            usage = {
                "prompt_tokens": accumulated_prompt_tokens,
                "completion_tokens": accumulated_completion_tokens,
                "total_tokens": accumulated_prompt_tokens
                + accumulated_completion_tokens,
                "estimated_cost_usd": accumulated_cost,
            }
            return assistant_msg.content or "", tools_used, usage

        # Append assistant message with tool_calls to conversation
        messages.append(assistant_msg.model_dump())

        # Execute each tool call
        for tc in assistant_msg.tool_calls:
            tool_name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, TypeError):
                args = {}

            tools_used.append(tool_name)
            logger.info("MCP tool call: %s(%s)", tool_name, list(args.keys()))

            try:
                result_text = await execute_tool_call(tool_name, args)
            except Exception as exc:
                logger.error("MCP tool %s failed: %s", tool_name, exc)
                result_text = f"Error executing {tool_name}: {exc}"

            messages.append(build_tool_result_message(tc, result_text))

    # Safety: hit max rounds, ask LLM for final answer without tools
    response = await litellm.acompletion(
        model=litellm_model,
        messages=messages,
        api_key=api_key,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    _accumulate_usage(response)
    usage = {
        "prompt_tokens": accumulated_prompt_tokens,
        "completion_tokens": accumulated_completion_tokens,
        "total_tokens": accumulated_prompt_tokens + accumulated_completion_tokens,
        "estimated_cost_usd": accumulated_cost,
    }
    return response.choices[0].message.content or "", tools_used, usage


async def run_tool_loop_streaming(
    *,
    litellm_model: str,
    api_key: str | None,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    max_tokens: int = 8192,
    temperature: float = 0.3,
    project_root: str | None = None,
):
    """
    Streaming version of run_tool_loop.

    Yields dicts:
      {"type": "chunk",      "text": "..."}
      {"type": "tool_start", "name": "tool_name"}
      {"type": "tool_end",   "name": "tool_name"}
      {"type": "done",       "tools_used": [...], "usage": {...}}

    The "done" event's "usage" key contains:
      prompt_tokens, completion_tokens, total_tokens, estimated_cost_usd
    accumulated across all rounds.
    """
    import litellm

    tools_used: list[str] = []
    accumulated_prompt_tokens = 0
    accumulated_completion_tokens = 0
    accumulated_cost = 0.0

    for _round in range(MAX_TOOL_ROUNDS):
        response = await litellm.acompletion(
            model=litellm_model,
            messages=messages,
            tools=tools,
            api_key=api_key,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            stream_options={"include_usage": True},
        )

        accumulated_content = ""
        # {index: {"id": ..., "function": {"name": ..., "arguments": ...}}}
        accumulated_tool_calls: dict[int, dict[str, Any]] = {}

        async for chunk in response:
            # Capture usage from the final chunk (sent when stream_options include_usage=True)
            if getattr(chunk, "usage", None):
                accumulated_prompt_tokens += (
                    getattr(chunk.usage, "prompt_tokens", 0) or 0
                )
                accumulated_completion_tokens += (
                    getattr(chunk.usage, "completion_tokens", 0) or 0
                )
                try:
                    accumulated_cost += litellm.completion_cost(
                        completion_response=chunk
                    )
                except Exception:
                    pass

            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta

            if getattr(delta, "content", None):
                accumulated_content += delta.content
                yield {"type": "chunk", "text": delta.content}

            if getattr(delta, "tool_calls", None):
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in accumulated_tool_calls:
                        accumulated_tool_calls[idx] = {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    if tc.id:
                        accumulated_tool_calls[idx]["id"] = tc.id
                    if tc.function and tc.function.name:
                        accumulated_tool_calls[idx]["function"][
                            "name"
                        ] = tc.function.name
                    if tc.function and tc.function.arguments:
                        accumulated_tool_calls[idx]["function"][
                            "arguments"
                        ] += tc.function.arguments

        if not accumulated_tool_calls:
            usage = {
                "prompt_tokens": accumulated_prompt_tokens,
                "completion_tokens": accumulated_completion_tokens,
                "total_tokens": accumulated_prompt_tokens
                + accumulated_completion_tokens,
                "estimated_cost_usd": accumulated_cost,
            }
            yield {"type": "done", "tools_used": tools_used, "usage": usage}
            return

        # Append assistant message with accumulated tool_calls
        messages.append(
            {
                "role": "assistant",
                "content": accumulated_content or None,
                "tool_calls": list(accumulated_tool_calls.values()),
            }
        )

        # Execute each tool call
        for idx in sorted(accumulated_tool_calls):
            tc = accumulated_tool_calls[idx]
            tool_name = tc["function"]["name"]
            tools_used.append(tool_name)
            raw_args = tc["function"]["arguments"] or "{}"

            # Include args so browser can intercept browser-native tools (e.g. audio_speak)
            yield {"type": "tool_start", "name": tool_name, "args": raw_args}

            try:
                args = json.loads(raw_args)
            except (json.JSONDecodeError, TypeError) as exc:
                # Arguments were truncated (likely hit max_tokens mid-JSON).
                logger.error(
                    "MCP tool %s has malformed arguments (truncated?): %s … Error: %s",
                    tool_name,
                    raw_args[:120],
                    exc,
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": (
                            "Error: tool arguments were truncated before parsing. "
                            "Please retry with shorter content or split into smaller writes."
                        ),
                    }
                )
                yield {"type": "tool_end", "name": tool_name}
                continue

            # Browser-native tools: server skips MCP execution, browser handles them.
            # audio_speak: browser plays audio via /llm/api/tts/
            # ui_action: browser drives DOM (navigate, highlight, fill, click, scroll)
            if tool_name in ("audio_speak", "ui_action"):
                yield {"type": "tool_end", "name": tool_name}
                content = (
                    "Speaking... (audio delivered to browser)"
                    if tool_name == "audio_speak"
                    else "UI action delivered to browser."
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": content,
                    }
                )
                continue

            try:
                result_text = await execute_tool_call(tool_name, args)
            except Exception as exc:
                logger.error("MCP tool %s failed: %s", tool_name, exc)
                result_text = f"Error executing {tool_name}: {exc}"

            yield {"type": "tool_end", "name": tool_name}

            # Emit media references for frontend rendering
            if project_root:
                from apps.llm_app.services.media_detect import extract_media_refs

                media = extract_media_refs(result_text, project_root)
                if media:
                    yield {"type": "tool_result", "name": tool_name, "media": media}

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result_text,
                }
            )

    # Safety: hit max rounds, get final answer without tools
    response = await litellm.acompletion(
        model=litellm_model,
        messages=messages,
        api_key=api_key,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
        stream_options={"include_usage": True},
    )
    async for chunk in response:
        # Capture usage from the final chunk
        if getattr(chunk, "usage", None):
            accumulated_prompt_tokens += getattr(chunk.usage, "prompt_tokens", 0) or 0
            accumulated_completion_tokens += (
                getattr(chunk.usage, "completion_tokens", 0) or 0
            )
            try:
                accumulated_cost += litellm.completion_cost(completion_response=chunk)
            except Exception:
                pass

        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta
        if getattr(delta, "content", None):
            yield {"type": "chunk", "text": delta.content}

    usage = {
        "prompt_tokens": accumulated_prompt_tokens,
        "completion_tokens": accumulated_completion_tokens,
        "total_tokens": accumulated_prompt_tokens + accumulated_completion_tokens,
        "estimated_cost_usd": accumulated_cost,
    }
    yield {"type": "done", "tools_used": tools_used, "usage": usage}


# EOF
