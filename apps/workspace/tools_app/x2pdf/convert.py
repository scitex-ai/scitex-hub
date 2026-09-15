"""Best-effort "anything to PDF": detect the input kind and dispatch to a converter.

Converters available in the hub image (measured 2026-09-15, dev django +
celery_worker): pandoc 3.1, Playwright Chromium, Pillow, pypdf, python-docx.
LibreOffice is NOT installed, so legacy Office / pptx / xlsx only convert where
``soffice`` exists; elsewhere they fail with a message saying so.
"""

from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from .ssrf import FetchError, UnsafeURLError, safe_fetch

MAX_INPUT_BYTES = 50 * 1024 * 1024
MAX_PAGES = 300
MAX_TEXT_CHARS = 2_000_000
SUBPROCESS_TIMEOUT_S = 90
RENDER_TIMEOUT_MS = 45_000
MAX_SUBRESOURCES = 150
MAX_IMAGE_PIXELS = 120_000_000

LOCAL_ORIGIN = "http://x2pdf.invalid"
FONT_STACK = (
    "'Noto Sans', 'Noto Sans JP', 'Noto Sans CJK JP', 'IPAexGothic', "
    "'Hiragino Sans', 'Yu Gothic', Arial, sans-serif"
)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".ico", ".ppm", ".pgm"}
HTML_EXTS = {".html", ".htm", ".xhtml", ".mhtml"}
PANDOC_FORMATS = {
    ".md": "markdown", ".markdown": "markdown", ".mdown": "markdown",
    ".docx": "docx", ".odt": "odt", ".epub": "epub", ".rtf": "rtf",
    ".rst": "rst", ".tex": "latex", ".latex": "latex", ".org": "org",
    ".ipynb": "ipynb", ".textile": "textile", ".wiki": "mediawiki",
    ".typ": "typst", ".adoc": "asciidoc",
}
OFFICE_EXTS = {".doc", ".xls", ".xlsx", ".ppt", ".pptx", ".odp", ".ods", ".pages", ".key", ".numbers", ".vsd", ".pub"}
TEXT_EXTS = {
    ".txt", ".text", ".log", ".csv", ".tsv", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".xml", ".py", ".js", ".ts", ".tsx", ".jsx", ".css", ".scss", ".sh", ".bash", ".zsh", ".r",
    ".m", ".c", ".h", ".cpp", ".hpp", ".cc", ".java", ".kt", ".go", ".rs", ".rb", ".php", ".pl",
    ".swift", ".sql", ".bib", ".sty", ".cls", ".el", ".lua", ".jl", ".scala", ".dart", ".vue",
    ".svelte", ".env", ".conf", ".properties", ".diff", ".patch", ".srt", ".vtt",
}


class ConversionError(Exception):
    """A failure whose message is safe and useful to show the user."""


@dataclass
class Result:
    pdf_path: Path
    kind: str
    title: str | None = None
    pages: int = 0
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- detection
def detect_kind(filename: str, head: bytes) -> str:
    ext = PurePosixPath((filename or "").lower()).suffix
    if head.startswith(b"%PDF-") or (ext == ".pdf" and b"%PDF-" in head[:1024]):
        return "pdf"
    if (
        head.startswith(b"\x89PNG") or head.startswith(b"\xff\xd8\xff") or head[:6] in (b"GIF87a", b"GIF89a")
        or head.startswith(b"BM") and ext == ".bmp" or head[:4] in (b"II*\x00", b"MM\x00*")
        or (head[:4] == b"RIFF" and head[8:12] == b"WEBP")
    ):
        return "image"
    if ext in IMAGE_EXTS:
        return "image"
    if ext == ".svg":
        return "svg"
    if ext in HTML_EXTS:
        return "html"
    if ext in PANDOC_FORMATS:
        return "pandoc"
    if ext in OFFICE_EXTS:
        return "office"
    if ext == ".pdf":
        return "pdf"
    sniff = head[:2048].lstrip().lower()
    if sniff.startswith(b"<!doctype html") or sniff.startswith(b"<html"):
        return "html"
    if sniff.startswith(b"<svg") or (sniff.startswith(b"<?xml") and b"<svg" in sniff):
        return "svg"
    if ext in TEXT_EXTS or _looks_like_text(head):
        return "text"
    return "unknown"


def _looks_like_text(head: bytes) -> bool:
    if not head or b"\x00" in head[:4096]:
        return False
    return _decode_text(head[:4096], strict=True) is not None


