/**
 * App Launcher — workspace home grid (approved design 2026-07-07).
 *
 * Behaviour:
 * - Tap a tile to open the app.
 * - Right-click (desktop) opens a context popover: Open, Pin to sidebar,
 *   Rearrange apps, Details. The popover flips above the tile when it
 *   would overflow the viewport bottom and shifts to stay on screen.
 * - Long-press (touch or mouse) enters iPhone-style EDIT MODE: every tile
 *   jiggles and can be dragged to a new slot; a floating "Done" pill (or
 *   Escape) exits. The order persists per-user via POST api/reorder/.
 * - Pin to sidebar persists via POST /apps/store/api/<module>/pin/.
 */

import { showToast } from "@utils/ui";

// Hold this long before the grid enters jiggle/edit mode.
const LONG_PRESS_MS = 420;
// Finger travel (px) that reads as a scroll and cancels the long-press.
const MOVE_CANCEL_PX = 10;

function getCsrf(): string {
  const input = document.querySelector(
    "[name=csrfmiddlewaretoken]",
  ) as HTMLInputElement | null;
  if (input) return input.value;
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
}

class AppLauncher {
  private grid: HTMLElement;
  private tiles: HTMLElement[];
  private popover: HTMLElement | null = null;

  // Edit / drag state
  private editMode = false;
  private doneBtn: HTMLElement | null = null;
  private pressTimer: number | null = null;
  private pressStart: { x: number; y: number } | null = null;
  private dragTile: HTMLElement | null = null;
  private dragPointerId: number | null = null;
  private suppressClick = false;

  // Bound drag handlers so add/removeEventListener pair up.
  private onDragMove = (e: PointerEvent) => this.handleDragMove(e);
  private onDragEnd = (e: PointerEvent) => this.handleDragEnd(e);

  constructor(grid: HTMLElement) {
    this.grid = grid;
    this.tiles = Array.from(
      grid.querySelectorAll<HTMLElement>(".launcher-tile"),
    );
  }

