"""
Execution environment management views.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from ..models import CodeExecutionJob


@login_required
def environments(request):
    """List user's execution environments."""
    from ..services.environment_manager import EnvironmentManager

    env_manager = EnvironmentManager(request.user)
    environments = env_manager.list_environments()

    context = {"environments": environments, "total_environments": len(environments)}
    return render(request, "code_app/environments.html", context)


@login_required
@require_http_methods(["POST"])
def create_environment(request):
    """Create a new execution environment."""
    try:
        from ..services.environment_manager import EnvironmentManager

        data = json.loads(request.body)
        name = data.get("name", "").strip()
        requirements = data.get("requirements", [])

        if not name:
            return JsonResponse({"error": "Environment name is required"}, status=400)

        env_manager = EnvironmentManager(request.user)
        environment = env_manager.create_environment(name, requirements)

        return JsonResponse(
            {
                "success": True,
                "environment": {
                    "id": environment.env_id,
                    "name": environment.name,
                    "requirements": [str(req) for req in environment.requirements],
                    "created_at": environment.created_at.isoformat(),
                },
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def setup_environment(request, env_id):
    """Set up an environment with packages."""
    try:
        from ..services.environment_manager import EnvironmentManager

        env_manager = EnvironmentManager(request.user)
        success, message = env_manager.setup_environment(env_id)

        if success:
            return JsonResponse({"success": True, "message": message})
        else:
            return JsonResponse({"success": False, "error": message}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def environment_detail(request, env_id):
    """View environment details."""
    from ..services.environment_manager import EnvironmentManager

    env_manager = EnvironmentManager(request.user)
    env_info = env_manager.get_environment_info(env_id)

    if not env_info:
        messages.error(request, "Environment not found.")
        return redirect("code:environments")

    context = {"environment": env_info}
    return render(request, "code_app/environment_detail.html", context)


@login_required
@require_http_methods(["POST"])
def execute_in_environment(request, env_id):
    """Execute code in a specific environment."""
    try:
        from ..services.environment_manager import EnvironmentManager

        data = json.loads(request.body)
        code = data.get("code", "").strip()
        timeout = min(int(data.get("timeout", 300)), 600)

        if not code:
            return JsonResponse({"error": "Code is required"}, status=400)

        env_manager = EnvironmentManager(request.user)
        success, result = env_manager.execute_in_environment(env_id, code, timeout)

        if success:
            # Create execution job record
            job = CodeExecutionJob.objects.create(
                user=request.user,
                execution_type="script",
                source_code=code,
                status="completed",
                output=result.get("stdout", ""),
                error_output=result.get("stderr", ""),
                return_code=result.get("return_code", 0),
                execution_time=result.get("execution_time", 0),
                timeout_seconds=timeout,
            )

            return JsonResponse(
                {"success": True, "job_id": str(job.job_id), "result": result}
            )
        else:
            return JsonResponse(
                {"success": False, "error": result.get("error", "Unknown error")},
                status=400,
            )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