def _decode_text(data: bytes, strict: bool = False) -> str | None:
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", "replace")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        # A sniffed prefix can cut a multi-byte character in half.
        if strict and exc.start >= len(data) - 3:
            return data[: exc.start].decode("utf-8-sig", "replace")
    for enc in ("cp932", "euc-jp"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return None if strict else data.decode("latin-1")


# ---------------------------------------------------------------- titles
def html_title(markup: bytes | str, use_title_tag: bool = True) -> str | None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(markup, "html.parser")
    for node in (soup.title if use_title_tag else None, soup.find("h1")):
        if node is not None:
            text = " ".join(node.get_text(" ").split())
            if text:
                return text[:200]
    return None


def docx_title(path: Path) -> str | None:
    try:
        import docx

        document = docx.Document(str(path))
    except Exception:
        return None
    title = (document.core_properties.title or "").strip()
    if title:
        return title
    for para in document.paragraphs[:60]:
        style = (para.style.name if para.style is not None else "") or ""
        if para.text.strip() and (style.startswith("Title") or style.startswith("Heading")):
            return para.text.strip()[:200]
    return None


def markdown_title(text: str) -> str | None:
    front = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if front:
        m = re.search(r"^title:\s*['\"]?(.+?)['\"]?\s*$", front.group(1), re.M)
        if m:
            return m.group(1)
    m = re.search(r"^#\s+(.+?)\s*#*\s*$", text, re.M)
    return m.group(1) if m else None


def pdf_title(path: Path) -> str | None:
    try:
        from pypdf import PdfReader

        meta = PdfReader(str(path)).metadata
        title = (meta.title if meta else None) or ""
    except Exception:
        return None
    title = title.strip()
    # Producers stamp junk like "Microsoft Word - draft3.docx"; still better than nothing.
    return title.removeprefix("Microsoft Word - ") or None


# ---------------------------------------------------------------- rendering
def _launch_chromium(p):
    args = [
        # Chromium never touches the network itself: every request is either
        # served by the route handler or refused, so even requests the handler
        # cannot see (WebSocket, WebRTC) have nowhere to go.
        "--proxy-server=http://127.0.0.1:9",
        "--host-resolver-rules=MAP * ~NOTFOUND",
        "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
        "--disable-dev-shm-usage",
    ]
    try:
        return p.chromium.launch(headless=True, args=args)
    except Exception:
        system = shutil.which("chromium") or shutil.which("chromium-browser")
        if not system:
            raise ConversionError("The PDF renderer (Chromium) is not available on this server.")
        return p.chromium.launch(headless=True, args=args, executable_path=system)


def render_html(
    markup: bytes | str,
    out_pdf: Path,
    *,
    doc_url: str = f"{LOCAL_ORIGIN}/document.html",
    local_root: Path | None = None,
    allow_network: bool = False,
    fetcher=safe_fetch,
) -> None:
    """Print HTML to PDF in headless Chromium with all traffic mediated here."""
    from playwright.sync_api import sync_playwright

    body = markup.encode("utf-8") if isinstance(markup, str) else markup
    budget = {"count": 0}

    def serve_local(route, url: str) -> None:
        if local_root is None:
            return route.abort()
        rel = unquote(urlsplit(url).path).lstrip("/")
        candidate = (local_root / rel).resolve()
        if not candidate.is_file() or not candidate.is_relative_to(local_root.resolve()):
            return route.abort()
        route.fulfill(status=200, body=candidate.read_bytes())

    def handle(route):
        url = route.request.url
        # The first navigation is ours (Chromium may normalise doc_url, so no string match).
        if route.request.resource_type == "document" and not budget.get("doc"):
            budget["doc"] = True
            return route.fulfill(status=200, content_type="text/html; charset=utf-8", body=body)
        budget["count"] += 1
        if budget["count"] > MAX_SUBRESOURCES:
            return route.abort()
        if url.startswith(LOCAL_ORIGIN + "/"):
            return serve_local(route, url)
        if not allow_network or urlsplit(url).scheme not in ("http", "https"):
            return route.abort()
        try:
            fetched = fetcher(url, max_bytes=10 * 1024 * 1024, timeout=15)
        except (UnsafeURLError, FetchError):
            return route.abort()
        except Exception:
            return route.abort()
        ctype = fetched.headers.get("content-type") or "application/octet-stream"
        route.fulfill(status=fetched.status, headers={"content-type": ctype}, body=fetched.body)

    with sync_playwright() as p:
        browser = _launch_chromium(p)
        try:
            context = browser.new_context(service_workers="block", accept_downloads=False)
            context.set_default_timeout(RENDER_TIMEOUT_MS)
            context.route("**/*", handle)
            page = context.new_page()
            try:
                page.goto(doc_url, wait_until="load", timeout=RENDER_TIMEOUT_MS)
            except Exception as exc:
                raise ConversionError("The page did not finish loading in time.") from exc
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            page.pdf(
                path=str(out_pdf), format="A4", print_background=True,
                margin={"top": "12mm", "bottom": "12mm", "left": "12mm", "right": "12mm"},
            )
        finally:
            browser.close()


# ---------------------------------------------------------------- converters
def _wrap_html(inner: str, title: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title><style>"
        f"body{{font-family:{FONT_STACK};margin:0;color:#111}}"
        "pre{white-space:pre-wrap;word-break:break-word;font:10pt/1.45 'DejaVu Sans Mono',"
        "'Noto Sans Mono','Noto Sans JP',monospace;margin:0}"
        "img{max-width:100%;max-height:260mm;display:block;margin:auto}"
        "</style></head><body>" + inner + "</body></html>"
    )


PANDOC_CSS = (
    f"<style>html,body{{font-family:{FONT_STACK};max-width:none!important;padding:0!important;"
    "font-size:11pt}img,svg{max-width:100%;height:auto}pre{white-space:pre-wrap}"
    "table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:2px 6px}</style>"
)


def _run(cmd: list[str], cwd: Path, what: str) -> subprocess.CompletedProcess:
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(cwd), "LANG": "C.UTF-8"}
    try:
        proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, timeout=SUBPROCESS_TIMEOUT_S)
    except subprocess.TimeoutExpired as exc:
        raise ConversionError(f"{what} took longer than {SUBPROCESS_TIMEOUT_S}s and was stopped.") from exc
    if proc.returncode != 0:
        tail = (proc.stderr or b"").decode("utf-8", "replace").strip().splitlines()
        raise ConversionError(f"{what} failed" + (f": {tail[-1][:200]}" if tail else "."))
    return proc


