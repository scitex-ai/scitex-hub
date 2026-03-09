#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clew API views - Thin wrappers around scitex.clew package."""

from __future__ import annotations

import scitex as stx
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods


def _set_project_db(request) -> bool:
    """Set clew DB to current project's scitex/clew.db.

    Returns True if DB was set, False if no project context.
    """
    if not request.user.is_authenticated:
        return False
    from apps.infra.project_app.services.filesystem.paths import get_project_root_path
    from apps.infra.project_app.services.project_utils import get_current_project

    project = get_current_project(request)
    if not project:
        return False
    project_path = get_project_root_path(request.user, project)
    if not project_path:
        return False
    db_path = project_path / "scitex" / "clew.db"
    if db_path.exists():
        stx.clew.set_db(str(db_path))
        return True
    return False


@require_http_methods(["GET"])
def verification_status(request):
    """Get verification status summary (like git status).

    Wrapper around scitex.clew.get_status()
    """
    try:
        _set_project_db(request)
        status = stx.clew.get_status()
        return JsonResponse(
            {
                "success": True,
                "data": status,
            }
        )
    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@require_http_methods(["GET"])
def list_runs(request):
    """List tracked runs with optional filtering.

    Query parameters:
    - limit: int (default: 50)
    - offset: int (default: 0)
    - status: str (optional filter)

    Wrapper around scitex.clew.list_runs()
    """
    try:
        _set_project_db(request)
        limit = int(request.GET.get("limit", 50))
        offset = int(request.GET.get("offset", 0))
        status_filter = request.GET.get("status")

        runs = stx.clew.list_runs(limit=limit, status=status_filter)

        # Apply offset manually (list_runs doesn't support it)
        if offset > 0:
            runs = runs[offset:]

        return JsonResponse(
            {
                "success": True,
                "data": {
                    "runs": runs,
                    "count": len(runs),
                    "limit": limit,
                    "offset": offset,
                },
            }
        )
    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@require_http_methods(["GET"])
def verify_chain(request):
    """Verify the dependency chain for a target file.

    Query parameters:
    - target: str (required) - Path to target file

    Wrapper around scitex.clew.verify_chain()
    """
    target = request.GET.get("target")
    if not target:
        return JsonResponse(
            {
                "success": False,
                "error": "Missing required parameter: target",
            },
            status=400,
        )

    try:
        _set_project_db(request)
        chain = stx.clew.verify_chain(target)

        # Convert dataclass to dict for JSON serialization
        chain_data = {
            "target_file": chain.target_file,
            "status": chain.status.value,
            "is_verified": chain.is_verified,
            "runs": [
                {
                    "session_id": run.session_id,
                    "script_path": run.script_path,
                    "status": run.status.value,
                    "is_verified": run.is_verified,
                    "is_verified_from_scratch": run.is_verified_from_scratch,
                    "files": [
                        {
                            "path": f.path,
                            "role": f.role,
                            "expected_hash": f.expected_hash,
                            "current_hash": f.current_hash,
                            "status": f.status.value,
                            "is_verified": f.is_verified,
                        }
                        for f in run.files
                    ],
                }
                for run in chain.runs
            ],
        }

        return JsonResponse(
            {
                "success": True,
                "data": chain_data,
            }
        )
    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@require_http_methods(["GET"])
def verify_run(request):
    """Verify a specific run by session ID.

    Query parameters:
    - session_id: str (required)
    - from_scratch: bool (optional, default: false)

    Wrapper around scitex.clew.verify_run()
    """
    session_id = request.GET.get("session_id")
    if not session_id:
        return JsonResponse(
            {
                "success": False,
                "error": "Missing required parameter: session_id",
            },
            status=400,
        )

    try:
        _set_project_db(request)
        from_scratch = request.GET.get("from_scratch", "false").lower() == "true"
        verification = stx.clew.run(session_id, from_scratch=from_scratch)

        # Convert dataclass to dict
        verification_data = {
            "session_id": verification.session_id,
            "script_path": verification.script_path,
            "status": verification.status.value,
            "is_verified": verification.is_verified,
            "is_verified_from_scratch": verification.is_verified_from_scratch,
            "combined_hash_expected": verification.combined_hash_expected,
            "combined_hash_current": verification.combined_hash_current,
            "files": [
                {
                    "path": f.path,
                    "role": f.role,
                    "expected_hash": f.expected_hash,
                    "current_hash": f.current_hash,
                    "status": f.status.value,
                    "is_verified": f.is_verified,
                }
                for f in verification.files
            ],
        }

        return JsonResponse(
            {
                "success": True,
                "data": verification_data,
            }
        )
    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@require_http_methods(["GET"])
