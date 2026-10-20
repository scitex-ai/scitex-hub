/** Keep the site-wide dock inside a single top-level document boundary. */

const DOCK_SELECTOR = "[data-site-dock]";
const CHAT_PANEL_SELECTOR = "[data-dock-chat-panel]";

function removeAll(elements: Element[]): void {
  elements.forEach((element) => element.remove());
}

/**
 * Return the one dock allowed to initialize.
 *
 * Framed documents remove all dock chrome. Top-level documents keep the first
 * server-rendered pair and discard accidental middleware/template duplicates.
 */
export function enforceDockBoundary(
  root: ParentNode,
  framed: boolean,
): HTMLElement | null {
  const docks = Array.from(root.querySelectorAll<HTMLElement>(DOCK_SELECTOR));
  const panels = Array.from(
    root.querySelectorAll<HTMLElement>(CHAT_PANEL_SELECTOR),
  );
  if (framed) {
    removeAll([...docks, ...panels]);
    return null;
  }
  removeAll(docks.slice(1));
  removeAll(panels.slice(1));
  return docks[0] ?? null;
}
