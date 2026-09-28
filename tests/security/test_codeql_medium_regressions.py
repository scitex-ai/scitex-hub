"""Regression tests for the medium-severity CodeQL remediation set."""

from pathlib import Path

from apps.security import safe_log_field

ROOT = Path(__file__).resolve().parents[2]


def test_untrusted_log_fields_are_single_line_and_bounded():
    rendered = safe_log_field("doi\r\nforged-entry" + "x" * 600)
    assert "\r" not in rendered
    assert "\n" not in rendered
    assert "\\r\\n" in rendered
    assert len(rendered) == 512


def test_external_scripts_are_pinned_with_sri():
    templates = [
        "apps/workspace/scholar_app/templates/scholar_app/scholar_unified.html",
        "apps/workspace/scholar_app/templates/scholar_app/scholar_partial.html",
        "apps/workspace/scholar_app/templates/scholar_app/index.html",
        "apps/workspace/docs_app/templates/docs_app/docs_design_rules.html",
    ]
    for relative in templates:
        text = (ROOT / relative).read_text()
        assert 'integrity="sha384-' in text
        assert 'crossorigin="anonymous"' in text


def test_project_redirects_use_named_local_routes():
    files = [
        "apps/infra/project_app/views/repository/add_file.py",
        "apps/infra/project_app/views/projects/detail.py",
    ]
    for relative in files:
        text = (ROOT / relative).read_text()
        assert 'redirect(f"/{username}' not in text
        assert '"project_app:' in text
    assert "reverse(" in (ROOT / files[1]).read_text()


def test_exception_details_are_not_returned_by_remediated_views():
    files = [
        "apps/workspace/scholar_app/api/citation_graph.py",
        "apps/workspace/scholar_app/views/library/views.py",
        "apps/workspace/scholar_app/views/search/api_crossref_local.py",
        "apps/workspace/console_app/job_api_views.py",
        "apps/infra/public_app/views/status/api/realtime.py",
        "apps/infra/public_app/views/status/api/history.py",
        "apps/infra/public_app/views/status/visitor.py",
        "apps/infra/workspace_api/views/file_content.py",
        "apps/workspace/apps_app/views/api.py",
        "apps/workspace/apps_app/views/app_create.py",
        "apps/workspace/files_app/views.py",
        "apps/workspace/tools_app/views/x2pdf_api.py",
    ]
    forbidden = (
        '"error": str(e)',
        '"error": str(exc)',
        '"message": f"Error: {str(e)}"',
    )
    for relative in files:
        text = (ROOT / relative).read_text()
        assert not any(pattern in text for pattern in forbidden), relative
