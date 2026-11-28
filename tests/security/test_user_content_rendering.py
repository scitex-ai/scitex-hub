#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""User-authored Markdown and user files reach the browser only through
``apps/user_content.py``.

Three layers:

* the renderer itself, on real Markdown: active markup is removed and the
  formatting researchers write (links, code, tables, math, headings) is kept;
* the views, through the Django test client against real files on disk: the
  pages that show READMEs and ``.md`` files carry no active markup, and raw
  file responses never display HTML/SVG inline on the Hub origin;
* source guards that fail when a new Markdown renderer, ``|safe`` on user
  content, or a hand-built inline file response appears elsewhere.

No mocks: real ``markdown`` + ``nh3``, real templates, real HTTP responses.
One assertion per test (STX-TQ007).
"""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from apps.user_content import SANDBOX_CSP, render_user_markdown, user_file_response
from tests.tracked_source import tracked_source_files

pytestmark = pytest.mark.security

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALL_EXTENSIONS = ["fenced_code", "tables", "nl2br", "codehilite", "toc"]

# Each entry is Markdown a user can commit to a README or .md file.
PAYLOADS = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)></svg>",
    "<iframe src=https://example.org></iframe>",
    '<a href="javascript:alert(1)">a</a>',
    "[b](javascript:alert(1))",
    "[c](JaVaScRiPt:alert(1))",
    "[d](&#106;avascript:alert(1))",
    "[e](vbscript:msgbox(1))",
    '<a href="data:text/html,<script>alert(1)</script>">f</a>',
    "![g](data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=)",
    "<details open ontoggle=alert(1)>h</details>",
    '<p style="position:fixed;inset:0">i</p>',
    "<form action=/x><input name=j><button>k</button></form>",
    "<object data=x></object><embed src=x>",
    "<math><mtext><table><mglyph><style><img src=x onerror=alert(1)>",
    "<base href=https://example.org/>",
    "<meta http-equiv=refresh content=0;url=https://example.org>",
]

# What must never survive into rendered user HTML.
_ACTIVE = re.compile(
    r"<\s*(script|iframe|svg|object|embed|form|input|button|style|base|meta|math)\b"
    r"|\son\w+\s*="
    r"|javascript:|vbscript:|data:"
    r"|\sstyle\s*=",
    re.IGNORECASE,
)

LEGITIMATE = """# Results

