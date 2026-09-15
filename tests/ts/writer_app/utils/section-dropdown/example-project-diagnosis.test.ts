/**
 * Tests for the Example-Project initial-state diagnosis in
 * apps/workspace/writer_app/static/writer_app/ts/utils/_section-dropdown/SectionDropdown.ts
 * (compass §11 Writer Initial State, TODO 158-161).
 *
 * Only TWO states are reachable in the section dropdown (the reviewer's finding
 * #4): auto-select (sections exist) and no-manuscript (configured but empty).
 * "uninitialized" is the full-page index.html block and "not-enabled" cannot
 * occur because the backend scanner always pre-creates every doc-type key.
 */
import { describe, it, expect, beforeEach } from "vitest";
import {
  diagnoseExampleProject,
  renderExampleState,
} from "@writer_app/utils/_section-dropdown/SectionDropdown";

function makeContainer(): HTMLElement {
  const el = document.createElement("div");
  el.id = "section-selector-dropdown";
  document.body.appendChild(el);
  return el;
}

describe("diagnoseExampleProject (158-159: the two reachable states)", () => {
  it("158: sections present → auto-select (cause says a manuscript is present, next = auto-selected)", () => {
    const d = diagnoseExampleProject("manuscript", { sectionCount: 3 });
    expect(d.state).toBe("auto-select");
    expect(d.cause).toContain("manuscript");
    expect(d.cause).toContain("present");
    expect(d.nextAction).toMatch(/selected automatically/i);
  });

  it("159: configured but zero sections → no-manuscript (never a bare 'No manuscript selected')", () => {
    const d = diagnoseExampleProject("manuscript", { sectionCount: 0 });
    expect(d.state).toBe("no-manuscript");
    expect(d.cause).toMatch(/No manuscript is selected/i);
    expect(d.cause).toMatch(/no sections yet/i);
    expect(d.cause).not.toMatch(/manuscript manuscript/i);
    // next action points at the REAL control (verified: data-action="new-section"
    // in the section dropdown footer opens #add-section-modal).
    expect(d.nextAction).toMatch(/Add New Section/i);
  });

  it("respects a non-manuscript docType in the message", () => {
    const d = diagnoseExampleProject("supplementary", { sectionCount: 0 });
    expect(d.state).toBe("no-manuscript");
    expect(d.cause).toContain("supplementary");
  });

  it("defaults to manuscript when docType omitted", () => {
    const d = diagnoseExampleProject("", { sectionCount: 0 });
    expect(d.cause).not.toContain("this document type this document type");
  });
});

describe("diagnoseExampleProject — only the two reachable states are produced", () => {
  it("never returns an unreachable state (uninitialized / not-enabled)", () => {
    // The reviewer flagged that a 4-state model claimed unreachable states.
    // For every combination the live code can pass in, only the two real states
    // may come back.
    for (const count of [0, 1, 5]) {
      const d = diagnoseExampleProject("manuscript", { sectionCount: count });
      expect(["auto-select", "no-manuscript"]).toContain(d.state);
    }
  });

  it("always returns a non-empty cause AND next action", () => {
    for (const count of [0, 1]) {
      const d = diagnoseExampleProject("manuscript", { sectionCount: count });
      expect(d.cause.length).toBeGreaterThan(0);
      expect(d.nextAction.length).toBeGreaterThan(0);
    }
  });
});

describe("renderExampleState", () => {
  let container: HTMLElement;
  beforeEach(() => {
    container = makeContainer();
  });

  it("auto-select renders nothing (caller proceeds to populate + select)", () => {
    renderExampleState(container, diagnoseExampleProject("manuscript", { sectionCount: 1 }));
    expect(container.querySelector(".section-empty")).toBeNull();
  });

  it("no-manuscript renders the diagnosis with data-empty='no-manuscript'", () => {
    renderExampleState(container, diagnoseExampleProject("manuscript", { sectionCount: 0 }));
    expect(container.querySelector('[data-empty="no-manuscript"]')).not.toBeNull();
    expect(container.textContent).toMatch(/No manuscript is selected/i);
    expect(container.textContent).toMatch(/Next:/i);
  });
});

/**
 * CodeQL regression: "DOM text reinterpreted as HTML". A hostile docType flows
 * into diagnosis.cause / nextAction (via the ${label} interpolation). render
 * MUST treat it as inert text — no element injection, no attribute/JS execution.
 */
describe("renderExampleState — hostile docType is NOT reinterpreted as HTML (CodeQL)", () => {
  let container: HTMLElement;
  beforeEach(() => {
    container = makeContainer();
  });

  it("a markup/docType payload is rendered as text, not parsed as elements", () => {
    // No '-' or '_' in the payload: diagnoseExampleProject turns the docType
    // into a label via .replace(/[-_]/g, " "), so a dash/underscore-free payload
    // survives that transform verbatim and lets us assert the raw markup is
    // present as inert TEXT (while proving no live elements were created).
    const hostile =
      '"><img src=x onerror=window.XSSimg>' +
      "<script>window.XSSscript</" + "script>" +
      '<svg onload=window.XSSsvg>';
    const diagnosis = diagnoseExampleProject(hostile, { sectionCount: 0 }); // → no-manuscript

    renderExampleState(container, diagnosis);

    // No injected live elements exist in the rendered container.
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("svg")).toBeNull();
    // The hostile markup is present as inert TEXT (textContent), verbatim.
    expect(container.textContent).toContain("onerror=window.XSSimg");
    expect(container.textContent).toContain("window.XSSscript");
    expect(container.textContent).toContain("onload=window.XSSsvg");
    // No side-effect globals were executed.
    const w = window as any;
    expect(w.XSSimg).toBeUndefined();
    expect(w.XSSscript).toBeUndefined();
    expect(w.XSSsvg).toBeUndefined();
  });

  it("nextAction payload is inert too (only the single 'Next:' label is markup)", () => {
    // No-manuscript nextAction embeds the docType label.
    const hostile = '"><b onload=window.XSSnext>pwned';
    const diagnosis = diagnoseExampleProject(hostile, { sectionCount: 0 }); // → no-manuscript
    renderExampleState(container, diagnosis);
    expect(container.querySelector("b[onload]")).toBeNull();
    expect(container.querySelector("b")).toBeNull();
    expect(container.textContent).toContain("onload=window.XSSnext");
    expect((window as any).XSSnext).toBeUndefined();
  });

  it("still renders the expected structure for a benign no-manuscript state", () => {
    renderExampleState(container, diagnoseExampleProject("manuscript", { sectionCount: 0 }));
    expect(container.querySelector('[data-empty="no-manuscript"]')).not.toBeNull();
    expect(container.querySelector("strong")?.textContent).toBe("Next:");
  });
});
