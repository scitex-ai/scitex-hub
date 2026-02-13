from .base import NotebookAPIView

class NotebookSharingAPI(NotebookAPIView):
    """API for notebook sharing."""

    def post(self, request, notebook_id):
        """Share notebook with other users."""
        try:
            data = json.loads(request.body)
            usernames = data.get("usernames", [])
            is_public = data.get("is_public", False)

            manager = self.get_notebook_manager()
            notebook = manager.load_notebook(notebook_id)

            if not notebook:
                return JsonResponse(
                    {"status": "error", "message": "Notebook not found"},
                    status=404,
                )

            # Update public status
            notebook.is_public = is_public

            # Share with specific users
            if usernames:
                from django.contrib.auth.models import User

                users = User.objects.filter(username__in=usernames)
                notebook.shared_with.set(users)

            notebook.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Notebook sharing updated",
                    "shared_with": [
                        user.username for user in notebook.shared_with.all()
                    ],
                    "is_public": notebook.is_public,
                }
            )

        except json.JSONDecodeError:
            return JsonResponse(
                {"status": "error", "message": "Invalid JSON"}, status=400
            )
        except Exception as e:
            logger.error(f"Error sharing notebook {notebook_id}: {e}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


# EOF
