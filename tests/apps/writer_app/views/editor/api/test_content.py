#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/writer_app/views/editor/api/content.py"""

import pytest

# from apps.workspace.writer_app.views.editor.api.content import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/writer_app/views/editor/api/content.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# # File: /home/ywatanabe/proj/scitex-hub/apps/writer_app/views/editor/api/content.py
# """Section content operations - read, write, save."""
#
# from __future__ import annotations
# import json
# import logging
# from django.http import JsonResponse
# from django.views.decorators.http import require_http_methods
# from ..auth_utils import api_login_optional, get_user_for_request
#
# logger = logging.getLogger(__name__)
#
#
# @api_login_optional
# @require_http_methods(["GET", "POST"])
# def section_view(request, project_id, section_name):
#     """Read or write a section's .tex file from/to disk.
#
#     Supports hierarchical section IDs (e.g., "shared/title", "manuscript/abstract").
#
#     GET: Read section content from disk - returns SectionReadResponse
#     POST: Write section content to disk
#     """
#     try:
#         from scitex.writer.dataclasses.results import SectionReadResponse
#         from ....services import WriterService
#         from apps.infra.project_app.models import Project
#         from ....configs.sections_config import parse_section_id
#
#         # Get project
#         project = Project.objects.get(id=project_id)
#
#         # Get effective user (authenticated or visitor)
#         user, is_visitor = get_user_for_request(request, project_id)
#         if not user:
#             return JsonResponse(
#                 {"success": False, "error": "Invalid session"}, status=403
#             )
#
#         writer_service = WriterService(project_id, user.id)
#
#         # Parse section ID to get category and name
#         category, name = parse_section_id(section_name)
#
#         # GET: Read section from disk
#         if request.method == "GET":
#             try:
#                 # Allow query param to override category for legacy compatibility
#                 doc_type = request.GET.get("doc_type", category)
#
#                 logger.info(
#                     f"[SectionView GET] Reading section: {section_name} -> category={category}, name={name}, doc_type={doc_type}"
#                 )
#
#                 # Read content from disk using WriterService
#                 content = writer_service.read_section(name, doc_type)
#
#                 # Validate content was actually read
#                 if content is None:
#                     raise ValueError(f"read_section returned None for {name}")
#
#                 logger.info(f"[SectionView GET] Read {len(content)} chars for {name}")
#
#                 # Build section file path for reference
#                 doc_dir_map = {
#                     "manuscript": "01_manuscript/contents",
#                     "supplementary": "02_supplementary/contents",
#                     "revision": "03_revision/contents",
#                     "shared": "shared",
#                 }
#                 section_dir = writer_service.writer_dir / doc_dir_map.get(
#                     doc_type, "01_manuscript/contents"
#                 )
#                 file_path = section_dir / f"{name}.tex"
#
#                 # Create response
#                 response = SectionReadResponse.create_success(
#                     content=content,
#                     section_name=name,
#                     section_id=section_name,
#                     doc_type=doc_type,
#                     file_path=file_path if file_path.exists() else None,
#                 )
#
#                 # Validate before returning
#                 response.validate()
#                 return JsonResponse(response.to_dict())
#
#             except Exception as e:
#                 logger.error(
#                     f"Error reading section {section_name}: {e}", exc_info=True
#                 )
#                 response = SectionReadResponse.create_failure(
#                     section_id=section_name,
#                     error_message=f"Failed to read section: {str(e)}",
#                 )
#                 return JsonResponse(response.to_dict(), status=500)
#
#         # POST: Write section to disk
#         elif request.method == "POST":
#             try:
#                 data = json.loads(request.body)
#                 content = data.get("content")
#                 # Allow body doc_type to override, but prefer parsed category
#                 doc_type = data.get("doc_type", category)
#
#                 # Validate content
#                 if content is None:
#                     response = SectionReadResponse.create_failure(
#                         section_id=section_name, error_message="Content is required"
#                     )
#                     return JsonResponse(response.to_dict(), status=400)
#
#                 if not isinstance(content, str):
#                     response = SectionReadResponse.create_failure(
#                         section_id=section_name,
#                         error_message=f"Content must be string, got {type(content).__name__}",
#                     )
#                     return JsonResponse(response.to_dict(), status=400)
#
#                 logger.info(
#                     f"[SectionView POST] Writing section: {section_name} -> category={category}, name={name}, doc_type={doc_type}, length: {len(content)}"
#                 )
#
#                 # Write content to disk using WriterService
#                 success = writer_service.write_section(name, content, doc_type)
#
#                 if success:
#                     # Auto-commit disabled - users should commit manually when ready
#                     # Changes will show in git gutter until committed
#
#                     # Return a read response with the saved content
#                     response = SectionReadResponse.create_success(
#                         content=content,
#                         section_name=name,
#                         section_id=section_name,
#                         doc_type=doc_type,
#                     )
#                     response.validate()
#                     return JsonResponse(response.to_dict())
#                 else:
#                     response = SectionReadResponse.create_failure(
#                         section_id=section_name,
#                         error_message="write_section returned False (unknown reason)",
#                     )
#                     return JsonResponse(response.to_dict(), status=500)
#
#             except Exception as e:
#                 logger.error(
#                     f"Error writing section {section_name}: {e}", exc_info=True
#                 )
#                 response = SectionReadResponse.create_failure(
#                     section_id=section_name,
#                     error_message=f"Failed to write section: {str(e)}",
#                 )
#                 return JsonResponse(response.to_dict(), status=500)
#
#     except Project.DoesNotExist:
#         return JsonResponse(
#             {"success": False, "error": "Project not found"}, status=404
#         )
#     except Exception as e:
#         logger.error(f"Error in section_view: {e}", exc_info=True)
#         return JsonResponse({"success": False, "error": str(e)}, status=500)
#
#
# @api_login_optional
# @require_http_methods(["POST"])
# def save_sections_view(request, project_id):
#     """Save multiple sections at once.
#
#     POST body:
#         {
#             "sections": {
#                 "section_name1": "content1",
#                 "section_name2": "content2",
#                 ...
#             },
#             "doc_type": "manuscript" (optional, default: manuscript)
#         }
#
#     Returns:
#         JSON response with SaveSectionsResponse structure
#     """
#     try:
#         from scitex.writer.dataclasses.results import SaveSectionsResponse
#
#         data = json.loads(request.body)
#         sections = data.get("sections", {})
#         doc_type = data.get("doc_type", "manuscript")
#
#         # Validate input
#         if not isinstance(sections, dict):
#             response = SaveSectionsResponse.create_failure(
#                 "Invalid request: 'sections' must be a dictionary"
#             )
#             return JsonResponse(response.to_dict(), status=400)
#
#         if not sections:
#             response = SaveSectionsResponse.create_failure("No sections provided")
#             return JsonResponse(response.to_dict(), status=400)
#
#         # Get project and service
#         from ....services import WriterService
#         from apps.infra.project_app.models import Project
#
#         project = Project.objects.get(id=project_id)
#
#         # Get effective user (authenticated or visitor)
#         user, is_visitor = get_user_for_request(request, project_id)
#         if not user:
#             response = SaveSectionsResponse.create_failure("Invalid session")
#             return JsonResponse(response.to_dict(), status=403)
#
#         writer_service = WriterService(project_id, user.id)
#
#         # Save each section
#         saved_count = 0
#         error_list = []
#         error_details = {}
#
#         from ....configs.sections_config import parse_section_id
#
#         for section_id, content in sections.items():
#             try:
#                 # Validate content type
#                 if not isinstance(content, str):
#                     error_msg = f"Content must be string, got {type(content).__name__}"
#                     error_list.append(f"{section_id}: {error_msg}")
#                     error_details[section_id] = error_msg
#                     continue
#
#                 # Parse hierarchical section ID
#                 category, section_name = parse_section_id(section_id)
#
#                 # Use parsed category instead of global doc_type
#                 success = writer_service.write_section(section_name, content, category)
#
#                 if success:
#                     saved_count += 1
#                 else:
#                     error_msg = "write_section returned False (unknown reason)"
#                     error_list.append(f"{section_id}: {error_msg}")
#                     error_details[section_id] = error_msg
#
#             except Exception as e:
#                 error_msg = str(e)
#                 logger.error(f"Error saving section {section_id}: {e}", exc_info=True)
#                 error_list.append(f"{section_id}: {error_msg}")
#                 error_details[section_id] = error_msg
#
#         # Create response
#         if error_list:
#             response = SaveSectionsResponse(
#                 success=saved_count > 0,  # Partial success if some saved
#                 sections_saved=saved_count,
#                 sections_skipped=len(error_list),
#                 message=f"Saved {saved_count}/{len(sections)} sections",
#                 errors=error_list,
#                 error_details=error_details,
#             )
#             # Validate before returning
#             response.validate()
#             return JsonResponse(
#                 response.to_dict(), status=500 if saved_count == 0 else 200
#             )
#
#         response = SaveSectionsResponse.create_success(
#             sections_saved=saved_count, message=f"Saved {saved_count} sections"
#         )
#         # Validate before returning
#         response.validate()
#         return JsonResponse(response.to_dict())
#
#     except Project.DoesNotExist:
#         response = SaveSectionsResponse.create_failure("Project not found")
#         return JsonResponse(response.to_dict(), status=404)
#     except Exception as e:
#         logger.error(f"Error saving sections: {e}", exc_info=True)
#         response = SaveSectionsResponse.create_failure(
#             f"Server error: {str(e)}", errors=[str(e)]
#         )
#         return JsonResponse(response.to_dict(), status=500)
#
#
# @api_login_optional
# @require_http_methods(["GET"])
# def read_tex_file_view(request, project_id):
#     """Read a .tex file directly from disk by path.
#
#     GET params:
#         path: File path relative to workspace (e.g., scitex/writer/01_manuscript/contents/methods.tex)
#
#     Returns:
#         JSON with file content
#     """
#     try:
#         from apps.infra.project_app.models import Project
#         from ..auth_utils import get_user_for_request
#
#         # Get path from query params
#         file_path = request.GET.get("path")
#         if not file_path:
#             return JsonResponse(
#                 {"success": False, "error": "Missing 'path' query parameter"},
#                 status=400
#             )
#
#         # Get project
#         project = Project.objects.get(id=project_id)
#
#         # Get effective user (authenticated or visitor)
#         user, is_visitor = get_user_for_request(request, project_id)
#         if not user:
#             return JsonResponse(
#                 {"success": False, "error": "Invalid session"}, status=403
#             )
#
#         # Get workspace path using get_local_path() method
#         workspace_path = project.get_local_path()
#         if not workspace_path:
#             return JsonResponse(
#                 {"success": False, "error": "Project has no local path configured"},
#                 status=400
#             )
#         full_path = workspace_path / file_path
#
#         # Security: Ensure path is within workspace
#         try:
#             full_path = full_path.resolve()
#             workspace_resolved = workspace_path.resolve()
#             if not str(full_path).startswith(str(workspace_resolved)):
#                 return JsonResponse(
#                     {"success": False, "error": "Path outside workspace"},
#                     status=403
#                 )
#         except Exception as e:
#             return JsonResponse(
#                 {"success": False, "error": f"Invalid path: {e}"},
#                 status=400
#             )
#
#         # Check file exists
#         if not full_path.exists():
#             return JsonResponse(
#                 {"success": False, "error": f"File not found: {file_path}"},
#                 status=404
#             )
#
#         # Read file content
#         try:
#             content = full_path.read_text(encoding="utf-8")
#             return JsonResponse({
#                 "success": True,
#                 "content": content,
#                 "path": file_path,
#                 "filename": full_path.name,
#             })
#         except Exception as e:
#             logger.error(f"Error reading file {file_path}: {e}")
#             return JsonResponse(
#                 {"success": False, "error": f"Failed to read file: {e}"},
#                 status=500
#             )
#
#     except Project.DoesNotExist:
#         return JsonResponse(
#             {"success": False, "error": "Project not found"}, status=404
#         )
#     except Exception as e:
#         logger.error(f"Error in read_tex_file_view: {e}", exc_info=True)
#         return JsonResponse({"success": False, "error": str(e)}, status=500)
#
#
# # View aliases for backward compatibility
# section_history_view = section_view  # Temp stub
# section_diff_view = section_view  # Temp stub
# section_checkout_view = section_view  # Temp stub
# section_commit_view = section_view  # Temp stub
# available_sections_view = section_view  # Temp stub
# presence_update_view = section_view  # Temp stub
#
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: apps/writer_app/views/editor/api/content.py
# --------------------------------------------------------------------------------