def convert_pdf(src: Path, work: Path, name: str) -> Result:
    from pypdf import PdfReader

    try:
        PdfReader(str(src))
    except Exception as exc:
        raise ConversionError("That file looks like a PDF but could not be read.") from exc
    out = work / "output.pdf"
    shutil.copyfile(src, out)
    return Result(out, "pdf", title=pdf_title(src), notes=["Already a PDF; passed through unchanged."])


def convert_image(src: Path, work: Path, name: str) -> Result:
    from PIL import Image, ImageSequence

    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    try:
        img = Image.open(src)
        frames = []
        for frame in ImageSequence.Iterator(img):
            if len(frames) >= MAX_PAGES:
                break
            frame = frame.copy()
            if frame.mode in ("RGBA", "LA", "P"):
                frame = frame.convert("RGBA")
                canvas = Image.new("RGB", frame.size, "white")
                canvas.paste(frame, mask=frame.getchannel("A"))
                frame = canvas
            elif frame.mode != "RGB":
                frame = frame.convert("RGB")
            frames.append(frame)
    except Image.DecompressionBombError as exc:
        raise ConversionError("That image is too large to convert.") from exc
    except Exception as exc:
        raise ConversionError("That image could not be read.") from exc
    if not frames:
        raise ConversionError("That image has no frames.")
    w, h = frames[0].size
    # Fit the long side to roughly an A4 page instead of 1px = 1pt.
    resolution = max(72.0, max(w, h) / 11.0)
    out = work / "output.pdf"
    frames[0].save(out, "PDF", save_all=True, append_images=frames[1:], resolution=resolution)
    return Result(out, "image")


def convert_svg(src: Path, work: Path, name: str) -> Result:
    import base64

    data = base64.b64encode(src.read_bytes()).decode("ascii")
    out = work / "output.pdf"
    render_html(_wrap_html(f"<img src='data:image/svg+xml;base64,{data}'>", name), out)
    return Result(out, "svg")


def convert_html(src: Path, work: Path, name: str) -> Result:
    markup = src.read_bytes()
    out = work / "output.pdf"
    render_html(markup, out, allow_network=True)
    return Result(out, "html", title=html_title(markup))


def convert_text(src: Path, work: Path, name: str) -> Result:
    text = _decode_text(src.read_bytes()) or ""
    notes = []
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS]
        notes.append("The text was truncated to fit the size limit.")
    out = work / "output.pdf"
    render_html(_wrap_html(f"<pre>{html.escape(text)}</pre>", name), out)
    return Result(out, "text", notes=notes)


