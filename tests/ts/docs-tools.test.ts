import { beforeEach, afterEach, expect, test, vi } from "vitest";
import { initDocsFilter } from "../../apps/workspace/docs_app/static/docs_app/ts/docs-filter";
import { initDocsCopy } from "../../apps/workspace/docs_app/static/docs_app/ts/docs-copy";

beforeEach(() => {
 document.body.innerHTML = `<div class="docs-workspace"><input id="docs-filter-input"><button id="docs-filter-clear" hidden>Clear</button><input type="checkbox" id="docs-filter-show-hidden"><div id="docs-filter-options" hidden><span id="docs-filter-summary"></span></div>
 <button class="docs-category active" data-doc-category="apps">Workspace Apps</button>
 <div class="docs-page-group" data-doc-group="apps"><a class="docs-nav-item active" data-doc-slug="app-scholar"><span>Scholar</span></a><a class="docs-nav-item" data-doc-slug="app-storage"><span>Storage</span></a></div>
 <div id="docs-content-area">The open page</div><a id="docs-download-page" href="/apps/docs/export/app-storage/"></a><button id="docs-copy-page"><span>Copy Markdown</span></button></div>`;
});
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

test("fuzzy matches highlight letters, show counts and preserve the open document", () => {
 // Arrange
 const root = document.querySelector<HTMLElement>(".docs-workspace")!;
 initDocsFilter(root);
 const input = document.querySelector<HTMLInputElement>("#docs-filter-input")!;
 // Act
 input.value = "stg"; input.dispatchEvent(new Event("input"));
 // Assert
 expect(document.querySelector<HTMLElement>('[data-doc-slug="app-scholar"]')!.hidden).toBe(true);
 expect(document.querySelector<HTMLElement>('[data-doc-slug="app-storage"]')!.hidden).toBe(false);
 expect(Array.from(document.querySelectorAll('[data-doc-slug="app-storage"] mark')).map(e => e.textContent).join("")).toBe("Stg");
 expect(document.querySelector("#docs-filter-summary")!.textContent).toContain("1 of 2");
 expect(document.querySelector("#docs-filter-summary")!.textContent).toContain("outside the filter");
 expect(document.querySelector("#docs-content-area")!.textContent).toBe("The open page");
 expect(document.querySelectorAll(".docs-category")).toHaveLength(1);
});

test("show filtered out reveals dimmed clickable rows and clear restores them", () => {
 // Arrange
 initDocsFilter(document.querySelector<HTMLElement>(".docs-workspace")!);
 const input = document.querySelector<HTMLInputElement>("#docs-filter-input")!;
 input.value = "stg"; input.dispatchEvent(new Event("input"));
 const show = document.querySelector<HTMLInputElement>("#docs-filter-show-hidden")!;
 // Act
 show.checked = true; show.dispatchEvent(new Event("change"));
 // Assert
 const scholar = document.querySelector<HTMLAnchorElement>('[data-doc-slug="app-scholar"]')!;
 expect(scholar.hidden).toBe(false);
 expect(scholar.classList.contains("docs-filtered-out")).toBe(true);
 expect(scholar.hasAttribute("disabled")).toBe(false);
 document.querySelector<HTMLButtonElement>("#docs-filter-clear")!.click();
 expect(input.value).toBe("");
 expect(document.querySelectorAll("mark, .docs-filtered-out")).toHaveLength(0);
 expect(document.querySelector<HTMLElement>("#docs-filter-options")!.hidden).toBe(true);
});

test("copy uses the current page Markdown export and reports success", async () => {
 // Arrange
 const writeText = vi.fn().mockResolvedValue(undefined);
 Object.defineProperty(navigator, "clipboard", {configurable:true,value:{writeText}});
 const fetch = vi.fn().mockResolvedValue(new Response("# Storage\n\nOwned documentation", {headers:{"Content-Type":"text/markdown; charset=utf-8"}}));
 vi.stubGlobal("fetch", fetch); vi.useFakeTimers();
 initDocsCopy(document.querySelector<HTMLElement>(".docs-workspace")!);
 // Act
 document.querySelector<HTMLButtonElement>("#docs-copy-page")!.click();
 await vi.waitFor(() => expect(writeText).toHaveBeenCalledWith("# Storage\n\nOwned documentation"));
 // Assert
 expect(fetch.mock.calls[0][0]).toContain("/apps/docs/export/app-storage/");
 expect(document.querySelector("#docs-copy-page span")!.textContent).toBe("Copied");
 await vi.runAllTimersAsync();
});

test("copy failure never puts an HTML error page on the clipboard", async () => {
 // Arrange
 const writeText = vi.fn(); Object.defineProperty(navigator,"clipboard",{configurable:true,value:{writeText}});
 vi.stubGlobal("fetch",vi.fn().mockResolvedValue(new Response("Login page",{headers:{"Content-Type":"text/html"}})));vi.useFakeTimers();
 initDocsCopy(document.querySelector<HTMLElement>(".docs-workspace")!);
 // Act
 document.querySelector<HTMLButtonElement>("#docs-copy-page")!.click();
 await vi.waitFor(() => expect(document.querySelector("#docs-copy-page span")!.textContent).toBe("Copy failed"));
 // Assert
 expect(writeText).not.toHaveBeenCalled();
 expect(document.querySelector<HTMLButtonElement>("#docs-copy-page")!.disabled).toBe(false);
 await vi.runAllTimersAsync();
});


test("a fuzzy match cannot bridge unrelated title and category fields", () => {
 // Arrange
 const stats = document.querySelector<HTMLElement>('[data-doc-slug="app-scholar"]')!;
 stats.dataset.docSlug = "pkg-scitex-stats"; stats.querySelector("span")!.textContent = "Stats";
 document.querySelector(".docs-category")!.textContent = "Python Packages";
 initDocsFilter(document.querySelector<HTMLElement>(".docs-workspace")!);
 const input = document.querySelector<HTMLInputElement>("#docs-filter-input")!;
 // Act
 input.value = "stg"; input.dispatchEvent(new Event("input"));
 // Assert
 expect(stats.hidden).toBe(true);
 expect(document.querySelector<HTMLElement>('[data-doc-slug="app-storage"]')!.hidden).toBe(false);
});