  init(): void {
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        this.closePopover();
        this.exitEditMode();
      }
    });

    this.tiles.forEach((tile) => this.bindTile(tile));

    document.addEventListener("click", (e) => {
      if (this.popover && !this.popover.contains(e.target as Node)) {
        this.closePopover();
      }
    });
    window.addEventListener("resize", () => this.closePopover());
    window.addEventListener("scroll", () => this.closePopover(), true);
  }

  private bindTile(tile: HTMLElement): void {
    // A tile is an <a>, and links are natively draggable. The moment the
    // pointer MOVES while held, the browser starts an HTML5 link-drag and
    // takes over the gesture: pointermove stops reaching us, so the reorder
    // never runs and the tile looks stuck. (The long-press still worked,
    // which is why edit mode engaged but nothing could be moved.) Kill the
    // native drag so our pointer-driven reorder owns the gesture.
    tile.addEventListener("dragstart", (e) => e.preventDefault());

    // Right-click → context popover (desktop).
    tile.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      this.openPopover(tile);
    });

    // Pointer down starts a long-press (or, in edit mode, a drag).
    tile.addEventListener("pointerdown", (e) =>
      this.handlePointerDown(e, tile),
    );

    // Suppress the click that a drag/long-press would otherwise fire.
    tile.addEventListener("click", (e) => {
      if (this.editMode || this.suppressClick) {
        e.preventDefault();
        e.stopPropagation();
      }
    });
  }

  /* ── Long-press detection ───────────────────────────────── */

  private handlePointerDown(e: PointerEvent, tile: HTMLElement): void {
    if (this.popover) this.closePopover();
    if (e.pointerType === "mouse" && e.button !== 0) return;

    // Already editing: a press begins a drag straight away.
    if (this.editMode) {
      this.beginDrag(e, tile);
      return;
    }

    this.pressStart = { x: e.clientX, y: e.clientY };

    const onMove = (me: PointerEvent) => {
      if (!this.pressStart) return;
      const moved = Math.hypot(
        me.clientX - this.pressStart.x,
        me.clientY - this.pressStart.y,
      );
      if (moved > MOVE_CANCEL_PX) endPress();
    };
    const endPress = () => {
      this.clearPressTimer();
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", endPress);
      document.removeEventListener("pointercancel", endPress);
    };

    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", endPress);
    document.addEventListener("pointercancel", endPress);

    this.pressTimer = window.setTimeout(() => {
      this.pressTimer = null;
      this.pressStart = null;
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", endPress);
      document.removeEventListener("pointercancel", endPress);
      this.enterEditMode();
      this.beginDrag(e, tile); // same held pointer flows into the drag
    }, LONG_PRESS_MS);
  }

  private clearPressTimer(): void {
    if (this.pressTimer !== null) {
      clearTimeout(this.pressTimer);
      this.pressTimer = null;
    }
    this.pressStart = null;
  }

  /* ── Edit mode ──────────────────────────────────────────── */

  private enterEditMode(): void {
    if (this.editMode) return;
    this.editMode = true;
    this.grid.classList.add("edit-mode");
    this.showDoneButton();
  }

  private exitEditMode(): void {
    if (!this.editMode) return;
    this.editMode = false;
    this.grid.classList.remove("edit-mode");
    this.doneBtn?.remove();
    this.doneBtn = null;
    this.persistOrder();
  }

  private showDoneButton(): void {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "launcher-edit-done";
    btn.textContent = "Done";
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      this.exitEditMode();
    });
    document.body.appendChild(btn);
    this.doneBtn = btn;
  }

  /* ── Drag to reorder ────────────────────────────────────── */

  private beginDrag(e: PointerEvent, tile: HTMLElement): void {
    if (this.dragTile) return;
    this.dragTile = tile;
    this.dragPointerId = e.pointerId;
    this.suppressClick = false;
    tile.classList.add("dragging");
    document.addEventListener("pointermove", this.onDragMove);
    document.addEventListener("pointerup", this.onDragEnd);
    document.addEventListener("pointercancel", this.onDragEnd);
  }

  private handleDragMove(e: PointerEvent): void {
    if (!this.dragTile) return;
    if (this.dragPointerId !== null && e.pointerId !== this.dragPointerId) {
      return;
    }
    e.preventDefault();
    this.suppressClick = true; // movement means this was a drag, not a tap

    const under = document.elementFromPoint(
      e.clientX,
      e.clientY,
    ) as HTMLElement | null;
    const over = under?.closest<HTMLElement>(".launcher-tile") || null;
    if (!over || over === this.dragTile || over.parentElement !== this.grid) {
      return;
    }

    // Insert in the direction of travel so tiles push out of the way.
    const order = Array.from(
      this.grid.querySelectorAll<HTMLElement>(".launcher-tile"),
    );
    const from = order.indexOf(this.dragTile);
    const to = order.indexOf(over);
    if (from < to) {
      this.grid.insertBefore(this.dragTile, over.nextSibling);
    } else {
      this.grid.insertBefore(this.dragTile, over);
    }
  }

  private handleDragEnd(e: PointerEvent): void {
    if (!this.dragTile) return;
    if (this.dragPointerId !== null && e.pointerId !== this.dragPointerId) {
      return;
    }
    this.dragTile.classList.remove("dragging");
    this.dragTile = null;
    this.dragPointerId = null;
    document.removeEventListener("pointermove", this.onDragMove);
    document.removeEventListener("pointerup", this.onDragEnd);
    document.removeEventListener("pointercancel", this.onDragEnd);

    if (this.suppressClick) {
      this.persistOrder();
      // Let the click that trails pointerup be swallowed, then reset.
      window.setTimeout(() => {
        this.suppressClick = false;
      }, 0);
    }
  }

  private async persistOrder(): Promise<void> {
    const order = Array.from(
      this.grid.querySelectorAll<HTMLElement>(".launcher-tile"),
    )
      .map((t) => t.dataset.module || "")
      .filter(Boolean);
    if (!order.length) return;
    try {
      const resp = await fetch("/apps/store/api/reorder/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrf(),
        },
        credentials: "same-origin",
        body: JSON.stringify({ order }),
      });
      if (!resp.ok) showToast("Could not save the new app order.", "warning");
    } catch {
      showToast("Could not save order — network error.", "error");
    }
  }

  /* ── Context popover (right-click) ──────────────────────── */

  private openPopover(tile: HTMLElement): void {
    this.closePopover();

    const moduleName = tile.dataset.module || "";
    const pinned = tile.dataset.pinned === "1";
    const pop = document.createElement("div");
    pop.className = "launcher-popover";
    pop.setAttribute("role", "menu");

    pop.appendChild(
      this.popItem(
        "fas fa-arrow-right",
        "Open",
        () => {
          window.location.href = tile.getAttribute("href") || "/";
        },
        true,
      ),
    );
    pop.appendChild(
      this.popItem(
        "fas fa-thumbtack",
        pinned ? "Unpin from sidebar" : "Pin to sidebar",
        () => this.togglePin(moduleName),
      ),
    );
    pop.appendChild(
      this.popItem("fas fa-up-down-left-right", "Rearrange apps", () =>
        this.enterEditMode(),
      ),
    );
    const sep = document.createElement("div");
    sep.className = "launcher-pop-sep";
    pop.appendChild(sep);
    pop.appendChild(
      this.popItem("fas fa-circle-info", "Details", () => {
        window.location.href = tile.dataset.detailUrl || "/apps/store/";
      }),
    );

    document.body.appendChild(pop);
    this.popover = pop;
    this.positionPopover(tile, pop);

    this.grid.classList.add("popover-open");
    tile.classList.add("popover-anchor");
  }

  /**
   * Place the popover under the tile; flip above when it would overflow
   * the viewport bottom, and shift horizontally to stay on screen.
   */
  private positionPopover(tile: HTMLElement, pop: HTMLElement): void {
    const rect = tile.getBoundingClientRect();
    const popRect = pop.getBoundingClientRect();
    const margin = 8;

    let top = rect.bottom + 4;
    if (top + popRect.height > window.innerHeight - margin) {
      top = rect.top - popRect.height - 4; // flip above
    }
    if (top < margin) top = margin;

    let left = rect.left + rect.width / 2 - popRect.width / 2;
    left = Math.max(
      margin,
      Math.min(left, window.innerWidth - popRect.width - margin),
    );

    pop.style.top = `${top}px`;
    pop.style.left = `${left}px`;
  }

  private popItem(
    icon: string,
    label: string,
    onClick: () => void,
    primary = false,
  ): HTMLElement {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `launcher-pop-item${primary ? " primary" : ""}`;
    btn.setAttribute("role", "menuitem");
    const i = document.createElement("i");
    i.className = icon;
    i.setAttribute("aria-hidden", "true");
    btn.appendChild(i);
    btn.appendChild(document.createTextNode(` ${label}`));
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.closePopover();
      onClick();
    });
    return btn;
  }

  private closePopover(): void {
    this.popover?.remove();
    this.popover = null;
    this.grid.classList.remove("popover-open");
    this.grid
      .querySelectorAll(".popover-anchor")
      .forEach((t) => t.classList.remove("popover-anchor"));
  }

  /* ── Pin persistence ────────────────────────────────────── */

  private async togglePin(moduleName: string): Promise<void> {
    try {
      const resp = await fetch(`/apps/store/api/${moduleName}/pin/`, {
        method: "POST",
        headers: { "X-CSRFToken": getCsrf() },
        credentials: "same-origin",
      });
      const data = await resp.json();
      if (!resp.ok || !data.success) {
        showToast(data.error || "Could not update pin.", "warning");
        return;
      }
      // Sidebar pins are server-rendered — reload to reflect the change.
      window.location.reload();
    } catch {
      showToast("Could not update pin — network error.", "error");
    }
  }
}

/**
 * Re-parent the mobile dock to <body>. position:fixed resolves against
 * the nearest transformed/zoomed ancestor, and the dock is rendered
 * inside the workspace pane stack — a transform or CSS zoom anywhere up
 * that chain (e.g. context-zoom) makes the "fixed" dock float mid-screen
 * (operator's live iOS screenshot, msgs 608-610). <body> has no such
 * ancestor, so the dock reliably pins to the viewport bottom.
 */
function anchorDockToViewport(): void {
  const dock = document.querySelector<HTMLElement>(".launcher-dock");
  if (dock && dock.parentElement !== document.body) {
    document.body.appendChild(dock);
  }
}

function initLauncher(): void {
  anchorDockToViewport();
  const grid = document.getElementById("launcher-grid");
  if (!grid) return;
  new AppLauncher(grid).init();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initLauncher);
} else {
  initLauncher();
}

export { AppLauncher };
