/**
 * Planned-app sheet: tapping a Coming-soon tile shows what the app will do,
 * with "Notify me" and "Build this app". Both record interest server-side
 * (POST /apps/store/api/planned/<id>/interest/, idempotent per user).
 */

import { showToast } from "@utils/ui";

import { getCsrf } from "./csrf";

export class PlannedSheet {
  private dialog: HTMLDialogElement;
  private tile: HTMLElement | null = null;

  constructor(dialog: HTMLDialogElement) {
    this.dialog = dialog;
  }

  init(): void {
    this.dialog
      .querySelector<HTMLElement>("[data-planned-notify]")
      ?.addEventListener("click", () => this.notify());
    this.dialog
      .querySelector<HTMLAnchorElement>("[data-planned-build]")
      ?.addEventListener("click", () => {
        const app = this.tile?.dataset.planned;
        // keepalive lets the POST finish while the link navigates away.
        if (app) void this.record(app, "build", true);
      });
    // A tap on the backdrop (outside the sheet box) closes it.
    this.dialog.addEventListener("click", (e) => {
      if (e.target === this.dialog) this.dialog.close();
    });
  }

  open(tile: HTMLElement): void {
    this.tile = tile;
    const icon = this.dialog.querySelector<HTMLElement>("[data-planned-icon]");
    if (icon) {
      icon.dataset.tileCategory = tile.dataset.category || "other";
      icon.replaceChildren(
        tile.querySelector(".launcher-tile-icon > i")?.cloneNode(false) ?? "",
      );
    }
    this.setText("[data-planned-title]", tile.dataset.label || "");
    this.setText("[data-planned-description]", tile.dataset.description || "");
    const build = this.dialog.querySelector<HTMLAnchorElement>(
      "[data-planned-build]",
    );
    if (build) build.href = tile.dataset.createUrl || "/apps/create/";
    this.renderNotified(tile.dataset.notified === "1");
    this.dialog.showModal();
  }

  private setText(selector: string, text: string): void {
    const el = this.dialog.querySelector<HTMLElement>(selector);
    if (el) el.textContent = text;
  }

  private renderNotified(done: boolean): void {
    const button = this.dialog.querySelector<HTMLButtonElement>(
      "[data-planned-notify]",
    );
    const label = this.dialog.querySelector<HTMLElement>(
      "[data-planned-notify-label]",
    );
    if (!button || !label) return;
    button.disabled = done;
    button.classList.toggle("planned-sheet-btn--done", done);
    label.textContent =
      (done ? button.dataset.labelDone : button.dataset.labelIdle) || "";
  }

  private async notify(): Promise<void> {
    const tile = this.tile;
    const app = tile?.dataset.planned;
    if (!tile || !app) return;
    if (await this.record(app, "notify", false)) {
      tile.dataset.notified = "1";
      this.renderNotified(true);
    }
  }

  private async record(
    app: string,
    kind: "notify" | "build",
    keepalive: boolean,
  ): Promise<boolean> {
    try {
      const response = await fetch(
        `/apps/store/api/planned/${encodeURIComponent(app)}/interest/`,
        {
          method: "POST",
          headers: { "X-CSRFToken": getCsrf() },
          credentials: "same-origin",
          body: new URLSearchParams({ kind }),
          keepalive,
        },
      );
      if (!response.ok) showToast("Could not save your interest.", "warning");
      return response.ok;
    } catch {
      showToast("Could not save your interest: network error.", "error");
      return false;
    }
  }
}
