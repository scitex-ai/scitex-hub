/**
 * Dock editor — drag apps from the Home grid into the site dock and back out.
 *
 * Each app lives in exactly one place. The grid drag in launcher.ts asks this
 * editor whether the pointer is over the dock; a long-press on a dock button
 * starts a drag of its own. The dock list is saved per user through
 * POST /apps/store/api/dock/, so the phone and the desktop show the same dock.
 */

import { showToast } from "@utils/ui";

import { getCsrf } from "./csrf";
import {
  type DockChange,
  dockCapacity,
  dockInsertIndex,
  dropIntoDock,
  dropOutOfDock,
  dropZoneFor,
  type Point,
} from "./dock-drop";
import type { LauncherPager } from "./pager";

export const HOME_BUTTON = "launcher";
const FIXED_DOCK_APPS = [HOME_BUTTON];
const LONG_PRESS_MS = 420;
const MOVE_CANCEL_PX = 10;
const REFUSE_ANIMATION_MS = 450;

export interface DockEditorHooks {
  enterEditMode: () => void;
  persistGridOrder: () => void;
}

export class DockEditor {
  private grid: HTMLElement;
  private pager: LauncherPager;
  private hooks: DockEditorHooks;
  private dock: HTMLElement | null;
  private apps: HTMLElement | null;
  private dockTiles: HTMLTemplateElement | null;
  private placeholder: HTMLElement | null = null;
  private draggedButton: HTMLElement | null = null;
  private ghost: HTMLElement | null = null;
  private suppressDockClick = false;

  private onButtonDragMove = (e: PointerEvent) => this.moveButtonDrag(e);
  private onButtonDragEnd = (e: PointerEvent) => this.endButtonDrag(e);

  constructor(grid: HTMLElement, pager: LauncherPager, hooks: DockEditorHooks) {
    this.grid = grid;
    this.pager = pager;
    this.hooks = hooks;
    this.dock = document.querySelector<HTMLElement>("[data-site-dock]");
    this.apps =
      this.dock?.querySelector<HTMLElement>("[data-dock-apps]") ?? null;
    this.dockTiles = document.getElementById(
      "launcher-dock-tiles",
    ) as HTMLTemplateElement | null;
  }

  get isDraggingButton(): boolean {
    return this.draggedButton !== null;
  }

  init(): void {
    const apps = this.apps;
    if (!apps) return;
    apps.addEventListener("pointerdown", (e) => {
      const button = (e.target as HTMLElement).closest<HTMLElement>(
        "[data-dock-item]",
      );
      if (button) this.pressButton(e, button);
    });
    apps.addEventListener("contextmenu", (e) => e.preventDefault());
    apps.addEventListener("dragstart", (e) => e.preventDefault());
    apps.addEventListener(
      "click",
      (e) => {
        if (!this.suppressDockClick) return;
        e.preventDefault();
        e.stopPropagation();
      },
      true,
    );
  }

  /* ── Grid tile over the dock (called from launcher.ts) ───── */

  /** True when the dragged grid tile is over the dock; shows where it would land. */
  trackTile(point: Point, tile: HTMLElement): boolean {
    if (dropZoneFor(point, this.dockBox()) !== "dock") {
      this.clearTileHint(tile);
      return false;
    }
    tile.classList.add("launcher-tile--to-dock");
    const full = this.names().length >= this.capacity();
    this.dock?.classList.toggle("site-dock--full", full);
    if (!full) this.showPlaceholder(point, tile);
    return true;
  }

  /** Drop a grid tile; returns true when the tile went into the dock. */
  dropTile(point: Point, tile: HTMLElement): boolean {
    const overDock = dropZoneFor(point, this.dockBox()) === "dock";
    const index = this.placeholderIndex();
    this.clearTileHint(tile);
    if (!overDock) return false;
    const app = tile.dataset.module || "";
    const change = dropIntoDock(
      this.names(),
      app,
      index ?? this.insertIndex(point.x),
      this.capacity(),
    );
    if (!change.accepted) {
      this.refuse(change);
      return false;
    }
    const slotAfter = this.buttons()[change.dock.indexOf(app)] ?? null;
    this.apps?.insertBefore(dockButtonFromTile(tile), slotAfter);
    this.dockTiles?.content.appendChild(tile);
    this.pager.rebalance();
    this.saveDock(change.dock);
    return true;
  }

  clearTileHint(tile: HTMLElement): void {
    tile.classList.remove("launcher-tile--to-dock");
    this.dock?.classList.remove("site-dock--full");
    this.placeholder?.remove();
    this.placeholder = null;
  }

