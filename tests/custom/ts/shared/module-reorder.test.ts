/**
 * module-reorder — touch reorder regression.
 *
 * Field bug (real-iPhone test of live prod, 2026-07-12): app reordering
 * (tab bar, apps nav, workspace sidebar, apps store grid — everything that
 * routes through makeReorderable) was dead on iOS. Root cause: reorder was
 * implemented with the HTML5 Drag-and-Drop API only (item.draggable=true +
 * dragstart/dragover/drop), and iOS Safari never dispatches HTML5 drag
 * events from touch input. makeReorderable() now has a long-press-to-pick-up
 * touch path.
 *
 * jsdom has no layout engine, so getBoundingClientRect returns zeros and
 * document.elementFromPoint returns null. The touch path reads both, so the
 * tests SUPPLY that geometry (a real vertical stack) and let the actual code
 * run against it — no behaviour of the code under test is stubbed.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { makeReorderable } from "@shared/module-reorder";

const ROW_H = 50;

interface Row {
  el: HTMLElement;
  top: number;
}

/** Build a vertical list of `names.length` items with fixed, non-zero rects. */
function buildList(names: string[]): { container: HTMLElement; rows: Row[] } {
  const container = document.createElement("div");
  const rows: Row[] = names.map((name, i) => {
    const el = document.createElement("a");
    el.className = "it";
    el.dataset.module = name;
    const top = i * ROW_H;
    // jsdom computes no layout — give each item a real rect.
    el.getBoundingClientRect = () =>
      ({
        top,
        bottom: top + ROW_H,
        left: 0,
        right: 100,
        width: 100,
        height: ROW_H,
        x: 0,
        y: top,
        toJSON: () => ({}),
      }) as DOMRect;
    container.appendChild(el);
    return { el, top };
  });
  document.body.appendChild(container);
  return { container, rows };
}

/** Provide the layout lookup jsdom omits: find the item whose rect spans `y`. */
function installElementFromPoint(container: HTMLElement): void {
  document.elementFromPoint = (_x: number, y: number): Element | null => {
    const items = Array.from(container.querySelectorAll<HTMLElement>(".it"));
    return (
      items.find((el) => {
        const r = el.getBoundingClientRect();
        return y >= r.top && y < r.bottom;
      }) ?? null
    );
  };
}

/** Dispatch a touch event with a single touch point at (x, y). */
function touch(el: HTMLElement, type: string, x: number, y: number): Event {
  const ev = new Event(type, { bubbles: true, cancelable: true });
  const point = { clientX: x, clientY: y };
  Object.assign(ev, { touches: [point], changedTouches: [point] });
  el.dispatchEvent(ev);
  return ev;
}

/** Dispatch an HTML5 drag event with a minimal dataTransfer + coords. */
function drag(el: HTMLElement, type: string, x: number, y: number): Event {
  const ev = new Event(type, { bubbles: true, cancelable: true });
  Object.assign(ev, {
    clientX: x,
    clientY: y,
    dataTransfer: {
      effectAllowed: "",
      dropEffect: "",
      setData: (): void => {},
    },
  });
  el.dispatchEvent(ev);
  return ev;
}

const OPTS = (onReorder: (order: string[]) => void) => ({
  itemSelector: ".it",
  getModuleName: (el: HTMLElement) => el.dataset.module ?? "",
  dragClass: "dragging",
  beforeClass: "drop-before",
  afterClass: "drop-after",
  axis: "vertical" as const,
  onReorder,
});

function order(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll<HTMLElement>(".it")).map(
    (el) => el.dataset.module ?? "",
  );
}

describe("makeReorderable — touch", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    document.body.innerHTML = "";
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("long-press then drag reorders on touch and reports the new order", () => {
    // Arrange — a, b, c stacked vertically; move a below c.
    const { container, rows } = buildList(["a", "b", "c"]);
    installElementFromPoint(container);
    const onReorder = vi.fn();
    makeReorderable(container, OPTS(onReorder));

    // Act — pick up "a" (long-press), drag onto the lower half of "c", drop.
    touch(rows[0].el, "touchstart", 10, 10);
    vi.advanceTimersByTime(400); // > TOUCH_LONGPRESS_MS
    touch(rows[0].el, "touchmove", 10, rows[2].top + ROW_H - 5); // over c, after
    touch(rows[0].el, "touchend", 10, rows[2].top + ROW_H - 5);

    // Assert — a now sits after c, and the callback got the same order.
    expect(order(container)).toEqual(["b", "c", "a"]);
    expect(onReorder).toHaveBeenCalledWith(["b", "c", "a"]);
  });

  it("prevents the page from scrolling while dragging on touch", () => {
    // Arrange
    const { container, rows } = buildList(["a", "b", "c"]);
    installElementFromPoint(container);
    makeReorderable(container, OPTS(vi.fn()));

    // Act — after pickup, a touchmove must be cancelled (preventDefault).
    touch(rows[0].el, "touchstart", 10, 10);
    vi.advanceTimersByTime(400);
    const moved = touch(rows[0].el, "touchmove", 10, rows[1].top + 5);

    // Assert
    expect(moved.defaultPrevented).toBe(true);
  });

  it("does NOT reorder when the finger moves before the long-press (a scroll)", () => {
    // Arrange
    const { container, rows } = buildList(["a", "b", "c"]);
    installElementFromPoint(container);
    const onReorder = vi.fn();
    makeReorderable(container, OPTS(onReorder));

    // Act — move past the slop BEFORE the long-press fires, then release.
    touch(rows[0].el, "touchstart", 10, 10);
    touch(rows[0].el, "touchmove", 10, 40); // 30px > TOUCH_SLOP, cancels pickup
    vi.advanceTimersByTime(400);
    touch(rows[0].el, "touchend", 10, 40);

    // Assert — nothing moved; scrolling is preserved.
    expect(order(container)).toEqual(["a", "b", "c"]);
    expect(onReorder).not.toHaveBeenCalled();
  });
});

describe("makeReorderable — desktop drag-and-drop still works", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("mouse drag-and-drop reorders (guards the shared-helper refactor)", () => {
    // Arrange
    const { container, rows } = buildList(["a", "b", "c"]);
    const onReorder = vi.fn();
    makeReorderable(container, OPTS(onReorder));

    // Act — drag "a" over the lower half of "c" and drop.
    drag(rows[0].el, "dragstart", 10, 10);
    drag(rows[2].el, "dragover", 10, rows[2].top + ROW_H - 5);
    drag(rows[2].el, "drop", 10, rows[2].top + ROW_H - 5);

    // Assert
    expect(order(container)).toEqual(["b", "c", "a"]);
    expect(onReorder).toHaveBeenCalledWith(["b", "c", "a"]);
  });
});
