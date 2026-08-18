/**
 * App Launcher — workspace home grid (approved design 2026-07-07).
 *
 * Behaviour:
 * - Tap a tile to open the app.
 * - Right-click (desktop) opens a context popover: Open, Pin to sidebar,
 *   Rearrange apps, Details (see _launcher/popover.ts).
 * - Long-press (touch or mouse) enters iPhone-style EDIT MODE: every tile
 *   jiggles — including the one you are dragging — and can be dragged to a
 *   new slot. Tapping anywhere OUTSIDE a tile (or Escape) exits; there is
 *   deliberately no "Done" pill. The order persists via POST api/reorder/.
 * - On mobile the tiles are laid out in horizontal PAGES that fit above the
 *   dock (see _launcher/pager.ts). Drag a tile to the left/right edge and hold
 *   to carry it to the next page.
 * - Pin to sidebar persists via POST /apps/store/api/<module>/pin/.
 *
 * The drag code is deliberately page-AGNOSTIC: it inserts relative to the tile
 * you are over, into THAT tile's parent, and reads the resulting order straight
 * off the DOM. So the same path serves the flat desktop grid and the paged
 * mobile grid, and there is no second ordering model to keep in sync.
 */

import { showToast } from "@utils/ui";

import { getCsrf } from "./_launcher/csrf";
import { LauncherPager } from "./_launcher/pager";
import { LauncherPopover } from "./_launcher/popover";

// Hold this long before the grid enters jiggle/edit mode.
const LONG_PRESS_MS = 420;
// Finger travel (px) that reads as a scroll and cancels the long-press.
// On a paged grid this is also what lets a horizontal SWIPE turn the page
// instead of picking a tile up.
const MOVE_CANCEL_PX = 10;
// Must match the launcher mobile breakpoint (launcher/mobile.css): the
// same width that swaps the sidebar for the dock also decides where
// "desktop-only" starts to matter, so badge and behaviour cannot disagree.
const MOBILE_BREAKPOINT_QUERY = "(max-width: 767px)";

/**
 * Availability gate — the tile state is a registry/catalog FIELD rendered
 * into data-availability (operator, Telegram 1483: communicate can/cannot
 * AT the icon). Coming-soon tiles already carry no href (server-side);
 * blocking here is defence in depth. Desktop-only tiles keep their href,
 * but a phone tap gets an explanatory toast instead of a dead-end app.
 * Returns true when the launch was blocked.
 */
function blockUnavailableLaunch(e: Event, tile: HTMLElement): boolean {
  const availability = tile.dataset.availability || "available";
  if (availability === "coming_soon") {
    e.preventDefault();
    return true;
  }
  if (
    availability === "desktop_only" &&
    window.matchMedia(MOBILE_BREAKPOINT_QUERY).matches
  ) {
    e.preventDefault();
    const label = tile.dataset.label || "This app";
    showToast(`${label} is desktop-only — open it on a larger screen.`, "info");
    return true;
  }
  return false;
}

class AppLauncher {
  private grid: HTMLElement;
  private pager: LauncherPager;
  private popover: LauncherPopover;

  // Edit / drag state
  private editMode = false;
  private pressTimer: number | null = null;
  private pressStart: { x: number; y: number } | null = null;
  private dragTile: HTMLElement | null = null;
  private dragPointerId: number | null = null;
  private suppressClick = false;

  // Bound drag handlers so add/removeEventListener pair up.
  private onDragMove = (e: PointerEvent) => this.handleDragMove(e);
  private onDragEnd = (e: PointerEvent) => this.handleDragEnd(e);

  constructor(grid: HTMLElement, pager: LauncherPager) {
    this.grid = grid;
    this.pager = pager;
    this.popover = new LauncherPopover(grid, {
      onRearrange: () => this.enterEditMode(),
    });
  }

