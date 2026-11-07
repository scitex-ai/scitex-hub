"""Host identity adapter for the SDK's route-agnostic documentation action."""

from html import escape

API_DOCS_HEADER = "X-SciTeX-API-Docs-URL"


def stamp_module_docs_response(response, module):
    """Supply the registered fragment owner before the host mounts its content."""
    from apps.infra.public_app.services.interface_catalog import api_docs_url

    try:
        value = api_docs_url(module.pip_package) if module.pip_package else ""
    except ValueError:
        value = ""
    response[API_DOCS_HEADER] = value
    return response


def inject_api_docs_metadata(request, response, *, modules=None):
    """Stamp a registered GUI owner's docs URL, including embedded documents.

    No handler, package code, account data or endpoint is loaded/probed here.
    Fragments, streams, encoded bodies and non-HTML responses are unchanged.
    """
    if getattr(response, "streaming", False) or response.status_code != 200:
        return
    if (
        response.get("Content-Encoding")
        or "text/html" not in response.get("Content-Type", "").lower()
    ):
        return
    from apps.infra.public_app.services.interface_catalog import api_docs_url

    from .middleware_site_content_frame import _body_open_tag

    if modules is None:
        from .registry import get_all_modules

        modules = get_all_modules()
    available = modules
    candidates = []
    for module in available:
        path = module.get_url()
        if request.path == path or (
            path != "/" and request.path.startswith(path.rstrip("/") + "/")
        ):
            candidates.append(module)
    if candidates:
        module = max(candidates, key=lambda value: len(value.get_url()))
        package = module.pip_package
    else:
        from ._resolved_view_owner import resolved_view_owner

        package = resolved_view_owner(request)
    if not package:
        return
    try:
        href = api_docs_url(package)
    except ValueError:
        return
    body = response.content.decode(response.charset or "utf-8")
    tag = _body_open_tag(body)
    if tag is None or "data-stx-api-docs-url" in tag.group():
        return
    body = (
        body[: tag.end() - 1]
        + ' data-stx-api-docs-url="'
        + escape(href, quote=True)
        + '">'
        + body[tag.end() :]
    )
    response.content = body.encode(response.charset or "utf-8")
    if response.get("Content-Length") is not None:
        response["Content-Length"] = str(len(response.content))
    if response.get("ETag") is not None:
        del response["ETag"]
