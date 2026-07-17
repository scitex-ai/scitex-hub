/**
 * launcher pager — "icons hide under the dock" regression.
 *
 * Field bug (operator, real iPhone, 2026-07-13): the launcher grid scrolled
 * VERTICALLY under the fixed bottom dock, so the last row of app icons sat
 * behind it. Reproduced and measured in a 390x664 mobile viewport against live
 * prod: dock top y=586, last tile bottom y=642 — 56px of icons underneath the
 * dock, labels unreadable.
 *
 * The fix is structural, not cosmetic: LauncherPager sizes pages to the space
 * that is actually free ABOVE the dock and chunks the tiles into horizontal
 * pages, so no tile can land under the dock FOR ANY NUMBER OF APPS. That last
 * clause is the whole point (the operator asked for "任意の数のアプリに対応"),
 * so it is what these tests assert — over a range of app counts, not one.
 *
 * jsdom has no layout engine: getBoundingClientRect returns zeros and
 * offsetHeight is 0. The pager reads both to decide how many rows fit, so the
 * tests SUPPLY that geometry (a real dock rect, real tile heights) and let the
 * actual code run against it. No behaviour of the code under test is stubbed.
 */

import { beforeEach, describe, expect, it } from "vitest";

import { LauncherPager } from "@apps_app/_launcher/pager";

// A 390x664 iPhone-13 visible viewport, matching the reproduction above.
const VIEWPORT_H = 664;
const DOCK_TOP = 586;
const GRID_TOP = 240; // below the guest banner + "ALL APPS" head
const TILE_H = 120;
const ROW_GAP = 22;
const DOTS_H = 26;

interface Harness {
  grid: HTMLElement;
  dots: HTMLElement;
  pager: LauncherPager;
}

function build(tileCount: number, dockTop = DOCK_TOP): Harness {
  document.body.innerHTML = "";
  window.innerHeight = VIEWPORT_H;

  const dock = document.createElement("nav");
  dock.className = "launcher-dock";
  dock.getBoundingClientRect = () => ({ top: dockTop }) as DOMRect;
  // offsetParent is null for display:none in a real browser; jsdom always
  // reports null, so force a truthy value — the pager uses it to tell a
  // present dock (mobile) from an absent one (desktop).
  Object.defineProperty(dock, "offsetParent", { value: document.body });
  document.body.appendChild(dock);

  const grid = document.createElement("div");
  grid.className = "launcher-grid";
  grid.id = "launcher-grid";
  grid.getBoundingClientRect = () => ({ top: GRID_TOP }) as DOMRect;
  Object.defineProperty(grid, "clientWidth", { value: 390 });

  for (let i = 0; i < tileCount; i++) {
    const tile = document.createElement("a");
    tile.className = "launcher-tile";
    tile.dataset.module = `app-${i}`;
    Object.defineProperty(tile, "offsetHeight", { value: TILE_H });
    grid.appendChild(tile);
  }
  document.body.appendChild(grid);

  const dots = document.createElement("div");
  dots.className = "launcher-dots";
  dots.id = "launcher-dots";
  dots.hidden = true;
  Object.defineProperty(dots, "offsetHeight", { value: DOTS_H });
  document.body.appendChild(dots);

  return { grid, dots, pager: new LauncherPager(grid, dots) };
}

/** The pager reads row-gap off the computed style; jsdom needs it declared. */
function styleGap(grid: HTMLElement): void {
  const sheet = document.createElement("style");
  sheet.textContent = `#launcher-grid { row-gap: ${ROW_GAP}px; }`;
  document.head.appendChild(sheet);
  void grid;
}

// A real MediaQueryList is LIVE — the pager holds one from construction and
// relies on its `matches` updating when the viewport crosses the breakpoint.
// So the stub must be live too: back `matches` with a getter over a mutable
// flag. (A plain object frozen at construction time would make the pager look
// broken on resize when it is not.)
let mobile = true;

function setMobile(isMobile: boolean): void {
  mobile = isMobile;
}

window.matchMedia = ((q: string) =>
  ({
    get matches() {
      return q.includes("max-width: 767px") ? mobile : false;
    },
    media: q,
    addEventListener: () => {},
    removeEventListener: () => {},
  }) as unknown as MediaQueryList) as typeof window.matchMedia;