  init(): void {
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        this.popover.close();
        this.exitEditMode();
      }
    });

    // Bound on the grid, not per tile: the pager re-parents tiles into pages
    // on every relayout, and per-tile listeners would have to be re-attached
    // each time (and would leak if we forgot). Delegation survives re-chunking.
    this.grid.addEventListener("dragstart", (e) => {
      // Tiles are <a>. The native link-drag hijacks a press-and-move and
      // swallows pointermove, so our reorder would silently do nothing.
      if ((e.target as HTMLElement).closest(".launcher-tile")) {
        e.preventDefault();
      }
    });
    this.grid.addEventListener("contextmenu", (e) => {
      const tile = (e.target as HTMLElement).closest<HTMLElement>(
        ".launcher-tile",
      );
      if (!tile) return;
      e.preventDefault();
      this.popover.open(tile);
    });
    this.grid.addEventListener("pointerdown", (e) => {
      const tile = (e.target as HTMLElement).closest<HTMLElement>(
        ".launcher-tile",
      );
      if (tile) this.handlePointerDown(e, tile);
    });
    this.grid.addEventListener("click", (e) => {
      const tile = (e.target as HTMLElement).closest<HTMLElement>(
        ".launcher-tile",
      );
      if (!tile) return;
      if (this.editMode || this.suppressClick) {
        e.preventDefault();
        e.stopPropagation();
        return;
      }
      blockUnavailableLaunch(e, tile);
    });

    document.addEventListener("click", (e) => {
      const target = e.target as HTMLElement | null;
      if (this.popover.isOpen && target && !this.popover.contains(target)) {
        this.popover.close();
      }
      // There is no "Done" pill any more: tapping anywhere OUTSIDE a tile
      // leaves edit mode (the iOS-home gesture the operator asked for).
      // Ignore taps on the dock (those navigate), the page dots, and the
      // trailing click of a drag we have only just finished.
      if (
        this.editMode &&
        !this.dragTile &&
        !this.suppressClick &&
        target &&
        !target.closest(".launcher-tile") &&
        !target.closest(".launcher-dots") &&
        !target.closest(".launcher-dock")
      ) {
        this.exitEditMode();
      }
    });
    window.addEventListener("resize", () => this.popover.close());
    window.addEventListener("scroll", () => this.popover.close(), true);
  }

  /* ── Long-press detection ───────────────────────────────── */

  private handlePointerDown(e: PointerEvent, tile: HTMLElement): void {
    if (this.popover.isOpen) this.popover.close();
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
  }

  private exitEditMode(): void {
    if (!this.editMode) return;
    this.editMode = false;
    this.grid.classList.remove("edit-mode");
    this.pager.cancelEdgeTurn();
    this.persistOrder();
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

    // Hold against an edge to carry the tile to the next/previous page.
    this.pager.edgeTurn(e.clientX);

    const under = document.elementFromPoint(
      e.clientX,
      e.clientY,
    ) as HTMLElement | null;
    const over = under?.closest<HTMLElement>(".launcher-tile") || null;
    if (!over || over === this.dragTile || !this.grid.contains(over)) {
      return;
    }

    // Insert in the direction of travel so tiles push out of the way. The
    // parent is the tile we are OVER — on a paged grid that is its page, which
    // is what lets a tile move between pages at all.
    const order = Array.from(
      this.grid.querySelectorAll<HTMLElement>(".launcher-tile"),
    );
    const from = order.indexOf(this.dragTile);
    const to = order.indexOf(over);
    const dragged = this.dragTile;
    const host = over.parentElement;
    if (!host) return;

    this.reorderWithTravel(() => {
      if (from < to) {
        host.insertBefore(dragged, over.nextSibling);
      } else {
        host.insertBefore(dragged, over);
      }
    });
  }

  /**
   * Reorder the DOM and let the affected tiles VISIBLY travel to their new
   * slots, instead of teleporting.
   *
   * A bare insertBefore makes every displaced tile jump instantly, which reads
   * as a glitch — you cannot see what moved where, and it startles people.
   * FLIP: measure each tile, mutate the DOM, measure again, then animate each
   * from where it *was* to where it now *is*.
   *
   * composite: "add" is load-bearing. In edit mode the tiles carry a jiggle
   * (a rotate animation), and a plain transform keyframe would overwrite it —
   * the tile would stop wobbling mid-drag. Compositing ADDS our translate on
   * top of whatever rotation is running, so both survive.
   *
   * The travel is kept even under prefers-reduced-motion — it is not
   * decoration, it is the feedback that tells you where the tile went; hiding
   * it is what causes the startle. We only shorten it.
   */
  private reorderWithTravel(mutate: () => void): void {
    const tiles = Array.from(
      this.grid.querySelectorAll<HTMLElement>(".launcher-tile"),
    );
    const before = new Map<HTMLElement, DOMRect>();
    tiles.forEach((t) => before.set(t, t.getBoundingClientRect()));

    mutate();

    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const duration = reduced ? 120 : 200;

    tiles.forEach((tile) => {
      const start = before.get(tile);
      if (!start) return;
      const end = tile.getBoundingClientRect();
      const dx = start.left - end.left;
      const dy = start.top - end.top;
      if (dx === 0 && dy === 0) return;
      tile.animate(
        [
          { transform: `translate(${dx}px, ${dy}px)` },
          { transform: "translate(0px, 0px)" },
        ],
        {
          duration,
          easing: "cubic-bezier(0.2, 0, 0, 1)",
          composite: "add",
        },
      );
    });
  }

  private handleDragEnd(e: PointerEvent): void {
    if (!this.dragTile) return;
    if (this.dragPointerId !== null && e.pointerId !== this.dragPointerId) {
      return;
    }
    this.dragTile.classList.remove("dragging");
    this.dragTile = null;
    this.dragPointerId = null;
    this.pager.cancelEdgeTurn();
    document.removeEventListener("pointermove", this.onDragMove);
    document.removeEventListener("pointerup", this.onDragEnd);
    document.removeEventListener("pointercancel", this.onDragEnd);

    if (this.suppressClick) {
      // A tile dropped onto a full page leaves that page one over capacity;
      // re-chunk so the overflow pushes right (iOS does the same).
      this.pager.rebalance();
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
  // Must run BEFORE the pager measures: the pager sizes its pages against the
  // dock's rect, and the dock only sits at the viewport bottom once re-parented.
  anchorDockToViewport();

  const grid = document.getElementById("launcher-grid");
  const dots = document.getElementById("launcher-dots");
  if (!grid || !dots) return;

  const pager = new LauncherPager(grid, dots);
  pager.init();
  new AppLauncher(grid, pager).init();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initLauncher);
} else {
  initLauncher();
}

export { AppLauncher };
