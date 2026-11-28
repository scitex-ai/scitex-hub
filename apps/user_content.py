"""Render and serve content that users author.

Two entry points, one per way user content reaches a browser:

* :func:`render_user_markdown` turns user Markdown (READMEs, ``.md`` files,
  chat text) into HTML that is safe to place in a Hub page. Markdown passes
  raw HTML through, so every result is run through an allowlist sanitiser
  (``nh3``): only formatting tags survive, links and images keep only
  ``http``/``https``/``mailto`` or relative URLs, and no element keeps an
  event handler, ``style`` or arbitrary ``class``. The return value is a
  ``SafeString``; templates render it without ``|safe``.

* :func:`user_file_response` serves the bytes of a user file. A browser
  navigating to it must never run it as part of the Hub origin, so every
  response carries ``X-Content-Type-Options: nosniff`` and a sandbox CSP, and
  only passive media (raster images, audio, video, PDF) or plain text is
  displayed inline. HTML, SVG, XML, scripts and anything unrecognised are
  sent as attachments.

``tests/security/test_user_content_rendering.py`` keeps every Markdown
renderer and every inline file response in ``apps/`` routed through here.
"""

from __future__ import annotations

import mimetypes
import re
from functools import lru_cache
from typing import IO, Iterable

from django.http import FileResponse, HttpResponse
from django.utils.http import content_disposition_header
from django.utils.safestring import SafeString, mark_safe

__all__ = [
    "SANDBOX_CSP",
    "harden_user_file_headers",
    "render_user_markdown",
    "sanitize_user_html",
    "user_file_response",
]

# --------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------

DEFAULT_MARKDOWN_EXTENSIONS: tuple[str, ...] = ("fenced_code", "tables", "nl2br")

# Extensions whose output the allowlist below is written for. A new extension
# may emit markup the allowlist drops (harmless, but surprising) -- add it
# here deliberately.
SUPPORTED_MARKDOWN_EXTENSIONS = frozenset(
    {"extra", "fenced_code", "tables", "nl2br", "codehilite", "toc", "sane_lists"}
)

# Heading/anchor ids are prefixed so user markup cannot clobber page globals
# (``<h1 id="csrfToken">``); in-page links are rewritten to match.
ID_PREFIX = "user-content-"

_ALLOWED_TAGS = frozenset(
    {
        "a", "abbr", "b", "blockquote", "br", "caption", "code", "dd", "del",
        "details", "div", "dl", "dt", "em", "figcaption", "figure",
        "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "ins", "kbd",
        "li", "mark", "ol", "p", "pre", "q", "s", "samp", "small", "span",
        "strong", "sub", "summary", "sup", "table", "tbody", "td", "tfoot",
        "th", "thead", "tr", "u", "ul", "var",
    }
)  # fmt: skip

_HEADING_ATTRS = {"id"}
_ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    "a": {"href", "title"},
    "abbr": {"title"},
    "img": {"src", "alt", "title", "width", "height"},
    "ol": {"start"},
    "td": {"align", "colspan", "rowspan"},
    "th": {"align", "colspan", "rowspan"},
    "code": {"class"},
    "pre": {"class"},
    "span": {"class"},
    "div": {"class"},
    **{f"h{level}": set(_HEADING_ATTRS) for level in range(1, 7)},
}

_URL_SCHEMES = frozenset({"http", "https", "mailto"})
_ALIGN_VALUES = frozenset({"left", "right", "center"})
_LANGUAGE_CLASS = re.compile(r"^language-[A-Za-z0-9_+#.-]{1,40}$")
_DIV_CLASSES = frozenset({"codehilite", "toc"})


@lru_cache(maxsize=1)
def _highlight_classes() -> frozenset[str]:
    """Token classes Pygments emits for ``codehilite`` (empty if absent)."""
    try:
        from pygments.token import STANDARD_TYPES
    except ImportError:
        return frozenset()
    return frozenset(cls for cls in STANDARD_TYPES.values() if cls)


def _keep_classes(value: str, allowed) -> str | None:
    kept = [cls for cls in value.split() if allowed(cls)]
    return " ".join(kept) or None


def _attribute_filter(tag: str, attr: str, value: str) -> str | None:
    if attr == "class":
        if tag in {"code", "pre"}:
            return _keep_classes(
                value, lambda c: bool(_LANGUAGE_CLASS.match(c)) or c == "codehilite"
            )
        if tag == "span":
            return _keep_classes(value, _highlight_classes().__contains__)
        if tag == "div":
            return _keep_classes(value, _DIV_CLASSES.__contains__)
        return None
    if attr == "align":
        return value if value.lower() in _ALIGN_VALUES else None
    if attr in {"colspan", "rowspan", "start", "width", "height"}:
        return value if value.isdigit() and len(value) <= 4 else None
    if attr == "id":
        return value if value.startswith(ID_PREFIX) else ID_PREFIX + value
    if (
        attr == "href"
        and value.startswith("#")
        and not value.startswith("#" + ID_PREFIX)
    ):
        return "#" + ID_PREFIX + value[1:]
    return value


