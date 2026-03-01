/**
 * Repository Monitor Feed Renderer
 * DOM component for displaying real-time file change entries
 */

import type { FsEvent } from "./types.ts";

const MAX_ENTRIES = 500;
const DEBOUNCE_WINDOW_MS = 500;
const STATUS_BADGE_ID = "repo-monitor-status";

type EventIconMap = Record<FsEvent["event"], string>;

const EVENT_ICONS: EventIconMap = {
  create: "fa-plus",
  modify: "fa-pen",
  delete: "fa-minus",
  move: "fa-arrow-right",
};

export class RepoMonitorFeed {
  private container: HTMLElement;
  private statusBadge: HTMLElement | null;
  // Track last modify time per path for debouncing
  private lastModifyTime: Map<string, number> = new Map();

  constructor(container: HTMLElement) {
    this.container = container;
    this.statusBadge = document.getElementById(STATUS_BADGE_ID);
    this.container.addEventListener("click", this.handleEntryClick.bind(this));
  }

  addEvent(event: FsEvent): void {
    const now = Date.now();

    // Debounce rapid modify events for same path
    if (event.event === "modify") {
      const lastTime = this.lastModifyTime.get(event.path);
      if (lastTime && now - lastTime < DEBOUNCE_WINDOW_MS) {
        this.updateExistingEntry(event);
        this.lastModifyTime.set(event.path, now);
        return;
      }
      this.lastModifyTime.set(event.path, now);
    }

    const entry = this.buildEntry(event);
    const wasAtTop = this.container.scrollTop === 0;

    this.container.prepend(entry);
    this.trimEntries();

    if (wasAtTop) {
      this.container.scrollTop = 0;
    }

    this.updateStatusBadge();
  }

  private buildEntry(event: FsEvent): HTMLElement {
    const div = document.createElement("div");
    div.className = `repo-monitor-entry rm-${event.event}`;
    div.dataset.path = event.path;
    div.dataset.event = event.event;

    const timeSpan = document.createElement("span");
    timeSpan.className = "rm-time";
    timeSpan.textContent = this.formatTimestamp(event.timestamp);

    const iconSpan = document.createElement("span");
    iconSpan.className = "rm-icon";
    iconSpan.innerHTML = `<i class="fas ${EVENT_ICONS[event.event]}"></i>`;

    const pathSpan = document.createElement("span");
    pathSpan.className = "rm-path";
    pathSpan.title = event.path;
    pathSpan.textContent = event.path;

    div.appendChild(timeSpan);
    div.appendChild(iconSpan);
    div.appendChild(pathSpan);

    return div;
  }

  private updateExistingEntry(event: FsEvent): void {
    const existing = this.container.querySelector<HTMLElement>(
      `.repo-monitor-entry[data-path="${CSS.escape(event.path)}"]`,
    );
    if (!existing) {
      const entry = this.buildEntry(event);
      this.container.prepend(entry);
      this.trimEntries();
      this.updateStatusBadge();
      return;
    }

    // Update timestamp on existing entry
    const timeSpan = existing.querySelector<HTMLElement>(".rm-time");
    if (timeSpan) {
      timeSpan.textContent = this.formatTimestamp(event.timestamp);
    }

    // Move to top
    this.container.prepend(existing);
  }

  private trimEntries(): void {
    const entries = this.container.querySelectorAll(".repo-monitor-entry");
    if (entries.length > MAX_ENTRIES) {
      for (let i = MAX_ENTRIES; i < entries.length; i++) {
        entries[i].remove();
      }
    }
  }

  private formatTimestamp(ts: string): string {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString(undefined, { hour12: false });
    } catch {
      return ts;
    }
  }

  private handleEntryClick(e: Event): void {
    const target = e.target as HTMLElement;
    const entry = target.closest<HTMLElement>(".repo-monitor-entry");
    if (!entry) return;

    const path = entry.dataset.path;
    if (!path) return;

    document.dispatchEvent(
      new CustomEvent("repo-monitor:file-select", { detail: { path } }),
    );
  }

  private updateStatusBadge(): void {
    if (!this.statusBadge) return;
    const count = this.getEntryCount();
    this.statusBadge.textContent = String(count);
  }

  clear(): void {
    this.container.innerHTML = "";
    this.lastModifyTime.clear();
    this.updateStatusBadge();
  }

  getEntryCount(): number {
    return this.container.querySelectorAll(".repo-monitor-entry").length;
  }
}
