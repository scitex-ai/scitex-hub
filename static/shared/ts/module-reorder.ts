/**
 * Module Reorder — shared drag-drop utilities for module ordering.
 *
 * Auto-initializes tab bar drag-drop on load.
 * Exposes window._moduleReorder for apps inline scripts.
 */

import { API_URLS } from "./utils/api-urls";

/**
 * Touch reorder tuning. HTML5 drag-and-drop never fires from touch input
 * (iOS Safari most notably), so touch devices get a long-press-to-pick-up
 * gesture instead — see the touch branch in makeReorderable().
 */
/** Hold duration (ms) before a tile is "picked up" for reordering. */
const TOUCH_LONGPRESS_MS = 350;
/** Finger travel (px) before pickup that counts as scrolling, not a drag. */
const TOUCH_SLOP = 8;

/** CSRF token helper */
function getCsrf(): string {
  const input = document.querySelector<HTMLInputElement>(
    "[name=csrfmiddlewaretoken]",
  );
  if (input) return input.value;
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
}

/** POST the new module order to the backend */
export function postModuleOrder(order: string[]): Promise<void> {
  console.debug("[Module Reorder] Saving order:", order);
  return fetch(API_URLS.apps.reorder, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrf(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ order }),
  }).then((resp) => {
    if (!resp.ok) {
      console.error(
        "[Module Reorder] API error:",
        resp.status,
        resp.statusText,
      );
      return;
    }
    console.debug("[Module Reorder] Saved successfully");
    syncTabBar(order);
    syncAppsNav(order);
    syncAppsGrid(order);
  });
}

/** Reorder module tab bar DOM to match given order */
export function syncTabBar(orderedNames: string[]): void {
  const tabBar = document.querySelector(".module-tab-bar");
  if (!tabBar) return;

  const tabBtns = Array.from(
    tabBar.querySelectorAll<HTMLElement>(".module-tab-btn"),
  );
  const tabMap: Record<string, HTMLElement> = {};
  tabBtns.forEach((btn) => {
    const mod = btn.dataset.module;
    if (mod) tabMap[mod] = btn;
  });

  // Append in order
  orderedNames.forEach((name) => {
    if (tabMap[name]) tabBar.appendChild(tabMap[name]);
  });
  // Append remaining tabs not in the order list
  tabBtns.forEach((btn) => {
    const mod = btn.dataset.module ?? "";
    if (!orderedNames.includes(mod)) {
      tabBar.appendChild(btn);
    }
  });
}

/** Reorder apps nav sidebar DOM to match given order */
export function syncAppsNav(orderedNames: string[]): void {
  const nav = document.querySelector(".ws-apps-nav");
  if (!nav) return;

  const items = Array.from(
    nav.querySelectorAll<HTMLElement>(".ws-apps-nav-item"),
  );
  const itemMap: Record<string, HTMLElement> = {};
  items.forEach((el) => {
    const mod = el.dataset.module;
    if (mod) itemMap[mod] = el;
  });

  orderedNames.forEach((name) => {
    if (itemMap[name]) nav.appendChild(itemMap[name]);
  });
  items.forEach((el) => {
    const mod = el.dataset.module ?? "";
    if (!orderedNames.includes(mod)) nav.appendChild(el);
  });
}

/** Reorder apps grid DOM to match given order */
export function syncAppsGrid(orderedNames: string[]): void {
  const grid = document.getElementById("ap-grid");
  if (!grid) return;

  const cards = Array.from(grid.querySelectorAll<HTMLElement>(".ap-card"));
  const cardMap: Record<string, HTMLElement> = {};
  cards.forEach((card) => {
    const mod = card.dataset.module;
    if (mod) cardMap[mod] = card;
  });

  // Installed cards first, in order
  orderedNames.forEach((name) => {
    if (cardMap[name]) grid.appendChild(cardMap[name]);
  });
  // Non-ordered cards stay at end
  cards.forEach((card) => {
    const mod = card.dataset.module ?? "";
    if (!orderedNames.includes(mod)) {
      grid.appendChild(card);
    }
  });
}

interface ReorderableOptions {
  /** CSS selector for draggable items within container */
  itemSelector: string;
  /** Get module name from an item element */
  getModuleName: (el: HTMLElement) => string;
  /** Check if an item can be dragged */
  isReorderable?: (el: HTMLElement) => boolean;
  /** CSS class added to the dragged item */
  dragClass: string;
  /** CSS class for "insert before" indicator */
  beforeClass: string;
  /** CSS class for "insert after" indicator */
  afterClass: string;
  /** Axis: "horizontal" for tab bar, "vertical" for grid */
  axis?: "horizontal" | "vertical";
  /** Called after reorder with ordered module names */
  onReorder?: (orderedNames: string[]) => void;
}

