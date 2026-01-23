"""
Job management views for code execution and monitoring.
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
import json
import threading
from ..models import CodeExecutionJob


@login_required
def jobs(request):
    """List user's code execution jobs."""
    jobs_list = (
        CodeExecutionJob.objects.filter(user=request.user)
        .select_related("user")
        .order_by("-created_at")
    )

    # Filter by status if provided
    status_filter = request.GET.get("status")
    if status_filter:
        jobs_list = jobs_list.filter(status=status_filter)

    # Paginate results
    paginator = Paginator(jobs_list, 20)
    page = request.GET.get("page", 1)
    jobs = paginator.get_page(page)

    context = {
        "jobs": jobs,
        "status_filter": status_filter,
        "status_choices": CodeExecutionJob.JOB_STATUS,
    }
    return render(request, "code_app/jobs.html", context)


@login_required
def job_detail(request, job_id):
    """View details of a specific job."""
    job = get_object_or_404(CodeExecutionJob, job_id=job_id, user=request.user)

    context = {
        "job": job,
        "output_files": job.output_files,
        "plot_files": job.plot_files,
    }
    return render(request, "code_app/job_detail.html", context)


@login_required
@require_http_methods(["POST"])
def execute_code(request):
    """Execute code via web interface."""
    try:
        data = json.loads(request.body)
        code = data.get("code", "").strip()
        execution_type = data.get("type", "script")
        timeout = min(int(data.get("timeout", 300)), 600)
        max_memory = min(int(data.get("max_memory", 512)), 2048)

        if not code:
            return JsonResponse({"error": "Code is required"}, status=400)

        # Create execution job
        job = CodeExecutionJob.objects.create(
            user=request.user,
            execution_type=execution_type,
            source_code=code,
            timeout_seconds=timeout,
            max_memory_mb=max_memory,
        )

        # Start execution in background
        def run_execution():
            execute_code_safely(job)  # noqa: F821 - Legacy code, function not available

        execution_thread = threading.Thread(target=run_execution)
        execution_thread.daemon = True
        execution_thread.start()

        return JsonResponse(
            {
                "success": True,
                "job_id": str(job.job_id),
                "status": job.status,
                "message": "Code execution started",
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def job_status(request, job_id):
    """Get job status via AJAX."""
    try:
        job = CodeExecutionJob.objects.get(job_id=job_id, user=request.user)

        response_data = {
            "job_id": str(job.job_id),
            "status": job.status,
            "progress": get_job_progress(job.status),
            "message": f"Job {job.status}",
            "execution_time": job.execution_time,
            "cpu_time": job.cpu_time,
            "memory_peak": job.memory_peak,
            "created_at": job.created_at.isoformat(),
            "output": job.output,
            "error_output": job.error_output,
            "output_files": job.output_files,
            "plot_files": job.plot_files,
        }

        return JsonResponse(response_data)

    except CodeExecutionJob.DoesNotExist:
        return JsonResponse({"error": "Job not found"}, status=404)


def get_job_progress(status):
    """Calculate job progress percentage."""
    progress_map = {
        "queued": 10,
        "running": 50,
        "completed": 100,
        "failed": 0,
        "timeout": 0,
        "cancelled": 0,
    }
    return progress_map.get(status, 0)
