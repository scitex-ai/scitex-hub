"""Actual Chromium, Mermaid and Graphviz controls with owned local fixture data.

Run with declared browser test dependencies and installed Chromium. No live app,
model service, project store, authentication or domain endpoint is used.
"""

import subprocess
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def diagram_browser(tmp_path_factory, browser):
    output = tmp_path_factory.mktemp("diagram-browser")
    build = """
import { build } from 'esbuild';
await build({entryPoints:['tests/security/fixtures/diagram-browser.ts'],
 outdir:process.argv[1],bundle:true,splitting:true,format:'esm',
 alias:{'@':process.cwd()+'/static/shared/ts'},entryNames:'fixture',logLevel:'silent'});
"""
    subprocess.run(
        ["node", "--input-type=module", "-e", build, str(output)],
        cwd=ROOT,
        check=True,
        timeout=60,
    )
    (output / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><div id="fixture"></div><script type="module" src="fixture.js"></script>'
    )

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(QuietHandler, directory=str(output))
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # Reuse pytest-playwright's session runtime; own only this fixture context.
    context = None
    try:
        context = browser.new_context()
        page = context.new_page()
        origin = f"http://127.0.0.1:{server.server_port}"
        blocked = []

        def guard(route):
            if route.request.url.startswith(origin + "/"):
                route.continue_()
            else:
                blocked.append(route.request.url)
                route.abort()

        page.route("**/*", guard)
        page.goto(origin, wait_until="domcontentloaded")
        page.wait_for_function("!!window.diagramHarness")
        yield page, blocked
    finally:
        if context is not None:
            context.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_real_clew_node_click_and_safe_status_colors(diagram_browser):
    page, blocked = diagram_browser
    observed = page.evaluate("""async () => {
      const root=document.getElementById('fixture'); root.replaceChildren();
      const events=[];document.addEventListener('fileSelected',e=>events.push(e.detail.path),{once:true});
      const success=await diagramHarness.renderMermaidContent(root,
        'graph TD\\n A["paper.tex"] --> B["analysis.py"]\\n classDef verified fill:#b7e4c7,stroke:#28704b\\n class A verified');
      const node=Array.from(root.querySelectorAll('.node')).find(n=>n.textContent.includes('paper.tex'));
      const shape=node?.querySelector('rect');node?.dispatchEvent(new MouseEvent('click',{bubbles:true}));
      return {success, events, svg:!!root.querySelector('svg'), label:node?.textContent.trim(),
        fill:shape && getComputedStyle(shape).fill, width:shape?.getBoundingClientRect().width,
        active:!!root.querySelector('script,foreignObject,image,use,a,style,[onload],[onclick]')};
    }""")
    assert observed["success"] and observed["svg"]
    assert observed["events"] == ["paper.tex"], observed
    assert observed["fill"] == "rgb(183, 228, 199)" and observed["width"] > 0
    assert not observed["active"] and not blocked


def test_clew_malicious_input_and_invalid_fallback_never_become_html(diagram_browser):
    page, blocked = diagram_browser
    result = page.evaluate("""async () => {
      window.__diagramExecuted=0;
      const root=document.getElementById('fixture');root.replaceChildren();
      await diagramHarness.renderMermaidContent(root,
        'not a diagram <img src="https://owned.invalid/pixel" onerror="window.__diagramExecuted++">');
      return {text:root.textContent, images:root.querySelectorAll('img').length,
        handlers:!!root.querySelector('[onerror],script'), executed:window.__diagramExecuted};
    }""")
    assert "<img" in result["text"]
    assert result["images"] == 0 and not result["handlers"] and result["executed"] == 0
    assert not blocked


