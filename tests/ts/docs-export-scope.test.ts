import { afterEach, expect, it, vi } from "vitest";
import { syncDocsExportScope } from "../../apps/workspace/docs_app/static/docs_app/ts/docs-export-scope";
import { initDocsCopy } from "../../apps/workspace/docs_app/static/docs_app/ts/docs-copy";

afterEach(() => { document.body.replaceChildren(); vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.resetModules(); });

function workspace() {
  document.body.innerHTML = `<main class="docs-workspace">
    <a id="docs-download-page"></a><a id="docs-export-page-md"></a>
    <button id="docs-copy-page"><span>Copy Markdown</span></button>
    <div id="docs-content-area"><a class="sphinx-page-link" data-pkg-slug="pkg-example" data-sphinx-page="guide/cli.html">CLI</a></div>
  </main>`;
  return document.querySelector<HTMLElement>(".docs-workspace")!;
}

it("encodes the selected package subpage for both download choices and resets on navigation", () => {
  workspace();
  syncDocsExportScope("pkg-example", 'guide/cli & tips.html');
  const links = [...document.querySelectorAll<HTMLAnchorElement>("a[id]")];
  expect(links.map(a => a.getAttribute("href"))).toEqual(Array(2).fill('/apps/docs/export/pkg-example/?page=guide%2Fcli%20%26%20tips.html'));
  syncDocsExportScope("overview");
  expect(links.map(a => a.getAttribute("href"))).toEqual(Array(2).fill('/apps/docs/export/overview/'));
});

it("native subpage navigation scopes the existing copy control to the loaded document", async () => {
  const root = workspace();
  const fetch = vi.fn().mockResolvedValueOnce(new Response("<h1>CLI reference</h1>"))
    .mockResolvedValueOnce(new Response("# CLI reference", { headers: { "Content-Type": "text/markdown" } }));
  vi.stubGlobal("fetch", fetch);
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  initDocsCopy(root);
  await import("../../apps/workspace/docs_app/static/docs_app/ts/sphinx-page-nav");
  root.querySelector<HTMLAnchorElement>(".sphinx-page-link")!.click();
  await vi.waitFor(() => expect(root.querySelector("h1")?.textContent).toBe("CLI reference"));
  expect(root.querySelector("#docs-download-page")?.getAttribute("href")).toBe("/apps/docs/export/pkg-example/?page=guide%2Fcli.html");
  root.querySelector<HTMLButtonElement>("#docs-copy-page")!.click();
  await vi.waitFor(() => expect(writeText).toHaveBeenCalledWith("# CLI reference"));
  expect(String(fetch.mock.calls[1][0])).toContain("/apps/docs/export/pkg-example/?page=guide%2Fcli.html");
});

it("keeps export scope on the previous page when subpage loading fails", async () => {
  const root = workspace(); syncDocsExportScope("pkg-example", "index.html");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("Failed", { status: 500 })));
  await import("../../apps/workspace/docs_app/static/docs_app/ts/sphinx-page-nav");
  root.querySelector<HTMLAnchorElement>(".sphinx-page-link")!.click();
  await vi.waitFor(() => expect(root.querySelector(".docs-error")).not.toBeNull());
  expect(root.querySelector("#docs-download-page")?.getAttribute("href")).toBe("/apps/docs/export/pkg-example/?page=index.html");
});
