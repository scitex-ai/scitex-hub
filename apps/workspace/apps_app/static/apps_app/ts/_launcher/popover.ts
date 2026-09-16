/**
 * Launcher context popover (desktop right-click): Open, Edit Display,
 * Rearrange, and View in App Store.
 * limit once the pager landed (CLAUDE.md file-size rule).
 *
 * The popover flips above the tile when it would overflow the viewport bottom
 * and shifts horizontally to stay on screen.
 */

export interface PopoverActions {
  onRearrange: () => void;
  onEditDisplay: (tile: HTMLElement) => void;
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

    const pop = document.createElement("div");
    pop.className = "launcher-popover";
    pop.setAttribute("role", "menu");

    // Coming-soon tiles have no href and must not navigate (availability
    // field, operator Telegram 1483) — offering "Open" here would be the
    // same dishonest tap the grid just removed. Details stays: the store
    // page is a truthful destination.
    if (tile.dataset.availability !== "coming_soon") {
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
    }
    // Link tiles open an existing Hub page and have no catalogue row, display
    // override, or App Store page.
    const linkOnly = tile.dataset.linkOnly === "1";
    if (!linkOnly) {
      pop.appendChild(
        this.item(
          "fas fa-pen",
          "Edit Display…",
          () => this.actions.onEditDisplay(tile),
        ),
      );
    }
    pop.appendChild(
      this.item("fas fa-up-down-left-right", "Rearrange apps", () =>
        this.actions.onRearrange(),
      ),
    );
    if (!linkOnly) {
      const sep = document.createElement("div");
      sep.className = "launcher-pop-sep";
      pop.appendChild(sep);
      pop.appendChild(
        this.item("fas fa-store", "View in App Store", () => {
          window.location.href = tile.dataset.detailUrl || "/apps/store/";
        }),
      );
    }

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

}
