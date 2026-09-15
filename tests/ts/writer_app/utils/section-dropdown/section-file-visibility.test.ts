/**
 * Tests for the section↔file visibility (compass §11 Initial State, TODO 163/164):
 * each section item shows its real .tex filename inline, and the "open file"
 * action targets it — so the relationship between manuscript sections and
 * actual files is visible without opening the file tree / shell.
 *
 * apps/workspace/writer_app/static/writer_app/ts/utils/_section-dropdown/rendering.ts
 */
import { describe, it, expect, beforeAll } from "vitest";
import { renderSectionDropdown } from "@writer_app/utils/_section-dropdown/rendering";

beforeAll(() => {
  (window as any).WRITER_CONFIG = {
    projectOwner: "owner",
    projectSlug: "demo",
  };
});

function renderInto(html: string): HTMLElement {
  const el = document.createElement("div");
  el.innerHTML = html;
  document.body.appendChild(el);
  return el;
}

describe("renderSectionDropdown — section↔file relationship visible (163/164)", () => {
  const sections = [
    { id: "manuscript/abstract", name: "abstract", label: "Abstract", path: "01_manuscript/contents/abstract.tex" },
    { id: "manuscript/introduction", name: "introduction", label: "Introduction", path: "01_manuscript/contents/01_introduction.tex", optional: true },
    { id: "manuscript/compiled_pdf", name: "compiled_pdf", label: "📄 Full Manuscript", path: "01_manuscript/manuscript.tex", view_only: true, is_compiled: true },
  ];

  it("shows the real .tex filename inline for each editable section", () => {
    const root = renderInto(renderSectionDropdown(sections, "manuscript"));
    const hints = root.querySelectorAll(".section-file-hint");
    // 2 editable sections (abstract, introduction) show a filename; compiled_pdf does not
    expect(hints.length).toBe(2);
    const files = Array.from(hints).map((h) => h.textContent?.trim());
    expect(files).toContain("abstract.tex");
    expect(files).toContain("01_introduction.tex");
    // data-file attribute carries the exact filename for the open action
    const abstractHint = Array.from(hints).find((h) => h.textContent?.includes("abstract.tex"));
    expect(abstractHint?.getAttribute("data-file")).toBe("abstract.tex");
  });

  it("derives the filename from the path (last segment), not the label", () => {
    const root = renderInto(renderSectionDropdown(sections, "manuscript"));
    const introHint = Array.from(root.querySelectorAll(".section-file-hint")).find((h) =>
      h.textContent?.includes("01_introduction.tex"),
    );
    // The label is "Introduction" but the file is "01_introduction.tex"
    expect(introHint?.textContent).toBe("01_introduction.tex");
  });

  it("the 'open file' action links to each section's real file path (incl. the full manuscript)", () => {
    const root = renderInto(renderSectionDropdown(sections, "manuscript"));
    const links = root.querySelectorAll('a[title^="Open"]');
    // 3 sections (abstract, introduction, full-manuscript) each get a file-open action
    expect(links.length).toBe(3);
    const titles = Array.from(links).map((a) => a.getAttribute("title"));
    expect(titles).toContain("Open abstract.tex in the file viewer");
    expect(titles).toContain("Open 01_introduction.tex in the file viewer");
    expect(titles).toContain("Open manuscript.tex in the file viewer");
    // href points at the blob path for that file
    const abstractLink = Array.from(links).find((a) => a.getAttribute("title")?.includes("abstract.tex"));
    expect(abstractLink?.getAttribute("href")).toContain("01_manuscript/contents/abstract.tex");
    const fullLink = Array.from(links).find((a) => a.getAttribute("title")?.includes("manuscript.tex"));
    expect(fullLink?.getAttribute("href")).toContain("01_manuscript/manuscript.tex");
  });

  it("does NOT show a filename hint for view-only compiled sections", () => {
    const root = renderInto(renderSectionDropdown(sections, "manuscript"));
    const compiledItem = root.querySelector('[data-section-id="manuscript/compiled_pdf"]');
    expect(compiledItem).not.toBeNull();
    expect(compiledItem?.querySelector(".section-file-hint")).toBeNull();
  });

  it("falls back to <name>.tex when a section has no explicit path", () => {
    const root = renderInto(
      renderSectionDropdown(
        [{ id: "manuscript/discussion", name: "discussion", label: "Discussion" }],
        "manuscript",
      ),
    );
    const hint = root.querySelector(".section-file-hint");
    expect(hint?.textContent).toBe("discussion.tex");
    expect(hint?.getAttribute("data-file")).toBe("discussion.tex");
  });
});
