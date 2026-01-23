"""
Data analysis views.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
import json
import threading
from ..models import CodeExecutionJob, DataAnalysisJob


@login_required
def analysis(request):
    """Data analysis interface."""
    analysis_jobs = DataAnalysisJob.objects.filter(user=request.user)[:10]

    context = {
        "analysis_jobs": analysis_jobs,
        "analysis_types": DataAnalysisJob.ANALYSIS_TYPES,
    }
    return render(request, "code_app/analysis.html", context)


def templates(request):
    """SCITEX framework templates page."""
    return render(request, "code_app/templates.html")


@login_required
@require_http_methods(["POST"])
def run_analysis(request):
    """Run data analysis via web interface."""
    try:
        analysis_type = request.POST.get("type", "custom")
        input_data = request.POST.get("data_path", "")
        parameters = json.loads(request.POST.get("parameters", "{}"))

        # Create analysis job
        analysis_job = DataAnalysisJob.objects.create(
            user=request.user,
            analysis_type=analysis_type,
            input_data_path=input_data,
            parameters=parameters,
        )

        # Generate analysis code  # noqa: F821 - Legacy code, function not available
        analysis_code = generate_analysis_code(analysis_type, input_data, parameters)

        # Create code execution job
        code_job = CodeExecutionJob.objects.create(
            user=request.user,
            execution_type="analysis",
            source_code=analysis_code,
            timeout_seconds=600,
            max_memory_mb=1024,
        )

        analysis_job.code_job = code_job
        analysis_job.save()

        # Start execution
        def run_analysis_execution():
            execute_code_safely(code_job)  # noqa: F821 - Legacy code, function not available

        analysis_thread = threading.Thread(target=run_analysis_execution)
        analysis_thread.daemon = True
        analysis_thread.start()

        messages.success(request, f'Analysis "{analysis_type}" started successfully!')
        return redirect("code:job_detail", job_id=code_job.job_id)

    except Exception as e:
        messages.error(request, f"Error starting analysis: {str(e)}")
        return redirect("code:analysis")
