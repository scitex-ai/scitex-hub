/**
 * Site dock — the in-site history stack behind Back / Forward.
 *
 * Safari has no canGoForward, so the dock keeps its own record of the pages
 * visited in the tab and draws Forward dimmed when there is nothing ahead.
 * These tests walk realistic journeys through recordVisit() exactly as
 * site-dock.ts does on each page load (navigation type from
 * PerformanceNavigationTiming).
 */

import { describe, expect, it } from "vitest";

import {
  canGoBack,
  canGoForward,
  EMPTY_STACK,
  type HistoryStack,
  MAX_ENTRIES,
  parseStack,
  recordVisit,
} from "@/components/_site-dock/history-stack";

function visit(...urls: string[]): HistoryStack {
  return urls.reduce(
    (stack, url) => recordVisit(stack, url, "navigate"),
    EMPTY_STACK,
  );
}

describe("site dock history stack", () => {
  it("has neither Back nor Forward on the first page of a tab", () => {
    const stack = visit("/apps/");
    expect([canGoBack(stack), canGoForward(stack)]).toEqual([false, false]);
  });

  it("offers Back but not Forward after following links", () => {
    const stack = visit("/apps/", "/apps/home/", "/apps/discovery/");
    expect([canGoBack(stack), canGoForward(stack)]).toEqual([true, false]);
  });

  it("offers Forward after going Back", () => {
    const here = visit("/apps/", "/apps/home/", "/apps/discovery/");
    const back = recordVisit(here, "/apps/home/", "back_forward");
    expect([back.index, canGoForward(back)]).toEqual([1, true]);
  });

  it("walks Forward again to the end, where Forward dims", () => {
    const here = visit("/apps/", "/apps/home/", "/apps/discovery/");
    const back = recordVisit(here, "/apps/home/", "back_forward");
    const forward = recordVisit(back, "/apps/discovery/", "back_forward");
    expect([forward.index, canGoForward(forward)]).toEqual([2, false]);
  });

  it("drops the forward entries when a new link is followed after Back", () => {
    const here = visit("/apps/", "/apps/home/", "/apps/discovery/");
    const back = recordVisit(here, "/apps/home/", "back_forward");
    const branched = recordVisit(back, "/apps/store/", "navigate");
    expect(branched.entries).toEqual(["/apps/", "/apps/home/", "/apps/store/"]);
  });

  it("does not add an entry when the page is reloaded", () => {
    const here = visit("/apps/", "/apps/home/");
    const reloaded = recordVisit(here, "/apps/home/", "reload");
    expect(reloaded).toEqual(here);
  });

  it("lands on the nearest matching entry after a multi-step jump", () => {
    const here = visit("/a/", "/b/", "/c/", "/d/");
    const jumped = recordVisit(here, "/a/", "back_forward");
    expect(jumped.index).toBe(0);
  });

  it("starts over when a back/forward lands somewhere it never recorded", () => {
    const here = visit("/a/", "/b/");
    const stale = recordVisit(here, "/elsewhere/", "back_forward");
    expect(stale).toEqual({ entries: ["/elsewhere/"], index: 0 });
  });

  it("caps the record so it cannot grow without bound", () => {
    const urls = Array.from({ length: MAX_ENTRIES + 10 }, (_, i) => `/p/${i}/`);
    const stack = visit(...urls);
    expect([stack.entries.length, stack.index]).toEqual([
      MAX_ENTRIES,
      MAX_ENTRIES - 1,
    ]);
  });

  it("treats unreadable storage as a fresh tab", () => {
    expect([
      parseStack(null),
      parseStack("not json"),
      parseStack('{"entries":["/a/"],"index":5}'),
    ]).toEqual([EMPTY_STACK, EMPTY_STACK, EMPTY_STACK]);
  });
});
