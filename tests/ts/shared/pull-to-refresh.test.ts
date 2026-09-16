/**
 * pull-to-refresh — threshold, direction and start-eligibility, driven by
 * injected touch sequences. The reload is injected, so nothing navigates.
 */

import { beforeEach, describe, expect, it } from "vitest";

import {
  PULL_THRESHOLD,
  PullGesture,
  installPullToRefresh,
  pullBlockedAt,
} from "@shared/utils/pull-to-refresh";

function drag(
  gesture: PullGesture,
  path: Array<[number, number]>,
  blocked = false,
): boolean {
  const [[x0, y0], ...rest] = path;
  gesture.start(x0, y0, blocked);
  rest.forEach(([x, y]) => gesture.move(x, y));
  return gesture.end();
}

describe("PullGesture", () => {
  it("refreshes on a vertical pull past the threshold", () => {
    expect(
      drag(new PullGesture(), [
        [100, 100],
        [102, 130],
        [104, 100 + PULL_THRESHOLD + 5],
      ]),
    ).toBe(true);
  });

  it("does not refresh on a pull short of the threshold", () => {
    expect(
      drag(new PullGesture(), [
        [100, 100],
        [101, 130],
        [101, 100 + PULL_THRESHOLD - 5],
      ]),
    ).toBe(false);
  });

  it("does not refresh when a horizontal swipe dominates", () => {
    expect(
      drag(new PullGesture(), [
        [100, 100],
        [140, 115],
        [260, 100 + PULL_THRESHOLD + 30],
      ]),
    ).toBe(false);
  });

  it("does not refresh on an upward drag", () => {
    expect(
      drag(new PullGesture(), [
        [100, 300],
        [100, 280],
        [100, 100],
      ]),
    ).toBe(false);
  });

  it("does not refresh when the start was blocked", () => {
    expect(
      drag(
        new PullGesture(),
        [
          [100, 100],
          [100, 130],
          [100, 250],
        ],
        true,
      ),
    ).toBe(false);
  });

  it("keeps refreshing after the finger drifts sideways mid-pull", () => {
    expect(
      drag(new PullGesture(), [
        [100, 100],
        [100, 125],
        [180, 100 + PULL_THRESHOLD + 10],
      ]),
    ).toBe(true);
  });
});

describe("pullBlockedAt", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("allows a plain element on an unscrolled page", () => {
    document.body.innerHTML = '<main><p id="t">hi</p></main>';
    expect(pullBlockedAt(document.getElementById("t"), document)).toBe(false);
  });

  it("blocks inside a textarea", () => {
    document.body.innerHTML = '<textarea id="t"></textarea>';
    expect(pullBlockedAt(document.getElementById("t"), document)).toBe(true);
  });

  it("blocks inside a contenteditable", () => {
    document.body.innerHTML =
      '<div contenteditable="true"><span id="t">x</span></div>';
    expect(pullBlockedAt(document.getElementById("t"), document)).toBe(true);
  });

  it("blocks inside a CodeMirror editor", () => {
    document.body.innerHTML = '<div class="cm-editor"><div id="t"></div></div>';
    expect(pullBlockedAt(document.getElementById("t"), document)).toBe(true);
  });

  it("blocks on a canvas", () => {
    document.body.innerHTML = '<canvas id="t"></canvas>';
    expect(pullBlockedAt(document.getElementById("t"), document)).toBe(true);
  });

  it("blocks inside a pane that can still scroll up", () => {
    document.body.innerHTML = '<div id="pane"><p id="t">x</p></div>';
    document.getElementById("pane")!.scrollTop = 40;
    expect(pullBlockedAt(document.getElementById("t"), document)).toBe(true);
  });

  it("blocks on the dock grabber", () => {
    document.body.innerHTML =
      '<nav class="site-dock"><span class="site-dock-grabber" id="t"></span></nav>';
    expect(pullBlockedAt(document.getElementById("t"), document)).toBe(true);
  });

  it("blocks anywhere while the dock is dragging", () => {
    document.body.innerHTML =
      '<nav class="site-dock site-dock--dragging"></nav><p id="t">x</p>';
    expect(pullBlockedAt(document.getElementById("t"), document)).toBe(true);
  });
});

describe("installPullToRefresh", () => {
  function touch(type: string, target: Element, x: number, y: number): void {
    const t = { clientX: x, clientY: y, target } as unknown as Touch;
    const e = new Event(type, { bubbles: true }) as TouchEvent;
    Object.defineProperty(e, "touches", {
      value: type === "touchend" ? [] : [t],
    });
    target.dispatchEvent(e);
  }

  it("reloads after an injected pull sequence on the page", () => {
    document.body.innerHTML = '<main><p id="t">hi</p></main>';
    const target = document.getElementById("t")!;
    let reloads = 0;
    const uninstall = installPullToRefresh(window, {
      reload: () => (reloads += 1),
    });
    touch("touchstart", target, 50, 60);
    touch("touchmove", target, 52, 90);
    touch("touchmove", target, 53, 60 + PULL_THRESHOLD + 20);
    touch("touchend", target, 53, 60 + PULL_THRESHOLD + 20);
    uninstall();
    expect(reloads).toBe(1);
  });
});