See [the paper](https://example.org/paper) or [the methods](#methods).

## Methods

| condition | n | mean |
|:----------|--:|:----:|
| control   | 12 | 0.41 |

```python
def mean(xs):
    return sum(xs) / len(xs)
```

Inline `code`, **bold**, *italic* and ![fig](figures/fig1.png).

The effect is $\\beta = 0.3$ and $$E = mc^2$$.

<details><summary>Raw numbers</summary>42</details>
"""

# Marks the user-rendered region inside a full Hub page.
_START = "UCSTART"
_END = "UCEND"
# An unclosed <style> (the namespace-confusion payload) makes the sanitiser
# drop everything after it, end marker included; the renderer tests cover it.
_PAGE_PAYLOADS = [p for p in PAYLOADS if "<mglyph>" not in p]
README_ATTACK = (
    f"{_START}\n\n# Hello\n\n"
    + "\n\n".join(_PAGE_PAYLOADS)
    + f"\n\n[ok](https://example.org)\n\n{_END}\n"
)


def _user_region(html: str) -> str:
    """The part of a page produced from the fixture Markdown."""
    start = html.index(_START)
    return html[start : html.index(_END, start)]


def _render_legitimate(extensions=("fenced_code", "tables", "nl2br", "codehilite")):
    return str(render_user_markdown(LEGITIMATE, extensions=list(extensions)))


# --------------------------------------------------------------------------
# Renderer
# --------------------------------------------------------------------------


@pytest.mark.parametrize("payload", PAYLOADS)
def test_render_user_markdown_removes_active_markup(payload):
    # Arrange
    extensions = _ALL_EXTENSIONS
    # Act
    html = render_user_markdown(payload, extensions=extensions)
    # Assert
    assert not _ACTIVE.search(html), html


def test_render_user_markdown_keeps_external_link():
    # Arrange
    # Act
    html = _render_legitimate()
    # Assert
    assert 'href="https://example.org/paper"' in html


def test_render_user_markdown_points_in_page_link_at_prefixed_heading():
    # Arrange
    # Act
    html = _render_legitimate(["tables", "toc"])
    # Assert
    assert all(
        marker in html
        for marker in ('href="#user-content-methods"', 'id="user-content-methods"')
    )


def test_render_user_markdown_keeps_table_alignment_without_style():
    # Arrange
    # Act
    html = _render_legitimate()
    # Assert
    assert '<th align="right">n</th>' in html


def test_render_user_markdown_keeps_highlighted_code_block():
    # Arrange
    # Act
    html = _render_legitimate()
    # Assert
    assert '<div class="codehilite">' in html


def test_render_user_markdown_keeps_inline_code_bold_and_italic():
    # Arrange
    expected = ("<code>code</code>", "<strong>bold</strong>", "<em>italic</em>")
    # Act
    html = _render_legitimate()
    # Assert
    assert [tag for tag in expected if tag not in html] == []


def test_render_user_markdown_keeps_relative_image_source():
    # Arrange
    # Act
    html = _render_legitimate()
    # Assert
    assert 'src="figures/fig1.png"' in html


def test_render_user_markdown_leaves_tex_math_text_untouched():
    # Arrange
    expected = ("$\\beta = 0.3$", "$$E = mc^2$$")
    # Act
    html = _render_legitimate()
    # Assert
    assert [m for m in expected if m not in html] == []


def test_render_user_markdown_keeps_details_summary_raw_html():
    # Arrange
    # Act
    html = _render_legitimate()
    # Assert
    assert "<details><summary>Raw numbers</summary>42</details>" in html


def test_render_user_markdown_links_carry_noopener():
    # Arrange
    # Act
    html = _render_legitimate()
    # Assert
    assert 'rel="noopener noreferrer nofollow"' in html


def test_render_user_markdown_refuses_unreviewed_extension():
    # Arrange
    extensions = ["attr_list"]
    # Act
    # Assert
    with pytest.raises(ValueError):
        render_user_markdown("x", extensions=extensions)


# --------------------------------------------------------------------------
# File responses (helper level)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    ["page.html", "page.htm", "page.xhtml", "image.svg", "feed.xml", "app.js", "s.css"],
)
def test_user_file_response_downloads_active_types(filename):
    # Arrange
    body = b"<script>alert(1)</script>"
    # Act
    response = user_file_response(body, filename)
    # Assert
    assert response["Content-Disposition"].startswith("attachment")


@pytest.mark.parametrize(
    "filename", ["fig.png", "fig.jpg", "paper.pdf", "talk.mp4", "notes.txt"]
)
def test_user_file_response_displays_passive_types_inline(filename):
    # Arrange
    body = b"x"
    # Act
    response = user_file_response(body, filename)
    # Assert
    assert response["Content-Disposition"].startswith("inline")


def test_user_file_response_shows_source_code_as_plain_text():
    # Arrange
    body = b"print(1)"
    # Act
    response = user_file_response(body, "analysis.py")
    # Assert
    assert response["Content-Type"] == "text/plain; charset=utf-8"


def test_user_file_response_download_flag_forces_attachment():
    # Arrange
    body = b"x"
    # Act
    response = user_file_response(body, "fig.png", download=True)
    # Assert
    assert response["Content-Disposition"].startswith("attachment")


def test_user_file_response_is_sandboxed_and_nosniff():
    # Arrange
    body = b"x"
    # Act
    response = user_file_response(body, "fig.png")
    # Assert
    assert (
        response["X-Content-Type-Options"],
        response["Content-Security-Policy"],
    ) == ("nosniff", SANDBOX_CSP)


# --------------------------------------------------------------------------
# Views, over HTTP
# --------------------------------------------------------------------------


class TestUserContentOverHttp(TestCase):
    def setUp(self):
        from apps.infra.project_app.models import Project
        from apps.infra.project_app.services.filesystem.paths import (
            get_user_base_path,
        )
        from apps.infra.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        # A DB transaction does not isolate on-disk project homes across
        # xdist workers: each fixture owns and cleans only its unique home.
        self.owner = User.objects.create_user(username=f"uc-{uuid4().hex[:12]}")
        self.project = Project.objects.create(
            owner=self.owner, slug="notes", name="notes", visibility="public"
        )
        base = get_user_base_path(self.owner)
        self.addCleanup(shutil.rmtree, base.parent, ignore_errors=True)
        (base / self.project.slug).mkdir(parents=True, exist_ok=True)
        root = get_project_filesystem_manager(self.owner).get_project_root_path(
            self.project
        )
        (root / "README.md").write_text(README_ATTACK)
        (root / "notes.md").write_text(README_ATTACK)
        (root / "page.html").write_text("<script>alert(document.cookie)</script>")
        (root / "image.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>'
        )
        (root / "fig.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    def _raw(self, name):
        return self.client.get(
            f"/api/workspace/file-content/{name}",
            {"project_id": self.project.pk, "raw": "true"},
        )

    def test_project_page_readme_has_no_active_markup(self):
        # Arrange
        url = f"/{self.owner.username}/notes/?view=repository"
        # Act
        region = _user_region(self.client.get(url).content.decode())
        # Assert
        assert ("Hello" in region, _ACTIVE.search(region)) == (True, None)

    def test_markdown_file_view_has_no_active_markup(self):
        # Arrange
        url = f"/{self.owner.username}/notes/blob/notes.md?view=repository"
        # Act
        region = _user_region(self.client.get(url).content.decode())
        # Assert
        assert ("Hello" in region, _ACTIVE.search(region)) == (True, None)

    def test_workspace_file_pane_markdown_has_no_active_markup(self):
        # Arrange
        self.client.force_login(self.owner)
        # Act
        response = self.client.get("/apps/my-projects/api/file/", {"path": "notes.md"})
        region = _user_region(response.json()["html"])
        # Assert
        assert ("Hello" in region, _ACTIVE.search(region)) == (True, None)

    def test_workspace_raw_html_is_sent_as_attachment(self):
        # Arrange
        name = "page.html"
        # Act
        response = self._raw(name)
        # Assert
        assert (response.status_code, response["Content-Disposition"][:10]) == (
            200,
            "attachment",
        )

    def test_workspace_raw_svg_is_sent_as_attachment(self):
        # Arrange
        name = "image.svg"
        # Act
        response = self._raw(name)
        # Assert
        assert (response.status_code, response["Content-Disposition"][:10]) == (
            200,
            "attachment",
        )

    def test_workspace_raw_png_is_inline_but_sandboxed(self):
        # Arrange
        name = "fig.png"
        # Act
        response = self._raw(name)
        # Assert
        assert (
            response["Content-Disposition"][:6],
            response["Content-Security-Policy"],
            response["X-Content-Type-Options"],
        ) == ("inline", SANDBOX_CSP, "nosniff")

    def test_blob_raw_html_is_plain_text_and_sandboxed(self):
        # Arrange
        url = f"/{self.owner.username}/notes/blob/page.html"
        # Act
        response = self.client.get(url, {"mode": "raw"})
        # Assert
        assert (
            response.status_code,
            response["Content-Type"],
            response["Content-Security-Policy"],
            response["X-Content-Type-Options"],
        ) == (200, "text/plain; charset=utf-8", SANDBOX_CSP, "nosniff")




class TestSharedChatSession(TestCase):
    def test_shared_session_message_has_no_active_markup(self):
        # Arrange
        from apps.infra.llm_app.models import ChatMessage, ChatSession

        user = User.objects.create_user(username=f"uc-{uuid4().hex[:12]}")
        session = ChatSession.objects.create(user=user, is_shared=True)
        ChatMessage.objects.create(session=session, role="user", text=README_ATTACK)
        # Act
        response = self.client.get(f"/apps/llm/shared/{session.share_token}/")
        region = _user_region(response.content.decode())
        # Assert
        assert ("Hello" in region, _ACTIVE.search(region)) == (True, None)


def test_app_detail_readme_has_no_active_markup():
    # Arrange
    from apps.workspace.apps_app.views.pages import _render_readme

    module = SimpleNamespace(project=SimpleNamespace(slug="demo"))
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp) / "data" / "projects" / "demo"
        project_dir.mkdir(parents=True)
        (project_dir / "README.md").write_text(README_ATTACK)
        # Act
        with override_settings(BASE_DIR=Path(tmp)):
            region = _user_region(str(_render_readme(module)))
    # Assert
    assert ("Hello" in region, _ACTIVE.search(region)) == (True, None)


# --------------------------------------------------------------------------
# Source guards
# --------------------------------------------------------------------------

_HELPER = "apps/user_content.py"

_MARKDOWN_CALL = re.compile(
    r"\bmarkdown\.(markdown|Markdown|markdownFromFile)\s*\("
    r"|^\s*import bleach\b|\bbleach\.clean\s*\(",
    re.M,
)


def _apps_python():
    return [
        f
        for f in tracked_source_files(_REPO_ROOT, ("apps/*.py",))
        if "/tests/" not in f.path and not f.name.startswith("test_")
    ]


def test_markdown_is_rendered_only_by_the_shared_renderer():
    # Arrange
    sources = _apps_python()
    # Act
    offenders = [
        f.path
        for f in sources
        if f.path != _HELPER and _MARKDOWN_CALL.search(f.text(errors="replace"))
    ]
    # Assert
    assert offenders == []


# `|safe` is allowed only on content the Hub itself authors. Rendered user
# Markdown is already a SafeString and needs no filter.
_SAFE_FILTER_ALLOWLIST = {
    # Static translated link markup.
    ("apps/infra/auth_app/templates/auth_app/signup.html", "blocktrans"),
    # Pricing labels from the Hub's own catalogue.
    ("apps/infra/public_app/templates/public_app/landing_partials/landing_pricing.html", "row.label"),
    # Sphinx HTML built from SciTeX package documentation.
    ("apps/workspace/docs_app/templates/docs_app/docs_sphinx_package.html", "sphinx_toc"),
    ("apps/workspace/docs_app/templates/docs_app/docs_sphinx_package.html", "doc_content"),
    ("apps/workspace/docs_app/templates/docs_app/docs_page.html", "doc_content"),
}  # fmt: skip

_SAFE_USE = re.compile(r"(\{\{|\{%)(?P<body>[^}]*?)\|\s*safe\b")


def test_safe_filter_only_on_hub_authored_content():
    # Arrange
    templates = tracked_source_files(_REPO_ROOT, ("apps/*.html", "templates/*.html"))
    # Act
    offenders = [
        f"{f.path}: {m.group(0).strip()}"
        for f in templates
        for m in _SAFE_USE.finditer(f.text(errors="replace"))
        if not any(
            f.path == path and key in m.group("body")
            for path, key in _SAFE_FILTER_ALLOWLIST
        )
    ]
    # Assert
    assert offenders == []


_INLINE_DISPOSITION = re.compile(r"""["']inline["']\s+if\b|f["']inline;\s*filename""")
# Inline responses here are Hub-generated documents, not user bytes.
_INLINE_ALLOWLIST = {
    # Compiled manuscript PDF produced by the writer pipeline.
    "apps/workspace/writer_app/views/editor/api/files.py",
    _HELPER,
}


def test_user_files_are_served_inline_only_through_the_shared_helper():
    # Arrange
    sources = _apps_python()
    # Act
    offenders = [
        f.path
        for f in sources
        if f.path not in _INLINE_ALLOWLIST
        and _INLINE_DISPOSITION.search(f.text(errors="replace"))
    ]
    # Assert
    assert offenders == []


def test_source_guards_read_the_helper_and_base_template():
    # Arrange: positive control -- an empty offender list proves nothing
    # unless the scans actually saw the files they police.
    # Act
    seen = {f.path for f in _apps_python()} | {
        f.path for f in tracked_source_files(_REPO_ROOT, ("templates/*.html",))
    }
    # Assert
    assert {_HELPER, "templates/global_base.html"} <= seen
