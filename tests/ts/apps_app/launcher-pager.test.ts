/**
 * Launcher pager geometry and navigation.
 *
 * The fixed site dock is a true overlay. Pager capacity uses the viewport
 * floor regardless of dock geometry, while focus scroll margins keep a
 * keyboard-selected terminal tile reachable.
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

function build(tileCount: number): Harness {
  document.body.innerHTML = "";
  window.innerHeight = VIEWPORT_H;
  // jsdom cannot resolve the --launcher-cols custom property, so the pager
  // falls back to the viewport-width breakpoints: 390px = 4 columns.
  window.innerWidth = 390;

  const dock = document.createElement("nav");
  dock.className = "site-dock";
  dock.getBoundingClientRect = () => ({ top: DOCK_TOP, height: 64 }) as DOMRect;
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
      if (q.includes("max-width: 767px")) return mobile;
      // Desktop = a fine hovering pointer; the phone fixture is touch.
      if (q.includes("pointer: fine")) return !mobile;
      return false;
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
    history.replaceState(null, "", "/apps/");
  });

  it("uses zero-based canonical hashes with Favorites before Home", () => {
    const { grid, dots } = build(12);
    styleGap(grid);
    const favorites = document.createElement("div");
    favorites.className = "launcher-page launcher-page--favorites";
    favorites.dataset.launcherFixedPage = "favorites";
    grid.prepend(favorites);
    history.replaceState(null, "", "/apps/#1");
    let scrolledTo = -1;
    grid.scrollTo = ((opts: ScrollToOptions) => {
      scrolledTo = opts.left ?? -1;
      grid.scrollLeft = scrolledTo;
    }) as typeof grid.scrollTo;
    const pager = new LauncherPager(grid, dots);

    pager.init();

    expect(grid.querySelectorAll(".launcher-page")[0]).toBe(favorites);
    expect(scrolledTo).toBe(390);
    expect(window.location.hash).toBe("#1");
    expect(dots.children[0].getAttribute("aria-label")).toContain("Favorites");
    expect(dots.children[1].getAttribute("aria-label")).toContain("Home");
  });

  it("keeps arrows, swipe, hashchange, and invalid initial hashes synchronized", () => {
    const { grid, dots } = build(40);
    styleGap(grid);
    const favorites = document.createElement("div");
    favorites.className = "launcher-page launcher-page--favorites";
    favorites.dataset.launcherFixedPage = "favorites";
    grid.prepend(favorites);
    history.replaceState(null, "", "/apps/#favorite");
    grid.scrollTo = ((opts: ScrollToOptions) => {
      grid.scrollLeft = opts.left ?? 0;
    }) as typeof grid.scrollTo;
    const pager = new LauncherPager(grid, dots);

    pager.init();
    expect(window.location.hash).toBe("#1");
    expect(grid.scrollLeft).toBe(390);

    pager.goTo(2);
    expect(window.location.hash).toBe("#2");
    expect(grid.scrollLeft).toBe(780);

    grid.scrollLeft = 0;
    grid.dispatchEvent(new Event("scroll"));
    expect(window.location.hash).toBe("#0");

    history.replaceState(null, "", "/apps/#1");
    window.dispatchEvent(new HashChangeEvent("hashchange"));
    expect(grid.scrollLeft).toBe(390);
  });

  it("re-measures after a LATE layout instead of trusting the first reading", () => {
    // THE BUG THIS PINS (shipped to prod, 2026-07-13, and it put the icons
    // straight back under the dock):
    //
    // Page capacity is the gap between the top of the grid and the viewport.
    // The grid's top depends on everything above it — the guest banner, the
    // section head, the web fonts — and at DOMContentLoaded none of that has
    // laid out. The pager must converge on the settled layout, not the first
    // reading it happens to get.
    const { grid, pager } = build(20);
    styleGap(grid);

    let gridTop = 120; // pre-layout: the banner has not rendered yet
    grid.getBoundingClientRect = () => ({ top: gridTop }) as DOMRect;

    const perPage = () =>
      grid
        .querySelectorAll(".launcher-page")[0]
        .querySelectorAll(".launcher-tile").length;

    pager.init(); // measures the pre-layout geometry, as the browser would
    const earlyHeight = parseFloat(grid.style.height);
    expect(perPage()).toBeGreaterThan(0);

    gridTop = GRID_TOP; // the banner lays out; the grid is pushed down the page
    pager.apply();

    const lateHeight = parseFloat(grid.style.height);

    // The settled position, not an early pre-layout reading, controls the
    // viewport-based page height.
    expect(lateHeight).toBeLessThan(earlyHeight);
    // The page uses the viewport floor and therefore extends under the dock.
    expect(GRID_TOP + parseFloat(grid.style.height)).toBeLessThanOrEqual(
      VIEWPORT_H,
    );
    expect(GRID_TOP + parseFloat(grid.style.height)).toBeGreaterThan(DOCK_TOP);
  });

  it("uses the full viewport under the dock for any number of apps", () => {
    // The operator's ask was "任意の数のアプリに対応" — so sweep app counts
    // rather than pinning the one that happened to be installed that day.
    for (const count of [1, 4, 8, 12, 13, 40, 97]) {
      const { grid, dots, pager } = build(count);
      styleGap(grid);
      pager.apply();

      const height = parseFloat(grid.style.height);
      expect(height).toBeGreaterThan(0);

      expect(GRID_TOP + height).toBeLessThanOrEqual(VIEWPORT_H);
      expect(GRID_TOP + height).toBeGreaterThan(DOCK_TOP);

      // ...and every tile really is inside a page, not loose in the scroller.
      const loose = Array.from(grid.children).filter(
        (c) => !c.classList.contains("launcher-page"),
      );
      expect(loose).toHaveLength(0);
      expect(tileOrder(grid)).toHaveLength(count);
      void dots;
    }
  });

  it("does not let fixed dock geometry shorten the page", () => {
    const { grid, pager } = build(12);
    styleGap(grid);
    const dock = document.querySelector<HTMLElement>(".site-dock");
    expect(dock!.offsetParent).toBeNull();

    pager.apply();

    expect(GRID_TOP + parseFloat(grid.style.height)).toBeLessThanOrEqual(
      VIEWPORT_H,
    );
    expect(GRID_TOP + parseFloat(grid.style.height)).toBeGreaterThan(DOCK_TOP);
  });

  it("keeps the same page height when the dock disappears", () => {
    const { grid, pager } = build(8);
    styleGap(grid);
    const dock = document.querySelector<HTMLElement>(".site-dock")!;

    pager.apply();
    const withDock = parseFloat(grid.style.height);
    dock.getBoundingClientRect = () => ({ top: 0, height: 0 }) as DOMRect;

    pager.apply();

    expect(parseFloat(grid.style.height)).toBe(withDock);
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

  it("shows one dot per page, even when everything fits on one page", () => {
    // Operator, 2026-09-14: dots under the grid show the current page. A
    // single page still shows its one dot, so the Home screen reads as a page.
    const many = build(12);
    styleGap(many.grid);
    many.pager.apply();
    expect(many.dots.hidden).toBe(false);
    expect(many.dots.children.length).toBe(
      many.grid.querySelectorAll(".launcher-page").length,
    );

    const few = build(2);
    styleGap(few.grid);
    few.pager.apply();
    expect([few.dots.hidden, few.dots.children.length]).toEqual([false, 1]);
  });

  it("pages on desktop too — phone and desktop are the same UI", () => {
    // The pager used to tear its pages down above 767px. Since 2026-09-14 the
    // dock is on every page at every width, so the desktop grid pages too.
    const { grid, pager } = build(12);
    styleGap(grid);
    const before = tileOrder(grid);
    setMobile(false);

    pager.apply();

    expect(pager.paged).toBe(true);
    expect(tileOrder(grid)).toEqual(before);
  });

  it("keeps page height stable when the dock is moved", () => {
    const { grid, pager } = build(8);
    styleGap(grid);

    pager.apply();
    const dockedHeight = parseFloat(grid.style.height);
    document.querySelector(".site-dock")!.classList.add("site-dock--floating");

    pager.apply();

    expect(parseFloat(grid.style.height)).toBe(dockedHeight);
  });

  it("keeps the page arrows hidden on a phone, even with several pages", () => {
    // Operator iPhone, 2026-09-14: arrows showed as stray white boxes above the
    // grid and beside the dock. Swipe + dots is the phone UI.
    const { grid, dots } = build(40); // 390px wide, touch (setMobile(true))
    styleGap(grid);
    const prev = document.createElement("button");
    const next = document.createElement("button");
    const pager = new LauncherPager(grid, dots, { prev, next });

    pager.init();

    expect([prev.hidden, next.hidden]).toEqual([true, true]);
  });

  it("enables the desktop arrows only when there is somewhere to go", () => {
    const { grid, dots } = build(40);
    window.innerWidth = 1440;
    setMobile(false); // fine hovering pointer
    styleGap(grid);
    const prev = document.createElement("button");
    const next = document.createElement("button");
    const pager = new LauncherPager(grid, dots, { prev, next });

    pager.init();

    // On the first page of several: arrows shown, Back-arrow disabled.
    expect([prev.hidden, prev.disabled, next.hidden, next.disabled]).toEqual([
      false,
      true,
      false,
      false,
    ]);
  });

  it("scrolls by the MEASURED page width, not the container's", () => {
    // Pages are full-width today, but the scroller must key off the page's
    // real offsetWidth, never assume the container width: the retired 88%
    // "peek" basis (removed 2026-07-18 — it clipped the rightmost column
    // mid-icon) proved the two can drift, and when they did the old
    // clientWidth maths drifted one-eighth of a page per page and landed
    // the dots on the wrong index. Measuring keeps the pager correct under
    // ANY future flex-basis change.
    // 20 tiles = three pages, so goTo(2) is a real page (goTo clamps).
    const { grid, pager } = build(20);
    styleGap(grid);
    pager.apply();

    // Supply a page geometry narrower than the container (the drift case
    // jsdom cannot compute itself): 88% of 390.
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
    // the scroller must then fall back to the container width.
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
    const { grid, pager } = build(20);
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

    expect(pages()).toHaveLength(2);
    expect(pages()[0].querySelectorAll(".launcher-tile").length).toBeLessThan(20);
    // Nothing was lost in the reflow.
    expect(tileOrder(grid)).toHaveLength(20);
  });
});
