/**
 * Tests for apps/writer_app/static/writer_app/ts/utils/_section-dropdown/SectionDropdown.ts
 */
import { describe, it, expect, beforeEach } from "vitest";
import { renderEmptyState } from "@writer_app/utils/_section-dropdown/SectionDropdown";

function makeContainer(): HTMLElement {
  const el = document.createElement("div");
  el.id = "section-selector-dropdown";
  document.body.appendChild(el);
  return el;
}

describe("SectionDropdown.renderEmptyState", () => {
  let container: HTMLElement;
  beforeEach(() => {
    container = makeContainer();
  });

  it("for a CONFIGURED doc type with no sections, names the cause and the add-section next action", () => {
    renderEmptyState(container, "manuscript", true, null);
    const text = container.textContent || "";
    expect(container.querySelector('[data-empty="no-sections"]')).not.toBeNull();
    expect(text).toContain("No sections yet in the manuscript doc type");
    expect(text).toContain("Cause: this document type is configured but has no sections");
    expect(text).toMatch(/Next:.*add/i);
    expect(text).not.toContain("is not enabled in this project");
  });

  it("for an UNCONFIGURED doc type, names the cause and the enable-doc-type next action", () => {
    renderEmptyState(container, "supplementary", false, null);
    const text = container.textContent || "";
    expect(container.querySelector('[data-empty="not-configured"]')).not.toBeNull();
    expect(text).toContain("supplementary is not enabled in this project");
    expect(text).toContain("Cause: this document type has no sections configured");
    expect(text).toMatch(/Next:.*enable/i);
  });

  it("is idempotent — re-rendering replaces the previous empty state", () => {
    renderEmptyState(container, "manuscript", true, null);
    renderEmptyState(container, "manuscript", false, null);
    // Only the last state remains
    expect(container.querySelector('[data-empty="no-sections"]')).toBeNull();
    expect(container.querySelector('[data-empty="not-configured"]')).not.toBeNull();
  });

  it("accepts an add-section callback without throwing (wired for the next action)", () => {
    let called = 0;
    const cb = () => {
      called += 1;
    };
    expect(() => renderEmptyState(container, "revision", true, cb)).not.toThrow();
    // The callback is accepted; the visual next action is the in-app + control.
    expect(called).toBe(0);
  });
});
