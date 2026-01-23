from .base import NotebookAPIView

class NotebookConversionAPI(NotebookAPIView):
    """API for notebook format conversion."""

    def get(self, request, notebook_id, format_type):
        """Convert notebook to different formats."""
        try:
            manager = self.get_notebook_manager()
            notebook = manager.load_notebook(notebook_id)

            if not notebook:
                return JsonResponse(
                    {"status": "error", "message": "Notebook not found"},
                    status=404,
                )

            if format_type == "html":
                content = NotebookConverter.to_html(notebook)
                return JsonResponse(
                    {
                        "status": "success",
                        "format": "html",
                        "content": content,
                        "filename": f"{notebook.title}.html",
                    }
                )

            elif format_type == "python":
                content = NotebookConverter.to_python(notebook)
                return JsonResponse(
                    {
                        "status": "success",
                        "format": "python",
                        "content": content,
                        "filename": f"{notebook.title}.py",
                    }
                )

            elif format_type == "markdown":
                content = NotebookConverter.to_markdown(notebook)
                return JsonResponse(
                    {
                        "status": "success",
                        "format": "markdown",
                        "content": content,
                        "filename": f"{notebook.title}.md",
                    }
                )

            else:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Unsupported format. Supported formats: html, python, markdown",
                    },
                    status=400,
                )

        except Exception as e:
            logger.error(
                f"Error converting notebook {notebook_id} to {format_type}: {e}"
            )
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


# EOF
