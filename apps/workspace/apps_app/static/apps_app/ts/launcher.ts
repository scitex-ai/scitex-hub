/**
 * App Launcher — workspace home grid (approved design 2026-07-07).
 *
 * Behaviour:
 * - Instant search filter + category chips (client-side, same data
 *   attributes as the Store grid).
 * - Ctrl+K focuses the search input.
 * - Context popover (right-click / long-press) with Open, Pin to
 *   sidebar, and Details. The popover flips above the tile when it
 *   would overflow the viewport bottom, shifts horizontally to stay
 *   on screen, and dims the rest of the grid while open.
 * - Pin to sidebar persists via POST /apps/store/api/<module>/pin/
 *   (capped server-side).
 */

import { showToast } from "@utils/ui";

const LONG_PRESS_MS = 450;

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
  private searchInput: HTMLInputElement | null;
  private emptyEl: HTMLElement | null;
  private chips: HTMLElement[];
  private activeCategory = "";
  private popover: HTMLElement | null = null;
  private longPressTimer: number | null = null;

  constructor(grid: HTMLElement) {
    this.grid = grid;
    this.tiles = Array.from(
      grid.querySelectorAll<HTMLElement>(".launcher-tile"),
    );
    this.searchInput = document.getElementById(
      "launcher-search-input",
    ) as HTMLInputElement | null;
    this.emptyEl = document.getElementById("launcher-empty");
    this.chips = Array.from(
      document.querySelectorAll<HTMLElement>(".launcher-chip"),
    );
  }

  init(): void {
    this.searchInput?.addEventListener("input", () => this.applyFilters());

    this.chips.forEach((chip) => {
      chip.addEventListener("click", () => {
        this.chips.forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        this.activeCategory = chip.dataset.filterCategory || "";
        this.applyFilters();
      });
    });

    document.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k" && this.searchInput) {
        e.preventDefault();
        this.searchInput.focus();
        this.searchInput.select();
      }
      if (e.key === "Escape") this.closePopover();
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

  /* ── Filtering ──────────────────────────────────────────── */

  private applyFilters(): void {
    const query = (this.searchInput?.value || "").toLowerCase().trim();
    let visible = 0;

    this.tiles.forEach((tile) => {
      const catMatch =
        !this.activeCategory || tile.dataset.category === this.activeCategory;
      const text = `${tile.dataset.label} ${tile.dataset.module}`.toLowerCase();
      const textMatch = !query || text.indexOf(query) !== -1;
      const show = catMatch && textMatch;
      tile.hidden = !show;
      if (show) visible++;
    });

    if (this.emptyEl) this.emptyEl.hidden = visible !== 0;
  }

  /* ── Context popover ────────────────────────────────────── */

  private bindTile(tile: HTMLElement): void {
    tile.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      this.openPopover(tile);
    });

    // Long-press (touch) opens the popover instead of navigating
    tile.addEventListener("touchstart", () => {
      this.longPressTimer = window.setTimeout(() => {
        this.longPressTimer = null;
        this.openPopover(tile);
      }, LONG_PRESS_MS);
    });
    const cancelPress = () => {
      if (this.longPressTimer !== null) {
        clearTimeout(this.longPressTimer);
        this.longPressTimer = null;
      }
    };
    tile.addEventListener("touchend", cancelPress);
    tile.addEventListener("touchmove", cancelPress);
  }

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
   * the viewport bottom, and shift horizontally to stay on screen —
   * it must never sit over the tile row beneath unseen.
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
