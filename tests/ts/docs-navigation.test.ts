import { beforeEach, expect, test, vi } from "vitest";
import { initDocsColumns, syncDocsColumns } from "../../apps/workspace/docs_app/static/docs_app/ts/docs-navigation";

beforeEach(() => {
  document.body.innerHTML = `<div class="docs-workspace">
    <button class="docs-category active" data-doc-category="start">Getting Started</button>
    <button class="docs-category" data-doc-category="reference">Reference</button>
    <aside class="docs-sidebar">
      <div class="docs-page-group" data-doc-group="start"><a class="docs-nav-item" data-doc-slug="overview"><span>Overview</span></a></div>
      <div class="docs-page-group" data-doc-group="reference" hidden><a class="docs-nav-item" data-doc-slug="api-one"><span>API One</span></a><a class="docs-nav-item" data-doc-slug="api-two"><span>API Two</span></a></div>
    </aside><span id="docs-page-title"></span><a id="docs-export-page-md"></a>
  </div>`;
});

test("category selection changes only the second column and remembers its last page", () => {
  const workspace = document.querySelector<HTMLElement>(".docs-workspace")!;
  const navigate = vi.fn((slug: string) => syncDocsColumns(slug));
  initDocsColumns(workspace, navigate);
  syncDocsColumns("overview");
  const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>(".docs-category"));
  const initialRows = buttons.map((button) => button.outerHTML);
  buttons[1].click();
  expect(navigate).toHaveBeenLastCalledWith("api-one");
  syncDocsColumns("api-two");
  buttons[0].click();
  buttons[1].click();
  expect(navigate).toHaveBeenLastCalledWith("api-two");
  expect(buttons.map((button) => button.textContent)).toEqual(["Getting Started", "Reference"]);
  expect(document.querySelectorAll(".docs-category")).toHaveLength(initialRows.length);
  expect(Array.from(document.querySelectorAll<HTMLElement>(".docs-page-group")).map((group) => group.hidden)).toEqual([true, false]);
  expect(document.querySelector("#docs-page-title")?.textContent).toBe("API Two");
  expect(document.querySelector("#docs-export-page-md")?.getAttribute("href")).toBe("/apps/docs/export/api-two/");
});

test("reselecting the active category leaves its page and scroll state alone", () => {
  const navigate = vi.fn();
  initDocsColumns(document.querySelector<HTMLElement>(".docs-workspace")!, navigate);
  syncDocsColumns("overview");
  document.querySelector<HTMLButtonElement>(".docs-category")!.click();
  expect(navigate).not.toHaveBeenCalled();
  expect(document.querySelector(".docs-category[aria-current=true]")?.textContent).toBe("Getting Started");
});

test("deep links select the owning category without rebuilding its page rows", () => {
  const workspace = document.querySelector<HTMLElement>(".docs-workspace")!;
  initDocsColumns(workspace, vi.fn());
  const rows = Array.from(workspace.querySelectorAll(".docs-nav-item"));
  syncDocsColumns("api-two");
  expect(workspace.querySelector(".docs-category[aria-current=true]")?.textContent).toBe("Reference");
  expect(Array.from(workspace.querySelectorAll(".docs-nav-item"))).toEqual(rows);
  syncDocsColumns("unknown");
  expect(workspace.querySelector("#docs-page-title")?.textContent).toBe("API Two");
});
