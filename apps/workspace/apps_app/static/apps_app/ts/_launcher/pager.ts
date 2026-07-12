/**
 * Launcher pager — iPhone-home-style horizontal pages (mobile only).
 *
 * WHY THIS EXISTS (operator, real iPhone, 2026-07-13): the grid scrolled
 * VERTICALLY under the fixed bottom dock, so the last row of icons sat behind
 * it — measured at 56px of overlap on an iPhone 13 (dock top y=586, last tile
 * bottom y=642). Bottom padding alone is a losing game: it has to be re-tuned
 * for every dock height, safe-area inset and dynamic-toolbar state, and it
 * still leaves icons hidden the moment one more app is installed.
 *
 * Paging removes the failure mode STRUCTURALLY instead of padding around it:
 * the pages are sized to the space that is actually free ABOVE the dock, so a
 * tile can never land under it — for ANY number of apps. Overflow goes
 * sideways (swipe right for more), which is the iOS home screen the operator
 * asked for ("かさならないように右に右にと移動できるようにして任意の数のアプリに対応させて").
 *
 * Desktop (>767px) keeps the plain vertical grid — the dock is mobile-only, so
 * there is nothing to page around.
 */

// Columns per page. Matches the 4-col grid in launcher/mobile.css.
const COLS = 4;
// Never build a page shorter than this; below it, paging is worse than nothing.
const MIN_PAGE_HEIGHT = 200;
// Drag within this many px of an edge for EDGE_DWELL_MS to flip the page.
const EDGE_ZONE_PX = 44;
const EDGE_DWELL_MS = 500;

export class LauncherPager {
  private grid: HTMLElement;
  private dots: HTMLElement;
  private mq: MediaQueryList;
  private edgeTimer: number | null = null;
  private edgeDir: -1 | 1 | 0 = 0;

  constructor(grid: HTMLElement, dots: HTMLElement) {
    this.grid = grid;
    this.dots = dots;
    this.mq = window.matchMedia("(max-width: 767px)");
  }

  init(): void {
    this.apply();
    // Re-chunk when the viewport changes: a rotation or a dynamic-toolbar
    // resize changes how many rows fit, which changes the page count.
    const relayout = () => this.apply();
    this.mq.addEventListener("change", relayout);
    window.addEventListener("resize", relayout);
    window.addEventListener("orientationchange", relayout);
    this.grid.addEventListener("scroll", () => this.syncDots(), {
      passive: true,
    });
  }

  /** True while the grid is showing pages (i.e. mobile). */
  get paged(): boolean {
    return this.grid.classList.contains("launcher-grid--paged");
  }

  /** Every tile, in flat visual order, regardless of page. */
  private tiles(): HTMLElement[] {
    return Array.from(
      this.grid.querySelectorAll<HTMLElement>(".launcher-tile"),
    );
  }

  /** Build pages (mobile) or tear them down (desktop). */
  apply(): void {
    if (!this.mq.matches) {
      this.unpage();
      return;
    }
    this.page();
  }

  /** Flatten the pages back into a plain grid, preserving tile order. */
  private unpage(): void {
    if (!this.paged) return;
    const tiles = this.tiles();
    this.grid
      .querySelectorAll(".launcher-page")
      .forEach((page) => page.remove());
    tiles.forEach((t) => this.grid.appendChild(t));
    this.grid.classList.remove("launcher-grid--paged");
    this.grid.style.removeProperty("height");
    this.dots.hidden = true;
    this.dots.replaceChildren();
  }

  /**
   * Chunk the tiles into pages that fit the space above the dock.
   *
   * Height is MEASURED, not assumed: we take the gap between the top of the
   * grid and the top of the (fixed) dock. That self-corrects for the guest
   * banner, the safe-area inset and iOS's dynamic toolbar — the three things
   * that made a hard-coded padding wrong on a real device.
   */
  private page(): void {
    const tiles = this.tiles();
    if (!tiles.length) return;

    const perPage = COLS * this.rowsThatFit(tiles[0]);
    const pageCount = Math.max(1, Math.ceil(tiles.length / perPage));
    const scrollLeft = this.grid.scrollLeft;

    this.grid.classList.add("launcher-grid--paged");
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
    this.syncDots();
  }

  /**
   * How many tile rows fit ABOVE the dock.
   *
   * The dock is position:fixed and re-parented to <body>, so its rect is the
   * only honest measure of where the usable area ends. Falling back to the
   * viewport bottom keeps this working on the (desktop-width) pages that have
   * no dock at all.
   */
  private rowsThatFit(sample: HTMLElement): number {
    const gridTop = this.grid.getBoundingClientRect().top;
    const dock = document.querySelector<HTMLElement>(".launcher-dock");
    const floor =
      dock && dock.offsetParent !== null
        ? dock.getBoundingClientRect().top
        : window.innerHeight;
    const dotsRoom = this.dots.offsetHeight || 26;

    const available = Math.max(MIN_PAGE_HEIGHT, floor - gridTop - dotsRoom - 8);
    this.grid.style.height = `${available}px`;

    const rowGap = parseFloat(getComputedStyle(this.grid).rowGap) || 22;
    const tileH = sample.offsetHeight || 120;
    const rows = Math.floor((available + rowGap) / (tileH + rowGap));
    return Math.max(1, rows);
  }

  private buildDots(pageCount: number): void {
    this.dots.replaceChildren();
    this.dots.hidden = pageCount < 2;
    if (pageCount < 2) return;

    for (let i = 0; i < pageCount; i++) {
      const dot = document.createElement("button");
      dot.type = "button";
      dot.className = "launcher-dot";
      dot.setAttribute("aria-label", `Page ${i + 1} of ${pageCount}`);
      dot.addEventListener("click", () => this.goTo(i));
      this.dots.appendChild(dot);
    }
  }

  private get pageWidth(): number {
    return this.grid.clientWidth || 1;
  }

  private currentPage(): number {
    return Math.round(this.grid.scrollLeft / this.pageWidth);
  }

  private syncDots(): void {
    const active = this.currentPage();
    Array.from(this.dots.children).forEach((dot, i) => {
      dot.classList.toggle("active", i === active);
    });
  }

  goTo(index: number): void {
    this.grid.scrollTo({ left: index * this.pageWidth, behavior: "smooth" });
  }

  /**
   * Called on every drag move: hold a tile against the left/right edge and the
   * page turns, so a tile can be carried to any page (iOS does this too).
   * Anything other than a sustained hold in the edge zone cancels the flip.
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
      const last = this.grid.querySelectorAll(".launcher-page").length - 1;
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
   * pushes right — the same thing iOS does when you drop an icon onto a full
   * page. Tile ORDER is preserved: page() re-reads the tiles in DOM order.
   */
  rebalance(): void {
    if (!this.paged) return;
    this.page();
  }
}