def get_dag_data(request):
    """Get DAG data as JSON for visualization.

    Query parameters:
    - session_id: str (optional)
    - target_file: str (optional)
    - path_mode: str (optional, default: "name")

    Wrapper around scitex.clew._viz._json.generate_dag_json()
    """
    try:
        _set_project_db(request)
        session_id = request.GET.get("session_id")
        target_file = request.GET.get("target_file")
        path_mode = request.GET.get("path_mode", "name")

        # Import the visualization function
        from scitex.clew._viz._json import generate_dag_json  # noqa: E402

        dag_data = generate_dag_json(
            session_id=session_id,
            target_file=target_file,
            path_mode=path_mode,
        )

        return JsonResponse(
            {
                "success": True,
                "data": dag_data,
            }
        )
    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@require_http_methods(["GET"])
def get_mermaid_dag(request):
    """Get Mermaid diagram code for DAG visualization.

    Query parameters:
    - session_id: str (optional)
    - target_file: str (optional)
    - target_files: str (optional, comma-separated paths)
    - claims: bool (optional, default: false)
    - show_hashes: bool (optional, default: false)
    - path_mode: str (optional, default: "name")

    Wrapper around scitex.clew.generate_mermaid_dag()
    """
    try:
        _set_project_db(request)
        session_id = request.GET.get("session_id")
        target_file = request.GET.get("target_file")
        target_files_raw = request.GET.get("target_files")
        claims = request.GET.get("claims", "false").lower() == "true"
        show_hashes = request.GET.get("show_hashes", "false").lower() == "true"
        path_mode = request.GET.get("path_mode", "name")

        target_files = None
        if target_files_raw:
            target_files = [f.strip() for f in target_files_raw.split(",") if f.strip()]

        mermaid_code = stx.clew.generate_mermaid_dag(
            session_id=session_id,
            target_file=target_file,
            target_files=target_files,
            claims=claims,
            show_hashes=show_hashes,
            path_mode=path_mode,
        )

        return JsonResponse(
            {
                "success": True,
                "data": {
                    "mermaid": mermaid_code,
                },
            }
        )
    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@require_http_methods(["GET"])
def database_stats(request):
    """Get database statistics.

    Wrapper around scitex.clew.stats()
    """
    try:
        _set_project_db(request)
        stats = stx.clew.stats()
        return JsonResponse(
            {
                "success": True,
                "data": stats,
            }
        )
    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@require_http_methods(["GET"])
def list_claims_view(request):
    """List registered claims with optional filtering.

    Query parameters:
    - file_path: str (optional)
    - claim_type: str (optional)
    - status: str (optional)
    - limit: int (default: 100)

    Wrapper around scitex.clew.list_claims()
    """
    try:
        _set_project_db(request)
        file_path = request.GET.get("file_path")
        claim_type = request.GET.get("claim_type")
        status_filter = request.GET.get("status")
        limit = int(request.GET.get("limit", 100))

        claims = stx.clew.list_claims(
            file_path=file_path,
            claim_type=claim_type,
            status=status_filter,
            limit=limit,
        )

        return JsonResponse(
            {
                "success": True,
                "data": {
                    "claims": [c.to_dict() for c in claims],
                    "count": len(claims),
                },
            }
        )
    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@login_required
@csrf_protect
@require_http_methods(["POST"])
def add_examples(request):
    """Copy example Clew pipeline into the current project workspace.

    Thin wrapper around stx.clew.init_examples().
    """
    from apps.infra.project_app.services.filesystem.paths import get_project_root_path
    from apps.infra.project_app.services.project_utils import get_current_project

    try:
        project = get_current_project(request)
        if not project:
            return JsonResponse(
                {"success": False, "error": "No active project"},
                status=400,
            )

        project_path = get_project_root_path(request.user, project)
        if not project_path:
            return JsonResponse(
                {"success": False, "error": "Project workspace not found"},
                status=404,
            )

        dest = project_path / "examples" / "clew"
        result = stx.clew.init_examples(dest)
        return JsonResponse(
            {
                "success": True,
                "data": {
                    "message": "Examples saved to examples/clew/",
                    "path": result["path"],
                    "file_count": result["file_count"],
                },
            }
        )
    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


# EOF
