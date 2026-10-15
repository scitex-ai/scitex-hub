/**
 * How tall a launcher page may be — pure geometry, no DOM.
 *
 * Operator iPhone, 2026-09-15: the grid top was read relative to the VIEWPORT,
 * so once Home was scrolled it went negative, and every re-measure (iOS fires
 * resize as its toolbar collapses) grew the grid by the scroll offset: page 2
 * collapsed into page 1 and the document kept getting taller under the finger.
 * Measured on dev at 390px: grid 562px (2 pages) became 1436px (1 page) after
 * one scroll + one viewport-height change.
 *
 * So the page is sized for the document scrolled to the TOP and for the
 * SHORTEST viewport seen at this width (an `svh`): the result no longer
 * depends on scroll position or toolbar state. A width change (rotation)
 * starts over.
 */

// Never build a page shorter than this; below it, paging is worse than nothing.
export const MIN_PAGE_HEIGHT = 200;

/** The shortest viewport height seen at the current width. */
export interface ViewportMemory {
  width: number;
  minHeight: number;
}

export interface PageHeightInput {
  /** Grid top from getBoundingClientRect(), i.e. relative to the viewport. */
  gridTop: number;
  scrollY: number;
  viewportHeight: number;
  viewportWidth: number;
  dotsRoom: number;
  /** Updated in place: carries the shortest height across calls at one width. */
  viewport: ViewportMemory;
}

export function pageHeightFor(input: PageHeightInput): number {
  const mem = input.viewport;
  if (mem.width !== input.viewportWidth || !(mem.minHeight > 0)) {
    mem.width = input.viewportWidth;
    mem.minHeight = input.viewportHeight;
  } else {
    mem.minHeight = Math.min(mem.minHeight, input.viewportHeight);
  }
  // A fixed launcher is a true overlay. Page geometry always uses the viewport
  // floor; the dock may paint above it but never shortens the app surface.
  const floor = mem.minHeight;
  const gridTop = input.gridTop + Math.max(0, input.scrollY);
  return Math.max(MIN_PAGE_HEIGHT, floor - gridTop - input.dotsRoom - 8);
}