/** Make a container's children drag-reorderable */
export function makeReorderable(
  container: HTMLElement,
  opts: ReorderableOptions,
): void {
  let draggedEl: HTMLElement | null = null;
  let dropPosition: "before" | "after" = "before";
  let didDrag = false;

  const items = () =>
    Array.from(container.querySelectorAll<HTMLElement>(opts.itemSelector));

  function clearClasses(): void {
    container
      .querySelectorAll(`.${opts.beforeClass}, .${opts.afterClass}`)
      .forEach((el) => {
        el.classList.remove(opts.beforeClass, opts.afterClass);
      });
  }

  /**
   * Mark `target` with the before/after drop indicator for a pointer at
   * (x, y). Shared by the mouse (dragover) and touch (touchmove) paths so
   * the midpoint rule lives in exactly one place.
   */
  function markDropSide(target: HTMLElement, x: number, y: number): void {
    const rect = target.getBoundingClientRect();
    clearClasses();
    if (opts.axis === "horizontal") {
      const midX = rect.left + rect.width / 2;
      if (x < midX) {
        target.classList.add(opts.beforeClass);
        dropPosition = "before";
      } else {
        target.classList.add(opts.afterClass);
        dropPosition = "after";
      }
    } else {
      const midY = rect.top + rect.height / 2;
      if (y < midY) {
        target.classList.add(opts.beforeClass);
        dropPosition = "before";
      } else {
        target.classList.add(opts.afterClass);
        dropPosition = "after";
      }
    }
  }

  /**
   * Move the dragged element relative to `target` (per dropPosition) and
   * report the new order. Shared by the mouse (drop) and touch (touchend)
   * paths.
   */
  function applyDrop(target: HTMLElement): void {
    if (!draggedEl || draggedEl === target) return;

    if (dropPosition === "after") {
      container.insertBefore(draggedEl, target.nextSibling);
    } else {
      container.insertBefore(draggedEl, target);
    }

    const ordered: string[] = [];
    items().forEach((el) => {
      const name = opts.getModuleName(el);
      if (name) ordered.push(name);
    });

    if (opts.onReorder) {
      opts.onReorder(ordered);
    }
  }

  items().forEach((item) => {
    if (opts.isReorderable && !opts.isReorderable(item)) return;
    item.draggable = true;

    // Prevent <a> click navigation after drag
    item.addEventListener("click", (e: MouseEvent) => {
      if (didDrag) {
        e.preventDefault();
        didDrag = false;
      }
    });

    item.addEventListener("dragstart", (e: DragEvent) => {
      draggedEl = item;
      didDrag = true;
      item.classList.add(opts.dragClass);
      if (e.dataTransfer) {
        e.dataTransfer.effectAllowed = "move";
        // Prevent browser's default link-drag for <a> elements
        e.dataTransfer.setData("text/plain", "");
      }
    });

    item.addEventListener("dragend", () => {
      if (draggedEl) draggedEl.classList.remove(opts.dragClass);
      draggedEl = null;
      clearClasses();
      // Reset didDrag after a tick so the click handler can catch it
      setTimeout(() => {
        didDrag = false;
      }, 0);
    });

    item.addEventListener("dragover", (e: DragEvent) => {
      if (!draggedEl || draggedEl === item) return;
      if (opts.isReorderable && !opts.isReorderable(item)) return;
      e.preventDefault();
      if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
      markDropSide(item, e.clientX, e.clientY);
    });

    item.addEventListener("dragleave", (e: DragEvent) => {
      if (!item.contains(e.relatedTarget as Node)) {
        item.classList.remove(opts.beforeClass, opts.afterClass);
      }
    });

    item.addEventListener("drop", (e: DragEvent) => {
      e.preventDefault();
      clearClasses();
      applyDrop(item);
    });

    // ── Touch path ──────────────────────────────────────────
    // iOS Safari (and mobile browsers generally) never dispatch HTML5
    // drag events from touch input, so the mouse handlers above are dead
    // on a phone. Give touch its own long-press-to-pick-up gesture, like
    // reordering icons on the iOS home screen, and reuse markDropSide /
    // applyDrop so the reorder rule stays single-sourced.
    item.style.userSelect = "none";
    (
      item.style as CSSStyleDeclaration & { webkitTouchCallout?: string }
    ).webkitTouchCallout = "none";

    let lpTimer: number | null = null;
    let startX = 0;
    let startY = 0;
    let touchTarget: HTMLElement | null = null;

    const clearLongPress = (): void => {
      if (lpTimer !== null) {
        clearTimeout(lpTimer);
        lpTimer = null;
      }
    };

    item.addEventListener(
      "touchstart",
      (e: TouchEvent) => {
        const t = e.touches[0];
        if (!t) return;
        startX = t.clientX;
        startY = t.clientY;
        clearLongPress();
        lpTimer = window.setTimeout(() => {
          lpTimer = null;
          draggedEl = item;
          didDrag = true;
          item.classList.add(opts.dragClass);
        }, TOUCH_LONGPRESS_MS);
      },
      { passive: true },
    );

    item.addEventListener(
      "touchmove",
      (e: TouchEvent) => {
        const t = e.touches[0];
        if (!t) return;
        if (draggedEl !== item) {
          // Not picked up yet: a real move before the long-press fires means
          // the user is scrolling, not reordering — cancel the pickup and
          // let the browser scroll normally.
          if (
            lpTimer !== null &&
            Math.hypot(t.clientX - startX, t.clientY - startY) > TOUCH_SLOP
          ) {
            clearLongPress();
          }
          return;
        }
        // Picked up: we own the gesture, so stop the page scrolling under
        // the finger (needs a non-passive listener to call preventDefault).
        e.preventDefault();
        const under = document.elementFromPoint(
          t.clientX,
          t.clientY,
        ) as HTMLElement | null;
        const over = under?.closest<HTMLElement>(opts.itemSelector) ?? null;
        clearClasses();
        if (!over || over === item || !container.contains(over)) {
          touchTarget = null;
          return;
        }
        if (opts.isReorderable && !opts.isReorderable(over)) {
          touchTarget = null;
          return;
        }
        touchTarget = over;
        markDropSide(over, t.clientX, t.clientY);
      },
      { passive: false },
    );

    const endTouch = (): void => {
      clearLongPress();
      if (draggedEl !== item) return;
      item.classList.remove(opts.dragClass);
      if (touchTarget) applyDrop(touchTarget);
      clearClasses();
      draggedEl = null;
      touchTarget = null;
      // Reset didDrag after a tick so the click handler can catch it.
      setTimeout(() => {
        didDrag = false;
      }, 0);
    };
    item.addEventListener("touchend", endTouch);
    item.addEventListener("touchcancel", endTouch);
  });
}

