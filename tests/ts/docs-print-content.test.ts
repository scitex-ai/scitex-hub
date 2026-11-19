import { describe, it, expect } from "vitest";
import { preparePrintContent } from "../../apps/workspace/docs_app/static/docs_app/ts/docs-print";
const parse = (fragment: DocumentFragment) => {
  const doc = document.implementation.createHTMLDocument("Print content");
  doc.body.appendChild(doc.importNode(fragment, true));
  return doc;
};

describe("static print content", () => {
  it("removes enhanced copy controls while retaining a real SVG figure and code", () => {
    // Arrange
    const html = '<pre><button class="code-copy-button"><svg class="copy-icon"><path d="M0 0h16v16z"/></svg>Copy</button><code>x &lt; 2</code></pre><svg id="figure" viewBox="0 0 160 80"><path d="M0 80L160 0" stroke="blue"/></svg>';
    // Act
    const doc = parse(preparePrintContent(html));
    // Assert
    expect([doc.querySelector('button,.copy-icon'), doc.querySelector('pre')?.textContent, doc.querySelector('#figure path')?.getAttribute('d')]).toEqual([null, 'x < 2', 'M0 80L160 0']);
  });
  it("retains Unicode text, table values and local document anchors", () => {
    // Arrange
    const html = '<h2 id="result">結果</h2><table><tr><td>42</td></tr></table><a href="#result">Result</a>';
    // Act
    const doc = parse(preparePrintContent(html));
    // Assert
    expect([doc.querySelector('h2')?.textContent, doc.querySelector('td')?.textContent, doc.querySelector('a')?.getAttribute('href')]).toEqual(['結果', '42', '#result']);
  });
  it("keeps active document content inert", () => {
    // Arrange
    const html = '<script>window.bad=1</script><style>body{display:none}</style><svg onload="bad()"><path d="M0 0L1 1"/></svg><a href="javascript:bad()">Link</a>';
    // Act
    const doc = parse(preparePrintContent(html));
    // Assert
    expect([doc.querySelector('script,style,[onload]'), doc.querySelector('a')?.getAttribute('href'), doc.querySelectorAll('svg path').length]).toEqual([null, null, 1]);
  });
  it("omits unsupported embeds and local form controls", () => {
    // Arrange
    const html = '<iframe src="/embed"></iframe><object data="/x"></object><embed src="/x"><canvas></canvas><form><input value="private"><select><option>private</option></select><textarea>private</textarea><button>private</button></form><p>Document</p>';
    // Act
    const doc = parse(preparePrintContent(html));
    // Assert
    expect([doc.querySelector('iframe,object,embed,canvas,form,input,select,textarea,button'), doc.body.textContent]).toEqual([null, 'Document']);
  });
});
