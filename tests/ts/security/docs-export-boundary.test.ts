import { afterEach, expect, it, vi } from "vitest";

afterEach(() => {
  document.body.replaceChildren();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.resetModules();
});

async function workspace(slug = "overview", content = "<p>Documentation</p>") {
  document.body.innerHTML = `<main class="docs-workspace">
    <aside class="docs-sidebar"><a class="docs-nav-item"><span>Overview</span></a></aside>
    <button id="docs-export-all-pdf">Print all</button>
    <div id="docs-content-area"></div></main>`;
  document.querySelector<HTMLElement>(".docs-workspace")!.dataset.activeDoc = slug;
  document.querySelector<HTMLElement>(".docs-nav-item")!.dataset.docSlug = slug;
  const fetch = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => new Response(content));
  vi.stubGlobal("fetch", fetch);
  const printDocument = document.implementation.createHTMLDocument();
  const print = vi.fn();
  vi.spyOn(window, "open").mockReturnValue({ document: printDocument, print } as unknown as Window);
  await import("../../../apps/workspace/docs_app/static/docs_app/ts/docs-workspace");
  document.dispatchEvent(new Event("DOMContentLoaded"));
  await vi.waitFor(() => expect(document.querySelector(".docs-section-pdf-btn")).not.toBeNull());
  return { fetch, print, printDocument };
}

it("removes active content from the real single-page print action while preserving documentation", async () => {
  // Arrange: the live document may contain markup added after its initial load.
  const { print, printDocument } = await workspace();
  document.getElementById("docs-content-area")!.insertAdjacentHTML("beforeend",
    '<img src="owned.png" onerror="window.compromised=1"><iframe srcdoc="bad"></iframe>' +
    '<a href="javascript:alert(1)">unsafe link</a><table><tr><td>Result</td></tr></table><pre><code>scitex --help</code></pre>');
  // Act
  document.querySelector<HTMLButtonElement>(".docs-section-pdf-btn")!.click();
  // Assert
  expect(print).toHaveBeenCalledOnce();
  expect(printDocument.querySelector("[onerror], iframe, a[href^='javascript:']")).toBeNull();
  expect(printDocument.querySelector("td")?.textContent).toBe("Result");
  expect(printDocument.querySelector("code")?.textContent).toBe("scitex --help");
});

it("sanitizes fetched pages and generated headings in the real batch print action", async () => {
  // Arrange
  const { fetch, print, printDocument } = await workspace();
  fetch.mockImplementation(async () => new Response('<script>bad()</script><p onclick="bad()">Safe content</p>'));
  document.querySelector<HTMLElement>(".docs-nav-item")!.dataset.docSlug = '<img src=x onerror="bad()">';
  // Act
  document.getElementById("docs-export-all-pdf")!.click();
  await vi.waitFor(() => expect(print).toHaveBeenCalledOnce());
  // Assert
  expect(printDocument.querySelector("script, [onclick], [onerror]")).toBeNull();
  expect(printDocument.querySelector("p")?.textContent).toBe("Safe content");
});

it("encodes a document slug in fetch and export URLs without creating attributes", async () => {
  // Arrange
  const slug = 'guide/" onmouseover="bad()';
  // Act
  const { fetch } = await workspace(slug);
  // Assert
  expect(fetch.mock.calls[0][0]).toBe(`/apps/docs/content/${encodeURIComponent(slug)}/`);
  const link = document.querySelector<HTMLAnchorElement>(".docs-dropdown-item[href]")!;
  expect(link.getAttribute("href")).toBe(`/apps/docs/export/${encodeURIComponent(slug)}/`);
  expect(link.hasAttribute("onmouseover")).toBe(false);
});

it("renders failed-load messages as text", async () => {
  // Arrange
  const { fetch } = await workspace();
  fetch.mockRejectedValueOnce(new Error('<img src=x onerror="bad()">'));
  const link = document.querySelector<HTMLAnchorElement>(".docs-nav-item")!;
  link.dataset.docSlug = "another";
  // Act
  link.click();
  await vi.waitFor(() => expect(document.querySelector(".docs-error")).not.toBeNull());
  // Assert
  expect(document.querySelector(".docs-error img")).toBeNull();
  expect(document.querySelector(".docs-error")?.textContent).toContain('<img src=x onerror="bad()">');
});
