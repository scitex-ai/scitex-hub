/**
 * Tests for the PDF preview placeholder in
 * apps/workspace/writer_app/static/writer_app/ts/modules/pdf-preview/viewer.ts
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { PDFViewer } from "@writer_app/modules/pdf-preview/viewer";

/**
 * Regression: the placeholder must not claim a load is in progress.
 *
 * ComponentInitializer.loadInitialPDF() HEAD-checks for an existing preview. If
 * none exists AND the abstract is empty it takes neither branch — it does not
 * compile and it does not touch the panel — so this placeholder is the FINAL
 * state for a fresh project, not a transient one. It used to read "Loading PDF
 * preview...", which meant a new user watched a load that was never going to
 * happen. Measured on live scitex.ai 2026-08-04.
 *
 * Both directions are asserted on purpose. A test that only checked for the new
 * wording would still pass if someone re-added the old line alongside it, which
 * is exactly how the contradiction ("Loading..." above "Click Compile") arose in
 * the first place.
 */
describe("PDF preview placeholder honesty", () => {
  let container: HTMLElement;

  beforeEach(() => {
    document.body.innerHTML = '<div id="text-preview"></div>';
    container = document.getElementById("text-preview") as HTMLElement;
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("does NOT claim the preview is loading", () => {
    const viewer = new PDFViewer("text-preview", "light", 2);
    viewer.displayPlaceholder();
    expect(container.textContent).not.toMatch(/loading/i);
  });

  it("still tells the user how to get a preview", () => {
    const viewer = new PDFViewer("text-preview", "light", 2);
    viewer.displayPlaceholder();
    // The actionable instruction is the whole point of the panel; dropping the
    // false line must not drop this one with it.
    expect(container.textContent).toMatch(/Compile/);
  });

  it("says a preview does not exist yet", () => {
    const viewer = new PDFViewer("text-preview", "light", 2);
    viewer.displayPlaceholder();
    expect(container.textContent).toMatch(/No preview yet/);
  });

  it("renders into the container at all (control for the assertions above)", () => {
    // Without this, all three checks above pass for free on an empty string:
    // "" matches neither /loading/i nor anything else, so a placeholder that
    // rendered NOTHING would score two passes out of three.
    const viewer = new PDFViewer("text-preview", "light", 2);
    viewer.displayPlaceholder();
    expect((container.textContent || "").trim().length).toBeGreaterThan(0);
  });
});
