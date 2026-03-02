/**
 * TabManager - Single-file tracker for the shared workspace viewer.
 *
 * Displays the current filename with a close button. No multi-tab support.
 * Opening a new file replaces the current one.
 */

import type { TabInfo } from "./types";

interface TabManagerConfig {
  container: HTMLElement;
  storageKey: string;
  onSwitch: (path: string) => void;
  onClose: (path: string) => void;
}

export class TabManager {
  private currentFile: TabInfo | null = null;
  private container: HTMLElement;
  private storageKey: string;
  private onSwitch: (path: string) => void;
  private onClose: (path: string) => void;

  constructor(config: TabManagerConfig) {
    this.container = config.container;
    this.storageKey = config.storageKey;
    this.onSwitch = config.onSwitch;
    this.onClose = config.onClose;
  }

  /** Open a file, replacing the current one. */
  openTab(info: TabInfo): void {
    this.currentFile = info;
    this.render();
    this.saveState();
    this.onSwitch(info.path);
  }

  /** Close the current file and show empty state. */
  closeTab(path: string): void {
    if (!this.currentFile || this.currentFile.path !== path) return;
    const closedPath = this.currentFile.path;
    this.currentFile = null;
    this.render();
    this.saveState();
    this.onClose(closedPath);
  }

  /** Switch — with a single file, only fires if the path matches. */
  switchTab(path: string): void {
    if (!this.currentFile || this.currentFile.path !== path) return;
    this.onSwitch(path);
  }

  getActiveTab(): string | null {
    return this.currentFile?.path ?? null;
  }

  /** Render the current filename label (or nothing if empty). */
  render(): void {
    this.container.innerHTML = "";
    if (!this.currentFile) return;

    const label = document.createElement("span");
    label.className = "ws-viewer-current-file";
    label.textContent =
      this.currentFile.title ||
      this.currentFile.path.split("/").pop() ||
      this.currentFile.path;
    label.title = this.currentFile.path;
    this.container.appendChild(label);

    const closeBtn = document.createElement("span");
    closeBtn.className = "ws-viewer-file-close";
    closeBtn.innerHTML = "&times;";
    closeBtn.title = "Close file";
    closeBtn.addEventListener("click", () =>
      this.closeTab(this.currentFile!.path),
    );
    this.container.appendChild(closeBtn);
  }

  saveState(): void {
    localStorage.setItem(
      this.storageKey,
      JSON.stringify({ file: this.currentFile }),
    );
  }

  restoreState(): TabInfo[] | null {
    try {
      const raw = localStorage.getItem(this.storageKey);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      // Legacy format (tabs array)
      if (Array.isArray(parsed.tabs)) return parsed.tabs as TabInfo[];
      // New format (single file)
      if (parsed.file) return [parsed.file] as TabInfo[];
      return null;
    } catch {
      return null;
    }
  }
}