  private showPlaceholder(point: Point, tile: HTMLElement): void {
    if (!this.apps) return;
    if (!this.placeholder) {
      this.placeholder = document.createElement("span");
      this.placeholder.className =
        "site-dock-item site-dock-app site-dock-placeholder";
      this.placeholder.setAttribute("aria-hidden", "true");
      const icon = tile.querySelector(".launcher-tile-icon")?.cloneNode(true);
      if (icon instanceof HTMLElement) {
        icon.className = "launcher-tile-icon site-dock-app-icon";
        icon
          .querySelectorAll(".launcher-badge, .launcher-tile-icon-badge")
          .forEach((badge) => badge.remove());
        this.placeholder.appendChild(icon);
      }
    }
    const index = this.insertIndex(point.x);
    const before = this.buttons()[index] ?? null;
    if (
      this.placeholder.nextElementSibling !== before ||
      !this.placeholder.isConnected
    ) {
      this.apps.insertBefore(this.placeholder, before);
    }
  }

  private placeholderIndex(): number | null {
    if (!this.placeholder?.isConnected || !this.apps) return null;
    return Array.from(this.apps.children)
      .filter((el) => el === this.placeholder || this.isButton(el))
      .indexOf(this.placeholder);
  }

  /* ── Dock button drag (long-press) ─────────────────────────── */

  private pressButton(down: PointerEvent, button: HTMLElement): void {
    if (down.pointerType === "mouse" && down.button !== 0) return;
    const start = { x: down.clientX, y: down.clientY };
    let timer: number | null = null;

    const cancel = () => {
      if (timer !== null) window.clearTimeout(timer);
      timer = null;
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", cancel);
      document.removeEventListener("pointercancel", cancel);
    };
    const onMove = (move: PointerEvent) => {
      if (
        Math.hypot(move.clientX - start.x, move.clientY - start.y) >
        MOVE_CANCEL_PX
      ) {
        cancel();
      }
    };
    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", cancel);
    document.addEventListener("pointercancel", cancel);
    timer = window.setTimeout(() => {
      cancel();
      this.hooks.enterEditMode();
      this.beginButtonDrag(down, button);
    }, LONG_PRESS_MS);
  }

  private beginButtonDrag(down: PointerEvent, button: HTMLElement): void {
    this.draggedButton = button;
    this.suppressDockClick = true;
    button.classList.add("site-dock-app--dragging");
    const icon = button.querySelector(".site-dock-app-icon")?.cloneNode(true);
    this.ghost = document.createElement("div");
    this.ghost.className = "site-dock-ghost";
    if (icon) this.ghost.appendChild(icon);
    document.body.appendChild(this.ghost);
    this.placeGhost({ x: down.clientX, y: down.clientY });
    document.addEventListener("pointermove", this.onButtonDragMove);
    document.addEventListener("pointerup", this.onButtonDragEnd);
    document.addEventListener("pointercancel", this.onButtonDragEnd);
  }

  private moveButtonDrag(e: PointerEvent): void {
    const button = this.draggedButton;
    if (!button || !this.apps) return;
    e.preventDefault();
    const point = { x: e.clientX, y: e.clientY };
    this.placeGhost(point);
    const overDock = dropZoneFor(point, this.dockBox()) === "dock";
    button.classList.toggle("site-dock-app--leaving", !overDock);
    if (!overDock) return;
    const before =
      this.buttons(button)[this.insertIndex(point.x, button)] ?? null;
    if (button.nextElementSibling !== before)
      this.apps.insertBefore(button, before);
  }

  private endButtonDrag(e: PointerEvent): void {
    const button = this.draggedButton;
    if (!button) return;
    document.removeEventListener("pointermove", this.onButtonDragMove);
    document.removeEventListener("pointerup", this.onButtonDragEnd);
    document.removeEventListener("pointercancel", this.onButtonDragEnd);
    this.ghost?.remove();
    this.ghost = null;
    this.draggedButton = null;
    button.classList.remove(
      "site-dock-app--dragging",
      "site-dock-app--leaving",
    );
    window.setTimeout(() => {
      this.suppressDockClick = false;
    }, 0);

    const point = { x: e.clientX, y: e.clientY };
    const app = button.dataset.dockItem || "";
    if (
      e.type === "pointercancel" ||
      dropZoneFor(point, this.dockBox()) === "dock"
    ) {
      this.saveDock(this.names());
      return;
    }
    const change = dropOutOfDock(this.names(), app, FIXED_DOCK_APPS);
    if (!change.accepted) {
      this.refuse(change);
      return;
    }
    const tile = this.dockTiles?.content.querySelector<HTMLElement>(
      `.launcher-tile[data-module="${CSS.escape(app)}"]`,
    );
    if (!tile) return;
    button.remove();
    this.placeTileOnGrid(tile, point);
    this.pager.rebalance();
    this.saveDock(change.dock);
    this.hooks.persistGridOrder();
  }

  private placeGhost(point: Point): void {
    if (!this.ghost) return;
    this.ghost.style.left = `${point.x}px`;
    this.ghost.style.top = `${point.y}px`;
  }

