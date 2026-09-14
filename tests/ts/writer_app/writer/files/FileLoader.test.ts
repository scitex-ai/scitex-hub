/**
 * Tests for apps/workspace/writer_app/static/writer_app/ts/_writer/files/FileLoader.ts
 */

import { describe, it, expect } from "vitest";

import { loadTexFile } from "@writer_app/_writer/files/FileLoader";

describe("loadTexFile", () => {
  it("does not fetch the file when the manuscript does not exist", async () => {
    // Arrange
    (window as any).WRITER_CONFIG = { projectId: 7 };
    const requestedUrls: string[] = [];
    const dependencies = {
      getManuscriptStatus: async () => ({ exists: false, has_pdf: false }),
      fetchFile: (async (url: RequestInfo | URL) => {
        requestedUrls.push(String(url));
        return new Response("{}");
      }) as typeof fetch,
    };
    const editor = { setContent: () => undefined };

    // Act
    await loadTexFile(
      "scitex/writer/01_manuscript/contents/abstract.tex",
      editor,
      dependencies,
    );

    // Assert
    expect(requestedUrls).toEqual([]);
  });
});
