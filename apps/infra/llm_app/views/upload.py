"""File upload endpoint for AI chat file drops.

Accepts multipart file uploads and saves them to the user's downloads directory.
Returns the server-side paths so the AI agent can reference them.
"""

import json
import logging
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.infra.project_app.services.filesystem.permissions import (
    validate_path_in_user_jail,
)

logger = logging.getLogger(__name__)


def _get_downloads_dir(user) -> Path:
    """Get (and create) the user's downloads directory."""
    downloads = Path(settings.BASE_DIR) / "data" / "users" / user.username / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    return downloads


@login_required
@require_POST
def api_upload_files(request):
    """Upload files dropped into the AI chat input.

    Accepts multipart/form-data with one or more files.
    Saves each file to data/users/{username}/downloads/.
    Returns JSON with the list of saved file paths.
    """
    files = request.FILES.getlist("files")
    if not files:
        return JsonResponse({"error": "No files provided"}, status=400)

    downloads_dir = _get_downloads_dir(request.user)
    saved_paths = []

    for f in files:
        dest = downloads_dir / f.name
        # Avoid overwriting: append suffix if file exists
        if dest.exists():
            stem = dest.stem
            suffix = dest.suffix
            counter = 1
            while dest.exists():
                dest = downloads_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        with open(dest, "wb") as out:
            for chunk in f.chunks():
                out.write(chunk)
        saved_paths.append(str(dest))

    return JsonResponse({"paths": saved_paths})


@login_required
@require_POST
def api_copy_project_files(request):
    """Copy project files to the user's downloads directory.

    Accepts JSON body with {"paths": ["relative/path/to/file", ...]}.
    Copies from the project filesystem to downloads dir.
    Returns JSON with the list of destination paths.
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    paths = body.get("paths", [])
    if not paths:
        return JsonResponse({"error": "No paths provided"}, status=400)

    downloads_dir = _get_downloads_dir(request.user)
    user_base = Path(settings.BASE_DIR) / "data" / "users" / request.user.username
    saved_paths = []

    for rel_path in paths:
        # Resolve relative to user base (proj/ or downloads/)
        src = (user_base / "proj" / rel_path).resolve()

        # Security: BOTH checks in one call. validate_path_in_user_jail
        # derives the jail root from request.user (not from client input), so
        # it is simultaneously the containment check AND the tenant-ownership
        # check. A prefix match here was a genuine cross-USER hole: user
        # "alice" string-prefix-matches sibling "alice2", and the sink below
        # (shutil.copy2) lands the victim's file in the ATTACKER's downloads.
        #
        # BEHAVIOUR CHANGE (deliberate): the previous code silently
        # `continue`d past a rejected path. Silent fallbacks are forbidden in
        # this project -- refuse loudly and name the offending path.
        if not validate_path_in_user_jail(request.user, src):
            logger.warning(
                "Rejected out-of-jail copy for user %s: %s",
                request.user.username,
                rel_path,
            )
            return JsonResponse(
                {"error": f"Path outside your data directory: {rel_path}"},
                status=400,
            )
        if not src.is_file():
            continue

        dest = downloads_dir / src.name
        if dest.exists():
            stem = dest.stem
            suffix = dest.suffix
            counter = 1
            while dest.exists():
                dest = downloads_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        import shutil

        shutil.copy2(src, dest)
        saved_paths.append(str(dest))

    if not saved_paths:
        return JsonResponse({"error": "No valid files found"}, status=400)

    return JsonResponse({"paths": saved_paths})