function tileOrder(grid: HTMLElement): string[] {
  return Array.from(grid.querySelectorAll<HTMLElement>(".launcher-tile")).map(
    (t) => t.dataset.module || "",
  );
}

describe("LauncherPager", () => {
  beforeEach(() => {
    document.head.innerHTML = "";
    setMobile(true);
  });

  it("re-measures after a LATE layout instead of trusting the first reading", () => {
    // THE BUG THIS PINS (shipped to prod, 2026-07-13, and it put the icons
    // straight back under the dock):
    //
    // Page capacity is the gap between the top of the grid and the dock. But
    // the grid's top depends on everything above it — the guest banner, the
    // section head, the web fonts — and at DOMContentLoaded none of that has
    // laid out. So the first measurement saw the grid near the header, thought
    // it had ~430px of room instead of ~200px, and packed THREE rows into a
    // two-row gap. Live prod after that deploy: dock top 586, deepest tile 642
    // — the exact 56px overlap the pager existed to remove.
    //
    // The pager must therefore converge on the SETTLED layout, not the first
    // reading it happens to get.
    // NOTE this drives init(), not apply(). apply() always re-measures — it
    // did in the broken version too. The defect was that nothing ever CALLED it
    // again once the layout settled, so init() has to subscribe to that. Firing
    // the real `load` event is what makes this test fail against the old code.
    const { grid, pager } = build(12);
    styleGap(grid);

    let gridTop = 120; // pre-layout: the banner has not rendered yet
    grid.getBoundingClientRect = () => ({ top: gridTop }) as DOMRect;

    const perPage = () =>
      grid
        .querySelectorAll(".launcher-page")[0]
        .querySelectorAll(".launcher-tile").length;

    pager.init(); // measures the pre-layout geometry, as the browser would
    const early = perPage();

    gridTop = GRID_TOP; // the banner lays out; the grid is pushed down the page
    window.dispatchEvent(new Event("load")); // ...and the browser says so

    const late = perPage();

    // Less room => fewer tiles per page. In the shipped-and-broken version the
    // pager never heard about the settled layout, so this stayed at `early` and
    // the extra row rendered under the dock.
    expect(late).toBeLessThan(early);
    // And the settled page really does clear the dock.
    expect(GRID_TOP + parseFloat(grid.style.height)).toBeLessThanOrEqual(
      DOCK_TOP,
    );
  });

  it("keeps EVERY tile above the dock, for any number of apps", () => {
    // The operator's ask was "任意の数のアプリに対応" — so sweep app counts
    // rather than pinning the one that happened to be installed that day.
    for (const count of [1, 4, 8, 12, 13, 40, 97]) {
      const { grid, dots, pager } = build(count);
      styleGap(grid);
      pager.apply();

      const height = parseFloat(grid.style.height);
      expect(height).toBeGreaterThan(0);

      // A page is laid out from the top of the grid downward, so the deepest
      // pixel any tile can reach is gridTop + the grid's own height. That must
      // clear the dock — this is the exact inequality that failed on prod
      // (642 > 586).
      expect(GRID_TOP + height).toBeLessThanOrEqual(DOCK_TOP);

      // ...and every tile really is inside a page, not loose in the scroller.
      const loose = Array.from(grid.children).filter(
        (c) => !c.classList.contains("launcher-page"),
      );
      expect(loose).toHaveLength(0);
      expect(tileOrder(grid)).toHaveLength(count);
      void dots;
    }
  });

  it("chunks tiles into pages without reordering them", () => {
    const { grid, pager } = build(12);
    styleGap(grid);
    const before = tileOrder(grid);

    pager.apply();

    // Order is the launcher's persisted state — paging must never disturb it.
    expect(tileOrder(grid)).toEqual(before);

    const pages = grid.querySelectorAll(".launcher-page");
    expect(pages.length).toBeGreaterThan(1); // 12 tiles cannot fit one screen

    // Pages fill in order: page 1 is full before page 2 gets anything.
    const perPage = pages[0].querySelectorAll(".launcher-tile").length;
    expect(perPage).toBeGreaterThan(0);
    for (let i = 0; i < pages.length - 1; i++) {
      expect(pages[i].querySelectorAll(".launcher-tile")).toHaveLength(perPage);
    }
  });

  it("shows page dots only when there is more than one page", () => {
    const many = build(12);
    styleGap(many.grid);
    many.pager.apply();
    expect(many.dots.hidden).toBe(false);
    expect(many.dots.children.length).toBe(
      many.grid.querySelectorAll(".launcher-page").length,
    );

    // A single page needs no dots — a lone dot says nothing and steals the
    // vertical space we just fought to give back to the icons.
    const few = build(2);
    styleGap(few.grid);
    few.pager.apply();
    expect(few.dots.hidden).toBe(true);
  });

  it("tears the pages down on desktop, preserving order", () => {
    const { grid, dots, pager } = build(12);
    styleGap(grid);
    const before = tileOrder(grid);

    pager.apply(); // mobile → paged
    expect(pager.paged).toBe(true);

    setMobile(false);
    pager.apply(); // desktop → flat grid again

    expect(pager.paged).toBe(false);
    expect(grid.querySelectorAll(".launcher-page")).toHaveLength(0);
    expect(tileOrder(grid)).toEqual(before);
    // The explicit height was a paging artefact; the desktop grid must not
    // inherit it or it would clip the vertical list.
    expect(grid.style.height).toBe("");
    expect(dots.hidden).toBe(true);
  });

  it("scrolls by the REAL page width when pages peek (flex-basis < 100%)", () => {
    // The peek affordance (mobile.css) narrows every page to 88% when there
    // are 2+ pages so the next page's edge shows — the visible hint that the
    // grid scrolls sideways (operator: the paging was invisible). Scroll
    // positions are then multiples of the PAGE width, not the container's;
    // the old pageWidth (clientWidth) would drift one-eighth of a page per
    // page and land the dots on the wrong index.
    const { grid, pager } = build(12);
    styleGap(grid);
    pager.apply();

    // Supply the peeked page geometry jsdom cannot compute: 88% of 390.
    const firstPage = grid.querySelector<HTMLElement>(".launcher-page");
    expect(firstPage).not.toBeNull();
    Object.defineProperty(firstPage as HTMLElement, "offsetWidth", {
      value: 343,
    });

    // Recording stand-in for the scroller jsdom does not implement.
    let scrolledTo = -1;
    grid.scrollTo = ((opts: ScrollToOptions) => {
      scrolledTo = opts.left ?? -1;
    }) as typeof grid.scrollTo;

    pager.goTo(2);

    // 2 pages x 343px, NOT 2 x 390 (the container width).
    expect(scrolledTo).toBe(686);
  });

  it("falls back to the container width when page geometry is unmeasured", () => {
    // jsdom (and a not-yet-laid-out browser frame) reports offsetWidth 0;
    // the scroller must then behave exactly as before the peek existed.
    const { grid, pager } = build(12);
    styleGap(grid);
    pager.apply();

    let scrolledTo = -1;
    grid.scrollTo = ((opts: ScrollToOptions) => {
      scrolledTo = opts.left ?? -1;
    }) as typeof grid.scrollTo;

    pager.goTo(1);

    expect(scrolledTo).toBe(390); // build() pins clientWidth at 390
  });

  it("re-chunks after a drop so an over-full page pushes tiles right", () => {
    const { grid, pager } = build(12);
    styleGap(grid);
    pager.apply();

    const pages = () =>
      Array.from(grid.querySelectorAll<HTMLElement>(".launcher-page"));
    const perPage = pages()[0].querySelectorAll(".launcher-tile").length;

    // Simulate a cross-page drop: the drag code inserts into the page of the
    // tile it is over, which can leave that page one over capacity.
    const lastPage = pages()[pages().length - 1];
    const carried = lastPage.querySelector<HTMLElement>(".launcher-tile");
    expect(carried).not.toBeNull();
    pages()[0].appendChild(carried as HTMLElement);
    expect(pages()[0].querySelectorAll(".launcher-tile")).toHaveLength(
      perPage + 1,
    );

    pager.rebalance();

    expect(pages()[0].querySelectorAll(".launcher-tile")).toHaveLength(perPage);
    // Nothing was lost in the reflow.
    expect(tileOrder(grid)).toHaveLength(12);
  });
});
