/**
 * Opening a file on a project page keeps the project and path in the URL.
 *
 * Site audit 2026-09-14 (D12): a shared /<owner>/<slug>/blob/<path> link was
 * rewritten to /apps/<owner>/ as soon as the file opened (the owner segment
 * was taken for a module name), losing the project and the path.
 */

import { describe, it, expect } from "vitest";

import { buildNavUrl } from "@/_app-nav-url";

describe("in-app navigation URL", () => {
  it("keeps a blob deep link's path when its file opens", () => {
    // Arrange
    const loc = { pathname: "/alice/study/blob/docs/AGENTS.md", search: "" };
    const state = { module: "alice", file: "docs/AGENTS.md" };
    // Act
    const url = buildNavUrl(loc, state, "/alice/study/");
    // Assert
    expect(url).toBe("/alice/study/blob/docs/AGENTS.md");
  });

  it("points the URL at the file opened from the project tree", () => {
    // Arrange
    const loc = { pathname: "/alice/study/", search: "" };
    const state = { module: "alice", file: "data/plot 1.csv" };
    // Act
    const url = buildNavUrl(loc, state, "/alice/study/");
    // Assert
    expect(url).toBe("/alice/study/blob/data/plot%201.csv");
  });

  it("never rewrites a project page to an /apps/<owner>/ URL", () => {
    // Arrange
    const loc = { pathname: "/alice/study/tree/main/docs", search: "" };
    const state = { module: "alice" };
    // Act
    const url = buildNavUrl(loc, state, "/alice/study/");
    // Assert
    expect(url).toBe("/alice/study/tree/main/docs");
  });

  it("keeps module pages on their module URL", () => {
    // Arrange
    const loc = { pathname: "/apps/home/", search: "" };
    const state = { module: "home", file: "README.md" };
    // Act
    const url = buildNavUrl(loc, state, "/alice/study/");
    // Assert
    expect(url).toBe("/apps/home/");
  });
});
