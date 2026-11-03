"""Native HTTP regressions over the normally built shared form-handler entry.

The admitted mobile job builds Vite and installs Chromium before this file.
Fixtures use only an owned loopback server; no login, database, model or user
workspace is involved. Missing built bytes/browser fail rather than skip.
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest


@pytest.fixture(scope="module")
def native_form_server(browser):
    project = Path(__file__).resolve().parents[3]
    manifest = Path(
        os.environ.get(
            "SCITEX_HUB_TEST_VITE_MANIFEST",
            project / "staticfiles/vite/.vite/manifest.json",
        )
    )
    entries = json.loads(manifest.read_text())
    asset = (
        manifest.parent.parent
        / entries["static/shared/ts/utils/form-enter-handler.ts"]["file"]
    ).resolve()
    asset.relative_to(manifest.parent.parent.resolve())
    script = asset.read_bytes()
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, body, content_type="text/html"):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query)
            if parsed.path == "/handler.js":
                self.reply(script, "text/javascript")
            elif parsed.path == "/received":
                received.append((query["case"][0], "GET", query.get("q", [""])[0]))
                self.reply(b"<p>Owned GET received</p>")
            elif parsed.path == "/":
                method = query["method"][0]
                attribute = "" if method == "implicit" else f' method="{method}"'
                required = "required" if query["required"][0] == "yes" else ""
                cancel = str(query["cancel"][0] == "yes").lower()
                case = query["case"][0]
                self.reply(
                    f"""<!doctype html><form{attribute} action="/received">
<input type="hidden" name="case" value="{case}"><input name="q" {required}>
<button type="submit">Calculate</button></form>
<script>document.querySelector('form').addEventListener('submit',e=>{{if({cancel})e.preventDefault()}})</script>
<script type="module" src="/handler.js" onload="window.handlerLoaded=true"></script>""".encode()
                )
            else:
                self.send_error(404)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length > 4096:
                self.send_error(413)
                return
            query = parse_qs(self.rfile.read(length).decode())
            received.append((query["case"][0], "POST", query.get("q", [""])[0]))
            self.reply(b"<p>Owned POST received</p>")

    # pytest-playwright owns the one browser/runtime for the admitted job.
    # Starting a nested sync runtime here fails after any earlier page fixture.
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield browser, f"http://127.0.0.1:{server.server_port}", received
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize(
    "name,method,enter,cancel,required,expected",
    [
        ("get-click", "get", False, False, False, ["GET"]),
        ("get-enter", "get", True, False, False, ["GET"]),
        ("post-click", "post", False, False, False, ["POST"]),
        ("implicit-JS", "implicit", False, False, False, []),
        ("JS-owner-cancel", "get", False, True, False, []),
        ("invalid-required", "get", False, False, True, []),
    ],
)
def test_native_form_http_contract(
    native_form_server, name, method, enter, cancel, required, expected
):
    # Arrange -- only the exact build artifact and owned loopback endpoint exist.
    browser, base, received = native_form_server
    context = browser.new_context(
        viewport={"width": 390, "height": 844}, service_workers="block"
    )
    context.route(
        "**/*",
        lambda route: (
            route.continue_()
            if route.request.url.startswith(base + "/")
            else route.abort("blockedbyclient")
        ),
    )
    page = context.new_page()
    query = urlencode(
        {
            "case": name,
            "method": method,
            "cancel": "yes" if cancel else "no",
            "required": "yes" if required else "no",
        }
    )
    try:
        page.goto(base + "/?" + query, wait_until="domcontentloaded")
        page.wait_for_function("window.handlerLoaded === true", timeout=8000)
        if not required:
            page.locator("input[name=q]").fill("37")

        # Act -- actual click/Enter and browser validation, no request substitution.
        def submit():
            if enter:
                page.locator("input[name=q]").press("Enter")
            else:
                page.get_by_role("button", name="Calculate", exact=True).click()

        if expected:
            with page.expect_response(
                lambda response: urlsplit(response.url).path == "/received",
                timeout=4000,
            ):
                submit()
        else:
            submit()
            page.wait_for_timeout(180)
        actual = [(method, value) for case, method, value in received if case == name]
        # Assert
        assert actual == [(method, "37") for method in expected]
    finally:
        context.close()
