"""
Jupyter notebook management views.
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json
import threading
from ..models import CodeExecutionJob, Notebook


@login_required
def notebooks(request):
    """List user's notebooks."""
    notebooks_list = (
        Notebook.objects.filter(user=request.user)
        .prefetch_related("shared_with")
        .order_by("-updated_at")
    )

    # Paginate results
    paginator = Paginator(notebooks_list, 20)
    page = request.GET.get("page", 1)
    notebooks = paginator.get_page(page)

    context = {"notebooks": notebooks}
    return render(request, "code_app/notebooks.html", context)


@login_required
def notebook_detail(request, notebook_id):
    """View/edit a specific notebook."""
    notebook = get_object_or_404(Notebook, notebook_id=notebook_id, user=request.user)

    context = {"notebook": notebook}
    return render(request, "code_app/notebook_detail.html", context)


@login_required
@require_http_methods(["POST"])
def create_notebook(request):
    """Create a new notebook."""
    try:
        from ..services.jupyter import NotebookManager, NotebookTemplates

        data = json.loads(request.body)
        title = data.get("title", "").strip()
        description = data.get("description", "")
        template_type = data.get("template", "basic")

        if not title:
            return JsonResponse({"error": "Notebook title is required"}, status=400)

        notebook_manager = NotebookManager(request.user)

        if template_type == "data_analysis":
            content = NotebookTemplates.get_data_analysis_template()
        elif template_type == "machine_learning":
            content = NotebookTemplates.get_machine_learning_template()
        elif template_type == "visualization":
            content = NotebookTemplates.get_visualization_template()
        else:
            # Create basic notebook
            notebook = notebook_manager.create_notebook(title, description)
            return JsonResponse(
                {
                    "success": True,
                    "notebook_id": str(notebook.notebook_id),
                    "redirect_url": f"/code/notebooks/{notebook.notebook_id}/",
                }
            )

        # Create notebook with template
        notebook = Notebook.objects.create(
            user=request.user,
            title=title,
            description=description,
            content=content,
            status="draft",
        )

        return JsonResponse(
            {
                "success": True,
                "notebook_id": str(notebook.notebook_id),
                "redirect_url": f"/code/notebooks/{notebook.notebook_id}/",
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def execute_notebook(request, notebook_id):
    """Execute a Jupyter notebook."""
    try:
        from ..services.jupyter import NotebookExecutor

        notebook = get_object_or_404(
            Notebook, notebook_id=notebook_id, user=request.user
        )

        # Create execution job
        job = CodeExecutionJob.objects.create(
            user=request.user,
            execution_type="notebook",
            source_code=json.dumps(notebook.content),
            timeout_seconds=600,
            max_memory_mb=1024,
        )

        # Execute notebook in background
        def run_notebook_execution():
            executor = NotebookExecutor(timeout=600)
            success, result = executor.execute_notebook(notebook, job)

            if success:
                job.status = "completed"
                job.output = json.dumps(result, indent=2)
            else:
                job.status = "failed"
                job.error_output = result.get("error", "Unknown error")

            job.completed_at = timezone.now()
            job.save()

        execution_thread = threading.Thread(target=run_notebook_execution)
        execution_thread.daemon = True
        execution_thread.start()

        return JsonResponse(
            {
                "success": True,
                "job_id": str(job.job_id),
                "message": "Notebook execution started",
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
