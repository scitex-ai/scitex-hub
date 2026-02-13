from .base import NotebookAPIView

class NotebookDetailAPI(NotebookAPIView):
    """API for individual notebook operations."""

    def get(self, request, notebook_id):
        """Get notebook details and content."""
        try:
            manager = self.get_notebook_manager()
            notebook = manager.load_notebook(notebook_id)

            if not notebook:
                return JsonResponse(
                    {"status": "error", "message": "Notebook not found"},
                    status=404,
                )

            return JsonResponse(
                {
                    "status": "success",
                    "notebook": {
                        "id": str(notebook.notebook_id),
                        "title": notebook.title,
                        "description": notebook.description,
                        "status": notebook.status,
                        "content": notebook.content,
                        "is_public": notebook.is_public,
                        "execution_count": notebook.execution_count,
                        "last_executed": (
                            notebook.last_executed.isoformat()
                            if notebook.last_executed
                            else None
                        ),
                        "created_at": notebook.created_at.isoformat(),
                        "updated_at": notebook.updated_at.isoformat(),
                        "shared_with": [
                            user.username for user in notebook.shared_with.all()
                        ],
                    },
                }
            )

        except Exception as e:
            logger.error(f"Error getting notebook {notebook_id}: {e}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    def put(self, request, notebook_id):
        """Update notebook content."""
        try:
            data = json.loads(request.body)
            content = data.get("content")
            title = data.get("title")
            description = data.get("description")

            manager = self.get_notebook_manager()
            notebook = manager.load_notebook(notebook_id)

            if not notebook:
                return JsonResponse(
                    {"status": "error", "message": "Notebook not found"},
                    status=404,
                )

            # Update metadata if provided
            updated = False
            if title and title != notebook.title:
                # Check for duplicate titles
                if (
                    Notebook.objects.filter(user=request.user, title=title)
                    .exclude(notebook_id=notebook_id)
                    .exists()
                ):
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "A notebook with this title already exists",
                        },
                        status=400,
                    )
                notebook.title = title
                updated = True

            if description is not None and description != notebook.description:
                notebook.description = description
                updated = True

            # Update content if provided
            if content:
                # Validate notebook content
                is_valid, errors = NotebookValidator.validate_notebook(content)
                if not is_valid:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "Invalid notebook content",
                            "errors": errors,
                        },
                        status=400,
                    )

                success = manager.save_notebook(notebook_id, content)
                if not success:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "Failed to save notebook content",
                        },
                        status=500,
                    )
                updated = True

            if updated:
                notebook.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Notebook updated successfully",
                }
            )

        except json.JSONDecodeError:
            return JsonResponse(
                {"status": "error", "message": "Invalid JSON"}, status=400
            )
        except Exception as e:
            logger.error(f"Error updating notebook {notebook_id}: {e}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    def delete(self, request, notebook_id):
        """Delete a notebook."""
        try:
            manager = self.get_notebook_manager()
            notebook = manager.load_notebook(notebook_id)

            if not notebook:
                return JsonResponse(
                    {"status": "error", "message": "Notebook not found"},
                    status=404,
                )

            # Delete file if exists
            if notebook.file_path and notebook.file_path.startswith(
                str(manager.base_path)
            ):
                try:
                    import os

                    if os.path.exists(notebook.file_path):
                        os.remove(notebook.file_path)
                except Exception as e:
                    logger.warning(
                        f"Could not delete notebook file {notebook.file_path}: {e}"
                    )

            # Delete from database
            notebook.delete()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Notebook deleted successfully",
                }
            )

        except Exception as e:
            logger.error(f"Error deleting notebook {notebook_id}: {e}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


# EOF
