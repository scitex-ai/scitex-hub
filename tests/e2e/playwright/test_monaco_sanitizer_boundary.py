"""Real Monaco hover/markdown, isolated hooks and compiled-module ownership."""

import json
import subprocess
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def monaco_browser(tmp_path_factory, browser):
    output = tmp_path_factory.mktemp("monaco-browser")
    # Load the SAME resolver plugin used by the production Vite configuration.
    build = """
import {build} from 'vite';import fs from 'node:fs';import {transformSync} from 'esbuild';
const code=transformSync(fs.readFileSync('vite.monaco-sanitizer.ts','utf8'),{loader:'ts',format:'esm'}).code;
const {monacoSanitizerBoundary}=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'));
const modules=[];
await build({configFile:false,base:'/',plugins:[monacoSanitizerBoundary(process.cwd()),
{name:'compiled-module-witness',generateBundle(_,bundle){for(const item of Object.values(bundle))
if(item.type==='chunk')for(const [id,data]of Object.entries(item.modules))
if(data.renderedLength>0)modules.push(id);}}],
build:{outDir:process.argv[1],emptyOutDir:true,rollupOptions:{input:'tests/security/fixtures/monaco-browser.ts',
output:{entryFileNames:'fixture.js',chunkFileNames:'chunks/[name]-[hash].js'}}}});
fs.writeFileSync(process.argv[1]+'/modules.json',JSON.stringify(modules));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", build, str(output / "assets")],
        cwd=ROOT,
        timeout=120,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assets = output / "assets"
    modules = json.loads((assets / "modules.json").read_text())
    styles = "".join(
        f'<link rel="stylesheet" href="{p.relative_to(assets).as_posix()}">'
        for p in assets.rglob("*.css")
    )
    (assets / "index.html").write_text(
        '<!doctype html><meta charset="utf-8">'
        + styles
        + '<div id="fixture"></div><script type="module" src="fixture.js"></script>'
    )

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(QuietHandler, directory=str(assets))
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
        page.wait_for_function("!!window.monacoHarness")
        yield page, blocked, modules
    finally:
        if context is not None:
            context.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_actual_compiled_modules_exclude_vendor_and_include_patched_adapter(
    monaco_browser,
):
    page, blocked, modules = monaco_browser
    assert not any(
        "monaco-editor/esm/vs/base/browser/dompurify/dompurify.js" in name
        for name in modules
    )
    assert any(
        name.endswith("/static/shared/ts/utils/monaco-sanitizer.ts") for name in modules
    )
    assert any("/dompurify/dist/purify.es.mjs" in name for name in modules)
    assert page.evaluate("monacoHarness.sanitizer.version") == "3.4.17"
    assert not blocked


def test_actual_editor_markdown_hover_keeps_normal_content(monaco_browser):
    page, blocked, _ = monaco_browser
    page.evaluate("""() => {
      const {monaco}=monacoHarness;const root=document.getElementById('fixture');root.replaceChildren();
      monaco.languages.registerHoverProvider('plaintext',{provideHover:()=>({
        range:new monaco.Range(1,1,1,6),contents:[{value:'**Scientific paper** with `code`',isTrusted:false}]
      })});
      window.ownedEditor=monaco.editor.create(root,{value:'paper',language:'plaintext',
        dimension:{width:700,height:200},hover:{enabled:true,delay:0}});
      ownedEditor.setPosition({lineNumber:1,column:2});
      ownedEditor.trigger('owned-fixture','editor.action.showHover',{});
    }""")
    page.wait_for_function(
        "document.querySelector('.monaco-hover strong')?.textContent==='Scientific paper'"
    )
    assert page.locator(".monaco-hover code").inner_text() == "code"
    page.evaluate("ownedEditor.dispose()")
    assert not blocked


def test_real_monaco_markdown_refuses_script_svg_and_javascript_links(monaco_browser):
    page, blocked, _ = monaco_browser
    result = page.evaluate("""() => {
      window.__monacoExecuted=0;const root=document.getElementById('fixture');root.replaceChildren();
      const result=monacoHarness.renderMarkdown({supportHtml:true,isTrusted:false,
        value:'**Safe** <script>window.__monacoExecuted++</script><svg onload="window.__monacoExecuted++"><image href="https://owned.invalid/svg"/></svg><a href="javascript:window.__monacoExecuted++">click</a>'});
      root.append(result.element);
      return {strong:root.querySelector('strong')?.textContent,executed:window.__monacoExecuted,
        active:!!root.querySelector('svg,script,[onload],[href^="javascript:"]')};
    }""")
    assert result == {"strong": "Safe", "executed": 0, "active": False}
    assert not blocked


def test_monaco_hook_instance_does_not_pollute_shared_sanitizer(monaco_browser):
    page, blocked, _ = monaco_browser
    result = page.evaluate("""() => {
      const own=monacoHarness.sanitizer;own.addHook('afterSanitizeAttributes',node=>node.removeAttribute('title'));
      const value={own:own.sanitize('<b title="owned">safe</b>'),shared:monacoHarness.shared.sanitize('<b title="owned">safe</b>')};
      own.removeAllHooks();return value;
    }""")
    assert result == {"own": "<b>safe</b>", "shared": '<b title="owned">safe</b>'}
    assert not blocked
