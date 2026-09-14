/**
 * A missing file shows a not-found state — never an editable editor.
 *
 * Site audit 2026-09-14 (D12): opening a file that does not exist gave an
 * "Editor" tab whose content was "// Error loading file: ... HTTP 404".
 *
 * No mocking library: the fetch is a plain function returning a real 404
 * Response.
 */

import { describe, it, expect } from "vitest";

import {
  fetchTextFile,
  showLoadFailure,
} from "@/components/workspace-viewer/_file-state";

const notFound = async (): Promise<Response> =>
  new Response(JSON.stringify({ error: "File not found" }), { status: 404 });

function panes() {
  const monacoContainer = document.createElement("div");
  const mediaContainer = document.createElement("div");
  const previewContainer = document.createElement("div");
  monacoContainer.style.display = "block";
  return { monacoContainer, mediaContainer, previewContainer };
}

describe("workspace viewer: missing file", () => {
  it("reports a 404 as not-found instead of file content", async () => {
    // Arrange
    const url = "/api/workspace/file-content/does-not-exist.txt?raw=true";
    // Act
    const load = await fetchTextFile(url, notFound);
    // Assert
    expect(load.kind).toBe("not-found");
  });

  it("hides the editor for a missing file", async () => {
    // Arrange
    const p = panes();
    const load = await fetchTextFile("/x", notFound);
    // Act
    if (load.kind !== "ok") showLoadFailure(p, "does-not-exist.txt", load);
    // Assert
    expect(p.monacoContainer.style.display).toBe("none");
  });

  it("shows a not-found state for a missing file", async () => {
    // Arrange
    const p = panes();
    const load = await fetchTextFile("/x", notFound);
    // Act
    if (load.kind !== "ok") showLoadFailure(p, "does-not-exist.txt", load);
    // Assert
    expect(
      p.mediaContainer.querySelector('[data-viewer-load-failure="not-found"]'),
    ).not.toBeNull();
  });
});
