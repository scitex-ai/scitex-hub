import asyncio
import json
from datetime import datetime, timezone

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.llm_app.skills import get_all_skills, get_skill, get_skill_for_page


def _serialize_skill(skill):
    """Serialize a Skill dataclass to a dict."""
    return {
        "app_name": skill.app_name,
        "display_name": skill.display_name,
        "description": skill.description,
        "tool_prefixes": skill.tool_prefixes,
        "capabilities": skill.capabilities,
        "page_patterns": skill.page_patterns,
    }


@require_http_methods(["GET"])
def api_list_skills(request):
    """List all registered skills."""
    skills = get_all_skills()
    return JsonResponse(
        {
            "success": True,
            "skills": {name: _serialize_skill(s) for name, s in skills.items()},
        }
    )


@require_http_methods(["GET"])
def api_get_skill(request, app_name: str):
    """Get a specific skill by app_name."""
    skill = get_skill(app_name)
    if not skill:
        return JsonResponse(
            {"success": False, "error": f"Skill '{app_name}' not found"},
            status=404,
        )
    return JsonResponse({"success": True, "skill": _serialize_skill(skill)})


@login_required
@require_http_methods(["POST"])
def api_agent_context(request):
    """Return full agent context as received by the AI — no hardcoding.

    Assembles: system prompt, skills, MCP tools, page hints dynamically.
    Frontend sends current page and page_hints in POST body.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = {}

    page = data.get("page", "")
    page_hints = data.get("page_hints", [])
    context = {"page": page, "page_hints": page_hints}

    # Build system prompt exactly as chat endpoint does
    from apps.llm_app.views.chat import _build_system_prompt

    system_prompt = _build_system_prompt(context, request.user)

    # Active skill for this page
    active_skill = get_skill_for_page(page) if page else None

    # All skills
    all_skills = get_all_skills()

    # MCP tools
    mcp_tools = []
    try:
        from apps.llm_app.services.mcp_client import load_openai_tools

        tools = asyncio.run(load_openai_tools())
        mcp_tools = [
            {
                "name": t["function"]["name"],
                "description": t["function"].get("description", ""),
            }
            for t in tools
            if t.get("type") == "function"
        ]
    except Exception:
        pass

    return JsonResponse(
        {
            "success": True,
            "system_prompt": system_prompt,
            "active_skill": _serialize_skill(active_skill) if active_skill else None,
            "all_skills": {name: _serialize_skill(s) for name, s in all_skills.items()},
            "page_hints": page_hints,
            "mcp_tools": mcp_tools,
            "page": page,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
