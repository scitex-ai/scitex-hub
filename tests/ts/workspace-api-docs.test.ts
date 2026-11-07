import { afterEach, expect, test, vi } from "vitest";
import { API_DOCS_HEADER, prepareModuleDocumentation, mountModuleHeader } from "../../static/shared/ts/workspace-api-docs";

afterEach(() => { document.body.innerHTML = ""; document.body.removeAttribute("data-stx-api-docs-url"); });

test("owner transitions preserve an explicit empty boundary against stale body inheritance", () => {
  document.body.setAttribute("data-stx-api-docs-url", "/docs?package=stale-body");
  const pane = document.createElement("main");
  document.body.append(pane);
  const observed: (string | null)[] = [];
  for (const owner of ["scitex-a", "scitex-b", null, "scitex-a"]) {
    const headers = owner ? { [API_DOCS_HEADER]: `/docs/web-api/?package=${owner}` } : {};
    prepareModuleDocumentation(pane, new Response("owned fragment", { headers }));
    observed.push(pane.getAttribute("data-stx-api-docs-url"));
  }
  expect(observed).toEqual(["/docs/web-api/?package=scitex-a", "/docs/web-api/?package=scitex-b", "", "/docs/web-api/?package=scitex-a"]);
});

test("cached module mounting delegates once to the SDK's existing lifecycle port", () => {
  const pane = document.createElement("main");
  const mount = vi.fn();
  const previous = (window as any).stxAppHeader;
  (window as any).stxAppHeader = { mount };
  try {
    mountModuleHeader(pane);
    expect(mount.mock.calls).toEqual([[pane]]);
  } finally { (window as any).stxAppHeader = previous; }
});
