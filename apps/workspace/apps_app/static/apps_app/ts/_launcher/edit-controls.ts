import { showToast } from "@utils/ui";
import { getCsrf } from "./csrf";

export class LauncherEditControls {
  private tile: HTMLElement | null = null;
  private dialog = document.getElementById("launcher-display-dialog") as HTMLDialogElement | null;

  constructor(private grid: HTMLElement, private rebalance: () => void) {}

  init(): void {
    const syncTabStops = () => this.grid.querySelectorAll<HTMLElement>(".launcher-edit-control")
      .forEach((el) => { el.tabIndex = this.grid.classList.contains("edit-mode") ? 0 : -1; });
    new MutationObserver(syncTabStops).observe(this.grid, { attributes: true, attributeFilter: ["class"] });
    syncTabStops();
    this.grid.addEventListener("pointerdown", (event) => {
      if ((event.target as HTMLElement).closest(".launcher-edit-control")) event.stopImmediatePropagation();
    }, true);
    this.grid.addEventListener("keydown", (event) => {
      const control = (event.target as HTMLElement).closest<HTMLElement>(".launcher-edit-control");
      if (control && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        control.click();
      }
    });
    this.grid.addEventListener("click", (event) => {
      const control = (event.target as HTMLElement).closest<HTMLElement>(".launcher-edit-control");
      const tile = control?.closest<HTMLElement>(".launcher-tile");
      if (!control || !tile || !this.grid.classList.contains("edit-mode")) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      control.classList.contains("launcher-uninstall-control")
        ? void this.uninstall(tile)
        : this.open(tile);
    }, true);
    document.getElementById("launcher-display-cancel")?.addEventListener("click", () => this.dialog?.close());
    document.getElementById("launcher-display-reset")?.addEventListener("click", () => void this.save(true));
    document.getElementById("launcher-display-favorite")?.addEventListener("click", () => void this.toggleFavorite());
    document.getElementById("launcher-display-uninstall")?.addEventListener("click", () => {
      if (this.tile) void this.uninstall(this.tile, true);
    });
    document.getElementById("launcher-display-form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      void this.save(false);
    });
  }

  private async post(url: string, body?: object): Promise<Record<string, unknown>> {
    const response = await fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": getCsrf(), ...(body ? { "Content-Type": "application/json" } : {}) },
      credentials: "same-origin",
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.error || "Request failed.");
    return result;
  }

  private async uninstall(tile: HTMLElement, fromDialog = false): Promise<void> {
    const name = tile.dataset.module || "";
    const label = tile.dataset.label || name;
    if (!name || !window.confirm(`Uninstall ${label}?`)) return;
    try {
      await this.post(`/apps/store/api/${encodeURIComponent(name)}/uninstall/`);
      if (fromDialog) this.dialog?.close();
      this.grid.querySelectorAll<HTMLElement>(".launcher-tile")
        .forEach((matching) => {
          if (matching.dataset.module === name) matching.remove();
        });
      this.rebalance();
      showToast(`${label} uninstalled.`, "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Could not uninstall app.", "error");
    }
  }

  private input(id: string): HTMLInputElement {
    return document.getElementById(id) as HTMLInputElement;
  }

  open(tile: HTMLElement): void {
    if (!this.dialog) return;
    this.tile = tile;
    this.input("launcher-display-name").value = tile.dataset.label || "";
    this.input("launcher-display-icon").value = tile.querySelector(".launcher-tile-icon > i")?.className || "";
    const box = tile.querySelector<HTMLElement>(".launcher-tile-icon");
    this.input("launcher-display-color").value = box?.style.getPropertyValue("--launcher-glyph-color").trim() || "#ffffff";
    const uninstall = document.getElementById("launcher-display-uninstall") as HTMLButtonElement | null;
    if (uninstall) uninstall.hidden = !tile.querySelector(".launcher-uninstall-control");
    this.syncFavoriteButton(tile.dataset.favorite === "1");
    this.dialog.showModal();
  }

  private syncFavoriteButton(favorite: boolean): void {
    const button = document.getElementById("launcher-display-favorite");
    if (button) button.innerHTML = `<i class="${favorite ? "fas" : "far"} fa-star" aria-hidden="true"></i> ${favorite ? "Remove from Favorites" : "Add to Favorites"}`;
  }

  private async toggleFavorite(): Promise<void> {
    const name = this.tile?.dataset.module || "";
    if (!name) return;
    const favorite = this.tile?.dataset.favorite !== "1";
    try {
      await this.post(`/apps/store/api/${encodeURIComponent(name)}/launcher-display/`, { favorite });
      this.grid.querySelectorAll<HTMLElement>(".launcher-tile")
        .forEach((tile) => {
          if (tile.dataset.module === name) tile.dataset.favorite = favorite ? "1" : "0";
        });
      this.syncFavoritePage(name, favorite);
      this.syncFavoriteButton(favorite);
      showToast(favorite ? "Added to Favorites." : "Removed from Favorites.", "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Could not update Favorites.", "error");
    }
  }

  private syncFavoritePage(name: string, favorite: boolean): void {
    const page = this.grid.querySelector<HTMLElement>("[data-launcher-fixed-page='favorites']");
    if (!page) return;
    const aliases = Array.from(page.querySelectorAll<HTMLElement>("[data-favorite-alias]"))
      .filter((tile) => tile.dataset.module === name);
    if (!favorite) {
      aliases.forEach((tile) => tile.remove());
      if (!page.querySelector("[data-favorite-alias]")) {
        page.innerHTML = '<div class="launcher-favorites-empty"><i class="far fa-star" aria-hidden="true"></i><strong>No favorites yet</strong><span>Edit an app to add a shortcut here.</span></div>';
      }
      return;
    }
    if (aliases.length) return;
    const source = Array.from(this.grid.querySelectorAll<HTMLElement>(".launcher-tile:not([data-favorite-alias])"))
      .find((tile) => tile.dataset.module === name);
    if (!source) return;
    page.querySelector(".launcher-favorites-empty")?.remove();
    let group = page.querySelector<HTMLElement>(".launcher-favorites-grid");
    if (!group) {
      group = document.createElement("div");
      group.className = "launcher-group launcher-favorites-grid";
      group.dataset.group = "favorites";
      group.setAttribute("role", "group");
      group.setAttribute("aria-label", "Favorites");
      page.appendChild(group);
    }
    const alias = source.cloneNode(true) as HTMLElement;
    alias.dataset.favoriteAlias = "1";
    alias.querySelector(".launcher-uninstall-control")?.remove();
    group.appendChild(alias);
  }

  private async save(reset: boolean): Promise<void> {
    const tile = this.tile;
    const name = tile?.dataset.module || "";
    if (!tile || !name) return;
    const values = {
      display_name: this.input("launcher-display-name").value,
      icon: this.input("launcher-display-icon").value,
      icon_color: this.input("launcher-display-color").value,
    };
    try {
      await this.post(`/apps/store/api/${encodeURIComponent(name)}/launcher-display/`, reset ? { reset: true } : values);
      const label = reset ? tile.dataset.manifestLabel || name : values.display_name;
      const icon = reset ? tile.dataset.manifestIcon || "fas fa-puzzle-piece" : values.icon;
      tile.dataset.label = label;
      const labelNode = tile.querySelector<HTMLElement>(".launcher-tile-name");
      if (labelNode) labelNode.textContent = label;
      const iconNode = tile.querySelector<HTMLElement>(".launcher-tile-icon > i");
      if (iconNode) iconNode.className = icon;
      tile.querySelector<HTMLElement>(".launcher-tile-icon")?.style.setProperty("--launcher-glyph-color", reset ? "" : values.icon_color);
      tile.querySelector(".launcher-uninstall-control")?.setAttribute("aria-label", `Uninstall ${label}`);
      tile.querySelector(".launcher-display-control")?.setAttribute("aria-label", `Edit ${label} display`);
      this.dialog?.close();
      showToast(reset ? "Manifest display restored." : "App display saved.", "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Could not save display.", "error");
    }
  }
}
