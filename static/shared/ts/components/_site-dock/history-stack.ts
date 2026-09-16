/**
 * In-site history stack for the dock's Back / Forward buttons.
 *
 * WHY A STACK. The dock draws Forward DIMMED when there is nothing to go
 * forward to, and browsers do not tell a page that: `history.length` counts
 * entries in both directions, and Safari has no Navigation API
 * (`navigation.canGoForward`). So the dock keeps its own record of the pages
 * visited in this tab (sessionStorage: per tab, gone when the tab closes) and
 * works out where the user is in it on every page load.
 *
 * Pure functions only: the entry file (site-dock.ts) supplies the URL, the
 * navigation type and the storage, which is what makes this testable.
 */

export interface HistoryStack {
  entries: string[];
  index: number;
}

/** How the current document was reached (PerformanceNavigationTiming.type). */
export type NavigationKind =
  "navigate" | "reload" | "back_forward" | "prerender";

/** Oldest entries are dropped past this, so the record cannot grow forever. */
export const MAX_ENTRIES = 50;

export const EMPTY_STACK: HistoryStack = { entries: [], index: -1 };

function isValid(stack: unknown): stack is HistoryStack {
  if (!stack || typeof stack !== "object") return false;
  const s = stack as HistoryStack;
  return (
    Array.isArray(s.entries) &&
    s.entries.every((e) => typeof e === "string") &&
    Number.isInteger(s.index) &&
    s.index >= -1 &&
    s.index < s.entries.length
  );
}

/** Parse a stored stack; anything unreadable is treated as a fresh tab. */
export function parseStack(raw: string | null): HistoryStack {
  if (!raw) return EMPTY_STACK;
  try {
    const parsed: unknown = JSON.parse(raw);
    return isValid(parsed) ? parsed : EMPTY_STACK;
  } catch {
    return EMPTY_STACK;
  }
}

function push(stack: HistoryStack, url: string): HistoryStack {
  if (stack.index >= 0 && stack.entries[stack.index] === url) return stack;
  // A new visit discards everything "forward" of the current position, which
  // is exactly what the browser does to its own history.
  let entries = stack.entries.slice(0, stack.index + 1).concat(url);
  if (entries.length > MAX_ENTRIES) {
    entries = entries.slice(entries.length - MAX_ENTRIES);
  }
  return { entries, index: entries.length - 1 };
}

/** Index of the entry equal to `url` nearest to `from`, or -1. */
function nearest(entries: string[], url: string, from: number): number {
  let best = -1;
  entries.forEach((entry, i) => {
    if (entry !== url) return;
    if (best === -1 || Math.abs(i - from) < Math.abs(best - from)) best = i;
  });
  return best;
}

/**
 * The stack after arriving at `url` by a navigation of kind `kind`.
 *
 * back_forward: the user moved along the existing record, so only the index
 * changes. One step back is checked before one step forward (Back is by far
 * the common case, and when both neighbours are the same URL they are
 * indistinguishable anyway). A longer jump, e.g. from the browser's long-press
 * history menu, lands on the nearest matching entry. A URL that is nowhere in
 * the record means the record is stale, so it starts again from here.
 */
export function recordVisit(
  stack: HistoryStack,
  url: string,
  kind: NavigationKind,
): HistoryStack {
  if (kind === "back_forward") {
    const { entries, index } = stack;
    if (index >= 0 && entries[index] === url) return stack;
    if (index > 0 && entries[index - 1] === url) {
      return { entries, index: index - 1 };
    }
    if (index + 1 < entries.length && entries[index + 1] === url) {
      return { entries, index: index + 1 };
    }
    const found = nearest(entries, url, index);
    if (found !== -1) return { entries, index: found };
    return { entries: [url], index: 0 };
  }
  if (kind === "reload") {
    if (stack.index >= 0 && stack.entries[stack.index] === url) return stack;
  }
  return push(stack, url);
}

export function canGoBack(stack: HistoryStack): boolean {
  return stack.index > 0;
}

export function canGoForward(stack: HistoryStack): boolean {
  return stack.index >= 0 && stack.index < stack.entries.length - 1;
}
