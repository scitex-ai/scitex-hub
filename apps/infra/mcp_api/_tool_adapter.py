# -*- coding: utf-8 -*-
"""Adapt public FastMCP tool runners to the existing REST executor."""

from __future__ import annotations

from typing import Any, Callable


def get_tool_callable(tool_obj: Any) -> tuple[Callable, bool]:
    """Keep function tools native; adapt public Tool.run for provider tools."""
    fn = getattr(tool_obj, "fn", None)
    if callable(fn):
        return fn, False

    run = getattr(tool_obj, "run", None)
    if not callable(run):
        raise RuntimeError(f"MCP tool has no callable fn or run: {tool_obj.name}")

    async def run_tool(**arguments):
        return await run(arguments)

    return run_tool, True


def tool_result_to_rest(result: Any) -> dict[str, Any]:
    """Preserve Tool.run structured data, MCP content, metadata and error state."""
    payload = result.model_dump(mode="json", by_alias=True)
    content = payload["content"]
    structured_content = payload.get("structured_content")
    is_error = payload.get("is_error", False)
    response = {
        "success": not is_error,
        "data": structured_content if structured_content is not None else content,
        "content": content,
    }
    if payload.get("meta") is not None:
        response["meta"] = payload["meta"]
    if is_error:
        response["error"] = "\n".join(
            block["text"] for block in content if block.get("type") == "text"
        ) or "Tool returned an error"
        response["error_code"] = "EXECUTION_ERROR"
    return response