def test_interactive_svg_strips_active_resources_and_untrusted_css(diagram_browser):
    page, blocked = diagram_browser
    result = page.evaluate("""() => {
      window.__diagramExecuted=0;
      const root=document.getElementById('fixture');root.replaceChildren();
      const svg=diagramHarness.interactiveSvg(`<svg xmlns="http://www.w3.org/2000/svg" onload="window.__diagramExecuted++">
        <style>@import url(https://owned.invalid/style); #victim{fill:url(https://owned.invalid/paint);stroke:#123456}</style>
        <script>window.__diagramExecuted++</script><image href="https://owned.invalid/image"/>
        <foreignObject><img src="https://owned.invalid/foreign" onerror="window.__diagramExecuted++"/></foreignObject>
        <a href="javascript:window.__diagramExecuted++"><text>link</text></a>
        <rect id="victim" width="50" height="50" fill="url(https://owned.invalid/raw)" style="filter:url(https://owned.invalid/filter);fill:#123456"/>
      </svg>`);root.append(svg);
      return {html:svg.outerHTML,stroke:svg.querySelector('rect').style.stroke,
        fill:svg.querySelector('rect').style.fill,executed:window.__diagramExecuted};
    }""")
    assert result["stroke"] == "rgb(18, 52, 86)" and result["fill"] == "rgb(18, 52, 86)"
    assert not any(
        token in result["html"]
        for token in (
            "owned.invalid",
            "onload",
            "<script",
            "<image",
            "foreignObject",
            "javascript:",
        )
    )
    assert result["executed"] == 0 and not blocked


@pytest.mark.parametrize(
    "kind,code",
    [
        ("mermaid", 'graph TD; A["Safe paper"] --> B["Result"]'),
        ("dot", 'digraph { a [label="Safe paper"]; a -> b; }'),
    ],
)
def test_actual_chat_diagrams_render_as_inert_images(diagram_browser, kind, code):
    page, blocked = diagram_browser
    page.evaluate(
        """({kind,code}) => {
      const root=document.getElementById('fixture');root.replaceChildren();
      const pre=document.createElement('pre'), element=document.createElement('code');
      element.className='language-'+kind;element.textContent=code;pre.append(element);root.append(pre);
      diagramHarness.highlightCodeBlocks(root);
    }""",
        {"kind": kind, "code": code},
    )
    page.wait_for_function(
        "document.querySelector('#fixture img')?.naturalWidth > 0", timeout=20000
    )
    result = page.evaluate("""() => ({src:document.querySelector('#fixture img').src,
      active:!!document.querySelector('#fixture svg,#fixture script,#fixture [onerror]')})""")
    assert result["src"].startswith("blob:") and not result["active"] and not blocked


def test_raw_generated_svg_stays_inert_when_published_as_image(diagram_browser):
    page, blocked = diagram_browser
    page.evaluate("""() => {
      window.__diagramExecuted=0;const root=document.getElementById('fixture');root.replaceChildren();
      diagramHarness.appendSvgImage(root,`<svg xmlns="http://www.w3.org/2000/svg" width="60" height="30" onload="window.__diagramExecuted++">
        <script>window.__diagramExecuted++</script><image href="https://owned.invalid/image"/><text x="1" y="20">Safe</text>
      </svg>`,'owned SVG');
    }""")
    page.wait_for_function("document.querySelector('#fixture img')?.naturalWidth > 0")
    assert page.evaluate("window.__diagramExecuted") == 0
    assert not blocked


@pytest.mark.parametrize("kind", ["mermaid", "dot"])
def test_chat_code_markup_never_gets_reparsed_as_active_html(diagram_browser, kind):
    page, blocked = diagram_browser
    result = page.evaluate(
        """async kind => {
      window.__diagramExecuted=0;const root=document.getElementById('fixture');root.replaceChildren();
      const pre=document.createElement('pre'),code=document.createElement('code');
      code.className='language-'+kind;
      code.textContent='<img src="https://owned.invalid/chat" onerror="window.__diagramExecuted++">';
      pre.append(code);root.append(pre);await diagramHarness.highlightCodeBlocks(root);
      await new Promise(requestAnimationFrame);
      return {executed:window.__diagramExecuted,handlers:!!root.querySelector('[onerror],[onload]'),
        externalImages:Array.from(root.querySelectorAll('img')).filter(image=>!image.src.startsWith('blob:')).length};
    }""",
        kind,
    )
    assert result == {"executed": 0, "handlers": False, "externalImages": 0}
    assert not blocked


def test_clew_error_messages_remain_literal_text(diagram_browser):
    page, blocked = diagram_browser
    result = page.evaluate("""() => {
      const root=document.getElementById('fixture');root.replaceChildren();
      diagramHarness.showError(root,'<img src="https://owned.invalid/error" onerror="window.__diagramExecuted++">');
      return {text:root.textContent, image:!!root.querySelector('img'), handlers:!!root.querySelector('[onerror]')};
    }""")
    assert "<img" in result["text"] and not result["image"] and not result["handlers"]
    assert not blocked
