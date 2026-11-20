import { afterEach, expect, it, vi } from "vitest";
import { printAllDocs } from "../../../apps/workspace/docs_app/static/docs_app/ts/docs-batch-print";

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

function printWindow() {
  const doc = document.implementation.createHTMLDocument();
  const print = vi.fn();
  const win = { document: doc, print, closed: false } as unknown as Window;
  const open = vi.spyOn(window, "open").mockReturnValue(win);
  return { doc, print, win, open };
}

it("opens during the click and prints all pages in order after a delayed fetch", async () => {
  const { doc, print, open } = printWindow();
  let resolve!: (response: Response) => void;
  const fetch = vi.fn().mockReturnValueOnce(new Promise<Response>(r => { resolve = r; }))
    .mockResolvedValueOnce(new Response("<p>Second page</p>"));
  vi.stubGlobal("fetch", fetch);
  const pending = printAllDocs(["first", "second"]);
  expect(open).toHaveBeenCalledOnce();
  expect(doc.body.textContent).toContain("Preparing all documentation");
  expect(print).not.toHaveBeenCalled();
  resolve(new Response('<p onclick="bad()">First page</p><iframe></iframe><button>Download</button>'));
  await pending;
  expect(open).toHaveBeenCalledOnce();
  expect(print).toHaveBeenCalledOnce();
  expect([...doc.querySelectorAll("h1")].map(e => e.textContent)).toEqual(["first", "second"]);
  expect(doc.body.textContent).toContain("First page");
  expect(doc.querySelector("iframe,button,[onclick]")).toBeNull();
});

it("explains blocked popups without fetching pages", async () => {
  vi.spyOn(window, "open").mockReturnValue(null);
  const alert = vi.spyOn(window, "alert").mockImplementation(() => {});
  const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
  await printAllDocs(["overview"]);
  expect(alert).toHaveBeenCalledWith(expect.stringContaining("Allow popups"));
  expect(fetch).not.toHaveBeenCalled();
});

it.each([404, 500])("does not print a partial export on HTTP %i", async status => {
  const { doc, print } = printWindow();
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<h1>Error page</h1>", { status })));
  await printAllDocs(["overview"]);
  expect(print).not.toHaveBeenCalled();
  expect(doc.querySelector('[role="alert"]')?.textContent).toContain(`HTTP ${status}`);
  expect(doc.body.textContent).not.toContain("Error page");
});

it("renders network errors as text without printing", async () => {
  const { doc, print } = printWindow();
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error('<img src=x onerror="bad()">')));
  await printAllDocs(["overview"]);
  expect(print).not.toHaveBeenCalled();
  expect(doc.querySelector('[role="alert"]')?.textContent).toContain("<img");
  expect(doc.querySelector("img")).toBeNull();
});

it("does not print when the user closes the preparation window", async () => {
  const { print, win } = printWindow();
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<p>Overview</p>")));
  const pending = printAllDocs(["overview"]);
  Object.defineProperty(win, "closed", { value: true });
  await pending;
  expect(print).not.toHaveBeenCalled();
});
