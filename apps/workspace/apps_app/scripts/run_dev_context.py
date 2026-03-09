#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run a dev app context builder inside an Apptainer container.

Called by DevAppRunner. Reads JSON from stdin, calls the context builder
from /workspace/views.py, writes JSON result to stdout.

Input JSON (stdin):
    {
        "function": "build_hello_world_app_context",
        "username": "ywatanabe",
        "project_slug": "my-project",
        "project_id": 42,
        "get_params": {}
    }

Output JSON (stdout):
    {
        "success": true,
        "context": { ... }
    }
    or
    {
        "success": false,
        "error": "..."
    }
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path


def _make_request_proxy(data: dict) -> types.SimpleNamespace:
    """Build a minimal request proxy from serialized input."""
    proxy = types.SimpleNamespace()
    proxy.user = types.SimpleNamespace(
        username=data.get("username", ""),
        is_authenticated=bool(data.get("username")),
    )
    proxy.GET = data.get("get_params", {})
    proxy.POST = {}
    proxy.method = "GET"
    return proxy


def _make_project_proxy(data: dict):
    """Build a minimal project proxy."""
    if not data.get("project_id"):
        return None
    proj = types.SimpleNamespace()
    proj.id = data.get("project_id")
    proj.slug = data.get("project_slug", "")
    return proj


def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        print(json.dumps({"success": False, "error": "No input on stdin"}))
        return 1

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(json.dumps({"success": False, "error": f"Invalid JSON: {exc}"}))
        return 1

    app_dir = Path("/workspace")
    views_path = app_dir / "views.py"

    if not views_path.is_file():
        # No views.py — return empty context
        print(json.dumps({"success": True, "context": {}}))
        return 0

    fn_name = data.get("function", "build_context")

    try:
        spec = importlib.util.spec_from_file_location("dev_app_views", views_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as exc:
        print(
            json.dumps({"success": False, "error": f"Failed to load views.py: {exc}"})
        )
        return 1

    fn = getattr(mod, fn_name, None)
    if fn is None:
        # Function not found — return empty context
        print(json.dumps({"success": True, "context": {}}))
        return 0

    try:
        request_proxy = _make_request_proxy(data)
        project_proxy = _make_project_proxy(data)
        result = fn(request_proxy, project_proxy)
        # Ensure result is JSON-serialisable
        if not isinstance(result, dict):
            result = {}
        print(json.dumps({"success": True, "context": result}))
        return 0
    except Exception as exc:
        print(json.dumps({"success": False, "error": f"Context builder error: {exc}"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())


# EOF
