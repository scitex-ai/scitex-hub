/**
 * Repository Monitor - Orchestrator
 * Wires together client, feed, filter, and resizer components
 *
 * Usage:
 * ```typescript
 * import { initRepoMonitor } from '@shared/components/repo-monitor';
 *
 * initRepoMonitor({
 *   projectId: "42",
 *   username: "test-user",
 *   slug: "my-project",
 * });
 * ```
 */

import { RepoMonitorClient } from "./_RepoMonitorClient";
import { RepoMonitorFeed } from "./_RepoMonitorFeed";
import { RepoMonitorFilter } from "./_RepoMonitorFilter";
import type { MonitorConfig } from "./types";

const STORAGE_KEY = "repo-monitor-collapsed";
let toggleInitialized = false;

/**
 * Initialize the monitor header toggle (collapse/expand + localStorage).
 * Always safe to call — works even without a project context.
 * Idempotent: multiple calls are harmless.
 */
export function initMonitorToggle(): void {
  if (toggleInitialized) return;

  const monitorArea = document.getElementById("ws-repo-monitor");
  const headerEl = document.getElementById("repo-monitor-header");
  if (!monitorArea || !headerEl) return;

  toggleInitialized = true;

  // Restore persisted state
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === "false") {
    monitorArea.classList.remove("collapsed");
  }

  // Header click toggles collapse (toolbar buttons handled independently)
  headerEl.addEventListener("click", (e) => {
    if ((e.target as HTMLElement).closest(".repo-monitor-toolbar")) return;
    monitorArea.classList.toggle("collapsed");
    const isCollapsed = monitorArea.classList.contains("collapsed");
    localStorage.setItem(STORAGE_KEY, String(isCollapsed));

    // Notify resizer and client if they exist
    window.dispatchEvent(
      new CustomEvent("repo-monitor:toggle", {
        detail: { collapsed: isCollapsed },
      }),
    );
  });
}

/**
 * Initialize the full repo monitor (WebSocket client, feed, filter, resizer).
 * Requires a project context — call initMonitorToggle() first.
 */
export function initRepoMonitor(
  config: MonitorConfig,
): RepoMonitorClient | null {
  const feedContainer = document.getElementById("repo-monitor-feed");
  const monitorArea = document.getElementById("ws-repo-monitor");

  if (!feedContainer || !monitorArea) {
    console.warn("[RepoMonitor] Missing required DOM elements — init skipped");
    return null;
  }

  // Vertical resizer is now auto-initialized by the unified resizer system
  // via data-v-resizer attribute on #repo-monitor-resizer

  const client = new RepoMonitorClient(config.projectId);
  const feed = new RepoMonitorFeed(feedContainer);
  const filter = new RepoMonitorFilter(feed);

  // Wire events
  client.onEvent((event) => feed.addEvent(event));
  filter.onFilterChange((filters) => client.reconfigure(filters));

  // Listen for toggle events from initMonitorToggle
  window.addEventListener("repo-monitor:toggle", ((e: CustomEvent) => {
    if (e.detail.collapsed) {
      client.pause();
    } else {
      client.resume();
    }
  }) as EventListener);

  // Connect and initialize
  client.connect();
  filter.init();

  return client;
}

// Named re-exports for consumers that need individual classes
export { RepoMonitorClient } from "./_RepoMonitorClient";
export { RepoMonitorFeed } from "./_RepoMonitorFeed";
export { RepoMonitorFilter } from "./_RepoMonitorFilter";
export type { FsEvent, FilterConfig, MonitorConfig } from "./types";
