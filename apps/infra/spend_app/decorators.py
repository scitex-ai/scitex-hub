"""View decorators that put spend controls on a request path."""

from __future__ import annotations

import functools

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme

from .services import gate


def _wants_json(request) -> bool:
    accept = request.headers.get("Accept", "")
    return (
        "/api/" in request.path
        or "application/json" in accept
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.content_type == "application/json"
    )


def refusal_response(request, exc: gate.Refused):
    if _wants_json(request):
        return gate.refusal_json(exc)
    messages.error(request, exc.message)
    back = request.META.get("HTTP_REFERER", "")
    if back and url_has_allowed_host_and_scheme(
        back, allowed_hosts={request.get_host()}
    ):
        return redirect(back)
    return HttpResponse(exc.message, status=exc.http_status, content_type="text/plain")


def storage_write(view):
    """Refuse a WRITE when storage is read-only (cap reached / restricted) or
    the upload would break the storage quota. Reads and deletes are never
    wrapped with this: deleting is how an account gets back under its limit."""

    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.method in ("POST", "PUT", "PATCH"):
            sizes = [f.size for files in request.FILES.lists() for f in files[1]]
            try:
                gate.require_storage_write(request.user, incoming_sizes=sizes)
            except gate.Refused as exc:
                return refusal_response(request, exc)
        return view(request, *args, **kwargs)

    return wrapper


__all__ = ["refusal_response", "storage_write"]
