/**
 * Launcher context popover (desktop right-click): Open, Pin, Rearrange,
 * Details. Extracted from launcher.ts so that file stays under the 512-line
 * limit once the pager landed (CLAUDE.md file-size rule).
 *
 * The popover flips above the tile when it would overflow the viewport bottom
 * and shifts horizontally to stay on screen.
 */

import { showToast } from "@utils/ui";

import { getCsrf } from "./csrf";

export interface PopoverActions {
  onRearrange: () => void;
}

export class LauncherPopover {
  private grid: HTMLElement;
  private actions: PopoverActions;
  private el: HTMLElement | null = null;

  constructor(grid: HTMLElement, actions: PopoverActions) {
    this.grid = grid;
    this.actions = actions;
  }

  get isOpen(): boolean {
    return this.el !== null;
  }

  contains(node: Node): boolean {
    return this.el !== null && this.el.contains(node);
  }

  open(tile: HTMLElement): void {
    this.close();

    const moduleName = tile.dataset.module || "";
    const pinned = tile.dataset.pinned === "1";
    const pop = document.createElement("div");
    pop.className = "launcher-popover";
    pop.setAttribute("role", "menu");

    pop.appendChild(
      this.item(
        "fas fa-arrow-right",
        "Open",
        () => {
          window.location.href = tile.getAttribute("href") || "/";
        },
        true,
      ),
    );
    pop.appendChild(
      this.item(
        "fas fa-thumbtack",
        pinned ? "Unpin from sidebar" : "Pin to sidebar",
        () => this.togglePin(moduleName),
      ),
    );
    pop.appendChild(
      this.item("fas fa-up-down-left-right", "Rearrange apps", () =>
        this.actions.onRearrange(),
      ),
    );
    const sep = document.createElement("div");
    sep.className = "launcher-pop-sep";
    pop.appendChild(sep);
    pop.appendChild(
      this.item("fas fa-circle-info", "Details", () => {
        window.location.href = tile.dataset.detailUrl || "/apps/store/";
      }),
    );

    document.body.appendChild(pop);
    this.el = pop;
    this.position(tile, pop);

    this.grid.classList.add("popover-open");
    tile.classList.add("popover-anchor");
  }

  close(): void {
    this.el?.remove();
    this.el = null;
    this.grid.classList.remove("popover-open");
    this.grid
      .querySelectorAll(".popover-anchor")
      .forEach((t) => t.classList.remove("popover-anchor"));
  }

  /** Under the tile; flipped above when it would overflow the viewport. */
  private position(tile: HTMLElement, pop: HTMLElement): void {
    const rect = tile.getBoundingClientRect();
    const popRect = pop.getBoundingClientRect();
    const margin = 8;

    let top = rect.bottom + 4;
    if (top + popRect.height > window.innerHeight - margin) {
      top = rect.top - popRect.height - 4;
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

  private item(
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
      this.close();
      onClick();
    });
    return btn;
  }

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
