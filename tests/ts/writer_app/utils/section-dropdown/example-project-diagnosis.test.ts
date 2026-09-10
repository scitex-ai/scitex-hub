/**
 * Tests for the Example-Project initial-state diagnosis in
 * apps/writer_app/static/writer_app/ts/utils/_section-dropdown/SectionDropdown.ts
 * (compass §11 Writer Initial State, TODO 158-161).
 */
import { describe, it, expect, beforeEach } from "vitest";
import {
  diagnoseExampleProject,
  renderExampleState,
} from "@writer_app/utils/_section-dropdown/SectionDropdown";

const base = { sectionCount: 0, docTypeConfigured: true, writerInitialized: true };

function makeContainer(): HTMLElement {
  const el = document.createElement("div");
  el.id = "section-selector-dropdown";
  document.body.appendChild(el);
  return el;
}

describe("diagnoseExampleProject (158-161: distinguish the four initial states)", () => {
  it("158: when a manuscript IS present (sectionCount>0) → auto-select, never an error", () => {
    const d = diagnoseExampleProject("manuscript", { ...base, sectionCount: 3 });
    expect(d.state).toBe("auto-select");
    expect(d.cause).toContain("manuscript");
    expect(d.cause).toContain("present");
    expect(d.nextAction).toMatch(/selected automatically/i);
  });

  it("159: configured but zero sections + workspace initialized → no-manuscript (not a bare 'No manuscript selected')", () => {
    const d = diagnoseExampleProject("manuscript", base); // initialized, configured, 0 sections
    expect(d.state).toBe("no-manuscript");
    expect(d.cause).toMatch(/No manuscript is selected/i);
    expect(d.cause).toMatch(/no sections yet/i);
    expect(d.cause).not.toMatch(/manuscript manuscript/i); // no doubled word
    expect(d.nextAction).toMatch(/add the first manuscript section/i);
  });

  it("161: workspace not initialized → uninitialized (cause + Initialize Writer next action)", () => {
    const d = diagnoseExampleProject("manuscript", { ...base, writerInitialized: false });
    expect(d.state).toBe("uninitialized");
    expect(d.cause).toMatch(/not initialized/i);
    expect(d.nextAction).toMatch(/initialize the workspace/i);
    expect(d.nextAction).not.toMatch(/^Next:/i); // renderer adds the single "Next:" label
  });

  it("161: doc type not enabled → not-enabled (enable-doc-type next action)", () => {
    const d = diagnoseExampleProject("supplementary", { ...base, docTypeConfigured: false });
    expect(d.state).toBe("not-enabled");
    expect(d.cause).toContain("supplementary");
    expect(d.cause).toMatch(/not enabled/i);
    expect(d.nextAction).toMatch(/enable the supplementary document type/i);
    expect(d.nextAction).not.toMatch(/^Next:/i);
  });

  it("priority: auto-select wins when sections exist even if uninitialized", () => {
    const d = diagnoseExampleProject("manuscript", { ...base, sectionCount: 2, writerInitialized: false });
    expect(d.state).toBe("auto-select");
  });

  it("priority: uninitialized wins over no-manuscript (no structure yet beats configured-but-empty)", () => {
    const d = diagnoseExampleProject("manuscript", { ...base, writerInitialized: false });
    expect(d.state).toBe("uninitialized");
  });

  it("always returns a non-empty cause AND next action for every state", () => {
    const cases: Array<[string, typeof base]> = [
      ["manuscript", { ...base, sectionCount: 1 }],
      ["manuscript", { ...base }],
      ["manuscript", { ...base, writerInitialized: false }],
      ["revision", { ...base, docTypeConfigured: false }],
    ];
    for (const [dt, opts] of cases) {
      const d = diagnoseExampleProject(dt, opts);
      expect(d.cause.length).toBeGreaterThan(0);
      expect(d.nextAction.length).toBeGreaterThan(0);
      expect(["auto-select", "no-manuscript", "uninitialized", "not-enabled"]).toContain(d.state);
    }
  });
});

describe("renderExampleState", () => {
  let container: HTMLElement;
  beforeEach(() => {
    container = makeContainer();
  });

  it("auto-select renders nothing (caller proceeds to populate + select)", () => {
    renderExampleState(container, diagnoseExampleProject("manuscript", { ...base, sectionCount: 1 }));
    expect(container.querySelector(".section-empty")).toBeNull();
  });

  it("no-manuscript renders the diagnosis with data-empty='no-manuscript'", () => {
    renderExampleState(container, diagnoseExampleProject("manuscript", base));
    expect(container.querySelector('[data-empty="no-manuscript"]')).not.toBeNull();
    expect(container.textContent).toMatch(/No manuscript is selected/i);
    expect(container.textContent).toMatch(/Next:/i);
  });

  it("uninitialized renders data-empty='uninitialized' + Initialize Writer action", () => {
    renderExampleState(container, diagnoseExampleProject("manuscript", { ...base, writerInitialized: false }));
    expect(container.querySelector('[data-empty="uninitialized"]')).not.toBeNull();
    expect(container.textContent).toMatch(/initialize the workspace/i);
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
    const hostile =
      '"><img src=x onerror="window.__xss_img=1">' +
      '<script>window.__xss_script=1</script>' +
      '<svg onload="window.__xss_svg=1">';
    const diagnosis = diagnoseExampleProject(hostile, { ...base }); // → no-manuscript (configured, 0 sections)

    renderExampleState(container, diagnosis);

    // No injected live elements exist in the rendered container.
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("svg")).toBeNull();
    // The hostile string is present as inert TEXT (textContent), verbatim.
    expect(container.textContent).toContain(hostile);
    // No side-effect globals were executed.
    const w = window as any;
    expect(w.__xss_img).toBeUndefined();
    expect(w.__xss_script).toBeUndefined();
    expect(w.__xss_svg).toBeUndefined();
  });

  it("nextAction payload is inert too (only the single 'Next:' label is markup)", () => {
    // Not-enabled state embeds the label in nextAction as well.
    const hostile = '"><b onload="window.__xss_next=1">pwned';
    const diagnosis = diagnoseExampleProject(hostile, {
      ...base,
      docTypeConfigured: false,
    }); // → not-enabled
    renderExampleState(container, diagnosis);
    expect(container.querySelector("b[onload]")).toBeNull();
    expect(container.textContent).toContain(hostile);
    expect((window as any).__xss_next).toBeUndefined();
  });

  it("still renders the expected structure for a benign no-manuscript state", () => {
    renderExampleState(container, diagnoseExampleProject("manuscript", base));
    expect(container.querySelector('[data-empty="no-manuscript"]')).not.toBeNull();
    expect(container.querySelector("strong")?.textContent).toBe("Next:");
  });
});
