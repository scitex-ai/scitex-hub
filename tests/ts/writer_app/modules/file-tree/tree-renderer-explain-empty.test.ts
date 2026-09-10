/**
 * Tests for the empty-file-tree diagnosis in
 * apps/workspace/writer_app/static/writer_app/ts/modules/_file-tree/tree-renderer.ts
 * (compass §11 Initial State, TODO item 161).
 */
import { describe, it, expect } from "vitest";
import { explainFileTreeEmpty } from "@writer_app/modules/_file-tree/tree-renderer";

describe("explainFileTreeEmpty (item 161: cause + next action for an empty tree)", () => {
  it("when a section is selected but its file is missing, names the section file and the fix", () => {
    const d = explainFileTreeEmpty("manuscript", "abstract");
    expect(d.cause).toContain("abstract.tex");
    expect(d.cause).toContain("manuscript");
    expect(d.cause).toMatch(/Cause:/);
    expect(d.nextAction).toMatch(/Next:/);
    expect(d.nextAction).toMatch(/create that section file/i);
  });

  it("when no section is selected, explains the workspace is not initialized", () => {
    const d = explainFileTreeEmpty("manuscript", null);
    expect(d.cause).toMatch(/not initialized/i);
    expect(d.cause).toContain("manuscript");
    expect(d.nextAction).toMatch(/initialize the workspace/i);
  });

  it("respects a non-manuscript doctype", () => {
    const d = explainFileTreeEmpty("supplementary", null);
    expect(d.cause).toContain("supplementary");
  });

  it("defaults to manuscript when doctype is omitted", () => {
    const d = explainFileTreeEmpty();
    expect(d.cause).toContain("manuscript");
  });

  it("always returns both a cause and a next action (never just a bare message)", () => {
    for (const [dt, sec] of [
      ["manuscript", null],
      ["manuscript", "methods"],
      ["revision", "conclusion"],
    ] as [string, string | null][]) {
      const d = explainFileTreeEmpty(dt, sec);
      expect(d.cause.length).toBeGreaterThan(0);
      expect(d.nextAction.length).toBeGreaterThan(0);
      expect(d.cause).toMatch(/^Cause:/);
      expect(d.nextAction).toMatch(/^Next:/);
    }
  });
});