def sanitize_user_html(html: str) -> SafeString:
    """Reduce *html* to the formatting allowlist and mark the result safe."""
    import nh3

    cleaned = nh3.clean(
        html,
        tags=set(_ALLOWED_TAGS),
        clean_content_tags={"script", "style"},
        attributes={tag: set(attrs) for tag, attrs in _ALLOWED_ATTRIBUTES.items()},
        attribute_filter=_attribute_filter,
        url_schemes=set(_URL_SCHEMES),
        link_rel="noopener noreferrer nofollow",
        strip_comments=True,
    )
    return mark_safe(cleaned)  # noqa: S308 -- output of the allowlist sanitiser


def render_user_markdown(
    text: str | None, extensions: Iterable[str] = DEFAULT_MARKDOWN_EXTENSIONS
) -> SafeString:
    """Render user-authored Markdown to sanitised HTML.

    Formatting, links, images, fenced and highlighted code, tables and TeX
    math written as text (``$...$``, ``\\(...\\)``) are preserved; raw HTML is
    reduced to the allowlist, and scripts, event handlers, ``style`` and
    ``javascript:``/``data:`` URLs are removed.
    """
    if not text:
        return mark_safe("")
    extensions = tuple(extensions)
    unknown = set(extensions) - SUPPORTED_MARKDOWN_EXTENSIONS
    if unknown:
        raise ValueError(f"unsupported Markdown extensions: {sorted(unknown)}")

    import markdown

    configs = {}
    if "tables" in extensions or "extra" in extensions:
        # `align="..."` instead of `style="text-align: ..."`: style is not on
        # the allowlist, alignment is.
        configs["tables"] = {"use_align_attribute": True}
    html = markdown.markdown(text, extensions=extensions, extension_configs=configs)
    return sanitize_user_html(html)


# --------------------------------------------------------------------------
# Files
# --------------------------------------------------------------------------

# Same policy files_app has applied since it shipped: a document opened from a
# user file gets a unique opaque origin and may load nothing.
SANDBOX_CSP = "sandbox; default-src 'none'"

_INLINE_MEDIA_PREFIXES = ("image/", "audio/", "video/")
_INLINE_EXACT = frozenset({"application/pdf"})
# Types a browser may execute or render as an active document even when they
# arrive as an image or text subtype.
_ACTIVE_TYPES = frozenset(
    {
        "text/html",
        "application/xhtml+xml",
        "image/svg+xml",
        "text/xml",
        "application/xml",
        "text/xsl",
        "application/xslt+xml",
        "text/javascript",
        "application/javascript",
        "application/x-javascript",
        "text/ecmascript",
        "application/ecmascript",
        "text/css",
        "text/cache-manifest",
    }
)


# Data formats researchers open to read; shown as plain text, never parsed.
_TEXTUAL_TYPES = frozenset(
    {
        "application/json",
        "application/yaml",
        "application/x-yaml",
        "application/toml",
        "application/x-sh",
        "application/x-tex",
        "application/x-latex",
        "application/x-bibtex",
    }
)


def _base_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


def _is_active(base: str) -> bool:
    return base in _ACTIVE_TYPES or base.endswith("+xml") or base.endswith("/xml")


def _decide(content_type: str, download: bool) -> tuple[str, bool]:
    """Return ``(content_type, inline)`` for a user file of *content_type*."""
    base = _base_type(content_type)
    if download or _is_active(base):
        return content_type, False
    if base.startswith(_INLINE_MEDIA_PREFIXES) or base in _INLINE_EXACT:
        return content_type, True
    if base.startswith("text/") or base in _TEXTUAL_TYPES or base.endswith("+json"):
        return "text/plain; charset=utf-8", True
    return content_type, False


def harden_user_file_headers(response: HttpResponse) -> HttpResponse:
    """Add the headers every response carrying user file bytes needs."""
    response["X-Content-Type-Options"] = "nosniff"
    # Chrome's built-in PDF viewer does not render under a sandbox CSP; its
    # scripting is isolated from the embedding origin regardless.
    if _base_type(response.get("Content-Type", "")) != "application/pdf":
        response["Content-Security-Policy"] = SANDBOX_CSP
    return response


def user_file_response(
    content: bytes | IO[bytes],
    filename: str,
    *,
    content_type: str | None = None,
    download: bool = False,
) -> HttpResponse:
    """Serve user file bytes without letting them run on the Hub origin.

    *content* is either the bytes or an open binary file (streamed). The
    guessed or given *content_type* decides the disposition: raster images,
    audio, video and PDF display inline; other text displays inline as
    ``text/plain``; HTML, SVG, XML, scripts, CSS and unknown types download.
    """
    if content_type is None:
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    content_type, inline = _decide(content_type, download)
    if isinstance(content, (bytes, bytearray)):
        response = HttpResponse(bytes(content), content_type=content_type)
        response.headers["Content-Disposition"] = content_disposition_header(
            not inline, filename
        )
    else:
        response = FileResponse(
            content,
            as_attachment=not inline,
            filename=filename,
            content_type=content_type,
        )
    return harden_user_file_headers(response)

