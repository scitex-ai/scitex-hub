from .base import NotebookAPIView

class NotebookTemplatesAPI(NotebookAPIView):
    """API for notebook templates."""

    def get(self, request):
        """Get available notebook templates."""
        try:
            templates = [
                {
                    "id": "blank",
                    "name": "Blank Notebook",
                    "description": "Start with an empty notebook",
                    "category": "general",
                },
                {
                    "id": "data_analysis",
                    "name": "Data Analysis",
                    "description": "Structured template for data analysis projects",
                    "category": "analysis",
                },
                {
                    "id": "machine_learning",
                    "name": "Machine Learning",
                    "description": "Template for ML model development and evaluation",
                    "category": "ml",
                },
                {
                    "id": "visualization",
                    "name": "Data Visualization",
                    "description": "Create publication-ready visualizations",
                    "category": "visualization",
                },
            ]

            return JsonResponse({"status": "success", "templates": templates})

        except Exception as e:
            logger.error(f"Error getting templates: {e}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


# REST Framework API Views


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notebook_status_api(request, job_id):
    """Get notebook execution status via REST API."""
    try:
        job = CodeExecutionJob.objects.get(job_id=job_id, user=request.user)

        return Response(
            {
                "job_id": str(job.job_id),
                "status": job.status,
                "execution_type": job.execution_type,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "execution_time": job.execution_time,
                "cpu_time": job.cpu_time,
                "memory_peak": job.memory_peak,
                "output": json.loads(job.output) if job.output else None,
                "error_output": job.error_output,
            }
        )

    except CodeExecutionJob.DoesNotExist:
        return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error getting job status {job_id}: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def duplicate_notebook_api(request, notebook_id):
    """Duplicate a notebook via REST API."""
    try:
        data = request.data
        new_title = data.get("title", "").strip()

        if not new_title:
            return Response(
                {"error": "New title is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        manager = NotebookManager(request.user)
        new_notebook = manager.duplicate_notebook(notebook_id, new_title)

        if not new_notebook:
            return Response(
                {"error": "Notebook not found or duplication failed"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "status": "success",
                "message": "Notebook duplicated successfully",
                "notebook": {
                    "id": str(new_notebook.notebook_id),
                    "title": new_notebook.title,
                    "description": new_notebook.description,
                    "status": new_notebook.status,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error duplicating notebook {notebook_id}: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# EOF
# EOF
