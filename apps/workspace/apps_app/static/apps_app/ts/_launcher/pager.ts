/**
 * Launcher pager — iPhone-home-style horizontal pages, at EVERY width.
 *
 * Paging keeps arbitrary app counts in predictable horizontal pages. The site
 * dock is a true fixed overlay: pages use the full viewport and render beneath
 * it rather than treating its current position as a layout boundary.
 *
 * 2026-09-14 (Home + dock redesign): the dock is now on every page at every
 * width, and the operator wants phone and desktop to be the same UI, so the
 * pager runs on desktop too. Touch swipes; desktop gets arrow buttons, the
 * trackpad's horizontal scroll, the arrow keys and clickable dots. CSS
 * scroll-snap does the actual paging (launcher/mobile.css).
 */

import { packGroups, planSignature } from "./group-pack";
import { pageHeightFor, type ViewportMemory } from "./page-height";
// Drag within this many px of an edge for EDGE_DWELL_MS to flip the page.
const EDGE_ZONE_PX = 44;
const EDGE_DWELL_MS = 500;

export interface PageLayoutInput {
  /** Pixels available for tile rows (grid top to viewport bottom, minus dots). */
  available: number;
  tileHeight: number;
  rowGap: number;
  cols: number;
  tileCount: number;
}

export interface PageLayout {
  rows: number;
  perPage: number;
  pageCount: number;
}

/**
 * How many rows fit, how many tiles that makes per page, and how many pages.
 * Pure: the class below measures the DOM and hands the numbers in.
 */
export function computePageLayout(input: PageLayoutInput): PageLayout {
  const tileHeight = input.tileHeight > 0 ? input.tileHeight : 120;
  const rowGap = Math.max(0, input.rowGap);
  const cols = Math.max(1, Math.floor(input.cols) || 1);
  const rows = Math.max(
    1,
    Math.floor((Math.max(0, input.available) + rowGap) / (tileHeight + rowGap)),
  );
  const perPage = rows * cols;
  const pageCount = Math.max(
    1,
    Math.ceil(Math.max(0, input.tileCount) / perPage),
  );
  return { rows, perPage, pageCount };
}

/**
 * The grid is 4 columns at EVERY width (operator 2026-09-14: the launcher
 * order is designed in rows of 4, one group per row; 6 columns interleaved
 * the groups). launcher/grid.css declares it as --launcher-cols; 4 is also
 * the fallback where the property cannot be read (jsdom, pre-layout).
 */
export const LAUNCHER_COLUMNS = 4;

export function readColumns(
  grid: HTMLElement,
  _viewportWidth?: number,
): number {
  const declared = parseInt(
    getComputedStyle(grid).getPropertyValue("--launcher-cols"),
    10,
  );
  if (Number.isFinite(declared) && declared > 0) return declared;
  return LAUNCHER_COLUMNS;
}

/**
 * Which page a horizontal scroll offset shows: the nearest snap point,
 * clamped to the pages that exist. Drives the active dot and the arrows, so
 * a rubber-band overscroll past either end (iOS) never lights a dot that is
 * not there.
 */
export function pageIndexFor(
  scrollLeft: number,
  pageWidth: number,
  pageCount: number,
): number {
  const last = Math.max(0, Math.floor(pageCount) - 1);
  if (!(pageWidth > 0)) return 0;
  const index = Math.round(scrollLeft / pageWidth);
  return Math.min(Math.max(0, index), last);
}

/** Smallest gap kept between the dock and either viewport edge. */
export const DOCK_MIN_GUTTER = 8;

export interface DockFrame {
  /** Dock width in px. */
  width: number;
  /** Viewport x of the dock's centre in px (the dock is translateX(-50%)). */
  center: number;
}

/**
 * The dock's frame on Home: the SAME left/right edges as the group panels
 * (operator, 2026-09-14, after the real iOS home screen, whose dock lines up
 * with the icon grid). Clamped so it never leaves the viewport.
 */
export function dockFrameFor(
  left: number,
  right: number,
  viewportWidth: number,
): DockFrame {
  const minLeft = DOCK_MIN_GUTTER;
  const maxRight = Math.max(minLeft, viewportWidth - DOCK_MIN_GUTTER);
  const l = Math.min(Math.max(left, minLeft), maxRight);
  const r = Math.max(Math.min(right, maxRight), l);
  return { width: r - l, center: (l + r) / 2 };
}

/** Below this width the arrows never show (matches launcher/mobile.css). */
export const ARROWS_MIN_WIDTH = 768;

/** Whether page arrows may be shown: wide viewport AND a fine, hovering pointer. */
export function arrowsAllowed(): boolean {
  if (window.innerWidth < ARROWS_MIN_WIDTH) return false;
  try {
    return window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  } catch {
    return false;
  }
}

