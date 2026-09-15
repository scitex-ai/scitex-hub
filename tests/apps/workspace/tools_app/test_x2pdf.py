"""X2PDF: dispatcher, filename derivation and the SSRF guard (no network, no browser)."""

import datetime as dt
import shutil

import pytest

from apps.workspace.tools_app.x2pdf import convert
from apps.workspace.tools_app.x2pdf.naming import derive_pdf_filename, slugify_filename
from apps.workspace.tools_app.x2pdf.ssrf import (
    FetchError,
    UnsafeURLError,
    is_public_ip,
    safe_fetch,
    validate_url,
)

PUBLIC = "93.184.215.14"
TODAY = dt.date(2026, 9, 15)


def _resolver(table):
    return lambda host, port: table[host]


def _literal_resolver(host, port):
    return [host]


class _Opener:
    """Hand-rolled HTTP stand-in: replays scripted responses and records each hop."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, target, ip, headers, timeout):
        self.calls.append({"host": target.host, "ip": ip, "Host": headers["Host"], "path": target.path})
        status, resp_headers, chunks = self.responses[min(len(self.calls), len(self.responses)) - 1]
        return status, resp_headers, iter(chunks), None


# ---------------------------------------------------------------- dispatcher
@pytest.mark.parametrize(
    "name, head, kind",
    [
        ("paper.pdf", b"%PDF-1.7\n", "pdf"),
        ("misnamed.txt", b"%PDF-1.4\n", "pdf"),
        ("fig.png", b"\x89PNG\r\n\x1a\n", "image"),
        ("noext", b"\xff\xd8\xff\xe0", "image"),
        ("draw.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>", "svg"),
        ("page.html", b"<p>x</p>", "html"),
        ("saved", b"<!DOCTYPE html><html>", "html"),
        ("draft.docx", b"PK\x03\x04", "pandoc"),
        ("notes.md", b"# Title", "pandoc"),
        ("slides.pptx", b"PK\x03\x04", "office"),
        ("script.py", b"print('hi')", "text"),
        ("README", "日本語のテキスト".encode("utf-8"), "text"),
        ("blob.bin", b"\x00\x01\x02\x03binary", "unknown"),
    ],
)
def test_detect_kind_routes_input_to_expected_converter(name, head, kind):
    # Arrange
    sample = (name, head)
    # Act
    detected = convert.detect_kind(*sample)
    # Assert
    assert detected == kind


def test_dispatcher_has_a_converter_for_every_detected_kind():
    # Arrange
    kinds = {"pdf", "image", "svg", "html", "text", "pandoc", "office", "unknown"}
    # Act
    missing = kinds - set(convert.CONVERTERS)
    # Assert
    assert missing == set()


@pytest.mark.skipif(bool(shutil.which("soffice") or shutil.which("libreoffice")), reason="LibreOffice present")
def test_office_file_without_libreoffice_raises_explaining_error(tmp_path):
    # Arrange
    src = tmp_path / "input.pptx"
    src.write_bytes(b"PK\x03\x04")
    # Act
    call = lambda: convert.convert_file(src, tmp_path, "slides.pptx")  # noqa: E731
    # Assert
    with pytest.raises(convert.ConversionError, match="LibreOffice"):
        call()


def test_png_with_alpha_converts_to_a_one_page_pdf(tmp_path):
    # Arrange
    from PIL import Image

    src = tmp_path / "input.png"
    Image.new("RGBA", (400, 300), (255, 0, 0, 128)).save(src)
    # Act
    result = convert.convert_file(src, tmp_path, "fig.png")
    # Assert
    assert (result.kind, result.pages, result.pdf_path.read_bytes()[:4]) == ("image", 1, b"%PDF")


def test_input_over_size_limit_is_refused(tmp_path):
    # Arrange
    src = tmp_path / "input.txt"
    src.write_bytes(b"x" * 11)
    # Act
    call = lambda: convert.convert_file(src, tmp_path, "a.txt", max_bytes=10)  # noqa: E731
    # Assert
    with pytest.raises(convert.ConversionError, match="larger"):
        call()


# ---------------------------------------------------------------- titles
@pytest.mark.parametrize(
    "markup, use_title_tag, expected",
    [
        (b"<title> Example  Domain </title>", True, "Example Domain"),
        ("<h1>見出し</h1>", True, "見出し"),
        ("<title>file.md</title><h1>Real</h1>", False, "Real"),
    ],
)
def test_html_title_prefers_title_tag_then_first_heading(markup, use_title_tag, expected):
    # Arrange
    kwargs = {"use_title_tag": use_title_tag}
    # Act
    title = convert.html_title(markup, **kwargs)
    # Assert
    assert title == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("---\ntitle: 'My Paper'\n---\n# Other", "My Paper"),
        ("intro\n\n# Results #\n", "Results"),
    ],
)
def test_markdown_title_reads_front_matter_then_heading(text, expected):
    # Arrange
    source = text
    # Act
    title = convert.markdown_title(source)
    # Assert
    assert title == expected


def test_docx_title_reads_core_properties(tmp_path):
    # Arrange
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.core_properties.title = "研究計画書"
    document.save(tmp_path / "a.docx")
    # Act
    title = convert.docx_title(tmp_path / "a.docx")
    # Assert
    assert title == "研究計画書"


# ---------------------------------------------------------------- filenames
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("論文 草稿: v2/final?", "論文_草稿_v2_final"),
        ("../../etc/passwd", "etc_passwd"),
        ("\x00\n", ""),
    ],
)
def test_slugify_filename_keeps_japanese_and_strips_unsafe(raw, expected):
    # Arrange
    text = raw
    # Act
    slug = slugify_filename(text)
    # Assert
    assert slug == expected


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"title": "Annual Report", "original_name": "x.docx"}, "Annual_Report.pdf"),
        ({"title": "  ", "original_name": "C:\\Users\\me\\報告書.docx"}, "報告書.pdf"),
        ({"title": "Example Domain", "url": "https://example.com"}, "Example_Domain_2026-09-15.pdf"),
        ({"url": "https://www.example.com/docs/guide.html"}, "example.com_guide_2026-09-15.pdf"),
        ({}, "converted_2026-09-15.pdf"),
    ],
)
def test_derive_pdf_filename_uses_title_then_name_then_url(kwargs, expected):
    # Arrange
    sources = dict(kwargs, today=TODAY)
    # Act
    filename = derive_pdf_filename(**sources)
    # Assert
    assert filename == expected


def test_derive_pdf_filename_bounds_long_titles():
    # Arrange
    title = "a" * 500
    # Act
    filename = derive_pdf_filename(title=title)
    # Assert
    assert len(filename) <= 84


# ---------------------------------------------------------------- SSRF guard
@pytest.mark.parametrize(
    "ip",
    ["127.0.0.1", "10.1.2.3", "172.16.0.1", "192.168.1.1", "169.254.169.254", "100.64.0.1",
     "0.0.0.0", "::1", "fe80::1", "fc00::1", "::ffff:127.0.0.1", "224.0.0.1", "not-an-ip"],
)
def test_is_public_ip_rejects_inward_addresses(ip):
    # Arrange
    candidate = ip
    # Act
    public = is_public_ip(candidate)
    # Assert
    assert public is False


@pytest.mark.parametrize("ip", [PUBLIC, "2606:2800:21f:cb07:6820:80da:af6b:8b2c"])
def test_is_public_ip_accepts_global_addresses(ip):
    # Arrange
    candidate = ip
    # Act
    public = is_public_ip(candidate)
    # Assert
    assert public is True


@pytest.mark.parametrize(
    "url",
    ["file:///etc/passwd", "ftp://example.com/", "gopher://x/", "javascript:alert(1)", "http://",
     "http://127.0.0.1:8000/admin", "http://[::1]/", "http://2130706433/"],
)
def test_validate_url_rejects_bad_scheme_or_inward_literal(url):
    # Arrange
    resolver = _literal_resolver
    # Act
    call = lambda: validate_url(url, resolver=resolver)  # noqa: E731
    # Assert
    with pytest.raises(UnsafeURLError):
        call()


@pytest.mark.parametrize("answers", [["169.254.169.254"], [PUBLIC, "10.0.0.5"]])
def test_validate_url_blocks_host_with_any_private_dns_answer(answers):
    # Arrange
    resolver = _resolver({"sneaky.test": answers})
    # Act
    call = lambda: validate_url("https://sneaky.test/", resolver=resolver)  # noqa: E731
    # Assert
    with pytest.raises(UnsafeURLError):
        call()


def test_safe_fetch_blocks_redirect_to_private_host():
    # Arrange
    resolver = _resolver({"public.test": [PUBLIC], "internal.test": ["192.168.0.10"]})
    opener = _Opener((302, {"location": "http://internal.test/secret"}, []))
    # Act
    call = lambda: safe_fetch("https://public.test/start", resolver=resolver, opener=opener)  # noqa: E731
    # Assert
    with pytest.raises(UnsafeURLError):
        call()


def test_safe_fetch_never_connects_to_redirected_private_host():
    # Arrange
    resolver = _resolver({"public.test": [PUBLIC], "internal.test": ["192.168.0.10"]})
    opener = _Opener((302, {"location": "http://internal.test/secret"}, []))
    # Act
    try:
        safe_fetch("https://public.test/start", resolver=resolver, opener=opener)
    except UnsafeURLError:
        pass
    # Assert
    assert [c["ip"] for c in opener.calls] == [PUBLIC]


def test_safe_fetch_pins_connection_to_checked_address():
    # Arrange
    resolver = _resolver({"public.test": [PUBLIC]})
    opener = _Opener((200, {"content-type": "text/html; charset=utf-8"}, [b"<title>ok</title>"]))
    # Act
    safe_fetch("http://public.test:8080/a?b=1", resolver=resolver, opener=opener)
    # Assert
    assert opener.calls == [{"host": "public.test", "ip": PUBLIC, "Host": "public.test:8080", "path": "/a?b=1"}]


def test_safe_fetch_returns_body_and_content_type():
    # Arrange
    resolver = _resolver({"public.test": [PUBLIC]})
    opener = _Opener((200, {"content-type": "text/html; charset=utf-8"}, [b"<title>ok</title>"]))
    # Act
    result = safe_fetch("http://public.test/", resolver=resolver, opener=opener)
    # Assert
    assert (result.content_type, result.body) == ("text/html", b"<title>ok</title>")


def test_safe_fetch_caps_body_size():
    # Arrange
    resolver = _resolver({"public.test": [PUBLIC]})
    opener = _Opener((200, {}, [b"x" * 600, b"x" * 600]))
    # Act
    call = lambda: safe_fetch("http://public.test/", max_bytes=1000, resolver=resolver, opener=opener)  # noqa: E731
    # Assert
    with pytest.raises(FetchError, match="larger"):
        call()


def test_safe_fetch_stops_redirect_loops():
    # Arrange
    resolver = _resolver({"public.test": [PUBLIC]})
    opener = _Opener((301, {"location": "/again"}, []))
    # Act
    call = lambda: safe_fetch("http://public.test/", max_redirects=3, resolver=resolver, opener=opener)  # noqa: E731
    # Assert
    with pytest.raises(FetchError, match="redirects"):
        call()
