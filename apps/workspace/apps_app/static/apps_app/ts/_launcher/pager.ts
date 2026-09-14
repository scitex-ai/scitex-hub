/**
 * Launcher pager — iPhone-home-style horizontal pages, at EVERY width.
 *
 * WHY THIS EXISTS (operator, real iPhone, 2026-07-13): the grid scrolled
 * VERTICALLY under the fixed bottom dock, so the last row of icons sat behind
 * it — measured at 56px of overlap on an iPhone 13 (dock top y=586, last tile
 * bottom y=642). Bottom padding alone is a losing game: it has to be re-tuned
 * for every dock height, safe-area inset and dynamic-toolbar state, and it
 * still leaves icons hidden the moment one more app is installed.
 *
 * Paging removes the failure mode STRUCTURALLY: pages are sized to the space
 * actually free ABOVE the dock, so a tile can never land under it — for ANY
 * number of apps. Overflow goes sideways.
 *
 * 2026-09-14 (Home + dock redesign): the dock is now on every page at every
 * width, and the operator wants phone and desktop to be the same UI, so the
 * pager runs on desktop too. Touch swipes; desktop gets arrow buttons, the
 * trackpad's horizontal scroll, the arrow keys and clickable dots. CSS
 * scroll-snap does the actual paging (launcher/mobile.css).
 */

// Never build a page shorter than this; below it, paging is worse than nothing.
const MIN_PAGE_HEIGHT = 200;
// Drag within this many px of an edge for EDGE_DWELL_MS to flip the page.
const EDGE_ZONE_PX = 44;
const EDGE_DWELL_MS = 500;

export interface PageLayoutInput {
  /** Pixels available for tile rows (grid top to dock top, minus the dots). */
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
 * Column count for the current viewport. launcher/grid.css declares it as
 * --launcher-cols (6, 5 at <=960px, 4 at <=640px); the same breakpoints are
 * the fallback where the custom property cannot be read (jsdom).
 */
export function readColumns(grid: HTMLElement, viewportWidth: number): number {
  const declared = parseInt(
    getComputedStyle(grid).getPropertyValue("--launcher-cols"),
    10,
  );
  if (Number.isFinite(declared) && declared > 0) return declared;
  if (viewportWidth <= 640) return 4;
  if (viewportWidth <= 960) return 5;
  return 6;
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
  private lastPerPage = 0;
  private lastPageCount = 0;

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

    // MEASURE LATE, NOT EARLY. How much room a page gets is the gap between the
    // TOP OF THE GRID and the dock — and the grid's top depends on everything
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
    this.grid.addEventListener("scroll", () => this.syncControls(), {
      passive: true,
    });

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

  /** Every tile, in flat visual order, regardless of page. */
  private tiles(): HTMLElement[] {
    return Array.from(
      this.grid.querySelectorAll<HTMLElement>(".launcher-tile"),
    );
  }

  private pageCount(): number {
    return this.grid.querySelectorAll(".launcher-page").length;
  }

  /** Build (or refresh) the pages for the current viewport. */
  apply(): void {
    this.page();
  }

  /**
   * Chunk the tiles into pages that fit the space above the dock.
   *
   * `force` re-chunks even when the capacity is unchanged — rebalance() needs
   * that after a drop moved a tile between pages.
   */
  private page(force = false): void {
    const tiles = this.tiles();
    if (!tiles.length) return;

    const { perPage, pageCount } = computePageLayout({
      available: this.availableHeight(),
      tileHeight: tiles[0].offsetHeight,
      rowGap: parseFloat(getComputedStyle(this.grid).rowGap) || 22,
      cols: readColumns(this.grid, window.innerWidth),
      tileCount: tiles.length,
    });
    const scrollLeft = this.grid.scrollLeft;

    this.grid.classList.add("launcher-grid--paged");

    if (
      !force &&
      perPage === this.lastPerPage &&
      pageCount === this.lastPageCount &&
      this.grid.querySelector(".launcher-page")
    ) {
      return;
    }
    this.lastPerPage = perPage;
    this.lastPageCount = pageCount;

    this.grid
      .querySelectorAll(".launcher-page")
      .forEach((page) => page.remove());

    for (let i = 0; i < pageCount; i++) {
      const page = document.createElement("div");
      page.className = "launcher-page";
      tiles.slice(i * perPage, (i + 1) * perPage).forEach((t) => {
        page.appendChild(t);
      });
      this.grid.appendChild(page);
    }

    this.buildDots(pageCount);
    // Keep the reader where they were across a relayout (e.g. rotation).
    this.grid.scrollLeft = scrollLeft;
    this.syncControls();
  }

  /**
   * Pixels for tile rows ABOVE the dock, and pin the grid to that height.
   *
   * The dock is position:fixed on <body>, so its rect is the only honest
   * measure of where the usable area ends. Presence comes from the RECT, never
   * offsetParent (null BY SPEC for position:fixed, which once made the pager
   * read the dock as absent in every real browser). A dock the user dragged
   * off the bottom (.site-dock--floating) no longer bounds the page, and a
   * display:none dock measures 0x0: both fall back to the viewport bottom.
   */
  private availableHeight(): number {
    const gridTop = this.grid.getBoundingClientRect().top;
    const dock = document.querySelector<HTMLElement>(".site-dock");
    const dockRect =
      dock && !dock.classList.contains("site-dock--floating")
        ? dock.getBoundingClientRect()
        : null;
    const floor =
      dockRect && dockRect.height > 0 ? dockRect.top : window.innerHeight;
    const dotsRoom = this.dots.offsetHeight || 26;

    const available = Math.max(MIN_PAGE_HEIGHT, floor - gridTop - dotsRoom - 8);
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
      dot.setAttribute("aria-label", `Page ${i + 1} of ${pageCount}`);
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
    return Math.round(this.grid.scrollLeft / this.pageWidth);
  }

  private syncControls(): void {
    const active = this.currentPage();
    const count = this.pageCount();
    Array.from(this.dots.children).forEach((dot, i) => {
      dot.classList.toggle("active", i === active);
      dot.setAttribute("aria-selected", i === active ? "true" : "false");
    });
    const multi = count > 1;
    if (this.prev) {
      this.prev.hidden = !multi;
      this.prev.disabled = active <= 0;
    }
    if (this.next) {
      this.next.hidden = !multi;
      this.next.disabled = active >= count - 1;
    }
  }

  goTo(index: number): void {
    const last = Math.max(0, this.pageCount() - 1);
    const target = Math.min(Math.max(0, index), last);
    this.grid.scrollTo({ left: target * this.pageWidth, behavior: "smooth" });
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
