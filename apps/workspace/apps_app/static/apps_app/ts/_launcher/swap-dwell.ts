/**
 * Swap dwell — reorder only after the pointer has STAYED over a slot.
 *
 * Operator, 2026-09-14 16:34Z: while dragging, the other icons jumped as the
 * finger merely passed over them, which is startling. swap-intent.ts already
 * requires the pointer to be PAST the target's centre (#724, the thrash fix);
 * this adds hysteresis in time: the same target must stay under the pointer
 * for DWELL_MS before the swap happens. A finger sweeping across a row
 * therefore moves nothing until it settles.
 *
 * Pure (time is passed in), so it is unit-testable without a browser.
 */

export const DWELL_MS = 150;

export class SwapDwell<T> {
  private target: T | null = null;
  private since = 0;

  constructor(private readonly dwellMs: number = DWELL_MS) {}

  /**
   * Report what is under the pointer at `now`. Returns the milliseconds still
   * to wait before a swap onto `target` is allowed: 0 means swap now, and null
   * means there is nothing to swap onto.
   */
  update(target: T | null, now: number): number | null {
    if (target === null) {
      this.reset();
      return null;
    }
    if (target !== this.target) {
      this.target = target;
      this.since = now;
    }
    return Math.max(0, this.dwellMs - (now - this.since));
  }

  /** Forget the current target (after a swap, or when the drag ends). */
  reset(): void {
    this.target = null;
    this.since = 0;
  }
}
