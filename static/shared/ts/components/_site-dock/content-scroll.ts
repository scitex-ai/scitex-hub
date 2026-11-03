/** Mobile outside-content scroll intent; never changes layout or preferences. */
import { isMinimized } from "./minimize";

export const PHONE_MAX_WIDTH = 768;
const SCROLL_INTENT_MS = 1500;
const SCROLL_KEYS = ["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End", " "];

/** Install capture listeners and return a way to cancel the current gesture. */
export function initContentScrollAvoidance(
  dock: HTMLElement,
  collapse: () => void,
): () => void {
  const previousTop = new WeakMap<EventTarget, number>();
  let interactionUntil = 0;
  const owned = (target: EventTarget | null): boolean =>
    target instanceof Element &&
    (dock.contains(target) || !!target.closest("[data-dock-chat-panel]"));
  const top = (target: EventTarget): number =>
    target instanceof Element
      ? target.scrollTop
      : document.scrollingElement?.scrollTop ?? window.scrollY;
  const arm = (event: Event): void => {
    if (!dock.isConnected || window.innerWidth > PHONE_MAX_WIDTH || owned(event.target)) return;
    // Read before default scrolling: restoring a page or resizing a workspace
    // without a user gesture must not collapse the launcher.
    const fresh = performance.now() > interactionUntil;
    interactionUntil = performance.now() + SCROLL_INTENT_MS;
    let node = event.target instanceof Element ? event.target : null;
    while (node) {
      if (fresh || !previousTop.has(node)) previousTop.set(node, node.scrollTop);
      node = node.parentElement;
    }
    if (fresh || !previousTop.has(document)) previousTop.set(document, top(document));
  };
  document.addEventListener("wheel", arm, { capture: true, passive: true });
  document.addEventListener("touchstart", arm, { capture: true, passive: true });
  document.addEventListener("touchmove", arm, { capture: true, passive: true });
  document.addEventListener("keydown", (event) => {
    if (SCROLL_KEYS.includes(event.key)) arm(event);
  }, true);
  document.addEventListener("scroll", (event) => {
    const target = event.target;
    if (
      !dock.isConnected || !target || window.innerWidth > PHONE_MAX_WIDTH ||
      owned(target) || performance.now() > interactionUntil ||
      dock.classList.contains("site-dock--floating") ||
      dock.classList.contains("site-dock--dragging") || isMinimized(dock)
    ) return;
    const before = previousTop.get(target);
    const after = top(target);
    previousTop.set(target, after);
    if (before !== undefined && before !== after) collapse();
  }, true); // Element scroll does not bubble: nested workspaces need capture.
  return () => { interactionUntil = 0; };
}
