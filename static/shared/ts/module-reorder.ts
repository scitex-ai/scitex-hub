/**
 * Module Reorder — shared drag-drop utilities for module ordering.
 *
 * Auto-initializes tab bar drag-drop on load.
 * Exposes window._moduleReorder for apps inline scripts.
 */

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
  return fetch("/apps/api/reorder/", {
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

      const rect = item.getBoundingClientRect();
      clearClasses();

      if (opts.axis === "horizontal") {
        const midX = rect.left + rect.width / 2;
        if (e.clientX < midX) {
          item.classList.add(opts.beforeClass);
          dropPosition = "before";
        } else {
          item.classList.add(opts.afterClass);
          dropPosition = "after";
        }
      } else {
        const midY = rect.top + rect.height / 2;
        if (e.clientY < midY) {
          item.classList.add(opts.beforeClass);
          dropPosition = "before";
        } else {
          item.classList.add(opts.afterClass);
          dropPosition = "after";
        }
      }
    });

    item.addEventListener("dragleave", (e: DragEvent) => {
      if (!item.contains(e.relatedTarget as Node)) {
        item.classList.remove(opts.beforeClass, opts.afterClass);
      }
    });

    item.addEventListener("drop", (e: DragEvent) => {
      e.preventDefault();
      clearClasses();
      if (!draggedEl || draggedEl === item) return;

      if (dropPosition === "after") {
        container.insertBefore(draggedEl, item.nextSibling);
      } else {
        container.insertBefore(draggedEl, item);
      }

      // Collect ordered module names
      const ordered: string[] = [];
      items().forEach((el) => {
        const name = opts.getModuleName(el);
        if (name) ordered.push(name);
      });

      if (opts.onReorder) {
        opts.onReorder(ordered);
      }
    });
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

// Auto-init
function initAll(): void {
  initTabBarDragDrop();
  initAppsNavDragDrop();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initAll);
} else {
  initAll();
}

console.debug("[Module Reorder] Loaded — tab bar + apps nav drag-drop active");
