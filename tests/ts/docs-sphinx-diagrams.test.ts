import { afterEach, expect, test, vi } from "vitest";
import { renderSphinxDiagrams } from "../../apps/workspace/docs_app/static/docs_app/ts/sphinx-diagrams";

const { render, initialize } = vi.hoisted(() => ({
  render: vi.fn(async () => ({ svg: '<svg xmlns="http://www.w3.org/2000/svg"><text>Viewer</text></svg>' })),
  initialize: vi.fn(),
}));
vi.mock("mermaid", () => ({ default: { initialize, render } }));

afterEach(() => {
  document.body.innerHTML = "";
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

function documentPage() {
  document.body.innerHTML = '<main><div class="sphinx-inline-content"><pre class="mermaid">graph LR; A--&gt;B</pre></div></main>';
  return document.querySelector("main")!;
}

test("embedded Sphinx content gains an inert diagram image, once", async () => {
  const container = documentPage();
  vi.stubGlobal("URL", { createObjectURL: vi.fn(() => "blob:owned-diagram"), revokeObjectURL: vi.fn() });
  await renderSphinxDiagrams(container);
  expect(initialize).toHaveBeenCalledWith(expect.objectContaining({ securityLevel: "strict", startOnLoad: false }));
  expect(render).toHaveBeenCalledWith(expect.any(String), "graph LR; A-->B");
  expect(container.querySelector("img")?.getAttribute("src")).toBe("blob:owned-diagram");
  expect(container.querySelector("svg")).toBeNull();
  expect(container.querySelector("pre")).toBeNull();
  await renderSphinxDiagrams(container);
  expect(render).toHaveBeenCalledTimes(1);
});

test("invalid diagrams keep readable source without breaking the page", async () => {
  const container = documentPage();
  render.mockRejectedValueOnce(new Error("Bad syntax"));
  await renderSphinxDiagrams(container);
  expect(container.textContent).toContain("graph LR; A-->B");
  expect(container.querySelector("pre")?.getAttribute("aria-label")).toContain("preview unavailable");
});

test("navigation during a pending render cannot publish into the new page", async () => {
  const container = documentPage();
  let deliver!: (value: { svg: string }) => void;
  render.mockImplementationOnce(() => new Promise((resolve) => { deliver = resolve; }));
  const pending = renderSphinxDiagrams(container);
  await vi.waitFor(() => expect(deliver).toBeTypeOf("function"));
  container.innerHTML = "New page";
  deliver({ svg: "<svg/>" });
  await pending;
  expect(container.textContent).toBe("New page");
});
