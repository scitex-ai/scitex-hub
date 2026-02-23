from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.llm_app.skills import get_all_skills, get_skill


@require_http_methods(["GET"])
def api_list_skills(request):
    """List all registered skills."""
    skills = get_all_skills()
    return JsonResponse(
        {
            "success": True,
            "skills": {
                name: {
                    "app_name": s.app_name,
                    "display_name": s.display_name,
                    "description": s.description,
                    "tool_prefixes": s.tool_prefixes,
                    "capabilities": s.capabilities,
                    "page_patterns": s.page_patterns,
                }
                for name, s in skills.items()
            },
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
    return JsonResponse(
        {
            "success": True,
            "skill": {
                "app_name": skill.app_name,
                "display_name": skill.display_name,
                "description": skill.description,
                "tool_prefixes": skill.tool_prefixes,
                "capabilities": skill.capabilities,
                "page_patterns": skill.page_patterns,
            },
        }
    )
