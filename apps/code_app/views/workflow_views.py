"""
Research workflow management views.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
import json
from pathlib import Path


@login_required
def workflows(request):
    """List user's research workflows."""
    workflows_dir = Path(settings.MEDIA_ROOT) / "workflows" / str(request.user.id)

    workflows = []
    if workflows_dir.exists():
        for workflow_file in workflows_dir.glob("*.json"):
            try:
                with open(workflow_file) as f:
                    workflow_data = json.load(f)
                    workflows.append(workflow_data)
            except Exception:
                continue

    # Sort by creation date
    workflows.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    context = {"workflows": workflows}
    return render(request, "code_app/workflows.html", context)


@login_required
@require_http_methods(["POST"])
def create_workflow(request):
    """Create a new research workflow."""
    try:
        from ..services.environment_manager import WorkflowManager

        data = json.loads(request.body)
        name = data.get("name", "").strip()
        description = data.get("description", "")
        steps = data.get("steps", [])

        if not name:
            return JsonResponse({"error": "Workflow name is required"}, status=400)

        if not steps:
            return JsonResponse({"error": "At least one step is required"}, status=400)

        workflow_manager = WorkflowManager(request.user)
        workflow = workflow_manager.create_workflow(name, description, steps)

        return JsonResponse({"success": True, "workflow": workflow})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def execute_workflow(request, workflow_id):
    """Execute a research workflow."""
    try:
        from ..services.environment_manager import WorkflowManager

        workflow_manager = WorkflowManager(request.user)
        success, results = workflow_manager.execute_workflow(workflow_id)

        return JsonResponse({"success": success, "results": results})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def workflow_detail(request, workflow_id):
    """View workflow details."""
    workflows_dir = Path(settings.MEDIA_ROOT) / "workflows" / str(request.user.id)
    workflow_file = workflows_dir / f"{workflow_id}.json"

    if not workflow_file.exists():
        messages.error(request, "Workflow not found.")
        return redirect("code:workflows")

    try:
        with open(workflow_file) as f:
            workflow = json.load(f)
    except Exception as e:
        messages.error(request, f"Error loading workflow: {e}")
        return redirect("code:workflows")

    context = {"workflow": workflow}
    return render(request, "code_app/workflow_detail.html", context)