/** Initialize tab bar drag-drop */
function initTabBarDragDrop(): void {
  const tabBar = document.querySelector<HTMLElement>(".module-tab-bar");
  if (!tabBar) return;

  makeReorderable(tabBar, {
    itemSelector: ".module-tab-btn",
    getModuleName: (el) => el.dataset.module ?? "",
    dragClass: "tab-dragging",
    beforeClass: "tab-drag-before",
    afterClass: "tab-drag-after",
    axis: "horizontal",
    onReorder: (order) => {
      void postModuleOrder(order);
    },
  });
}

/** Initialize apps nav sidebar drag-drop (vertical) */
function initAppsNavDragDrop(): void {
  const nav = document.querySelector<HTMLElement>(".ws-apps-nav");
  if (!nav) return;

  makeReorderable(nav, {
    itemSelector: ".ws-apps-nav-item",
    getModuleName: (el) => el.dataset.module ?? "",
    dragClass: "nav-dragging",
    beforeClass: "nav-drag-before",
    afterClass: "nav-drag-after",
    axis: "vertical",
    onReorder: (order) => {
      void postModuleOrder(order);
    },
  });
}

// Expose on window for inline scripts (apps browse)
declare global {
  interface Window {
    _moduleReorder: {
      postModuleOrder: typeof postModuleOrder;
      syncTabBar: typeof syncTabBar;
      syncAppsNav: typeof syncAppsNav;
      syncAppsGrid: typeof syncAppsGrid;
      makeReorderable: typeof makeReorderable;
    };
  }
}

window._moduleReorder = {
  postModuleOrder,
  syncTabBar,
  syncAppsNav,
  syncAppsGrid,
  makeReorderable,
};

/** Initialize sidebar module drag-drop (vertical) */
function initSidebarDragDrop(): void {
  // Find the sidebar group containing module items
  const groups = document.querySelectorAll<HTMLElement>(".sidebar-group");
  // The second group (after divider) contains modules
  const moduleGroup = groups.length >= 2 ? groups[1] : null;
  if (!moduleGroup) return;

  makeReorderable(moduleGroup, {
    itemSelector: ".sidebar-item[data-module]",
    getModuleName: (el) => el.dataset.module ?? "",
    dragClass: "sidebar-dragging",
    beforeClass: "sidebar-drag-before",
    afterClass: "sidebar-drag-after",
    axis: "vertical",
    onReorder: (order) => {
      void postModuleOrder(order);
      syncTabBar(order);
      syncAppsNav(order);
    },
  });
}

// Auto-init
function initAll(): void {
  initTabBarDragDrop();
  initAppsNavDragDrop();
  initSidebarDragDrop();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initAll);
} else {
  initAll();
}

console.debug("[Module Reorder] Loaded — tab bar + apps nav drag-drop active");
