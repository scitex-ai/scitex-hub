import { describe, it, expect } from "vitest";
import { buildHtmlExport, initDocsHtmlExport } from "../../apps/workspace/docs_app/static/docs_app/ts/docs-html-export";
import { PRINT_CSS } from "../../apps/workspace/docs_app/static/docs_app/ts/docs-export-style";

const source = "https://docs.example/apps/docs/?project=private-marker#overview";
const parse = (html: string) => new DOMParser().parseFromString(html, "text/html");

describe("current-page HTML export", () => {
  it("preserves text, code, tables and Unicode in a complete document", () => {
    // Arrange
    const body = '<h1>文書</h1><pre><code>x &lt; 2</code></pre><table><tr><td>42</td></tr></table>';
    // Act
    const doc = parse(buildHtmlExport(body, "Documentation", PRINT_CSS, source));
    // Assert
    expect([doc.title, doc.querySelector('meta[charset]')?.getAttribute('charset'), doc.querySelector('h1')?.textContent, doc.querySelector('code')?.textContent, doc.querySelector('td')?.textContent]).toEqual(["Documentation", "utf-8", "文書", "x < 2", "42"]);
  });
  it("keeps the existing shared print styles", () => {
    // Arrange
    const body = '<h1>Title</h1>';
    // Act
    const doc = parse(buildHtmlExport(body, "Title", PRINT_CSS, source));
    // Assert
    expect(doc.querySelector('style')?.textContent).toBe(PRINT_CSS);
  });
  it("strips project queries, fragments and source credentials from the base", () => {
    // Arrange
    const url = 'https://name:password@docs.example/apps/docs/?token=private-marker#section';
    // Act
    const doc = parse(buildHtmlExport('<p>Docs</p><a href="guide/">Guide</a>', 'Title', PRINT_CSS, url));
    // Assert
    expect([doc.querySelector('base'), doc.querySelector('a')?.href]).toEqual([null, 'https://docs.example/apps/docs/guide/']);
  });
  it("escapes title markup without adding executable elements", () => {
    // Arrange
    const title = '<script>privateMarker()</script>';
    // Act
    const doc = parse(buildHtmlExport('<p>Docs</p>', title, PRINT_CSS, source));
    // Assert
    expect([doc.title, doc.querySelectorAll('script').length]).toEqual([title, 0]);
  });
  it("removes active handlers, forms, scripts and hostile metadata", () => {
    // Arrange
    const body = '<p>Docs</p><img src="x" onerror="alert(1)"><script>alert(1)</script><form><input value="private-marker"></form><base href="https://wrong.example"><meta http-equiv="refresh" content="0"><style>@import url(https://wrong.example)</style><a href="javascript:alert(1)">link</a>';
    // Act
    const doc = parse(buildHtmlExport(body, 'Title', PRINT_CSS, source));
    // Assert
    expect([doc.body.querySelectorAll('script,form,input,meta,base,style,[onerror]').length, doc.body.querySelector('a')?.getAttribute('href')]).toEqual([0, null]);
  });
  it.each(['iframe','object','embed','canvas'])("refuses an embedded %s instead of an incomplete download", (tag) => {
    // Arrange
    const body = `<p>External reference</p><${tag}></${tag}>`;
    // Act
    const build = () => buildHtmlExport(body, 'Title', PRINT_CSS, source);
    // Assert
    expect(build).toThrow('embedded documentation');
  });
  it.each(['javascript:alert(1)','file:///tmp/docs','data:text/html,Docs'])("refuses unsupported source %s", (url) => {
    // Arrange
    const body = '<p>Docs</p>';
    // Act
    const build = () => buildHtmlExport(body, 'Title', PRINT_CSS, url);
    // Assert
    expect(build).toThrow('online');
  });
  it("refuses empty document content", () => {
    // Arrange
    const body = '<div> </div>';
    // Act
    const build = () => buildHtmlExport(body, 'Title', PRINT_CSS, source);
    // Assert
    expect(build).toThrow('loading');
  });
});


it("preserves static SVG and local section anchors", () => {
  // Arrange
  const body = '<svg><path d="M0 0 L10 10" /></svg><a href="#part">Part</a><h2 id="part">Part</h2>';
  // Act
  const doc = parse(buildHtmlExport(body, 'Title', PRINT_CSS, source));
  // Assert
  expect([doc.querySelector('svg path')?.getAttribute('d'), doc.querySelector('a')?.getAttribute('href')]).toEqual(['M0 0 L10 10', '#part']);
});

it("keeps image-only content and resolves its source online", () => {
  // Arrange
  const body = '<img src="figure.png" alt="Figure">';
  // Act
  const doc = parse(buildHtmlExport(body, 'Title', PRINT_CSS, source));
  // Assert
  expect(doc.querySelector('img')?.getAttribute('src')).toBe('https://docs.example/apps/docs/figure.png');
});

it("omits injected export controls and data attributes", () => {
  // Arrange
  const body = '<div class="docs-section-export">Download controls</div><h1 data-private="marker">Docs</h1>';
  // Act
  const doc = parse(buildHtmlExport(body, 'Title', PRINT_CSS, source));
  // Assert
  expect([doc.body.textContent, doc.querySelector('[data-private]')]).toEqual(['Docs', null]);
});

it("refuses content that becomes empty after sanitization", () => {
  // Arrange
  const body = '<script>marker()</script>';
  // Act
  const build = () => buildHtmlExport(body, 'Title', PRINT_CSS, source);
  // Assert
  expect(build).toThrow('loading');
});


it("mounts once and permits a fresh mount after cleanup", () => {
  // Arrange
  const first = initDocsHtmlExport(PRINT_CSS);
  // Act
  const second = initDocsHtmlExport(PRINT_CSS);
  first();
  const next = initDocsHtmlExport(PRINT_CSS);
  next();
  // Assert
  expect([first === second, first === next]).toEqual([true, false]);
});


it("shows a plain unavailable result for an unsupported document context", () => {
  // Arrange
  const doc = document.implementation.createHTMLDocument('Inert context');
  doc.body.innerHTML = '<div class="docs-workspace"><button data-docs-html-export>HTML</button><div id="docs-content-area"><p>Docs</p></div></div>';
  const cleanup = initDocsHtmlExport(PRINT_CSS, doc);
  // Act
  doc.querySelector<HTMLButtonElement>('button')!.click();
  const text = doc.querySelector('[data-docs-html-status]')?.textContent;
  cleanup();
  // Assert
  expect(text).toBe('HTML download unavailable.');
});


describe("rendered code-block controls", () => {
  it("removes copy-control descendants while retaining the code and document SVG", () => {
    // Arrange: actual code-block enhancement wraps a copy SVG in a button.
    const html = '<pre><button class="code-copy-button"><svg class="copy-icon" viewBox="0 0 16 16"><path d="M0 0h16v16H0z"/></svg><span>Copy</span></button><code>x &lt; 2</code></pre><svg id="document-figure" viewBox="0 0 80 40"><path d="M0 0L80 40"/></svg>';
    // Act
    const doc = parse(buildHtmlExport(html, "Code", PRINT_CSS, source));
    // Assert
    expect([doc.querySelector('button,.copy-icon'), doc.querySelector('pre')?.textContent, doc.querySelectorAll('svg').length, doc.querySelector('#document-figure path')?.getAttribute('d')]).toEqual([null, 'x < 2', 1, 'M0 0L80 40']);
  });
});
