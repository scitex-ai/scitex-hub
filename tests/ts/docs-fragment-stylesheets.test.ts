import { afterEach, expect, test, vi } from "vitest";

const stylesheet = "/static/vite/docs-context-regression.css";

afterEach(() => {
  document.body.innerHTML = "";
  document.head.querySelectorAll('link[data-docs-style-test]').forEach((link) => link.remove());
  vi.unstubAllGlobals();
  vi.resetModules();
});

async function loadWorkspace() {
  document.body.innerHTML = `<main class="docs-workspace" data-active-doc="context-exposure">
    <aside class="docs-sidebar"><a class="docs-nav-item" data-doc-slug="context-exposure">Context</a>
    <a class="docs-nav-item" data-doc-slug="overview">Overview</a></aside>
    <div id="docs-content-area"></div></main>`;
  const fetch = vi.fn(async () => new Response(`<p>Owned Docs content</p>
    <link rel="stylesheet" href="${stylesheet}" media="screen" data-docs-style-test>
    <link rel="modulepreload" href="/static/vite/not-a-stylesheet.js">`));
  vi.stubGlobal("fetch", fetch);
  await import("../../apps/workspace/docs_app/static/docs_app/ts/docs-workspace");
  document.dispatchEvent(new Event("DOMContentLoaded"));
  await vi.waitFor(() => expect(fetch).toHaveBeenCalled());
  return fetch;
}

test("real Docs fragment loader promotes a new stylesheet before removing its body link", async () => {
  const fetch = await loadWorkspace();
  await vi.waitFor(() => expect(document.head.querySelectorAll(`link[href="${stylesheet}"]`)).toHaveLength(1));
  const link = document.head.querySelector<HTMLLinkElement>(`link[href="${stylesheet}"]`)!;
  expect(link.isConnected).toBe(true);
  expect(link.media).toBe("screen");
  expect(document.querySelector('#docs-content-area link[rel="stylesheet"]')).toBeNull();
  expect(document.querySelector('#docs-content-area link[rel="modulepreload"]')).not.toBeNull();
  document.querySelector<HTMLAnchorElement>('[data-doc-slug="overview"]')!.click();
  await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  await vi.waitFor(() => expect(document.querySelector('#docs-content-area link[rel="stylesheet"]')).toBeNull());
  expect(document.head.querySelectorAll(`link[href="${stylesheet}"]`)).toHaveLength(1);
});

test("real Docs fragment loader retains an already connected head stylesheet", async () => {
  const existing = document.createElement("link");
  existing.rel = "stylesheet";
  existing.href = stylesheet;
  existing.dataset.docsStyleTest = "";
  document.head.append(existing);
  await loadWorkspace();
  await vi.waitFor(() => expect(document.querySelector('#docs-content-area p')?.textContent).toBe("Owned Docs content"));
  expect(document.head.querySelectorAll(`link[href="${stylesheet}"]`)).toHaveLength(1);
  expect(document.head.querySelector(`link[href="${stylesheet}"]`)).toBe(existing);
  expect(document.querySelector('#docs-content-area link[rel="stylesheet"]')).toBeNull();
});
