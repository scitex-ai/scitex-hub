"""X2PDF endpoints: start a conversion, poll it, fetch the PDF, save it to Files."""

from __future__ import annotations

import logging

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET, require_POST

from apps.infra.platform_app.services.paths import resolve_within

from ..x2pdf import jobs
from ..x2pdf.convert import MAX_INPUT_BYTES
from ..x2pdf.ssrf import UnsafeURLError, validate_url

logger = logging.getLogger(__name__)


def tool_x2pdf(request):
    from django.shortcuts import render

    from .tools_views import _tool_context

    strings = {
        "converting": _("Converting %s"),
        "failed": _("Conversion failed."),
        "needInput": _("Choose a file or enter a URL."),
        "signIn": _("Sign in to use this tool, then try again."),
        "serverError": _("The server returned %s without a JSON body."),
        "onePage": _("1 page"),
        "pages": _("%s pages"),
        "savedTo": _("Saved to Files:"),
    }
    return render(
        request,
        "tools_app/tools/x2pdf.html",
        {
            **_tool_context(request),
            "max_mb": MAX_INPUT_BYTES // (1024 * 1024),
            "x2pdf_strings": strings,
        },
    )


def _dispatch(request, job_id: str) -> None:
    from ..tasks import x2pdf_convert

    try:
        x2pdf_convert.delay(request.user.pk, job_id)
    except Exception:
        # No broker: convert in this request instead of leaving the job queued.
        logger.warning("x2pdf: celery unavailable, converting inline", exc_info=True)
        path = jobs.job_dir(request.user, job_id)
        if path is not None:
            jobs.run_job(path)


def _public(meta: dict, job_id: str) -> dict:
    keys = (
        "status",
        "kind",
        "title",
        "pages",
        "notes",
        "size",
        "filename",
        "error",
        "original_name",
        "url",
    )
    return {"job": job_id, **{k: meta[k] for k in keys if k in meta}}


@login_required
@require_POST
def api_x2pdf_create(request):
    upload = request.FILES.get("file")
    url = (request.POST.get("url") or "").strip()
    if not upload and not url:
        return JsonResponse({"error": _("Choose a file or enter a URL.")}, status=400)
    if upload is not None:
        if upload.size > MAX_INPUT_BYTES:
            return JsonResponse(
                {
                    "error": _("The file is larger than %(mb)d MB.")
                    % {"mb": MAX_INPUT_BYTES // (1024 * 1024)}
                },
                status=413,
            )
        job_id = jobs.create_job(request.user, upload=upload)
    else:
        if "://" not in url:
            url = "https://" + url
        try:
            validate_url(url)
        except UnsafeURLError:
            return JsonResponse(
                {"error": _("The supplied URL is not allowed.")}, status=400
            )
        job_id = jobs.create_job(request.user, url=url)
    _dispatch(request, job_id)
    path = jobs.job_dir(request.user, job_id)
    return JsonResponse(_public(jobs.read_meta(path), job_id), status=202)


@login_required
@require_GET
def api_x2pdf_status(request, job_id):
    path = jobs.job_dir(request.user, job_id)
    if path is None:
        return JsonResponse({"error": _("Conversion not found.")}, status=404)
    meta = jobs.read_meta(path)
    if jobs.is_stale_queued(meta):
        meta = jobs.run_job(path)
    return JsonResponse(_public(meta, job_id))


@login_required
@require_GET
@xframe_options_sameorigin
def api_x2pdf_pdf(request, job_id):
    path = jobs.job_dir(request.user, job_id)
    meta = jobs.read_meta(path) if path else {}
    output = resolve_within(path, "output.pdf") if path else None
    if (
        path is None
        or output is None
        or meta.get("status") != "done"
        or not output.is_file()
    ):
        return JsonResponse({"error": _("Conversion not found.")}, status=404)
    return FileResponse(
        open(output, "rb"),
        content_type="application/pdf",
        as_attachment=request.GET.get("download") == "1",
        filename=meta.get("filename") or "converted.pdf",
    )


@login_required
@require_POST
def api_x2pdf_save(request, job_id):
    from apps.workspace.files_app.services import save_to_downloads, user_root

    path = jobs.job_dir(request.user, job_id)
    meta = jobs.read_meta(path) if path else {}
    output = resolve_within(path, "output.pdf") if path else None
    if path is None or output is None or meta.get("status") != "done":
        return JsonResponse({"error": _("Conversion not found.")}, status=404)
    saved = save_to_downloads(
        request.user, meta.get("filename") or "converted.pdf", output
    )
    rel = saved.relative_to(user_root(request.user)).as_posix()
    return JsonResponse({"saved": rel, "files_url": "/apps/files/"})