def convert_pandoc(src: Path, work: Path, name: str) -> Result:
    if not shutil.which("pandoc"):
        raise ConversionError("Document conversion (pandoc) is not available on this server.")
    fmt = PANDOC_FORMATS[src.suffix.lower()]
    header = work / "x2pdf-header.html"
    header.write_text(PANDOC_CSS, encoding="utf-8")
    site = work / "site"
    site.mkdir()
    # --sandbox stops reader-side file access (e.g. LaTeX \input{/etc/passwd}).
    # --embed-resources is deliberately NOT used: it fetches remote URLs itself,
    # bypassing the SSRF guard. Remote images are left to the guarded renderer.
    _run(
        ["pandoc", "--sandbox", "-f", fmt, "-t", "html5", "-s", "--extract-media=media",
         "-H", str(header), "--metadata", f"pagetitle={name}", "-o", str(site / "index.html"), str(src)],
        cwd=site, what="Document conversion",
    )
    markup = (site / "index.html").read_bytes()
    out = work / "output.pdf"
    render_html(markup, out, doc_url=f"{LOCAL_ORIGIN}/index.html", local_root=site, allow_network=True)
    title = None
    if fmt == "docx":
        title = docx_title(src)
    elif fmt == "markdown":
        title = markdown_title(_decode_text(src.read_bytes()[:200_000]) or "")
    # <title> is the pagetitle we injected (the filename), so only trust a heading.
    return Result(out, fmt, title=title or html_title(markup, use_title_tag=False))


def convert_office(src: Path, work: Path, name: str) -> Result:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise ConversionError(
            f"{src.suffix or 'This'} files need LibreOffice, which is not installed on this server yet."
        )
    _run([soffice, "--headless", "--norestore", "--nolockcheck", "--convert-to", "pdf",
          "--outdir", str(work / "office"), str(src)], cwd=work, what="Office conversion")
    produced = next((work / "office").glob("*.pdf"), None)
    if produced is None:
        raise ConversionError("Office conversion produced no PDF.")
    out = work / "output.pdf"
    shutil.move(str(produced), out)
    return Result(out, "office")


def convert_unknown(src: Path, work: Path, name: str) -> Result:
    if shutil.which("soffice") or shutil.which("libreoffice"):
        try:
            result = convert_office(src, work, name)
            result.kind = "unknown"
            return result
        except ConversionError:
            pass
    raise ConversionError("This file type is not supported yet.")


CONVERTERS = {
    "pdf": convert_pdf,
    "image": convert_image,
    "svg": convert_svg,
    "html": convert_html,
    "text": convert_text,
    "pandoc": convert_pandoc,
    "office": convert_office,
    "unknown": convert_unknown,
}


def _finalize(result: Result) -> Result:
    from pypdf import PdfReader, PdfWriter

    try:
        reader = PdfReader(str(result.pdf_path))
        pages = len(reader.pages)
    except Exception as exc:
        raise ConversionError("The converter produced an unreadable PDF.") from exc
    if pages > MAX_PAGES:
        writer = PdfWriter()
        for page in reader.pages[:MAX_PAGES]:
            writer.add_page(page)
        tmp = result.pdf_path.with_suffix(".cap.pdf")
        with open(tmp, "wb") as fh:
            writer.write(fh)
        os.replace(tmp, result.pdf_path)
        result.notes.append(f"Only the first {MAX_PAGES} of {pages} pages were kept.")
        pages = MAX_PAGES
    result.pages = pages
    return result


def convert_file(src: Path, work: Path, original_name: str, max_bytes: int = MAX_INPUT_BYTES) -> Result:
    if src.stat().st_size > max_bytes:
        raise ConversionError(f"The file is larger than {max(1, max_bytes // (1024 * 1024))} MB.")
    with open(src, "rb") as fh:
        head = fh.read(8192)
    kind = detect_kind(original_name, head)
    return _finalize(CONVERTERS[kind](src, work, original_name))


_CTYPE_EXT = {
    "application/pdf": ".pdf", "image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
    "image/webp": ".webp", "image/svg+xml": ".svg", "image/bmp": ".bmp", "image/tiff": ".tiff",
    "text/plain": ".txt", "text/markdown": ".md", "application/json": ".json", "text/csv": ".csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


def convert_url(url: str, work: Path) -> Result:
    try:
        fetched = safe_fetch(url, max_bytes=MAX_INPUT_BYTES, timeout=30,
                             accept="text/html,application/xhtml+xml,*/*;q=0.8")
    except (UnsafeURLError, FetchError) as exc:
        raise ConversionError(str(exc)) from exc
    if fetched.status >= 400:
        raise ConversionError(f"The site answered HTTP {fetched.status}.")
    ctype = fetched.content_type
    if ctype in ("text/html", "application/xhtml+xml") or (not ctype and b"<html" in fetched.body[:2048].lower()):
        out = work / "output.pdf"
        render_html(fetched.body, out, doc_url=fetched.url.split("#")[0], allow_network=True)
        return _finalize(Result(out, "url", title=html_title(fetched.body)))
    # A direct link to a file: treat it like an upload of that file.
    leaf = PurePosixPath(unquote(urlsplit(fetched.url).path)).name or "download"
    ext = _CTYPE_EXT.get(ctype)
    if ext and not leaf.lower().endswith(ext):
        leaf += ext
    src = work / ("input" + (PurePosixPath(leaf).suffix[:12] or ".bin"))
    src.write_bytes(fetched.body)
    return convert_file(src, work, leaf)
