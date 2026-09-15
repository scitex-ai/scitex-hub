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

  private async uninstall(tile: HTMLElement): Promise<void> {
    const name = tile.dataset.module || "";
    const label = tile.dataset.label || name;
    if (!name || !window.confirm(`Uninstall ${label}?`)) return;
    try {
      await this.post(`/apps/store/api/${encodeURIComponent(name)}/uninstall/`);
      tile.remove();
      this.rebalance();
      showToast(`${label} uninstalled.`, "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Could not uninstall app.", "error");
    }
  }

  private input(id: string): HTMLInputElement {
    return document.getElementById(id) as HTMLInputElement;
  }

  private open(tile: HTMLElement): void {
    if (!this.dialog) return;
    this.tile = tile;
    this.input("launcher-display-name").value = tile.dataset.label || "";
    this.input("launcher-display-icon").value = tile.querySelector(".launcher-tile-icon > i")?.className || "";
    const box = tile.querySelector<HTMLElement>(".launcher-tile-icon");
    this.input("launcher-display-color").value = box?.style.getPropertyValue("--launcher-glyph-color").trim() || "#ffffff";
    this.dialog.showModal();
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