  /** Back on the grid: before the same-group tile under the finger, else at the end of its group. */
  private placeTileOnGrid(tile: HTMLElement, point: Point): void {
    const group = tile.dataset.group ?? "";
    const under = document
      .elementFromPoint(point.x, point.y)
      ?.closest<HTMLElement>(".launcher-tile");
    if (under && this.grid.contains(under) && under.dataset.group === group) {
      under.before(tile);
      return;
    }
    const bands = Array.from(
      this.grid.querySelectorAll<HTMLElement>(".launcher-group"),
    ).filter((band) => band.dataset.group === group);
    const lastBand = bands[bands.length - 1];
    if (lastBand) {
      lastBand.appendChild(tile);
      return;
    }
    this.newBandFor(group).appendChild(tile);
  }

  /** A band for a group that has no tiles left on the grid, in the groups' own order. */
  private newBandFor(group: string): HTMLElement {
    const template = this.dockTiles?.content.querySelector<HTMLElement>(
      `.launcher-group[data-group="${CSS.escape(group)}"]`,
    );
    const band =
      (template?.cloneNode(false) as HTMLElement | undefined) ??
      Object.assign(document.createElement("div"), {
        className: "launcher-group",
      });
    band.dataset.group = group;
    const groupOrder = Array.from(
      this.dockTiles?.content.querySelectorAll<HTMLElement>(
        ".launcher-group",
      ) ?? [],
    ).map((el) => el.dataset.group ?? "");
    const rank = groupOrder.indexOf(group);
    const later = Array.from(
      this.grid.querySelectorAll<HTMLElement>(".launcher-group"),
    ).find((el) => groupOrder.indexOf(el.dataset.group ?? "") > rank);
    const pages = this.grid.querySelectorAll(".launcher-page");
    const host = later?.parentElement ?? pages[pages.length - 1] ?? this.grid;
    host.insertBefore(band, later ?? null);
    return band;
  }

  /* ── Shared ────────────────────────────────────────────────── */

  private isButton(el: Element): el is HTMLElement {
    return el instanceof HTMLElement && el.hasAttribute("data-dock-item");
  }

  private buttons(except?: HTMLElement): HTMLElement[] {
    if (!this.apps) return [];
    return Array.from(this.apps.children).filter(
      (el): el is HTMLElement => this.isButton(el) && el !== except,
    );
  }

  private names(): string[] {
    return this.buttons().map((button) => button.dataset.dockItem || "");
  }

  private insertIndex(pointerX: number, except?: HTMLElement): number {
    const centers = this.buttons(except).map((button) => {
      const box = button.getBoundingClientRect();
      return box.left + box.width / 2;
    });
    return dockInsertIndex(pointerX, centers);
  }

  private capacity(): number {
    const serverCapacity =
      parseInt(this.dock?.dataset.dockCapacity ?? "", 10) || 5;
    return dockCapacity(this.apps?.clientWidth ?? 0, serverCapacity);
  }

  private dockBox(): DOMRect | null {
    const box = this.dock?.getBoundingClientRect();
    return box && box.width > 0 ? box : null;
  }

  private refuse(change: DockChange): void {
    const dock = this.dock;
    if (dock) {
      dock.classList.remove("site-dock--refused");
      void dock.offsetWidth; // restart the shake when refused twice in a row
      dock.classList.add("site-dock--refused");
      window.setTimeout(
        () => dock.classList.remove("site-dock--refused"),
        REFUSE_ANIMATION_MS,
      );
    }
    const message =
      change.refusal === "fixed"
        ? "Home always stays in the dock."
        : "The dock is full. Drag an app out of it first.";
    showToast(message, "info", 2500);
  }

  private async saveDock(dock: string[]): Promise<void> {
    try {
      const response = await fetch("/apps/store/api/dock/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrf(),
        },
        credentials: "same-origin",
        body: JSON.stringify({ dock }),
      });
      if (!response.ok) showToast("Could not save the dock.", "warning");
    } catch {
      showToast("Could not save the dock: network error.", "error");
    }
  }
}

/** A dock button drawn from a grid tile: same link, name and coloured icon. */
export function dockButtonFromTile(tile: HTMLElement): HTMLAnchorElement {
  const button = document.createElement("a");
  const name =
    tile.querySelector(".launcher-tile-name")?.textContent?.trim() ||
    tile.dataset.label ||
    "";
  const href = tile.getAttribute("href");
  if (href) button.href = href;
  button.className = "site-dock-item site-dock-app";
  button.dataset.dockItem = tile.dataset.module || "";
  button.draggable = false;
  button.setAttribute("aria-label", name);
  button.title = name;
  const icon = document.createElement("span");
  icon.className = "launcher-tile-icon site-dock-app-icon";
  icon.dataset.tileCategory = tile.dataset.category || "other";
  icon.setAttribute("aria-hidden", "true");
  const glyph = tile.querySelector(".launcher-tile-icon > i")?.cloneNode(false);
  if (glyph) icon.appendChild(glyph);
  button.appendChild(icon);
  const label = document.createElement("span");
  label.className = "site-dock-app-label";
  label.setAttribute("aria-hidden", "true");
  label.textContent = name;
  button.appendChild(label);
  return button;
}
