"""
Data visualization pipeline views.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
import json
from pathlib import Path
from ..models import CodeExecutionJob


@login_required
def visualizations(request):
    """List user's generated visualizations."""
    viz_dir = Path(settings.MEDIA_ROOT) / "visualizations" / str(request.user.id)
    visualizations = []

    if viz_dir.exists():
        for viz_file in viz_dir.glob("*.png"):
            try:
                stat = viz_file.stat()
                visualizations.append(
                    {
                        "filename": viz_file.name,
                        "size": stat.st_size,
                        "created": timezone.datetime.fromtimestamp(stat.st_ctime),
                        "path": f"visualizations/{request.user.id}/{viz_file.name}",
                    }
                )
            except Exception:
                continue

    # Sort by creation time
    visualizations.sort(key=lambda x: x["created"], reverse=True)

    context = {"visualizations": visualizations}
    return render(request, "code_app/visualizations.html", context)


@login_required
@require_http_methods(["POST"])
def generate_visualization(request):
    """Generate a visualization from data."""
    try:
        from ..services.visualization_pipeline import VisualizationGenerator

        data = json.loads(request.body)
        plot_type = data.get("type", "line")
        plot_data = data.get("data", {})
        options = data.get("options", {})

        generator = VisualizationGenerator(request.user)
        success, result = generator.generate_plot(plot_type, plot_data, options)

        if success:
            # Create a job record for tracking
            job = CodeExecutionJob.objects.create(
                user=request.user,
                execution_type="visualization",
                source_code=f"# Generated {plot_type} plot\n# Data points: {result.get('data_points', 'N/A')}",
                status="completed",
                output=json.dumps(result, indent=2),
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


@login_required
@require_http_methods(["POST"])
def process_data_visualization(request):
    """Process data file and generate multiple visualizations."""
    try:
        from ..services.visualization_pipeline import VisualizationPipeline

        data = json.loads(request.body)
        data_source = data.get("data_source", "")
        visualization_specs = data.get("visualizations", [])

        if not data_source:
            return JsonResponse({"error": "Data source is required"}, status=400)

        if not visualization_specs:
            return JsonResponse(
                {"error": "At least one visualization specification is required"},
                status=400,
            )

        pipeline = VisualizationPipeline(request.user)
        result = pipeline.process_data_and_visualize(data_source, visualization_specs)

        if result.get("success"):
            # Create job record
            job = CodeExecutionJob.objects.create(
                user=request.user,
                execution_type="analysis",
                source_code=f"# Data visualization pipeline\n# Data shape: {result.get('data_shape', 'N/A')}\n# Visualizations: {len(visualization_specs)}",
                status="completed",
                output=json.dumps(result, indent=2),
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


@login_required
@require_http_methods(["POST"])
def create_research_report(request):
    """Create a research report with visualizations."""
    try:
        from ..services.visualization_pipeline import VisualizationPipeline

        data = json.loads(request.body)
        title = data.get("title", "Research Report")
        sections = data.get("sections", [])

        if not sections:
            return JsonResponse(
                {"error": "At least one section is required"}, status=400
            )

        pipeline = VisualizationPipeline(request.user)
        report_path = pipeline.create_research_report(title, sections)

        return JsonResponse(
            {
                "success": True,
                "report_path": report_path,
                "message": "Research report created successfully",
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
