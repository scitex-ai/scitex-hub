/** Pure keyboard logic for the header command palette (no DOM access). */

export type PaletteAction =
  "next" | "previous" | "first" | "last" | "open" | "close";

export interface ShortcutKeyEvent {
  key: string;
  ctrlKey: boolean;
  metaKey: boolean;
  altKey: boolean;
  defaultPrevented: boolean;
}

const PALETTE_ACTIONS: Record<string, PaletteAction> = {
  ArrowDown: "next",
  ArrowUp: "previous",
  Home: "first",
  End: "last",
  Enter: "open",
  Escape: "close",
};

export function paletteActionForKey(key: string): PaletteAction | null {
  return PALETTE_ACTIONS[key] ?? null;
}

/** Index of the highlighted result after `action`; -1 means nothing highlighted. */
export function nextActiveIndex(
  currentIndex: number,
  action: PaletteAction,
  resultCount: number,
): number {
  if (resultCount === 0) return -1;
  const lastIndex = resultCount - 1;
  switch (action) {
    case "next":
      return currentIndex >= lastIndex ? 0 : currentIndex + 1;
    case "previous":
      return currentIndex <= 0 ? lastIndex : currentIndex - 1;
    case "first":
      return 0;
    case "last":
      return lastIndex;
    default:
      return currentIndex;
  }
}

/** "/" opens only outside editable fields; Ctrl/Cmd+K yields to page-specific handlers. */
export function isOpenPaletteShortcut(
  event: ShortcutKeyEvent,
  targetIsEditable: boolean,
): boolean {
  if (event.defaultPrevented || event.altKey) return false;
  const withCommandKey = event.ctrlKey || event.metaKey;
  if (event.key === "/") return !withCommandKey && !targetIsEditable;
  return withCommandKey && event.key.toLowerCase() === "k";
}
