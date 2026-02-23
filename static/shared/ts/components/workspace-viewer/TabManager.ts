/**
 * TabManager - Simplified tab manager for the shared workspace viewer.
 *
 * Differences from console_app FileTabManager:
 * - No scratch buffer support
 * - No FileCreationHelper dependency
 * - No ModalManager dependency
 * - No inline rename
 * Keeps: localStorage persistence, drag-and-drop reorder, tab switching.
 */

import type { TabInfo } from "./types.ts";

interface TabManagerConfig {
  container: HTMLElement;
  storageKey: string;
  onSwitch: (path: string) => void;
  onClose: (path: string) => void;
}

export class TabManager {
  private tabs: Map<string, TabInfo> = new Map();
  private activeTab: string | null = null;
  private container: HTMLElement;
  private storageKey: string;
  private onSwitch: (path: string) => void;
  private onClose: (path: string) => void;
  private draggedPath: string | null = null;

  constructor(config: TabManagerConfig) {
    this.container = config.container;
    this.storageKey = config.storageKey;
    this.onSwitch = config.onSwitch;
    this.onClose = config.onClose;
  }

  /** Add a tab if not already open, then switch to it. */
  openTab(info: TabInfo): void {
    if (!this.tabs.has(info.path)) {
      this.tabs.set(info.path, info);
    }
    this.switchTab(info.path);
  }

  /** Remove a tab and switch to an adjacent one if needed. */
  closeTab(path: string): void {
    if (!this.tabs.has(path)) return;

    const keys = Array.from(this.tabs.keys());
    const idx = keys.indexOf(path);

    this.tabs.delete(path);

    if (this.activeTab === path) {
      const remaining = Array.from(this.tabs.keys());
      const nextKey = remaining[Math.min(idx, remaining.length - 1)] ?? null;
      this.activeTab = nextKey;
      if (nextKey) {
        this.onSwitch(nextKey);
      }
    }

    this.render();
    this.saveState();
    this.onClose(path);
  }

  /** Activate a tab and update the UI. */
  switchTab(path: string): void {
    if (!this.tabs.has(path)) return;
    this.activeTab = path;
    this.render();
    this.saveState();
    this.onSwitch(path);
  }

  getActiveTab(): string | null {
    return this.activeTab;
  }

  /** Rebuild the tab bar from the current tabs map. */
  render(): void {
    this.container.innerHTML = "";

    this.tabs.forEach((info, path) => {
      const tab = this.createTabElement(path, info);
      this.container.appendChild(tab);
    });
  }

  saveState(): void {
    const state = Array.from(this.tabs.values());
    localStorage.setItem(
      this.storageKey,
      JSON.stringify({ tabs: state, active: this.activeTab }),
    );
  }

  restoreState(): TabInfo[] | null {
    try {
      const raw = localStorage.getItem(this.storageKey);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed.tabs)) return null;
      return parsed.tabs as TabInfo[];
    } catch {
      return null;
    }
  }

  // --- Private helpers ---

  private createTabElement(path: string, info: TabInfo): HTMLElement {
    const isActive = path === this.activeTab;

    const tab = document.createElement("div");
    tab.className = `ws-viewer-tab${isActive ? " active" : ""}`;
    tab.dataset.path = path;
    tab.title = path;

    const nameSpan = document.createElement("span");
    nameSpan.className = "ws-viewer-tab-name";
    nameSpan.textContent = info.title || path.split("/").pop() || path;
    tab.appendChild(nameSpan);

    const closeBtn = document.createElement("span");
    closeBtn.className = "ws-viewer-tab-close";
    closeBtn.innerHTML = "&times;";
    closeBtn.title = "Close";
    closeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.closeTab(path);
    });
    tab.appendChild(closeBtn);

    tab.addEventListener("click", () => this.switchTab(path));

    this.setupDragDrop(tab, path);

    return tab;
  }

  private setupDragDrop(tab: HTMLElement, path: string): void {
    tab.draggable = true;

    tab.addEventListener("dragstart", (e) => {
      this.draggedPath = path;
      tab.classList.add("dragging");
      if (e.dataTransfer) {
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", path);
      }
    });

    tab.addEventListener("dragend", () => {
      this.draggedPath = null;
      tab.classList.remove("dragging");
      this.container
        .querySelectorAll(".ws-viewer-tab")
        .forEach((t) => t.classList.remove("drag-over"));
    });

    tab.addEventListener("dragover", (e) => {
      e.preventDefault();
      if (this.draggedPath && this.draggedPath !== path) {
        tab.classList.add("drag-over");
      }
    });

    tab.addEventListener("dragleave", () => tab.classList.remove("drag-over"));

    tab.addEventListener("drop", (e) => {
      e.preventDefault();
      tab.classList.remove("drag-over");
      if (this.draggedPath && this.draggedPath !== path) {
        this.reorderTabs(this.draggedPath, path);
      }
    });
  }

  private reorderTabs(draggedPath: string, targetPath: string): void {
    const entries = Array.from(this.tabs.entries());
    const fromIdx = entries.findIndex(([p]) => p === draggedPath);
    const toIdx = entries.findIndex(([p]) => p === targetPath);
    if (fromIdx === -1 || toIdx === -1) return;

    const [dragged] = entries.splice(fromIdx, 1);
    const insertIdx = fromIdx < toIdx ? toIdx - 1 : toIdx;
    entries.splice(insertIdx, 0, dragged);

    this.tabs.clear();
    entries.forEach(([p, info]) => this.tabs.set(p, info));

    this.render();
    this.saveState();
  }
}