export interface PagerControls {
  prev?: HTMLButtonElement | null;
  next?: HTMLButtonElement | null;
}

export class LauncherPager {
  private grid: HTMLElement;
  private dots: HTMLElement;
  private prev: HTMLButtonElement | null;
  private next: HTMLButtonElement | null;
  private edgeTimer: number | null = null;
  private edgeDir: -1 | 1 | 0 = 0;
  // Last computed page capacity, so a re-measure that changes nothing does not
  // rebuild the DOM (the ResizeObserver below can fire often).
  private lastSignature = "";
  private viewport: ViewportMemory = { width: 0, minHeight: 0 };
  private requestedPage: number | null = null;

  constructor(
    grid: HTMLElement,
    dots: HTMLElement,
    controls: PagerControls = {},
  ) {
    this.grid = grid;
    this.dots = dots;
    this.prev = controls.prev ?? null;
    this.next = controls.next ?? null;
  }

  init(): void {
    this.apply();
    this.syncFromHash(true);

    // MEASURE LATE, NOT EARLY. How much room a page gets is the gap between the
    // TOP OF THE GRID and the viewport floor — and the top depends on everything
    // stacked above it (banner, section head, web fonts). At DOMContentLoaded
    // none of that has settled, so re-measure once layout has happened, and
    // keep watching. apply() only rebuilds when the capacity really changed.
    requestAnimationFrame(() => this.apply());
    window.addEventListener("load", () => this.apply());

    if ("ResizeObserver" in window) {
      // Observe the CONTAINER, never the grid itself: apply() sets the grid's
      // height, which would feed straight back into the observer.
      const host = this.grid.parentElement;
      if (host) new ResizeObserver(() => this.apply()).observe(host);
    }

    const relayout = () => this.apply();
    window.addEventListener("resize", relayout);
    window.addEventListener("orientationchange", relayout);
    this.grid.addEventListener("scroll", () => {
      this.syncControls();
      const current = this.currentPage();
      if (this.requestedPage === null || current === this.requestedPage) {
        this.requestedPage = null;
        this.replaceHash(current);
      }
    }, { passive: true });
    window.addEventListener("hashchange", () => this.syncFromHash(false));

    this.prev?.addEventListener("click", () =>
      this.goTo(this.currentPage() - 1),
    );
    this.next?.addEventListener("click", () =>
      this.goTo(this.currentPage() + 1),
    );
    document.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      const target = e.target as HTMLElement | null;
      if (
        target?.closest(
          "input, textarea, select, [contenteditable], [data-site-dock], .launcher-popover",
        )
      ) {
        return;
      }
      if (this.pageCount() < 2) return;
      this.goTo(this.currentPage() + (e.key === "ArrowRight" ? 1 : -1));
    });
  }

  /** True while the grid is showing pages. */
  get paged(): boolean {
    return this.grid.classList.contains("launcher-grid--paged");
  }

  /**
   * Every grid CELL, in flat visual order, regardless of page: the tiles plus
   * the empty .launcher-slot cells that keep each group on its own row. Slots
   * count toward a page's capacity, so page boundaries stay on row boundaries.
   */
  private tiles(): HTMLElement[] {
    return Array.from(
      this.grid.querySelectorAll<HTMLElement>(".launcher-tile, .launcher-slot"),
    ).filter((cell) => !cell.closest("[data-launcher-fixed-page]"));
  }

  /** Gap between two bands on a page (launcher/mobile.css .launcher-page row-gap). */
  private pageGap(): string {
    const page = this.grid.querySelector<HTMLElement>(".launcher-page");
    return page ? getComputedStyle(page).rowGap : "12";
  }

  private pageCount(): number {
    return this.grid.querySelectorAll(".launcher-page").length;
  }

  /** Build (or refresh) the pages for the current viewport. */
  apply(): void {
    this.alignDock();
    this.page();
  }

  /**
   * Give the site dock the grid's left/right edges. The dock is fixed and
   * centred on the VIEWPORT while the grid is centred in the content column
   * (a sidebar rail can offset it), so only a measurement lines the two up at
   * every width. site-dock.css reads these properties; a dock the user dragged
   * away carries inline left/top, which win over the centre.
   */
  private alignDock(): void {
    const dock = document.querySelector<HTMLElement>(".site-dock");
    if (!dock) return;
    const rect = this.grid.getBoundingClientRect();
    if (!(rect.width > 0)) return;
    const frame = dockFrameFor(rect.left, rect.right, window.innerWidth);
    dock.style.setProperty("--site-dock-width", `${frame.width}px`);
    dock.style.setProperty("--site-dock-center", `${frame.center}px`);
  }

  /**
   * Chunk the tiles into pages that fit the viewport.
   *
   * `force` re-chunks even when the capacity is unchanged — rebalance() needs
   * that after a drop moved a tile between pages.
   */
  private page(force = false): void {
    const cells = this.tiles();
    if (!cells.length) return;
    const fixed = this.grid.querySelector<HTMLElement>("[data-launcher-fixed-page]");

    // Cells grouped by their band (Foundation / Work / System). A grid without
    // bands (tests, older markup) is one unlabelled group.
    const groups: { key: string; label: string; cells: HTMLElement[] }[] = [];
    cells.forEach((cell) => {
      const band = cell.closest<HTMLElement>(".launcher-group");
      const key = band?.dataset.group ?? "";
      const label = band?.getAttribute("aria-label") ?? "";
      const last = groups[groups.length - 1];
      if (last && last.key === key) last.cells.push(cell);
      else groups.push({ key, label, cells: [cell] });
    });

    const band = this.grid.querySelector<HTMLElement>(".launcher-group");
    const bandStyle = band ? getComputedStyle(band) : null;
    const gridStyle = getComputedStyle(this.grid);
    const rowGap =
      parseFloat(bandStyle?.rowGap ?? "") || parseFloat(gridStyle.rowGap) || 22;
    const plan = packGroups(
      groups.map((g) => ({
        key: g.key,
        label: g.label,
        count: g.cells.length,
      })),
      {
        available: this.availableHeight(),
        cols: readColumns(this.grid, window.innerWidth),
        // The TALLEST tile: a "Coming soon" tile carries an extra badge line.
        rowHeight: Math.max(
          0,
          ...Array.from(
            this.grid.querySelectorAll<HTMLElement>(".launcher-tile"),
          ).map((t) => t.offsetHeight),
        ),
        rowGap,
        bandPadding: bandStyle
          ? (parseFloat(bandStyle.paddingTop) || 0) +
            (parseFloat(bandStyle.paddingBottom) || 0)
          : 0,
        groupGap: parseFloat(this.pageGap()) || 0,
      },
    );
    const signature = `${fixed ? "fixed:" : ""}${planSignature(plan)}`;
    const scrollLeft = this.grid.scrollLeft;

    this.grid.classList.add("launcher-grid--paged");

    if (
      !force &&
      signature === this.lastSignature &&
      this.grid.querySelector(".launcher-page")
    ) {
      return;
    }
    this.lastSignature = signature;

    // Old CONTAINERS only (pages, bands); a flat grid's cells are direct
    // children too, and they are about to be moved, not removed.
    const cellSet = new Set<Element>(cells);
    const old = Array.from(this.grid.children).filter(
      (el) => el !== fixed && !cellSet.has(el),
    );
    plan.forEach((chunks) => {
      const page = document.createElement("div");
      page.className = "launcher-page";
      chunks.forEach((chunk) => {
        const source = groups.find((g) => g.key === chunk.key);
        if (!source) return;
        const bandEl = document.createElement("div");
        bandEl.className = "launcher-group";
        if (chunk.key) {
          bandEl.dataset.group = chunk.key;
          bandEl.setAttribute("role", "group");
          if (chunk.label) bandEl.setAttribute("aria-label", chunk.label);
        }
        source.cells.slice(chunk.start, chunk.end).forEach((c) => {
          bandEl.appendChild(c);
        });
        page.appendChild(bandEl);
      });
      this.grid.appendChild(page);
    });
    old.forEach((el) => el.remove());

    const pageCount = plan.length + (fixed ? 1 : 0);
    this.buildDots(pageCount);
    // Keep the reader where they were across a relayout (e.g. rotation).
    this.grid.scrollLeft = scrollLeft;
    this.syncControls();
  }

  /**
   * Pixels for tile rows to the viewport floor, and pin the grid to that height.
   * The fixed dock intentionally does not participate in this measurement.
   */
  private availableHeight(): number {
    const available = pageHeightFor({
      gridTop: this.grid.getBoundingClientRect().top,
      scrollY: window.scrollY || 0,
      viewportHeight: window.innerHeight,
      viewportWidth: window.innerWidth,
      dotsRoom: this.dots.offsetHeight || 26,
      viewport: this.viewport,
    });
    this.grid.style.height = `${available}px`;
    return available;
  }

  /**
   * One dot per page, the current one highlighted. Shown whenever the grid is
   * paged, even for a single page: the operator asked for dots under the grid
   * that show the current page, and a lone dot also tells a first-time user
   * that this screen is a page.
   */
  private buildDots(pageCount: number): void {
    this.dots.replaceChildren();
    this.dots.hidden = false;
    for (let i = 0; i < pageCount; i++) {
      const dot = document.createElement("button");
      dot.type = "button";
      dot.className = "launcher-dot";
      dot.setAttribute("role", "tab");
      const fixed = !!this.grid.querySelector("[data-launcher-fixed-page]");
      const name = fixed && i === 0 ? "Favorites" : `Home ${fixed ? i : i + 1}`;
      dot.setAttribute("aria-label", `${name}, page ${i + 1} of ${pageCount}`);
      dot.addEventListener("click", () => this.goTo(i));
      this.dots.appendChild(dot);
    }
  }

  private get pageWidth(): number {
    // The REAL page width, measured off a page, not assumed from the container:
    // scroll positions are multiples of whatever flex-basis the CSS gives a
    // page. jsdom reports offsetWidth 0 — fall back to clientWidth.
    const page = this.grid.querySelector<HTMLElement>(".launcher-page");
    return page?.offsetWidth || this.grid.clientWidth || 1;
  }

  currentPage(): number {
    return pageIndexFor(this.grid.scrollLeft, this.pageWidth, this.pageCount());
  }

  private syncControls(): void {
    const active = this.currentPage();
    const count = this.pageCount();
    Array.from(this.dots.children).forEach((dot, i) => {
      dot.classList.toggle("active", i === active);
      dot.setAttribute("aria-selected", i === active ? "true" : "false");
    });
    // Arrows are a DESKTOP affordance only: a fine hovering pointer on a wide
    // viewport. On a phone, swipe + dots is the whole UI, and an arrow that
    // shows there reads as a stray mark beside the dock (operator iPhone,
    // 2026-09-14). Kept in JS as well as CSS, so a stale stylesheet cannot
    // put them back.
    const multi = count > 1 && arrowsAllowed();
    if (this.prev) {
      this.prev.hidden = !multi;
      this.prev.disabled = active <= 0;
    }
    if (this.next) {
      this.next.hidden = !multi;
      this.next.disabled = active >= count - 1;
    }
  }

  private replaceHash(index: number): void {
    const hash = `#${index}`;
    if (window.location.hash !== hash) history.replaceState(null, "", hash);
  }

  private syncFromHash(initial: boolean): void {
    const count = this.pageCount();
    if (!count) return;
    const raw = window.location.hash.slice(1);
    const parsed = /^\d+$/.test(raw) ? Number(raw) : NaN;
    const fallback = this.grid.querySelector("[data-launcher-fixed-page]") ? 1 : 0;
    const target = Math.min(
      Math.max(0, Number.isFinite(parsed) ? parsed : fallback),
      count - 1,
    );
    this.replaceHash(target);
    this.requestedPage = target;
    this.scrollToPage(target, initial ? "auto" : "smooth");
    if (this.currentPage() === target) this.requestedPage = null;
    this.syncControls();
  }

  private scrollToPage(index: number, behavior: ScrollBehavior): void {
    const left = index * this.pageWidth;
    if (typeof this.grid.scrollTo === "function") this.grid.scrollTo({ left, behavior });
    else this.grid.scrollLeft = left;
  }

  goTo(index: number): void {
    const last = Math.max(0, this.pageCount() - 1);
    const target = Math.min(Math.max(0, index), last);
    if (window.location.hash !== `#${target}`) window.location.hash = String(target);
    this.requestedPage = target;
    this.scrollToPage(target, "smooth");
    if (this.currentPage() === target) this.requestedPage = null;
    this.syncControls();
  }

  /**
   * Called on every drag move: hold a tile against the left/right edge and the
   * page turns, so a tile can be carried to any page (iOS does this too).
   */
  edgeTurn(clientX: number): void {
    if (!this.paged) return;
    const rect = this.grid.getBoundingClientRect();
    const dir: -1 | 1 | 0 =
      clientX < rect.left + EDGE_ZONE_PX
        ? -1
        : clientX > rect.right - EDGE_ZONE_PX
          ? 1
          : 0;

    if (dir === 0) {
      this.cancelEdgeTurn();
      return;
    }
    if (dir === this.edgeDir) return; // already counting down toward this edge

    this.cancelEdgeTurn();
    this.edgeDir = dir;
    this.edgeTimer = window.setTimeout(() => {
      const next = this.currentPage() + dir;
      const last = this.pageCount() - 1;
      if (next >= 0 && next <= last) this.goTo(next);
      this.edgeDir = 0;
      this.edgeTimer = null;
    }, EDGE_DWELL_MS);
  }

  cancelEdgeTurn(): void {
    if (this.edgeTimer !== null) {
      clearTimeout(this.edgeTimer);
      this.edgeTimer = null;
    }
    this.edgeDir = 0;
  }

  /**
   * After a drop, a page can hold one tile too many (it was dragged in from a
   * neighbour). Re-chunk so every page is exactly full again and the overflow
   * pushes right. Tile ORDER is preserved: page() re-reads tiles in DOM order.
   */
  rebalance(): void {
    if (!this.paged) return;
    this.page(true);
  }
}
