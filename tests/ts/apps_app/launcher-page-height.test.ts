/**
 * launcher page height — "Home keeps growing as I scroll" (operator iPhone,
 * 2026-09-15). Dev at 390px: grid 562px on 2 pages became 1436px on 1 page
 * after one scroll and one viewport-height change, because the grid top was
 * read relative to the viewport. These pin a scroll- and toolbar-independent
 * page height.
 */

import { describe, expect, it } from "vitest";

import {
  MIN_PAGE_HEIGHT,
  pageHeightFor,
  type PageHeightInput,
  type ViewportMemory,
} from "@apps_app/_launcher/page-height";

// Measured on dev at 390x844: grid top 109, dots 26.
function input(over: Partial<PageHeightInput> = {}): PageHeightInput {
  return {
    gridTop: 109,
    scrollY: 0,
    viewportHeight: 844,
    viewportWidth: 390,
    dotsRoom: 26,
    viewport: { width: 0, minHeight: 0 },
    ...over,
  };
}

describe("pageHeightFor", () => {
  it("fills the viewport and lets the fixed dock overlay the page", () => {
    expect(pageHeightFor(input())).toBe(844 - 109 - 26 - 8);
  });

  it("does not grow when the document is scrolled", () => {
    const viewport: ViewportMemory = { width: 0, minHeight: 0 };
    const top = pageHeightFor(input({ viewport }));
    const scrolled = pageHeightFor(
      input({ viewport, gridTop: 109 - 958, scrollY: 958 }),
    );
    expect(scrolled).toBe(top);
  });

  it("shrinks when the viewport gets shorter", () => {
    const viewport: ViewportMemory = { width: 0, minHeight: 0 };
    const tall = pageHeightFor(input({ viewport }));
    const short = pageHeightFor(
      input({ viewport, viewportHeight: 760 }),
    );
    expect(short).toBe(tall - 84);
  });

  it("stays at the short height when the iOS toolbar collapses again", () => {
    const viewport: ViewportMemory = { width: 0, minHeight: 0 };
    const short = pageHeightFor(
      input({ viewport, viewportHeight: 760 }),
    );
    const tallAgain = pageHeightFor(input({ viewport }));
    expect(tallAgain).toBe(short);
  });

  it("starts over when the width changes (rotation)", () => {
    const viewport: ViewportMemory = { width: 0, minHeight: 0 };
    pageHeightFor(input({ viewport, viewportHeight: 760 }));
    const rotated = pageHeightFor(
      input({
        viewport,
        viewportWidth: 844,
        viewportHeight: 900,
      }),
    );
    expect(rotated).toBe(900 - 109 - 26 - 8);
  });

  it("never builds a page shorter than the minimum", () => {
    expect(pageHeightFor(input({ gridTop: 700 }))).toBe(MIN_PAGE_HEIGHT);
  });

  it("floors at the viewport bottom", () => {
    expect(pageHeightFor(input())).toBe(844 - 109 - 26 - 8);
  });

  it("is stable across repeated scroll and resize cycles", () => {
    const viewport: ViewportMemory = { width: 0, minHeight: 0 };
    const heights = new Set<number>();
    for (let i = 0; i < 5; i++) {
      const vh = i % 2 ? 844 : 760;
      heights.add(
        pageHeightFor(
          input({
            viewport,
            viewportHeight: vh,
            scrollY: 300 * i,
            gridTop: 109 - 300 * i,
          }),
        ),
      );
    }
    expect([...heights]).toEqual([760 - 109 - 26 - 8]);
  });
});
